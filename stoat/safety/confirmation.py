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


class SelectionPrompt:
    """Prompts the user to choose one option from a numbered list."""

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        self._input = input_func

    def choose(self, prompt: str, options: list[str]) -> str | None:
        """Return the selected option value or None when cancelled/invalid."""
        if not options:
            return None
        for index, option in enumerate(options, start=1):
            print(f"{index}. {option}")
        response = self._input(f"{prompt} [1-{len(options)} or Enter to cancel]: ").strip()
        if not response:
            return None
        if not response.isdigit():
            return None
        choice = int(response)
        if choice < 1 or choice > len(options):
            return None
        return options[choice - 1]
