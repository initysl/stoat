"""Execution context shared across handlers."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExecutionContext:
    """Runtime context for one command execution."""

    cwd: Path
    home: Path
    skip_confirmations: bool = False

    @classmethod
    def from_runtime(cls, skip_confirmations: bool = False) -> "ExecutionContext":
        """Build context from the current environment."""
        return cls(cwd=Path.cwd(), home=Path.home(), skip_confirmations=skip_confirmations)
