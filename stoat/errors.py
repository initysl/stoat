"""Shared error codes for CLI and handlers."""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Stable machine-readable failure categories."""

    COMMAND_FAILED = "command_failed"
    CONFIG_ERROR = "config_error"
    PARSE_ERROR = "parse_error"
    UNKNOWN_INTENT = "unknown_intent"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"
    PROTECTED_PATH = "protected_path"
    BATCH_LIMIT = "batch_limit"
    COLLISION = "collision"
    CONFIRMATION_REQUIRED = "confirmation_required"
    ROUTER_NO_HANDLER = "router_no_handler"
    INVALID_TARGET = "invalid_target"
    UNDO_DISABLED = "undo_disabled"
    NOTHING_TO_UNDO = "nothing_to_undo"
    UNSUPPORTED_UNDO = "unsupported_undo"
    APP_LAUNCH_FAILED = "app_launch_failed"
    APP_CLOSE_FAILED = "app_close_failed"
