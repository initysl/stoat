"""Handler for read-only system information commands."""

from __future__ import annotations

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction
from stoat.errors import ErrorCode
from stoat.handlers.base import BaseHandler, HandlerResult
from stoat.integrations.system_info import SystemInfoIntegration


class SystemInfoHandler(BaseHandler):
    """Handles read-only system information intents."""

    def __init__(self, integration: SystemInfoIntegration | None = None) -> None:
        self._integration = integration or SystemInfoIntegration()

    def can_handle(self, intent: Intent) -> bool:
        return intent.action == IntentAction.SYSTEM_INFO

    def handle(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        if intent.target == "disk_usage":
            result = self._integration.get_disk_usage(context.home)
        elif intent.target == "memory_usage":
            result = self._integration.get_memory_usage()
        elif intent.target == "battery_status":
            result = self._integration.get_battery_status()
        else:
            return HandlerResult(
                success=False,
                message=f"System info target '{intent.target}' is not supported.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.INVALID_TARGET.value,
                    "target": intent.target,
                },
            )

        return HandlerResult(
            success=result.success,
            message=result.message,
            details={
                "action": intent.action.value,
                "target": intent.target,
                **result.details,
                "error_code": result.error_code,
            },
        )
