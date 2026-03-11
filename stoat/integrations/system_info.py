"""Read-only Linux system information integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess

from stoat.errors import ErrorCode


@dataclass(slots=True)
class SystemInfoResult:
    """Result of a read-only system information lookup."""

    success: bool
    message: str
    details: dict[str, object] = field(default_factory=dict)
    error_code: str | None = None


class SystemInfoIntegration:
    """Collects basic local system information without mutating state."""

    def get_disk_usage(self, path: Path) -> SystemInfoResult:
        usage = shutil.disk_usage(path)
        percent_used = round((usage.used / usage.total) * 100, 1) if usage.total else 0.0
        return SystemInfoResult(
            success=True,
            message=f"Disk usage for '{path}': {percent_used}% used.",
            details={
                "path": str(path),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "percent_used": percent_used,
            },
        )

    def get_memory_usage(self) -> SystemInfoResult:
        meminfo: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", maxsplit=1)
            meminfo[key] = int(value.strip().split()[0]) * 1024

        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        used = max(total - available, 0)
        percent_used = round((used / total) * 100, 1) if total else 0.0
        return SystemInfoResult(
            success=True,
            message=f"Memory usage: {percent_used}% used.",
            details={
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "percent_used": percent_used,
                "top_processes": self._top_memory_processes(),
            },
        )

    def get_battery_status(self) -> SystemInfoResult:
        battery_dirs = sorted(Path("/sys/class/power_supply").glob("BAT*"))
        if not battery_dirs:
            return SystemInfoResult(
                success=False,
                message="Battery information is not available on this system.",
                error_code=ErrorCode.SYSTEM_INFO_UNAVAILABLE.value,
                details={"target": "battery_status"},
            )

        battery = battery_dirs[0]
        capacity = (battery / "capacity").read_text(encoding="utf-8").strip()
        status = (battery / "status").read_text(encoding="utf-8").strip()
        return SystemInfoResult(
            success=True,
            message=f"Battery status: {capacity}% ({status}).",
            details={
                "battery": battery.name,
                "capacity_percent": int(capacity),
                "status": status,
            },
        )

    def _top_memory_processes(self) -> list[dict[str, object]]:
        result = subprocess.run(
            ["ps", "-eo", "pid=,comm=,%mem=", "--sort=-%mem"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        processes: list[dict[str, object]] = []
        for line in result.stdout.splitlines()[:5]:
            parts = line.split(None, 2)
            if len(parts) != 3:
                continue
            pid, command, memory_percent = parts
            processes.append(
                {
                    "pid": int(pid),
                    "command": command,
                    "memory_percent": float(memory_percent),
                }
            )
        return processes
