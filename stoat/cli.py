"""Main CLI interface."""

import importlib.util
import json
import logging
import platform
import sys
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console

from stoat import __version__
from stoat.config import Config
from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.core.nlp_engine import NLPEngine
from stoat.core.router import CommandRouter
from stoat.errors import ErrorCode
from stoat.handlers.app_management import AppManagementHandler
from stoat.handlers.file_operations import FileOperationsHandler
from stoat.handlers.search import SearchHandler
from stoat.handlers.system_info import SystemInfoHandler
from stoat.integrations.file_system import FileSystem
from stoat.integrations.search_engine import SearchEngine
from stoat.integrations.system_info import SystemInfoIntegration
from stoat.integrations.trash_manager import TrashManager
from stoat.observability import configure_logging, log_event
from stoat.safety.confirmation import ConfirmationPrompt
from stoat.safety.permissions import PermissionGuard
from stoat.safety.validator import SafetyValidator
from stoat.utils.undo_stack import UndoStack

console = Console()


def _resolve_skip_confirmations(yes: bool) -> bool:
    """Handle CLI parser edge-cases where boolean flags may degrade."""
    return yes or any(arg in {"--yes", "-y"} for arg in sys.argv[1:])


def _build_undo_stack(config: Config) -> UndoStack:
    undo_path = Path(config.undo.storage_path)
    return UndoStack(undo_path, max_history=config.undo.max_history)


def _build_router(config: Config) -> CommandRouter:
    search_engine = SearchEngine(
        index_hidden_files=config.search.index_hidden_files,
        max_results=config.search.max_results,
    )
    file_system = FileSystem(search_engine=search_engine)
    undo_path = Path(config.undo.storage_path)
    file_handler = FileOperationsHandler(
        file_system=file_system,
        trash_manager=TrashManager(undo_path),
        undo_stack=_build_undo_stack(config),
        permission_guard=PermissionGuard(config.safety.protected_paths),
        max_batch_size=config.safety.max_batch_size,
        enable_undo=config.safety.enable_undo,
    )
    return CommandRouter(
        handlers=[
            AppManagementHandler(),
            SearchHandler(search_engine=search_engine, file_system=file_system),
            SystemInfoHandler(integration=SystemInfoIntegration()),
            file_handler,
        ]
    )


def _build_parser(config: Config) -> NLPEngine:
    return NLPEngine(
        model=config.llm.model,
        temperature=config.llm.temperature,
        confidence_threshold=config.parser.confidence_threshold,
        enable_llm_fallback=config.parser.mode == "hybrid",
        parser_mode=config.parser.mode,
    )


def _load_config_or_exit(*, json_output: bool, command: str) -> Config:
    config_path = Config.resolve_path()
    try:
        return Config.load(config_path)
    except (ValidationError, ValueError) as exc:
        _emit_result(
            False,
            f"Invalid configuration: {exc}",
            {
                "action": "config",
                "error_code": ErrorCode.CONFIG_ERROR.value,
                "config_path": str(config_path),
            },
            json_output,
            command=command,
            action="config",
        )
        raise SystemExit(1)


def _build_json_response(
    success: bool,
    message: str,
    details: dict,
    *,
    command: str,
    action: str | None,
    dry_run: bool,
) -> dict:
    error_code = details.get("error_code")
    payload_details = {
        key: value
        for key, value in details.items()
        if key not in {"action", "error_code", "dry_run"}
    }
    return {
        "ok": success,
        "command": command,
        "action": action,
        "dry_run": dry_run,
        "message": message,
        "data": payload_details if success else None,
        "error": (
            None
            if success
            else {
                "code": error_code or "command_failed",
                "details": payload_details or None,
            }
        ),
    }


def _emit_result(
    success: bool,
    message: str,
    details: dict,
    json_output: bool,
    *,
    command: str,
    action: str | None = None,
    dry_run: bool = False,
) -> None:
    if json_output:
        response = _build_json_response(
            success,
            message,
            details,
            command=command,
            action=action or details.get("action"),
            dry_run=dry_run or bool(details.get("dry_run")),
        )
        click.echo(json.dumps(response, indent=2))
        return

    style = "bold green" if success else "bold red"
    console.print(f"[{style}]{message}[/{style}]")


def _path_probe(path: Path, *, directory: bool) -> dict[str, bool | str]:
    """Probe whether a file or directory path looks usable for Stoat runtime state."""
    target = path if directory else path.parent
    try:
        target.mkdir(parents=True, exist_ok=True)
        if directory:
            writable = target.is_dir() and target.exists()
        else:
            probe = path
            with probe.open("a", encoding="utf-8"):
                pass
            writable = probe.exists()
    except OSError:
        writable = False

    return {
        "path": str(path),
        "exists": path.exists(),
        "writable": writable,
    }


