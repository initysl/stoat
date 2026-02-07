"""Intent models used by the parser and router."""

from enum import Enum

from pydantic import BaseModel, Field


class IntentAction(str, Enum):
    """High-level actions understood by Stoat."""

    LAUNCH_APP = "launch_app"
    CLOSE_APP = "close_app"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    """Structured intent derived from user input."""

    action: IntentAction
    raw_text: str
    target: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_confirmation: bool = False
