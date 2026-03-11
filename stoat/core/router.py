"""Intent router that dispatches to matching handlers."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent
from stoat.errors import ErrorCode
from stoat.handlers.base import BaseHandler, HandlerResult

logger = logging.getLogger("stoat")


class CommandRouter:
    """Routes parsed intents to the first capable handler."""

    def __init__(self, handlers: Sequence[BaseHandler]) -> None:
        self._handlers = list(handlers)

    def route(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        for handler in self._handlers:
            if handler.can_handle(intent):
                logger.info(
                    "router.handler_selected",
                    extra={
                        "event_name": "router.handler_selected",
                        "stoat_fields": {
                            "action": intent.action.value,
                            "handler": handler.__class__.__name__,
                            "dry_run": context.dry_run,
                        },
                    },
                )
                return handler.handle(intent, context)

        logger.info(
            "router.no_handler",
            extra={
                "event_name": "router.no_handler",
                "stoat_fields": {"action": intent.action.value},
            },
        )
        return HandlerResult(
            success=False,
            message=f"No handler available for action '{intent.action.value}'.",
            details={
                "action": intent.action.value,
                "error_code": ErrorCode.ROUTER_NO_HANDLER.value,
            },
        )
