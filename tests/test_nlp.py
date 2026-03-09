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
