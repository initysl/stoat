"""Tests for rule-based intent parsing."""

from stoat.core.intent_schema import IntentAction
from stoat.core.nlp_engine import NLPEngine


def test_parse_launch_intent() -> None:
    engine = NLPEngine()
    intent = engine.parse("open firefox")

    assert intent.action == IntentAction.LAUNCH_APP
    assert intent.target == "firefox"
    assert intent.confidence > 0.9


def test_parse_close_intent_requires_confirmation() -> None:
    engine = NLPEngine()
    intent = engine.parse("close firefox")

    assert intent.action == IntentAction.CLOSE_APP
    assert intent.target == "firefox"
    assert intent.requires_confirmation is True


def test_parse_alias_normalization() -> None:
    engine = NLPEngine()
    intent = engine.parse("open chrome")

    assert intent.action == IntentAction.LAUNCH_APP
    assert intent.target == "google-chrome"


def test_parse_calendar_alias_normalization() -> None:
    engine = NLPEngine()
    intent = engine.parse("open calendar")

    assert intent.action == IntentAction.LAUNCH_APP
    assert intent.target == "gnome-calendar"


def test_parse_common_typo_calender_normalization() -> None:
    engine = NLPEngine()
    intent = engine.parse("open calender")

    assert intent.action == IntentAction.LAUNCH_APP
    assert intent.target == "gnome-calendar"


def test_parse_unknown_intent() -> None:
    engine = NLPEngine()
    intent = engine.parse("tell me a joke")

    assert intent.action == IntentAction.UNKNOWN


def test_parse_target_preserves_hyphen_app_suffix() -> None:
    engine = NLPEngine()
    intent = engine.parse("open definitely-not-a-real-app")

    assert intent.action == IntentAction.LAUNCH_APP
    assert intent.target == "definitely-not-a-real-app"
