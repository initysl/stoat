"""Action safety checks."""

from __future__ import annotations

from stoat.core.intent_schema import Intent


class SafetyValidator:
    """Decides whether a command requires user confirmation."""

    def __init__(self, required_confirmations: set[str] | None = None) -> None:
        self._required_confirmations = required_confirmations or {
            "delete",
            "uninstall",
            "move_multiple",
        }

    def requires_confirmation(self, intent: Intent) -> bool:
        if intent.requires_confirmation:
            return True
        return intent.action.value in self._required_confirmations
