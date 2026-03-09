"""Desktop environment integration for launching and stopping apps."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
import shutil
import subprocess


@dataclass(slots=True)
class DesktopActionResult:
    """Result for desktop operations."""

    success: bool
    message: str
    pid: int | None = None


class DesktopEnvironment:
    """Performs desktop-level process actions."""

    def launch_application(self, target: str) -> DesktopActionResult:
        cleaned = target.strip()
        if not cleaned:
            return DesktopActionResult(success=False, message="Application target is empty.")

        try:
            args = shlex.split(cleaned)
        except ValueError as exc:
            return DesktopActionResult(success=False, message=f"Invalid app command format: {exc}")
        binary = args[0]
        resolved = shutil.which(binary)
        if resolved is None:
            return DesktopActionResult(
                success=False,
                message=f"Application '{binary}' was not found in PATH.",
            )

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return DesktopActionResult(success=False, message=f"Failed to launch '{binary}': {exc}")

        return DesktopActionResult(
            success=True,
            message=f"Launched '{binary}'.",
            pid=process.pid,
        )

    def close_application(self, target: str) -> DesktopActionResult:
        cleaned = target.strip()
        if not cleaned:
            return DesktopActionResult(success=False, message="Application target is empty.")

        try:
            exact_match = subprocess.run(
                ["pkill", "-x", cleaned],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return DesktopActionResult(success=False, message=f"Failed to run pkill: {exc}")
        if exact_match.returncode == 0:
            return DesktopActionResult(success=True, message=f"Stopped '{cleaned}'.")
        if exact_match.returncode not in {0, 1}:
            return DesktopActionResult(
                success=False,
                message=f"Failed to stop '{cleaned}': {exact_match.stderr.strip()}",
            )

        try:
            fuzzy_match = subprocess.run(
                ["pkill", "-f", cleaned],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return DesktopActionResult(success=False, message=f"Failed to run pkill: {exc}")
        if fuzzy_match.returncode == 0:
            return DesktopActionResult(
                success=True, message=f"Stopped processes matching '{cleaned}'."
            )
        if fuzzy_match.returncode == 1:
            return DesktopActionResult(
                success=False,
                message=f"No running processes matched '{cleaned}'.",
            )

        return DesktopActionResult(
            success=False,
            message=f"Failed to stop '{cleaned}': {fuzzy_match.stderr.strip()}",
        )