def _collect_doctor_warnings(diagnostics: dict[str, bool | str]) -> list[str]:
    """Collect user-facing runtime warnings from doctor diagnostics."""
    warnings: list[str] = []
    if not diagnostics["config_exists"]:
        warnings.append("Config file does not exist; Stoat is using defaults.")
    if not diagnostics["log_path_writable"]:
        warnings.append("Log path is not writable; structured logs may be dropped.")
    if not diagnostics["undo_path_writable"]:
        warnings.append("Undo path is not writable; undo/history reliability may degrade.")
    return warnings


def _build_doctor_diagnostics(config: Config) -> dict[str, bool | str]:
    config_path = Config.resolve_path()
    log_path = Path(config.logging.file).expanduser()
    undo_path = Path(config.undo.storage_path).expanduser()

    diagnostics = {
        "config_valid": True,
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
        "llm_backend_available": importlib.util.find_spec("ollama") is not None,
    }
    diagnostics.update(
        {
            "log_path": str(log_path),
            "log_directory_exists": log_path.parent.exists(),
            "log_path_writable": bool(_path_probe(log_path, directory=False)["writable"]),
            "undo_path": str(undo_path),
            "undo_directory_exists": undo_path.exists() or undo_path.parent.exists(),
            "undo_path_writable": bool(_path_probe(undo_path, directory=True)["writable"]),
        }
    )
    warnings = _collect_doctor_warnings(diagnostics)
    diagnostics["status"] = "warning" if warnings else "ok"
    diagnostics["warnings"] = warnings
    return diagnostics


def _render_doctor_summary(diagnostics: dict[str, bool | str]) -> None:
    """Print a readable text-mode diagnostics summary."""
    status_style = "bold yellow" if diagnostics["status"] == "warning" else "bold green"
    console.print(f"[{status_style}]Stoat doctor summary[/{status_style}]")
    console.print(f"Status: {diagnostics['status']}")
    console.print(f"Config path: {diagnostics['config_path']}")
    console.print(f"Config exists: {diagnostics['config_exists']}")
    console.print(f"Platform: {diagnostics['platform']}")
    console.print(f"Python: {diagnostics['python_version']}")
    console.print(f"Log path: {diagnostics['log_path']}")
    console.print(f"Log writable: {diagnostics['log_path_writable']}")
    console.print(f"Undo path: {diagnostics['undo_path']}")
    console.print(f"Undo writable: {diagnostics['undo_path_writable']}")
    console.print(f"Ollama available: {diagnostics['llm_backend_available']}")
    warnings = diagnostics.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"- {warning}")


def _summarize_confirmation(intent: Intent, context: ExecutionContext) -> str:
    if intent.action in {IntentAction.MOVE, IntentAction.COPY}:
        source = intent.source or str(context.cwd)
        destination = intent.destination or str(context.cwd)
        return (
            f"Confirm {intent.action.value} of '{intent.target}' "
            f"from '{source}' to '{destination}'?"
        )

    if intent.action == IntentAction.DELETE:
        source = intent.source or str(context.cwd)
        return f"Confirm delete of '{intent.target}' from '{source}'?"

    if intent.action == IntentAction.UNDO:
        return "Confirm undo of the last Stoat-managed operation?"

    return f"Confirm '{intent.action.value}' for '{intent.target}'?"


def _execute_intent(
    intent: Intent,
    *,
    context: ExecutionContext,
    router: CommandRouter,
    safety: SafetyValidator,
    logger: logging.Logger,
    json_output: bool,
    command: str,
) -> int:
    if intent.action == IntentAction.UNKNOWN:
        log_event(
            logger,
            "intent.unknown",
            command=command,
            raw_text=intent.raw_text,
        )
        _emit_result(
            False,
            'I could not map that request yet. Try: `stoat run "open firefox"`.',
            {"action": intent.action.value, "error_code": ErrorCode.UNKNOWN_INTENT.value},
            json_output,
            command=command,
            action=intent.action.value,
            dry_run=context.dry_run,
        )
        return 1

    if safety.requires_confirmation(intent) and not (context.skip_confirmations or context.dry_run):
        log_event(
            logger,
            "confirmation.requested",
            command=command,
            action=intent.action.value,
            summary=_summarize_confirmation(intent, context),
        )
        confirmer = ConfirmationPrompt()
        confirmed = confirmer.ask(_summarize_confirmation(intent, context))
        if not confirmed:
            log_event(
                logger,
                "confirmation.cancelled",
                command=command,
                action=intent.action.value,
            )
            _emit_result(
                False,
                "Action cancelled.",
                {"action": intent.action.value, "error_code": ErrorCode.CANCELLED.value},
                json_output,
                command=command,
                action=intent.action.value,
                dry_run=context.dry_run,
            )
            return 1
        log_event(logger, "confirmation.accepted", command=command, action=intent.action.value)
        context = context.with_confirmation()

    result = router.route(intent, context)
    log_event(
        logger,
        "execution.result",
        command=command,
        action=intent.action.value,
        success=result.success,
        error_code=result.details.get("error_code"),
    )
    _emit_result(
        result.success,
        result.message,
        result.details,
        json_output,
        command=command,
        action=intent.action.value,
        dry_run=context.dry_run,
    )
    return 0 if result.success else 1


@click.group(help="Safe local Linux operations engine.")
def app() -> None:
    """Stoat CLI entrypoint."""


