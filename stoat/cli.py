"""Main CLI interface."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from stoat import __version__
from stoat.config import Config
from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.core.nlp_engine import NLPEngine
from stoat.core.router import CommandRouter
from stoat.handlers.app_management import AppManagementHandler
from stoat.handlers.file_operations import FileOperationsHandler
from stoat.handlers.search import SearchHandler
from stoat.integrations.file_system import FileSystem
from stoat.integrations.search_engine import SearchEngine
from stoat.integrations.trash_manager import TrashManager
from stoat.safety.confirmation import ConfirmationPrompt
from stoat.safety.permissions import PermissionGuard
from stoat.safety.validator import SafetyValidator
from stoat.utils.undo_stack import UndoStack

console = Console()


def _resolve_skip_confirmations(yes: bool) -> bool:
    """Handle CLI parser edge-cases where boolean flags may degrade."""
    return yes or any(arg in {"--yes", "-y"} for arg in sys.argv[1:])


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
        undo_stack=UndoStack(undo_path, max_history=config.undo.max_history),
        permission_guard=PermissionGuard(config.safety.protected_paths),
        max_batch_size=config.safety.max_batch_size,
        enable_undo=config.safety.enable_undo,
    )
    return CommandRouter(
        handlers=[
            AppManagementHandler(),
            SearchHandler(search_engine=search_engine, file_system=file_system),
            file_handler,
        ]
    )


def _build_parser(config: Config) -> NLPEngine:
    return NLPEngine(
        model=config.llm.model,
        temperature=config.llm.temperature,
        confidence_threshold=0.7,
        enable_llm_fallback=True,
    )


def _emit_result(success: bool, message: str, details: dict, json_output: bool) -> None:
    if json_output:
        click.echo(json.dumps({"success": success, "message": message, "details": details}))
        return

    style = "bold green" if success else "bold red"
    console.print(f"[{style}]{message}[/{style}]")


def _execute_intent(
    intent: Intent,
    *,
    context: ExecutionContext,
    router: CommandRouter,
    safety: SafetyValidator,
    json_output: bool,
) -> int:
    if intent.action == IntentAction.UNKNOWN:
        _emit_result(
            False,
            'I could not map that request yet. Try: `stoat run "open firefox"`.',
            {"action": intent.action.value},
            json_output,
        )
        return 1

    if safety.requires_confirmation(intent) and not context.skip_confirmations:
        confirmer = ConfirmationPrompt()
        confirmed = confirmer.ask(f"Confirm '{intent.action.value}' for '{intent.target}'?")
        if not confirmed:
            _emit_result(False, "Action cancelled.", {"action": intent.action.value}, json_output)
            return 1
        context = context.with_confirmation()

    result = router.route(intent, context)
    _emit_result(result.success, result.message, result.details, json_output)
    return 0 if result.success else 1


@click.group(help="Safe local Linux operations engine.")
def app() -> None:
    """Stoat CLI entrypoint."""


@app.command()
@click.argument("message")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmations.")
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def run(message: str, yes: bool, json_output: bool) -> None:
    """Execute a natural-language command."""
    config = Config.load()
    context = ExecutionContext.from_runtime(
        skip_confirmations=_resolve_skip_confirmations(yes=bool(yes))
    )
    parser = _build_parser(config)
    router = _build_router(config)
    safety = SafetyValidator(required_confirmations=set(config.safety.require_confirmation))

    try:
        intent = parser.parse(message)
    except Exception as exc:
        _emit_result(False, f"Failed to parse command: {exc}", {"action": "parse"}, json_output)
        raise SystemExit(1)

    raise SystemExit(
        _execute_intent(
            intent, context=context, router=router, safety=safety, json_output=json_output
        )
    )


@app.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmations.")
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON.")
def undo(yes: bool, json_output: bool) -> None:
    """Undo the last Stoat-managed reversible operation."""
    config = Config.load()
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
    raise SystemExit(
        _execute_intent(
            intent, context=context, router=router, safety=safety, json_output=json_output
        )
    )


@app.command()
def configure() -> None:
    """Open configuration wizard."""
    console.print("[yellow]Configuration wizard coming soon...[/yellow]")


@app.command()
def history() -> None:
    """View operation history."""
    console.print("[yellow]History viewer coming soon...[/yellow]")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]Stoat v{__version__}[/bold] - Safe local Linux operations engine")


if __name__ == "__main__":
    app()
