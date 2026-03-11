"""Configuration management"""

import os
from pathlib import Path
from typing import Optional

import toml
from pydantic import BaseModel, Field, field_validator

from stoat.core.intent_schema import IntentAction


class LLMConfig(BaseModel):
    model: str = "llama3.2:3b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, gt=0)
    timeout: int = Field(default=30, gt=0)


class SafetyConfig(BaseModel):
    require_confirmation: list[str] = ["delete", "move", "undo"]
    protected_paths: list[str] = ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc"]
    max_batch_size: int = Field(default=100, gt=0)
    enable_undo: bool = True

    @field_validator("require_confirmation")
    @classmethod
    def validate_required_confirmations(cls, value: list[str]) -> list[str]:
        allowed_actions = {
            action.value
            for action in IntentAction
            if action not in {IntentAction.UNKNOWN, IntentAction.FIND}
        }
        invalid = sorted(set(value) - allowed_actions)
        if invalid:
            raise ValueError(f"Unsupported safety confirmation actions: {', '.join(invalid)}")
        return value


class SearchConfig(BaseModel):
    index_hidden_files: bool = False
    max_results: int = Field(default=50, gt=0)
    use_locate: bool = True
    fuzzy_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    file: str = "~/.local/share/stoat/logs/stoat.log"
    max_size_mb: int = Field(default=10, gt=0)
    backup_count: int = Field(default=5, ge=0)

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Logging level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return normalized

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"json"}:
            raise ValueError("Logging format must be 'json'")
        return normalized


class UndoConfig(BaseModel):
    max_history: int = Field(default=50, gt=0)
    retention_days: int = Field(default=7, gt=0)
    storage_path: str = "~/.cache/stoat/undo"


class Config(BaseModel):
    llm: LLMConfig = LLMConfig()
    safety: SafetyConfig = SafetyConfig()
    search: SearchConfig = SearchConfig()
    logging: LoggingConfig = LoggingConfig()
    undo: UndoConfig = UndoConfig()

    @staticmethod
    def resolve_path(config_path: Optional[Path] = None) -> Path:
        """Resolve the active config path, honoring environment override."""
        if config_path is not None:
            return config_path

        override = os.environ.get("STOAT_CONFIG_PATH")
        if override:
            return Path(override).expanduser()

        return Path.home() / ".config" / "stoat" / "config.toml"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file"""
        config_path = cls.resolve_path(config_path)

        if config_path.exists():
            data = toml.load(config_path)
            return cls(**data)
        return cls()

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to file"""
        config_path = self.resolve_path(config_path)

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            toml.dump(self.model_dump(), f)
