"""Tests for rule-first NLP parsing."""

import pytest

from stoat.core.intent_schema import Intent, IntentAction, LowConfidenceError
from stoat.core.nlp_engine import NLPEngine


class StubRuleBackend:
    def parse(self, user_command: str) -> Intent:
        return Intent(action=IntentAction.UNKNOWN, target="", raw_text=user_command, confidence=0.0)


class StubLLMBackend:
    def parse(self, user_command: str) -> Intent | None:
        return Intent(
            action=IntentAction.FIND,
            target="resume",
            raw_text=user_command,
            confidence=0.95,
        )


class LowConfidenceLLMBackend:
    def parse(self, user_command: str) -> Intent | None:
        return Intent(
            action=IntentAction.FIND,
            target="resume",
            raw_text=user_command,
            confidence=0.4,
        )


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


def test_parse_most_recent_pdf_in_downloads() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("find the most recent pdf in downloads")

    assert intent.action == IntentAction.FIND
    assert intent.source == "~/Downloads"
    assert intent.filters is not None
    assert intent.filters.extension == ".pdf"
    assert intent.filters.sort_by == "modified"
    assert intent.filters.limit == 1


def test_parse_where_did_i_save_my_screenshot() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("where did i save my screenshot")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert intent.filters.name_contains == "screenshot"
    assert ".png" in (intent.filters.extensions or [])


def test_parse_help_me_find_spreadsheet_i_edited_yesterday() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("help me find the spreadsheet i edited yesterday")

    assert intent.action == IntentAction.FIND
    assert intent.filters is not None
    assert ".xlsx" in (intent.filters.extensions or [])
    assert intent.filters.modified_within_days == 2


def test_parse_show_disk_usage() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("show disk usage")

    assert intent.action == IntentAction.SYSTEM_INFO
    assert intent.target == "disk_usage"


def test_parse_whats_using_my_ram() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("what's using my ram")

    assert intent.action == IntentAction.SYSTEM_INFO
    assert intent.target == "memory_usage"


def test_parse_battery_status() -> None:
    engine = NLPEngine(enable_llm_fallback=False)

    intent = engine.parse("battery status")

    assert intent.action == IntentAction.SYSTEM_INFO
    assert intent.target == "battery_status"


def test_llm_fallback_used_for_unknown_command(monkeypatch) -> None:
    engine = NLPEngine(
        parser_mode="hybrid",
        rule_backend=StubRuleBackend(),
        llm_backend=StubLLMBackend(),
    )

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.FIND
    assert intent.target == "resume"


def test_hybrid_mode_without_llm_result_returns_unknown() -> None:
    class NoneLLMBackend:
        def parse(self, user_command: str) -> Intent | None:
            return None

    engine = NLPEngine(
        parser_mode="hybrid",
        rule_backend=StubRuleBackend(),
        llm_backend=NoneLLMBackend(),  # type: ignore[arg-type]
    )

    intent = engine.parse("please optimize my machine")

    assert intent.action == IntentAction.UNKNOWN


def test_engine_supports_injected_parser_backends() -> None:
    engine = NLPEngine(
        parser_mode="hybrid",
        rule_backend=StubRuleBackend(),
        llm_backend=StubLLMBackend(),
    )

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.FIND
    assert intent.target == "resume"


def test_rule_mode_ignores_llm_backend() -> None:
    engine = NLPEngine(
        parser_mode="rule",
        rule_backend=StubRuleBackend(),
        llm_backend=StubLLMBackend(),
    )

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.UNKNOWN


def test_llm_mode_uses_llm_backend_directly() -> None:
    engine = NLPEngine(
        parser_mode="llm",
        rule_backend=StubRuleBackend(),
        llm_backend=StubLLMBackend(),
    )

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.FIND
    assert intent.target == "resume"


def test_llm_mode_returns_unknown_when_backend_unavailable() -> None:
    class NoneLLMBackend:
        def parse(self, user_command: str) -> Intent | None:
            return None

    engine = NLPEngine(
        parser_mode="llm",
        rule_backend=StubRuleBackend(),
        llm_backend=NoneLLMBackend(),  # type: ignore[arg-type]
    )

    intent = engine.parse("please locate my resume")

    assert intent.action == IntentAction.UNKNOWN


def test_hybrid_mode_raises_on_low_confidence_llm_result() -> None:
    engine = NLPEngine(
        parser_mode="hybrid",
        rule_backend=StubRuleBackend(),
        llm_backend=LowConfidenceLLMBackend(),
        confidence_threshold=0.7,
    )

    with pytest.raises(LowConfidenceError):
        engine.parse("please locate my resume")
