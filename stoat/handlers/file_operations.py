"""Handler for safe file operations and undo."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction
from stoat.handlers.base import BaseHandler, HandlerResult
from stoat.integrations.file_system import FileSystem
from stoat.integrations.trash_manager import TrashManager
from stoat.safety.permissions import PermissionGuard
from stoat.utils.undo_stack import UndoOperation, UndoStack


class FileOperationsHandler(BaseHandler):
    """Executes file move/copy/delete/undo intents."""

    def __init__(
        self,
        file_system: FileSystem,
        trash_manager: TrashManager,
        undo_stack: UndoStack,
        permission_guard: PermissionGuard,
        max_batch_size: int = 100,
        enable_undo: bool = True,
    ) -> None:
        self._file_system = file_system
        self._trash_manager = trash_manager
        self._undo_stack = undo_stack
        self._permission_guard = permission_guard
        self._max_batch_size = max_batch_size
        self._enable_undo = enable_undo

    def can_handle(self, intent: Intent) -> bool:
        return intent.action in {
            IntentAction.MOVE,
            IntentAction.COPY,
            IntentAction.DELETE,
            IntentAction.UNDO,
        }

    def handle(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        if intent.action == IntentAction.UNDO:
            return self._undo_last_operation()

        base_dir = self._file_system.resolve_path(intent.source, cwd=context.cwd, home=context.home)
        matches = self._file_system.resolve_targets(intent.target, base_dir=base_dir)
        if not matches:
            return HandlerResult(
                success=False,
                message=f"No files matched '{intent.target}'.",
                details={"action": intent.action.value, "count": 0, "matches": []},
            )

        batch_error = self._validate_matches(intent, matches, context)
        if batch_error is not None:
            return batch_error

        if intent.action == IntentAction.DELETE:
            return self._delete(matches, intent)

        destination = self._file_system.resolve_path(
            intent.destination,
            cwd=context.cwd,
            home=context.home,
        )
        if self._permission_guard.is_protected_path(destination):
            return HandlerResult(
                success=False,
                message=f"Refusing to write to protected path '{destination}'.",
                details={"action": intent.action.value, "path": str(destination)},
            )
        if intent.action == IntentAction.MOVE:
            items = self._file_system.move(matches, destination)
            if self._enable_undo:
                self._record_operation("move", items)
            return HandlerResult(
                success=True,
                message=f"Moved {len(items)} item(s) to '{destination}'.",
                details={"action": intent.action.value, "count": len(items), "items": items},
            )

        items = self._file_system.copy(matches, destination)
        return HandlerResult(
            success=True,
            message=f"Copied {len(items)} item(s) to '{destination}'.",
            details={"action": intent.action.value, "count": len(items), "items": items},
        )

    def _validate_matches(
        self,
        intent: Intent,
        matches: list[Path],
        context: ExecutionContext,
    ) -> HandlerResult | None:
        if len(matches) > self._max_batch_size:
            return HandlerResult(
                success=False,
                message=(
                    f"Operation would affect {len(matches)} items, above the safety limit "
                    f"of {self._max_batch_size}."
                ),
                details={"action": intent.action.value, "count": len(matches)},
            )

        for path in matches:
            if self._permission_guard.is_protected_path(path):
                return HandlerResult(
                    success=False,
                    message=f"Refusing to modify protected path '{path}'.",
                    details={"action": intent.action.value, "path": str(path)},
                )

        if (
            intent.action == IntentAction.DELETE
            and intent.target == "*"
            and not (context.skip_confirmations or context.confirmed_action)
        ):
            return HandlerResult(
                success=False,
                message="Broad delete targets require explicit confirmation or --yes.",
                details={"action": intent.action.value, "count": len(matches)},
            )

        return None

    def _delete(self, matches: list[Path], intent: Intent) -> HandlerResult:
        operation_id, items = self._trash_manager.stage(matches)
        if self._enable_undo:
            self._record_operation("delete", items, operation_id=operation_id)
        return HandlerResult(
            success=True,
            message=f"Deleted {len(items)} item(s) to Stoat trash.",
            details={"action": intent.action.value, "count": len(items), "items": items},
        )

    def _undo_last_operation(self) -> HandlerResult:
        if not self._enable_undo:
            return HandlerResult(success=False, message="Undo is disabled in configuration.")

        operation = self._undo_stack.pop_last()
        if operation is None:
            return HandlerResult(success=False, message="No Stoat operation is available to undo.")

        if operation.action == "move":
            self._file_system.undo_move(operation.items)
            return HandlerResult(
                success=True,
                message="Reverted the last move operation.",
                details={"action": IntentAction.UNDO.value, "undone_action": operation.action},
            )

        if operation.action == "delete":
            for item in reversed(operation.items):
                self._trash_manager.restore(Path(item["trash_path"]), Path(item["original_path"]))
            return HandlerResult(
                success=True,
                message="Restored the last deleted item(s).",
                details={"action": IntentAction.UNDO.value, "undone_action": operation.action},
            )

        return HandlerResult(
            success=False,
            message=f"Undo is not implemented for '{operation.action}'.",
            details={"action": IntentAction.UNDO.value, "undone_action": operation.action},
        )

    def _record_operation(
        self,
        action: str,
        items: list[dict[str, str]],
        *,
        operation_id: str | None = None,
    ) -> None:
        self._undo_stack.record(
            UndoOperation(
                operation_id=operation_id or datetime.now(UTC).strftime("%Y%m%d%H%M%S%f"),
                action=action,
                items=items,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
