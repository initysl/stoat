"""Tests for system information handling."""

from __future__ import annotations

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.errors import ErrorCode
from stoat.handlers.system_info import SystemInfoHandler
from stoat.integrations.system_info import SystemInfoResult


class StubSystemInfoIntegration:
    def get_disk_usage(self, path):
        return SystemInfoResult(
            success=True,
            message="Disk usage for '/tmp': 50.0% used.",
            details={"path": str(path), "percent_used": 50.0},
        )

    def get_memory_usage(self):
        return SystemInfoResult(
            success=True,
            message="Memory usage: 42.0% used.",
            details={"percent_used": 42.0, "top_processes": [{"command": "python"}]},
        )

    def get_battery_status(self):
        return SystemInfoResult(
            success=False,
            message="Battery information is not available on this system.",
            details={"target": "battery_status"},
            error_code=ErrorCode.SYSTEM_INFO_UNAVAILABLE.value,
        )


def test_system_info_handler_disk_usage() -> None:
    handler = SystemInfoHandler(integration=StubSystemInfoIntegration())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.SYSTEM_INFO,
        target_type=TargetType.SYSTEM,
        target="disk_usage",
        raw_text="show disk usage",
        confidence=0.95,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["target"] == "disk_usage"
    assert result.details["percent_used"] == 50.0


def test_system_info_handler_memory_usage() -> None:
    handler = SystemInfoHandler(integration=StubSystemInfoIntegration())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.SYSTEM_INFO,
        target_type=TargetType.SYSTEM,
        target="memory_usage",
        raw_text="what's using my ram",
        confidence=0.95,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["top_processes"][0]["command"] == "python"


def test_system_info_handler_battery_unavailable() -> None:
    handler = SystemInfoHandler(integration=StubSystemInfoIntegration())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.SYSTEM_INFO,
        target_type=TargetType.SYSTEM,
        target="battery_status",
        raw_text="battery status",
        confidence=0.95,
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == ErrorCode.SYSTEM_INFO_UNAVAILABLE.value
