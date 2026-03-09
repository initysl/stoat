"""Tests for rule-first NLP parsing."""

from stoat.core.intent_schema import Intent, IntentAction
from stoat.core.nlp_engine import NLPEngine


def test_parse_launch_command() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("open firefox")

    assert intent.action == IntentAction.LAUNCH
    assert intent.target == "firefox"


def test_parse_move_command_with_paths() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("move all PDFs from Downloads to Documents")

    assert intent.action == IntentAction.MOVE
    assert intent.target == "*.pdf"
    assert intent.source == "Downloads"
    assert intent.destination == "Documents"


def test_parse_undo_command() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("undo")

    assert intent.action == IntentAction.UNDO
    assert intent.requires_confirmation is True


def test_parse_unknown_command_without_llm() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("please optimize my machine")

    assert intent.action == IntentAction.UNKNOWN


def test_parse_find_pdf_files_with_extension_filter() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("find pdf files")

    assert intent.action == IntentAction.FIND
    assert intent.target == "*"
    assert intent.filters is not None
    assert intent.filters.extension == ".pdf"


def test_parse_find_files_containing_phrase() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("find files containing report")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.name_contains == "report"


def test_parse_latest_download_request() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("find my latest download")

    assert intent.action == IntentAction.FIND
    assert intent.source == "~/Downloads"
    assert intent.filters is not None
    assert intent.filters.sort_by == "modified"
    assert intent.filters.descending is True
    assert intent.filters.limit == 1


def test_parse_conversational_documents_request() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("i'm finding a docs i last modified")

    assert intent.action == IntentAction.FIND
    assert intent.source == "~/Documents"
    assert intent.filters is not None
    assert intent.filters.sort_by == "modified"
    assert ".pdf" in (intent.filters.extensions or [])


def test_parse_saved_file_reference() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("i saved a file as abc, find it")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.name_contains == "abc"


def test_parse_where_is_recent_doc_request() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("where's that doc i edited recently")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.sort_by == "modified"
    assert intent.filters.descending is True
    assert intent.filters.modified_within_days == 7
    assert ".pdf" in (intent.filters.extensions or [])


def test_parse_show_me_last_week_query() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("show me files containing invoice from last week")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.name_contains == "invoice"
    assert intent.filters.modified_within_days == 7


def test_parse_file_named_reference() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("i saved a file named tax_report, find it")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.name_contains == "tax_report"


def test_llm_fallback_used_for_unknown_command(monkeypatch) -> None:
    engine = NLPEngine(enable_llm_fallback=True)

    def fake_parse_with_llm(_: str) -> Intent:
        return Intent(
            action=IntentAction.FIND,
            target="resume",
            confidence=0.91,
            raw_text="please locate my resume",
        )

    monkeypatch.setattr(engine, "_parse_with_llm", fake_parse_with_llm)

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.FIND
    assert intent.target == "resume"


def test_llm_fallback_failure_returns_unknown(monkeypatch) -> None:
    engine = NLPEngine(enable_llm_fallback=True)
    monkeypatch.setattr(engine, "_parse_with_llm", lambda _: None)

    intent = engine.parse("please optimize my machine")

    assert intent.action == IntentAction.UNKNOWN
