"""Action safety checks."""

from __future__ import annotations

from stoat.core.intent_schema import Intent


class SafetyValidator:
    """Decides whether a command requires user confirmation."""

    def __init__(self, required_confirmations: set[str] | None = None) -> None:
        self._required_confirmations = required_confirmations or {"delete", "move", "undo"}

    def requires_confirmation(self, intent: Intent) -> bool:
        return intent.requires_confirmation or intent.action.value in self._required_confirmations
