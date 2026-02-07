"""User confirmation utilities."""

from collections.abc import Callable


class ConfirmationPrompt:
    """Prompts for explicit confirmation before risky actions."""

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        self._input = input_func

    def ask(self, prompt: str) -> bool:
        """Return True when the user confirms an action."""
        response = self._input(f"{prompt} [y/N]: ").strip().lower()
        return response in {"y", "yes"}
