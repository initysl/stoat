"""Tests for CLI utility behavior."""

import sys

from stoat.cli import _resolve_skip_confirmations


def test_resolve_skip_confirmations_true_flag() -> None:
    assert _resolve_skip_confirmations(True) is True


def test_resolve_skip_confirmations_from_argv(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["stoat", "run", "--yes", "close firefox"])

    assert _resolve_skip_confirmations(False) is True


def test_resolve_skip_confirmations_false_without_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["stoat", "run", "close firefox"])

    assert _resolve_skip_confirmations(False) is False
