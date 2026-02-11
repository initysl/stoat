# """Handler for application launch/close intents."""

# from __future__ import annotations

# from stoat.core.context import ExecutionContext
# from stoat.core.intent_schema import Intent, IntentAction
# from stoat.handlers.base import BaseHandler, HandlerResult
# from stoat.integrations.desktop_env import DesktopEnvironment


# class AppManagementHandler(BaseHandler):
#     """Executes app-management intents through the desktop integration."""

#     def __init__(self, desktop_env: DesktopEnvironment | None = None) -> None:
#         self._desktop = desktop_env or DesktopEnvironment()

#     def can_handle(self, intent: Intent) -> bool:
#         return intent.action in {IntentAction.LAUNCH_APP, IntentAction.CLOSE_APP}

#     def handle(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
#         if not intent.target:
#             return HandlerResult(success=False, message="No application target was provided.")

#         if intent.action == IntentAction.LAUNCH_APP:
#             result = self._desktop.launch_application(intent.target)
#             return HandlerResult(
#                 success=result.success,
#                 message=result.message,
#                 details={
#                     "action": intent.action.value,
#                     "target": intent.target,
#                     "pid": result.pid,
#                 },
#             )

#         if intent.action == IntentAction.CLOSE_APP:
#             result = self._desktop.close_application(intent.target)
#             return HandlerResult(
#                 success=result.success,
#                 message=result.message,
#                 details={"action": intent.action.value, "target": intent.target},
#             )

#         return HandlerResult(
#             success=False,
#             message=f"Unsupported app action '{intent.action.value}'.",
#             details={"action": intent.action.value},
#         )
