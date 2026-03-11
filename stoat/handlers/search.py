"""Handler for file search intents."""

from __future__ import annotations

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction
from stoat.errors import ErrorCode
from stoat.handlers.base import BaseHandler, HandlerResult
from stoat.integrations.file_system import FileSystem
from stoat.integrations.search_engine import SearchEngine


class SearchHandler(BaseHandler):
    """Searches for files matching the parsed target query."""

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
        file_system: FileSystem | None = None,
    ) -> None:
        self._search_engine = search_engine or SearchEngine()
        self._file_system = file_system or FileSystem(search_engine=self._search_engine)

    def can_handle(self, intent: Intent) -> bool:
        return intent.action == IntentAction.FIND

    def handle(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        base_dir = self._file_system.resolve_path(intent.source, cwd=context.cwd, home=context.home)
        matches, search_roots = self._file_system.search_matches(
            intent.target,
            base_dir=base_dir,
            home=context.home,
            filters=intent.filters,
            explicit_source=bool(intent.source),
        )
        if not matches:
            return HandlerResult(
                success=False,
                message=f"No files matched '{intent.target}'.",
                details={
                    "action": intent.action.value,
                    "error_code": ErrorCode.NOT_FOUND.value,
                    "count": 0,
                    "target": intent.target,
                    "matches": [],
                    "search_roots": [str(root) for root in search_roots],
                    "filters": intent.filters.model_dump() if intent.filters else None,
                },
            )

        display = "\n".join(f"- {match.path} (score={match.score})" for match in matches)
        return HandlerResult(
            success=True,
            message=f"Found {len(matches)} match(es):\n{display}",
            details={
                "action": intent.action.value,
                "count": len(matches),
                "matches": [{"path": str(match.path), "score": match.score} for match in matches],
                "search_roots": [str(root) for root in search_roots],
                "filters": intent.filters.model_dump() if intent.filters else None,
            },
        )
