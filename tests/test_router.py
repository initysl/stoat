"""Tests for router failure metadata."""

from __future__ import annotations

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.core.router import CommandRouter
from stoat.errors import ErrorCode


def test_router_no_handler_returns_standard_failure_details() -> None:
    router = CommandRouter(handlers=[])
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    intent = Intent(
        action=IntentAction.LAUNCH,
        target_type=TargetType.APPLICATION,
        target="firefox",
        confidence=0.9,
        raw_text="open firefox",
    )

    result = router.route(intent, context)

    assert result.success is False
    assert result.details["error_code"] == ErrorCode.ROUTER_NO_HANDLER.value
    assert result.details["target"] == "firefox"
    assert result.details["target_type"] == TargetType.APPLICATION.value
