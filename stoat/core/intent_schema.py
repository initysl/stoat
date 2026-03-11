"""Canonical intent schema used across parsing, safety, and execution."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class IntentAction(str, Enum):
    """Actions supported by the v1 command loop."""

    UNKNOWN = "unknown"
    LAUNCH = "launch"
    CLOSE = "close"
    FIND = "find"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    UNDO = "undo"
    SYSTEM_INFO = "system_info"


class TargetType(str, Enum):
    """High-level target categories."""

    UNKNOWN = "unknown"
    FILE = "file"
    FOLDER = "folder"
    APPLICATION = "application"
    SYSTEM = "system"


class FileFilters(BaseModel):
    """Optional file filters retained for parser compatibility."""

    extension: str | None = None
    extensions: list[str] | None = None
    name_contains: str | None = None
    sort_by: str | None = None
    descending: bool = False
    limit: int | None = None
    modified_within_days: int | None = None


class Intent(BaseModel):
    """Represents a normalized command intent."""

    action: IntentAction = Field(default=IntentAction.UNKNOWN)
    target_type: TargetType = Field(default=TargetType.UNKNOWN)
    target: str = Field(default="")
    source: str | None = None
    destination: str | None = None
    filters: FileFilters | None = None
    requires_confirmation: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_text: str = Field(default="")

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Intent":
        if self.action not in {IntentAction.UNKNOWN, IntentAction.UNDO} and not self.target.strip():
            raise ValueError("Target cannot be empty for executable intents.")
        return self

    @property
    def is_unknown(self) -> bool:
        return self.action == IntentAction.UNKNOWN

    def requires_source(self) -> bool:
        return self.action in {IntentAction.MOVE, IntentAction.COPY}

    def requires_destination(self) -> bool:
        return self.action in {IntentAction.MOVE, IntentAction.COPY}

    def is_destructive(self) -> bool:
        return self.action in {IntentAction.DELETE, IntentAction.UNDO}

    def to_summary(self) -> str:
        parts = [f"action={self.action.value}", f"target={self.target or '-'}"]
        if self.source:
            parts.append(f"source={self.source}")
        if self.destination:
            parts.append(f"destination={self.destination}")
        parts.append(f"confidence={self.confidence:.2f}")
        return " | ".join(parts)


class IntentParseError(Exception):
    """Raised when parser output cannot be normalized."""


class LowConfidenceError(IntentParseError):
    """Raised when parser confidence is below the acceptance threshold."""

    def __init__(self, confidence: float, threshold: float) -> None:
        super().__init__(f"Intent confidence {confidence:.2f} is below threshold {threshold:.2f}")
        self.confidence = confidence
        self.threshold = threshold
