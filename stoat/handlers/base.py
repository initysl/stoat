"""Base contracts for command handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import Intent


@dataclass(slots=True)
class HandlerResult:
    """Result payload returned by handlers."""

    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class BaseHandler(ABC):
    """Base class for all command handlers."""

    @abstractmethod
    def can_handle(self, intent: Intent) -> bool:
        """Return True when this handler supports the provided intent."""

    @abstractmethod
    def handle(self, intent: Intent, context: ExecutionContext) -> HandlerResult:
        """Execute intent and return a handler result."""
