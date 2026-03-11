"""Tests for app management handler."""

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.errors import ErrorCode
from stoat.handlers.app_management import AppManagementHandler
from stoat.integrations.desktop_env import DesktopActionResult


class StubDesktopEnvironment:
    def launch_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(
            success=True,
            message=f"Launched '{target}'.",
            pid=4321,
            details={"binary": target},
        )

    def close_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(
            success=True,
            message=f"Stopped '{target}'.",
            details={"target": target, "match_mode": "exact"},
        )


class FailingDesktopEnvironment:
    def launch_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(
            success=False,
            message=f"Application '{target}' was not found in PATH.",
            error_code=ErrorCode.APP_NOT_FOUND.value,
            details={"binary": target},
        )

    def close_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(
            success=False,
            message=f"No running processes matched '{target}'.",
            error_code=ErrorCode.APP_NOT_RUNNING.value,
            details={"target": target},
        )


def test_launch_app_handler_returns_success() -> None:
    handler = AppManagementHandler(desktop_env=StubDesktopEnvironment())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.LAUNCH,
        target_type=TargetType.APPLICATION,
        raw_text="open firefox",
        target="firefox",
        confidence=0.95,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["target"] == "firefox"
    assert result.details["pid"] == 4321
    assert result.details["binary"] == "firefox"


def test_close_app_handler_returns_success() -> None:
    handler = AppManagementHandler(desktop_env=StubDesktopEnvironment())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.CLOSE,
        target_type=TargetType.APPLICATION,
        raw_text="close firefox",
        target="firefox",
        confidence=0.9,
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["action"] == IntentAction.CLOSE.value
    assert result.details["match_mode"] == "exact"


def test_launch_app_handler_surfaces_specific_failure_code() -> None:
    handler = AppManagementHandler(desktop_env=FailingDesktopEnvironment())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.LAUNCH,
        target_type=TargetType.APPLICATION,
        raw_text="open missingapp",
        target="missingapp",
        confidence=0.95,
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == ErrorCode.APP_NOT_FOUND.value
    assert result.details["binary"] == "missingapp"


def test_close_app_handler_surfaces_specific_failure_code() -> None:
    handler = AppManagementHandler(desktop_env=FailingDesktopEnvironment())
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.CLOSE,
        target_type=TargetType.APPLICATION,
        raw_text="close missingapp",
        target="missingapp",
        confidence=0.9,
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == ErrorCode.APP_NOT_RUNNING.value
    assert result.details["target"] == "missingapp"
