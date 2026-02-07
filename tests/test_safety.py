"""Tests for safety validation and confirmation behavior."""

from stoat.core.intent_schema import Intent, IntentAction
from stoat.safety.confirmation import ConfirmationPrompt
from stoat.safety.validator import SafetyValidator


def test_requires_confirmation_when_intent_marks_it() -> None:
    validator = SafetyValidator()
    intent = Intent(
        action=IntentAction.CLOSE_APP,
        raw_text="close firefox",
        target="firefox",
        confidence=0.9,
        requires_confirmation=True,
    )

    assert validator.requires_confirmation(intent) is True


def test_requires_confirmation_by_configured_action_name() -> None:
    validator = SafetyValidator(required_confirmations={"launch_app"})
    intent = Intent(
        action=IntentAction.LAUNCH_APP,
        raw_text="open firefox",
        target="firefox",
        confidence=0.95,
    )

    assert validator.requires_confirmation(intent) is True


def test_confirmation_prompt_yes() -> None:
    prompt = ConfirmationPrompt(input_func=lambda _: "yes")

    assert prompt.ask("continue?") is True


def test_confirmation_prompt_default_no() -> None:
    prompt = ConfirmationPrompt(input_func=lambda _: "")

    assert prompt.ask("continue?") is False
