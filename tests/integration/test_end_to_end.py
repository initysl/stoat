"""Integration test for parser -> router -> app handler flow."""

from stoat.core.context import ExecutionContext
from stoat.core.nlp_engine import NLPEngine
from stoat.core.router import CommandRouter
from stoat.handlers.app_management import AppManagementHandler
from stoat.integrations.desktop_env import DesktopActionResult


class StubDesktopEnvironment:
    def launch_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(success=True, message=f"Launched '{target}'.", pid=999)

    def close_application(self, target: str) -> DesktopActionResult:
        return DesktopActionResult(success=True, message=f"Stopped '{target}'.")


def test_end_to_end_launch_flow() -> None:
    engine = NLPEngine(enable_llm_fallback=False)
    intent = engine.parse("open firefox")
    context = ExecutionContext.from_runtime(skip_confirmations=True)
    router = CommandRouter(handlers=[AppManagementHandler(desktop_env=StubDesktopEnvironment())])  # type: ignore[arg-type]

    result = router.route(intent, context)

    assert result.success is True
    assert result.details["pid"] == 999
