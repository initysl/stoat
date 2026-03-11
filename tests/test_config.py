"""Tests for configuration validation."""

from __future__ import annotations

import pytest

from stoat.config import Config, LoggingConfig, SafetyConfig, SearchConfig


def test_logging_config_rejects_unknown_level() -> None:
    with pytest.raises(ValueError):
        LoggingConfig(level="TRACE")


def test_safety_config_rejects_unknown_confirmation_action() -> None:
    with pytest.raises(ValueError):
        SafetyConfig(require_confirmation=["delete", "explode"])


def test_search_config_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        SearchConfig(fuzzy_threshold=1.5)


def test_config_resolve_path_honors_env_override(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "stoat.toml"
    monkeypatch.setenv("STOAT_CONFIG_PATH", str(config_path))

    assert Config.resolve_path() == config_path
