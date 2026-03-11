"""Tests for search behavior."""

import os
from pathlib import Path
import time

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


def test_search_handler_no_match_reports_standard_failure_payload(temp_dir) -> None:
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
        target="missing-file",
        confidence=0.9,
        raw_text="find missing-file",
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == "not_found"
    assert result.details["count"] == 0
    assert result.details["target"] == "missing-file"


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


def test_search_engine_respects_modified_sort_and_limit(temp_dir: Path) -> None:
    older = temp_dir / "older.txt"
    newer = temp_dir / "newer.txt"
    older.write_text("old")
    time.sleep(0.01)
    newer.write_text("new")

    engine = SearchEngine(index_hidden_files=False, max_results=10)
    matches = engine.search(
        temp_dir,
        "*",
        FileFilters(sort_by="modified", descending=True, limit=1),
    )

    assert len(matches) == 1
    assert matches[0].path.name == "newer.txt"


def test_search_handler_uses_source_directory(temp_dir: Path) -> None:
    downloads = temp_dir / "Downloads"
    downloads.mkdir()
    (downloads / "recent.txt").write_text("download")
    (temp_dir / "recent.txt").write_text("root")
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
        target="recent",
        source=str(downloads),
        confidence=0.9,
        raw_text="find my latest download",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert all(str(downloads) in match["path"] for match in result.details["matches"])


def test_search_engine_respects_modified_within_days_filter(temp_dir: Path) -> None:
    recent = temp_dir / "recent.txt"
    older = temp_dir / "older.txt"
    recent.write_text("recent")
    older.write_text("old")
    old_timestamp = time.time() - (10 * 24 * 60 * 60)
    os.utime(older, (old_timestamp, old_timestamp))

    engine = SearchEngine(index_hidden_files=False, max_results=10)
    matches = engine.search(
        temp_dir,
        "txt",
        FileFilters(modified_within_days=7),
    )

    assert any(match.path.name == "recent.txt" for match in matches)
    assert all(match.path.name != "older.txt" for match in matches)


def test_search_handler_uses_preferred_roots_as_hints(temp_dir: Path) -> None:
    videos = temp_dir / "Videos"
    videos.mkdir()
    downloads = temp_dir / "Downloads"
    downloads.mkdir()
    (videos / "Avengers.mp4").write_text("video")
    (downloads / "Power Rangers.mp4").write_text("video")

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
        target="*",
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads"],
        ),
        confidence=0.9,
        raw_text="find all my movies",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert len(result.details["matches"]) == 2
    assert any(match["path"].endswith("Avengers.mp4") for match in result.details["matches"])
    assert any(match["path"].endswith("Power Rangers.mp4") for match in result.details["matches"])


def test_search_handler_uses_configured_fallback_roots(temp_dir: Path) -> None:
    workspace = temp_dir / "workspace"
    downloads = temp_dir / "Downloads"
    workspace.mkdir()
    downloads.mkdir()
    (downloads / "invoice.pdf").write_text("pdf")

    search_engine = SearchEngine(index_hidden_files=False, max_results=10)
    handler = SearchHandler(
        search_engine=search_engine,
        file_system=FileSystem(
            search_engine=search_engine,
            fallback_roots=["~/Downloads"],
        ),
    )
    context = ExecutionContext(cwd=workspace, home=temp_dir)
    intent = Intent(
        action=IntentAction.FIND,
        target_type=TargetType.FILE,
        target="invoice",
        filters=FileFilters(category="document", extensions=[".pdf"]),
        confidence=0.9,
        raw_text="find invoice",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["matches"][0]["path"].endswith("invoice.pdf")
    assert str(downloads) in result.details["search_roots"]


def test_search_engine_normalized_name_ranks_better(temp_dir: Path) -> None:
    (temp_dir / "Power Rangers.mp4").write_text("main")
    (temp_dir / "Power-Rangers-Extended.mp4").write_text("alt")

    engine = SearchEngine(index_hidden_files=False, max_results=10)
    matches = engine.search(temp_dir, "power rangers")

    assert matches[0].path.name == "Power Rangers.mp4"
