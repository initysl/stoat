"""Tests for search behavior."""

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent, IntentAction, TargetType
from stoat.handlers.search import SearchHandler
from stoat.integrations.file_system import FileSystem
from stoat.integrations.search_engine import SearchEngine


def test_search_handler_returns_matches(sample_files) -> None:
    handler = SearchHandler(
        search_engine=SearchEngine(index_hidden_files=False, max_results=10),
        file_system=FileSystem(
            search_engine=SearchEngine(index_hidden_files=False, max_results=10)
        ),
    )
    context = ExecutionContext(cwd=sample_files, home=sample_files)
    intent = Intent(
        action=IntentAction.FIND,
        target_type=TargetType.FILE,
        target="document",
        confidence=0.9,
        raw_text="find document",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert any(match.endswith("document.pdf") for match in result.details["matches"])
