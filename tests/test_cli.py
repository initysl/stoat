"""Tests for CLI behavior."""

from __future__ import annotations

import json
import sys

from click.testing import CliRunner

from stoat.cli import _resolve_skip_confirmations, app
from stoat.config import Config, LLMConfig, LoggingConfig, SafetyConfig, SearchConfig, UndoConfig


runner = CliRunner()


def _test_config(root) -> Config:
    return Config(
        llm=LLMConfig(),
        safety=SafetyConfig(
            require_confirmation=["delete", "move", "undo"],
            protected_paths=[str(root / "protected")],
            max_batch_size=10,
            enable_undo=True,
        ),
        search=SearchConfig(
            index_hidden_files=False, max_results=10, use_locate=False, fuzzy_threshold=0.6
        ),
        logging=LoggingConfig(),
        undo=UndoConfig(max_history=10, retention_days=7, storage_path=str(root / ".stoat")),
    )


def test_resolve_skip_confirmations_true_flag() -> None:
    assert _resolve_skip_confirmations(True) is True


def test_resolve_skip_confirmations_from_argv(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["stoat", "run", "--yes", "close firefox"])

    assert _resolve_skip_confirmations(False) is True


def test_resolve_skip_confirmations_false_without_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["stoat", "run", "close firefox"])

    assert _resolve_skip_confirmations(False) is False


def test_cli_supported_find_command(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "find test"])

    assert result.exit_code == 0
    assert "test.txt" in result.stdout


def test_cli_unsupported_command_fails(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "please optimize my machine"])

    assert result.exit_code == 1
    assert "could not map" in result.stdout.lower()


def test_cli_confirmation_prompt_can_cancel(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "delete test.txt"], input="n\n")

    assert result.exit_code == 1
    assert "action cancelled" in result.stdout.lower()
    assert "confirm delete" in result.stdout.lower()
    assert (sample_files / "test.txt").exists() is True


def test_cli_yes_skips_confirmation_and_undo_restores(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    delete_result = runner.invoke(app, ["run", "--yes", "delete test.txt"])
    undo_result = runner.invoke(app, ["undo", "--yes"])

    assert delete_result.exit_code == 0
    assert undo_result.exit_code == 0
    assert (sample_files / "test.txt").exists() is True


def test_cli_json_output_is_stable(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "--json", "find document"])

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert result.stdout.startswith("{\n")
    assert payload["ok"] is True
    assert payload["command"] == "run"
    assert payload["action"] == "find"
    assert payload["data"]["count"] >= 1


def test_cli_dry_run_does_not_modify_files(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "--dry-run", "--json", "delete test.txt"])

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert (sample_files / "test.txt").exists() is True


def test_cli_undo_without_history_fails(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["undo", "--yes"])

    assert result.exit_code == 1
    assert "no stoat operation" in result.stdout.lower()


def test_cli_history_reports_operations(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    runner.invoke(app, ["run", "--yes", "delete test.txt"])
    result = runner.invoke(app, ["history"])

    assert result.exit_code == 0
    assert "recent stoat history" in result.stdout.lower()
    assert "delete" in result.stdout.lower()


def test_cli_history_json_output(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    runner.invoke(app, ["run", "--yes", "delete test.txt"])
    result = runner.invoke(app, ["history", "--json"])

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["command"] == "history"
    assert payload["action"] == "history"
    assert payload["data"]["count"] == 1
    assert payload["data"]["operations"][0]["action"] == "delete"


def test_cli_json_failure_shape(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["run", "--json", "please optimize my machine"])

    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["command"] == "run"
    assert payload["action"] == "unknown"
    assert payload["data"] is None
    assert payload["error"]["code"] == "unknown_intent"


def test_cli_history_empty_state(monkeypatch, sample_files) -> None:
    monkeypatch.chdir(sample_files)
    monkeypatch.setattr(
        "stoat.cli.Config.load",
        classmethod(lambda cls, config_path=None: _test_config(sample_files)),
    )

    result = runner.invoke(app, ["history"])

    assert result.exit_code == 0
    assert "no stoat history" in result.stdout.lower()
