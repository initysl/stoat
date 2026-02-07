"""Filesystem permission helpers used by safety checks."""

from __future__ import annotations

from pathlib import Path


class PermissionGuard:
    """Checks whether paths are inside protected system locations."""

    def __init__(self, protected_paths: list[str] | None = None) -> None:
        raw_paths = protected_paths or ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc"]
        self._protected = [Path(path).resolve() for path in raw_paths]

    def is_protected_path(self, candidate: Path) -> bool:
        resolved = candidate.expanduser().resolve()
        return any(resolved == protected or protected in resolved.parents for protected in self._protected)
