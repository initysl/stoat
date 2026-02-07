"""Intent router that dispatches to matching handlers."""

from __future__ import annotations

from collections.abc import Sequence

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent
from stoat.handlers.base import BaseHandler, HandlerResult


class CommandRouter:
    """Routes parsed intents to the first capable handler."""

    def __init__(self, handlers: Sequence[BaseHandler]) -> None:
        self._handlers = list(handlers)

    def route(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        for handler in self._handlers:
            if handler.can_handle(intent):
                return handler.handle(intent, context)

        return HandlerResult(
            success=False,
            message=f"No handler available for action '{intent.action.value}'.",
            details={"action": intent.action.value},
        )
