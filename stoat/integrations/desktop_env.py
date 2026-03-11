"""Desktop environment integration for launching and stopping apps."""

from __future__ import annotations

from dataclasses import dataclass, field
import shlex
import shutil
import subprocess

from stoat.errors import ErrorCode


@dataclass(slots=True)
class DesktopActionResult:
    """Result for desktop operations."""

    success: bool
    message: str
    pid: int | None = None
    error_code: str | None = None
    details: dict[str, str | int | None] = field(default_factory=dict)


class DesktopEnvironment:
    """Performs desktop-level process actions."""

    def launch_application(self, target: str) -> DesktopActionResult:
        cleaned = target.strip()
        if not cleaned:
            return DesktopActionResult(
                success=False,
                message="Application target is empty.",
                error_code=ErrorCode.INVALID_TARGET.value,
            )

        try:
            args = shlex.split(cleaned)
        except ValueError as exc:
            return DesktopActionResult(
                success=False,
                message=f"Invalid app command format: {exc}",
                error_code=ErrorCode.INVALID_APP_COMMAND.value,
                details={"target": cleaned},
            )
        binary = args[0]
        resolved = shutil.which(binary)
        if resolved is None:
            return DesktopActionResult(
                success=False,
                message=f"Application '{binary}' was not found in PATH.",
                error_code=ErrorCode.APP_NOT_FOUND.value,
                details={"binary": binary},
            )

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return DesktopActionResult(
                success=False,
                message=f"Failed to launch '{binary}': {exc}",
                error_code=ErrorCode.APP_LAUNCH_FAILED.value,
                details={"binary": binary},
            )

        return DesktopActionResult(
            success=True,
            message=f"Launched '{binary}'.",
            pid=process.pid,
            details={"binary": binary},
        )

    def close_application(self, target: str) -> DesktopActionResult:
        cleaned = target.strip()
        if not cleaned:
            return DesktopActionResult(
                success=False,
                message="Application target is empty.",
                error_code=ErrorCode.INVALID_TARGET.value,
            )

        try:
            exact_match = subprocess.run(
                ["pkill", "-x", cleaned],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return DesktopActionResult(
                success=False,
                message=f"Failed to run pkill: {exc}",
                error_code=ErrorCode.APP_CLOSE_FAILED.value,
                details={"target": cleaned},
            )
        if exact_match.returncode == 0:
            return DesktopActionResult(
                success=True,
                message=f"Stopped '{cleaned}'.",
                details={"target": cleaned, "match_mode": "exact"},
            )
        if exact_match.returncode not in {0, 1}:
            return DesktopActionResult(
                success=False,
                message=f"Failed to stop '{cleaned}': {exact_match.stderr.strip()}",
                error_code=ErrorCode.APP_CLOSE_FAILED.value,
                details={"target": cleaned, "stderr": exact_match.stderr.strip()},
            )

        try:
            fuzzy_match = subprocess.run(
                ["pkill", "-f", cleaned],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return DesktopActionResult(
                success=False,
                message=f"Failed to run pkill: {exc}",
                error_code=ErrorCode.APP_CLOSE_FAILED.value,
                details={"target": cleaned},
            )
        if fuzzy_match.returncode == 0:
            return DesktopActionResult(
                success=True,
                message=f"Stopped processes matching '{cleaned}'.",
                details={"target": cleaned, "match_mode": "fuzzy"},
            )
        if fuzzy_match.returncode == 1:
            return DesktopActionResult(
                success=False,
                message=f"No running processes matched '{cleaned}'.",
                error_code=ErrorCode.APP_NOT_RUNNING.value,
                details={"target": cleaned},
            )

        return DesktopActionResult(
            success=False,
            message=f"Failed to stop '{cleaned}': {fuzzy_match.stderr.strip()}",
            error_code=ErrorCode.APP_CLOSE_FAILED.value,
            details={"target": cleaned, "stderr": fuzzy_match.stderr.strip()},
        )
