"""Tests for app management handler."""

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.handlers.app_management import AppManagementHandler
from stoat.integrations.desktop_env import DesktopActionResult


class StubDesktopEnvironment:
    def launch_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(success=True, message=f"Launched '{target}'.", pid=4321)

    def close_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(success=True, message=f"Stopped '{target}'.")


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
