"""Main CLI interface."""

import sys

import typer
from rich.console import Console

from stoat import __version__
from stoat.config import Config
from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import IntentAction
from stoat.core.nlp_engine import NLPEngine
from stoat.core.router import CommandRouter
from stoat.handlers.app_management import AppManagementHandler
from stoat.safety.confirmation import ConfirmationPrompt
from stoat.safety.validator import SafetyValidator

app = typer.Typer(
    name="stoat",
    help="Offline AI assistant for Linux - smart, quick, local",
    add_completion=True,
)
console = Console()


def _resolve_skip_confirmations(yes: bool) -> bool:
    """Handle CLI parser edge-cases where boolean flags may degrade."""
    return yes or any(arg in {"--yes", "-y"} for arg in sys.argv[1:])


@app.command()
def run(
    message: str = typer.Argument(..., help="Your command or question"),
    yes: bool = typer.Option(False, "--yes", "-y", is_flag=True, help="Skip confirmations"),
) -> None:
    """Execute a natural language command."""
    config = Config.load()
    context = ExecutionContext.from_runtime(
        skip_confirmations=_resolve_skip_confirmations(yes=bool(yes))
    )
    parser = NLPEngine()
    router = CommandRouter(handlers=[AppManagementHandler()])
    safety = SafetyValidator(required_confirmations=set(config.safety.require_confirmation))

    console.print(f"[bold blue]Stoat:[/bold blue] Processing '{message}'")
    intent = parser.parse(message)

    if intent.action == IntentAction.UNKNOWN:
        console.print(
            "[yellow]I could not map that request yet.[/yellow] "
            "Try: `stoat run \"open firefox\"` or `stoat run \"close firefox\"`."
        )
        raise typer.Exit(code=1)

    if safety.requires_confirmation(intent) and not context.skip_confirmations:
        confirmer = ConfirmationPrompt()
        confirmed = confirmer.ask(f"Confirm action '{intent.action.value}' on '{intent.target}'?")
        if not confirmed:
            console.print("[yellow]Action cancelled.[/yellow]")
            raise typer.Exit(code=1)

    result = router.route(intent, context)
    if result.success:
        console.print(f"[bold green]{result.message}[/bold green]")
        raise typer.Exit(code=0)

    console.print(f"[bold red]{result.message}[/bold red]")
    raise typer.Exit(code=1)


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
    console.print(f"[bold]Stoat v{__version__}[/bold] - Offline AI Assistant for Linux")


if __name__ == "__main__":
    app()
