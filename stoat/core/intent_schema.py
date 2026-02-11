"""Intent schema - Defines the structure of parsed user commands"""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Possible actions the assistant can perform"""
    LAUNCH = "launch"
    CLOSE = "close"
    FIND = "find"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    RENAME = "rename"
    INSTALL = "install"
    UNINSTALL = "uninstall"
    ORGANIZE = "organize"
    SYSTEM_INFO = "system_info"


class TargetType(str, Enum):
    """Type of target being operated on"""
    FILE = "file"
    FOLDER = "folder"
    APPLICATION = "application"
    PROCESS = "process"
    SYSTEM = "system"


class FileFilters(BaseModel):
    """Optional filters for file operations"""
    extension: Optional[str] = Field(None, description="File extension filter (e.g., .pdf, .txt)")
    size_min: Optional[str] = Field(None, description="Minimum file size (e.g., 10MB, 1GB)")
    size_max: Optional[str] = Field(None, description="Maximum file size")
    modified_after: Optional[str] = Field(None, description="Modified after date (e.g., last week, 2024-01-01)")
    modified_before: Optional[str] = Field(None, description="Modified before date")
    name_contains: Optional[str] = Field(None, description="Filename must contain this text")


class Intent(BaseModel):
    """Represents a parsed user intent"""
    
    action: ActionType = Field(..., description="The action to perform")
    target_type: TargetType = Field(..., description="Type of target being operated on")
    target: str = Field(..., description="The specific target (filename, app name, pattern)")
    
    source: Optional[str] = Field(None, description="Source path for move/copy operations")
    destination: Optional[str] = Field(None, description="Destination path for move/copy/organize")
    new_name: Optional[str] = Field(None, description="New name for rename operations")
    
    filters: Optional[FileFilters] = Field(None, description="Optional filters for file operations")
    
    confirmation_required: bool = Field(
        default=True,
        description="Whether this operation requires user confirmation"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the intent parsing (0.0 to 1.0)"
    )
    
    raw_query: Optional[str] = Field(None, description="Original user query for reference")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    @field_validator('target')
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Ensure target is not empty"""
        if not v or not v.strip():
            raise ValueError("Target cannot be empty")
        return v.strip()
    
    def requires_source(self) -> bool:
        """Check if this action requires a source path"""
        return self.action in [ActionType.MOVE, ActionType.COPY]
    
    def requires_destination(self) -> bool:
        """Check if this action requires a destination path"""
        return self.action in [ActionType.MOVE, ActionType.COPY, ActionType.ORGANIZE]
    
    def is_destructive(self) -> bool:
        """Check if this is a potentially destructive operation"""
        return self.action in [ActionType.DELETE, ActionType.UNINSTALL]
    
    def to_summary(self) -> str:
        """Generate a human-readable summary of the intent"""
        summary_parts = [f"Action: {self.action.value}"]
        summary_parts.append(f"Target: {self.target} ({self.target_type.value})")
        
        if self.source:
            summary_parts.append(f"From: {self.source}")
        if self.destination:
            summary_parts.append(f"To: {self.destination}")
        if self.new_name:
            summary_parts.append(f"New name: {self.new_name}")
        
        summary_parts.append(f"Confidence: {self.confidence:.0%}")
        
        return " | ".join(summary_parts)


class IntentParseError(Exception):
    """Raised when intent parsing fails"""
    pass


class LowConfidenceError(IntentParseError):
    """Raised when parsed intent has low confidence"""
    def __init__(self, confidence: float, threshold: float = 0.7):
        self.confidence = confidence
        self.threshold = threshold
        super().__init__(
            f"Intent confidence {confidence:.2f} is below threshold {threshold:.2f}"
        )