"""Tests for search behavior."""

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import FileFilters, Intent, IntentAction, TargetType
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
    assert any(match["path"].endswith("document.pdf") for match in result.details["matches"])


def test_search_handler_applies_extension_filter(temp_dir) -> None:
    (temp_dir / "report.pdf").write_text("pdf")
    (temp_dir / "report.txt").write_text("txt")
    handler = SearchHandler(
        search_engine=SearchEngine(index_hidden_files=False, max_results=10),
        file_system=FileSystem(
            search_engine=SearchEngine(index_hidden_files=False, max_results=10)
        ),
    )
    context = ExecutionContext(cwd=temp_dir, home=temp_dir)
    intent = Intent(
        action=IntentAction.FIND,
        target_type=TargetType.FILE,
        target="report",
        filters=FileFilters(extension=".pdf"),
        confidence=0.9,
        raw_text="find pdf files",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert len(result.details["matches"]) == 1
    assert result.details["matches"][0]["path"].endswith("report.pdf")


def test_search_engine_ranks_exact_match_first(temp_dir) -> None:
    (temp_dir / "report.txt").write_text("top")
    (temp_dir / "monthly-report.txt").write_text("second")

    engine = SearchEngine(index_hidden_files=False, max_results=10)
    matches = engine.search(temp_dir, "report")

    assert matches[0].path.name == "report.txt"


def test_search_engine_hides_hidden_files_by_default(temp_dir) -> None:
    (temp_dir / ".secret.txt").write_text("hidden")
    (temp_dir / "visible.txt").write_text("visible")

    hidden_off = SearchEngine(index_hidden_files=False, max_results=10).search(temp_dir, "txt")
    hidden_on = SearchEngine(index_hidden_files=True, max_results=10).search(temp_dir, "txt")

    assert all(match.path.name != ".secret.txt" for match in hidden_off)
    assert any(match.path.name == ".secret.txt" for match in hidden_on)