@app.command()
@click.argument("message")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmations.")
@click.option("--dry-run", is_flag=True, help="Preview file changes without modifying anything.")
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def run(message: str, yes: bool, dry_run: bool, json_output: bool) -> None:
    """Execute a natural-language command."""
    config = _load_config_or_exit(json_output=json_output, command="run")
    logger = configure_logging(config.logging)
    context = ExecutionContext.from_runtime(
        skip_confirmations=_resolve_skip_confirmations(yes=bool(yes)),
        dry_run=dry_run,
    )
    parser = _build_parser(config)
    router = _build_router(config)
    safety = SafetyValidator(required_confirmations=set(config.safety.require_confirmation))
    log_event(
        logger,
        "cli.run.start",
        command="run",
        raw_text=message,
        dry_run=dry_run,
        skip_confirmations=context.skip_confirmations,
    )

    try:
        intent = parser.parse(message)
    except Exception as exc:
        log_event(logger, "parser.failure", command="run", raw_text=message, error=str(exc))
        _emit_result(
            False,
            f"Failed to parse command: {exc}",
            {"action": "parse", "error_code": ErrorCode.PARSE_ERROR.value},
            json_output,
            command="run",
            action="parse",
            dry_run=dry_run,
        )
        raise SystemExit(1)

    log_event(
        logger,
        "parser.success",
        command="run",
        action=intent.action.value,
        summary=intent.to_summary(),
    )
    exit_code = _execute_intent(
        intent,
        context=context,
        router=router,
        safety=safety,
        logger=logger,
        json_output=json_output,
        command="run",
    )
    log_event(
        logger,
        "cli.run.complete",
        command="run",
        action=intent.action.value,
        exit_code=exit_code,
        dry_run=context.dry_run,
    )
    raise SystemExit(exit_code)


@app.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmations.")
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def undo(yes: bool, json_output: bool) -> None:
    """Undo the last Stoat-managed reversible operation."""
    config = _load_config_or_exit(json_output=json_output, command="undo")
    logger = configure_logging(config.logging)
    context = ExecutionContext.from_runtime(
        skip_confirmations=_resolve_skip_confirmations(yes=bool(yes))
    )
    router = _build_router(config)
    safety = SafetyValidator(required_confirmations=set(config.safety.require_confirmation))
    intent = Intent(
        action=IntentAction.UNDO,
        target_type=TargetType.FILE,
        target="last_operation",
        requires_confirmation=True,
        confidence=1.0,
        raw_text="undo",
    )
    log_event(
        logger, "cli.undo.start", command="undo", skip_confirmations=context.skip_confirmations
    )
    exit_code = _execute_intent(
        intent,
        context=context,
        router=router,
        safety=safety,
        logger=logger,
        json_output=json_output,
        command="undo",
    )
    log_event(logger, "cli.undo.complete", command="undo", exit_code=exit_code)
    raise SystemExit(exit_code)


@app.command()
def configure() -> None:
    """Open configuration wizard."""
    console.print("[yellow]Configuration wizard coming soon...[/yellow]")


@app.command()
@click.option("--limit", default=10, show_default=True, type=int, help="Maximum entries to show.")
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def history(limit: int, json_output: bool) -> None:
    """View operation history."""
    config = _load_config_or_exit(json_output=json_output, command="history")
    logger = configure_logging(config.logging)
    undo_stack = _build_undo_stack(config)
    operations = undo_stack.list_recent(
        limit=max(limit, 0),
        retention_days=config.undo.retention_days,
    )
    log_event(logger, "cli.history.loaded", command="history", limit=limit, count=len(operations))
    details = {
        "count": len(operations),
        "operations": [
            {
                "operation_id": operation.operation_id,
                "action": operation.action,
                "created_at": operation.created_at,
                "item_count": len(operation.items),
                "items": operation.items,
            }
            for operation in operations
        ],
    }

    if json_output:
        _emit_result(
            True,
            "History loaded.",
            details,
            json_output=True,
            command="history",
            action="history",
        )
        return

    if not operations:
        console.print("[yellow]No Stoat history found.[/yellow]")
        return

    console.print("[bold green]Recent Stoat history:[/bold green]")
    console.print(
        "\n".join(
            f"- {operation.created_at} | {operation.action} | {len(operation.items)} item(s)"
            for operation in operations
        )
    )


@app.command()
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def doctor(json_output: bool) -> None:
    """Run basic runtime diagnostics."""
    config = _load_config_or_exit(json_output=json_output, command="doctor")
    logger = configure_logging(config.logging)
    diagnostics = _build_doctor_diagnostics(config)
    log_event(logger, "cli.doctor.complete", command="doctor", **diagnostics)
    if json_output:
        _emit_result(
            True,
            "Diagnostics loaded.",
            diagnostics,
            json_output,
            command="doctor",
            action="doctor",
        )
        return

    _render_doctor_summary(diagnostics)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]Stoat v{__version__}[/bold] - Safe local Linux operations engine")


if __name__ == "__main__":
    app()
