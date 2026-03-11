"""Execution context shared across handlers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(slots=True)
class ExecutionContext:
    """Runtime context for one command execution."""

    cwd: Path
    home: Path
    skip_confirmations: bool = False
    dry_run: bool = False
    confirmed_action: bool = False

    @classmethod
    def from_runtime(
        cls, skip_confirmations: bool = False, dry_run: bool = False
    ) -> "ExecutionContext":
        """Build context from the current environment."""
        return cls(
            cwd=Path.cwd(),
            home=Path.home(),
            skip_confirmations=skip_confirmations,
            dry_run=dry_run,
        )

    def with_confirmation(self) -> "ExecutionContext":
        """Return a copy marked as explicitly confirmed by the user."""
        return replace(self, confirmed_action=True)

    def as_dry_run(self) -> "ExecutionContext":
        """Return a copy that performs preview-only execution."""
        return replace(self, dry_run=True)
