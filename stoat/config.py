"""Configuration management"""

from pathlib import Path
from typing import Optional
import toml
from pydantic import BaseModel


class LLMConfig(BaseModel):
    model: str = "llama3.2:3b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 512
    timeout: int = 30


class SafetyConfig(BaseModel):
    require_confirmation: list[str] = ["delete", "move", "undo"]
    protected_paths: list[str] = ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc"]
    max_batch_size: int = 100
    enable_undo: bool = True


class SearchConfig(BaseModel):
    index_hidden_files: bool = False
    max_results: int = 50
    use_locate: bool = True
    fuzzy_threshold: float = 0.6


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    file: str = "~/.local/share/stoat/logs/stoat.log"
    max_size_mb: int = 10
    backup_count: int = 5


class UndoConfig(BaseModel):
    max_history: int = 50
    retention_days: int = 7
    storage_path: str = "~/.cache/stoat/undo"


class Config(BaseModel):
    llm: LLMConfig = LLMConfig()
    safety: SafetyConfig = SafetyConfig()
    search: SearchConfig = SearchConfig()
    logging: LoggingConfig = LoggingConfig()
    undo: UndoConfig = UndoConfig()

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file"""
        if config_path is None:
            config_path = Path.home() / ".config" / "stoat" / "config.toml"

        if config_path.exists():
            data = toml.load(config_path)
            return cls(**data)
        return cls()

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to file"""
        if config_path is None:
            config_path = Path.home() / ".config" / "stoat" / "config.toml"

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            toml.dump(self.model_dump(), f)
