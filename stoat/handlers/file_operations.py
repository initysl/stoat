"""Handler for safe file operations and undo."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction
from stoat.errors import ErrorCode
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
        resolution_error: HandlerResult | None = None
        search_roots: list[Path] = [base_dir]
        if intent.target_items:
            matches, search_roots, resolution_error = self._resolve_named_targets(
                intent,
                base_dir=base_dir,
                context=context,
            )
        else:
            matches = self._file_system.resolve_targets(
                intent.target,
                base_dir=base_dir,
                home=context.home,
                filters=intent.filters,
                explicit_source=bool(intent.source),
            )
            search_roots = self._file_system.resolve_search_roots(
                base_dir=base_dir,
                home=context.home,
                filters=intent.filters,
                explicit_source=bool(intent.source),
            )

        if resolution_error is not None:
            return resolution_error

        if not matches:
            return HandlerResult(
                success=False,
                message=f"No files matched '{intent.target}'.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.NOT_FOUND.value,
                    "count": 0,
                    "matches": [],
                    "search_roots": [str(root) for root in search_roots],
                    "filters": intent.filters.model_dump() if intent.filters else None,
                },
            )

        batch_error = self._validate_matches(intent, matches, context)
        if batch_error is not None:
            return batch_error

        if intent.action == IntentAction.DELETE:
            if context.dry_run:
                return self._build_dry_run_result(intent, matches, search_roots=search_roots)
            return self._delete(matches, intent, search_roots=search_roots)

        destination = self._file_system.resolve_path(
            intent.destination,
            cwd=context.cwd,
            home=context.home,
        )
        if self._permission_guard.is_protected_path(destination):
            return HandlerResult(
                success=False,
                message=f"Refusing to write to protected path '{destination}'.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.PROTECTED_PATH.value,
                    "path": str(destination),
                },
            )
        transfer_plan = self._file_system.plan_transfer(matches, destination)
        collision_error = self._validate_transfer_plan(intent, transfer_plan)
        if collision_error is not None:
            return collision_error
        if context.dry_run:
            return self._build_dry_run_result(
                intent,
                matches,
                destination=destination,
                search_roots=search_roots,
            )
        if intent.action == IntentAction.MOVE:
            items = self._file_system.move(matches, destination)
            if self._enable_undo:
                self._record_operation("move", items)
            return HandlerResult(
                success=True,
                message=f"Moved {len(items)} item(s) to '{destination}'.",
                details={
                    "action": intent.action.value,
                    "count": len(items),
                    "items": items,
                    "search_roots": [str(root) for root in search_roots],
                    "requested_targets": intent.target_items or [intent.target],
                },
            )

        items = self._file_system.copy(matches, destination)
        return HandlerResult(
            success=True,
            message=f"Copied {len(items)} item(s) to '{destination}'.",
            details={
                "action": intent.action.value,
                "count": len(items),
                "items": items,
                "search_roots": [str(root) for root in search_roots],
                "requested_targets": intent.target_items or [intent.target],
            },
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
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.BATCH_LIMIT.value,
                    "count": len(matches),
                },
            )

        for path in matches:
            if self._permission_guard.is_protected_path(path):
                return HandlerResult(
                    success=False,
                    message=f"Refusing to modify protected path '{path}'.",
                    details={
                        "action": intent.action.value,
                        "error_code": ErrorCode.PROTECTED_PATH.value,
                        "path": str(path),
                    },
                )

        if (
            intent.action == IntentAction.DELETE
            and intent.target == "*"
            and not (context.skip_confirmations or context.confirmed_action or context.dry_run)
        ):
            return HandlerResult(
                success=False,
                message="Broad delete targets require explicit confirmation or --yes.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.CONFIRMATION_REQUIRED.value,
                    "count": len(matches),
                },
            )

        return None

    def _validate_transfer_plan(
        self,
        intent: Intent,
        transfer_plan: list[dict[str, str | bool]],
    ) -> HandlerResult | None:
        collisions = [
            item["destination_path"] for item in transfer_plan if bool(item["will_overwrite"])
        ]
        if collisions:
            preview = ", ".join(str(path) for path in collisions[:3])
            suffix = "" if len(collisions) <= 3 else f" and {len(collisions) - 3} more"
            return HandlerResult(
                success=False,
                message=(
                    f"Refusing to {intent.action.value} because destination files already exist: "
                    f"{preview}{suffix}."
                ),
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.COLLISION.value,
                    "collisions": [str(path) for path in collisions],
                },
            )
        return None

    def _build_dry_run_result(
        self,
        intent: Intent,
        matches: list[Path],
        *,
        destination: Path | None = None,
        search_roots: list[Path] | None = None,
    ) -> HandlerResult:
        if intent.action == IntentAction.DELETE:
            items = [{"original_path": str(path)} for path in matches]
            return HandlerResult(
                success=True,
                message=f"Dry run: would delete {len(items)} item(s).",
                details={
                    "action": intent.action.value,
                    "dry_run": True,
                    "count": len(items),
                    "items": items,
                    "search_roots": [str(root) for root in search_roots or []],
                    "requested_targets": intent.target_items or [intent.target],
                },
            )

        assert destination is not None
        items = self._file_system.plan_transfer(matches, destination)
        return HandlerResult(
            success=True,
            message=(
                f"Dry run: would {intent.action.value} {len(items)} item(s) " f"to '{destination}'."
            ),
            details={
                "action": intent.action.value,
                "dry_run": True,
                "count": len(items),
                "items": items,
                "search_roots": [str(root) for root in search_roots or []],
                "requested_targets": intent.target_items or [intent.target],
            },
        )

    def _delete(
        self,
        matches: list[Path],
        intent: Intent,
        *,
        search_roots: list[Path] | None = None,
    ) -> HandlerResult:
        operation_id, items = self._trash_manager.stage(matches)
        if self._enable_undo:
            self._record_operation("delete", items, operation_id=operation_id)
        return HandlerResult(
            success=True,
            message=f"Deleted {len(items)} item(s) to Stoat trash.",
            details={
                "action": intent.action.value,
                "count": len(items),
                "items": items,
                "search_roots": [str(root) for root in search_roots or []],
                "requested_targets": intent.target_items or [intent.target],
            },
        )

    def _resolve_named_targets(
        self,
        intent: Intent,
        *,
        base_dir: Path,
        context: ExecutionContext,
    ) -> tuple[list[Path], list[Path], HandlerResult | None]:
        resolved: list[Path] = []
        search_roots: list[Path] = self._file_system.resolve_search_roots(
            base_dir=base_dir,
            home=context.home,
            filters=intent.filters,
            explicit_source=bool(intent.source),
        )
        ambiguous: list[dict[str, object]] = []
        missing: list[str] = []

        for item in intent.target_items or []:
            matches, _ = self._file_system.search_matches(
                item,
                base_dir=base_dir,
                home=context.home,
                filters=intent.filters,
                explicit_source=bool(intent.source),
            )
            if not matches:
                missing.append(item)
                continue
            if len(matches) > 1:
                ambiguous.append(
                    {
                        "query": item,
                        "matches": [
                            {"path": str(match.path), "score": match.score} for match in matches[:5]
                        ],
                        "suggestions": self._build_clarification_suggestions(
                            intent.action.value,
                            matches[:3],
                        ),
                    }
                )
                continue
            resolved.append(matches[0].path.resolve())

        if ambiguous:
            preview_lines = self._format_ambiguous_preview(ambiguous)
            return [], search_roots, HandlerResult(
                success=False,
                message=(
                    f"Multiple files matched one or more {intent.action.value} targets. "
                    f"Please be more specific.\n{preview_lines}"
                ),
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.AMBIGUOUS_TARGET.value,
                    "ambiguous_targets": ambiguous,
                    "requested_targets": intent.target_items,
                    "search_roots": [str(root) for root in search_roots],
                    "filters": intent.filters.model_dump() if intent.filters else None,
                },
            )

        if missing:
            return [], search_roots, HandlerResult(
                success=False,
                message=f"No files matched: {', '.join(missing)}.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.NOT_FOUND.value,
                    "missing_targets": missing,
                    "requested_targets": intent.target_items,
                    "search_roots": [str(root) for root in search_roots],
                    "filters": intent.filters.model_dump() if intent.filters else None,
                },
            )

        deduped = list(dict.fromkeys(resolved))
        return deduped, search_roots, None

    def _format_ambiguous_preview(self, ambiguous: list[dict[str, object]]) -> str:
        lines: list[str] = []
        for entry in ambiguous:
            query = str(entry["query"])
            lines.append(f"- {query}:")
            for match in entry["matches"][:3]:  # type: ignore[index]
                if isinstance(match, dict):
                    lines.append(f"  - {match['path']}")
        return "\n".join(lines)

    def _build_clarification_suggestions(
        self,
        action: str,
        matches: list[object],
    ) -> list[str]:
        suggestions: list[str] = []
        for match in matches:
            path = getattr(match, "path", None)
            if path is None:
                continue
            suggestions.append(f'stoat run "{action} {path}"')
        return suggestions

    def _undo_last_operation(self) -> HandlerResult:
        if not self._enable_undo:
            return HandlerResult(
                success=False,
                message="Undo is disabled in configuration.",
                details={
                    "action": IntentAction.UNDO.value,
                    "error_code": ErrorCode.UNDO_DISABLED.value,
                },
            )

        operation = self._undo_stack.pop_last()
        if operation is None:
            return HandlerResult(
                success=False,
                message="No Stoat operation is available to undo.",
                details={
                    "action": IntentAction.UNDO.value,
                    "error_code": ErrorCode.NOTHING_TO_UNDO.value,
                },
            )

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
            details={
                "action": IntentAction.UNDO.value,
                "error_code": ErrorCode.UNSUPPORTED_UNDO.value,
                "undone_action": operation.action,
            },
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
