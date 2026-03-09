"""Filesystem abstraction for Stoat's file operations."""

from __future__ import annotations

from pathlib import Path
import shutil

from stoat.integrations.search_engine import SearchEngine


class FileSystem:
    """Encapsulates path resolution and local file mutations."""

    def __init__(self, search_engine: SearchEngine | None = None) -> None:
        self._search_engine = search_engine or SearchEngine()

    def resolve_path(self, raw_path: str | None, *, cwd: Path, home: Path) -> Path:
        if not raw_path:
            return cwd
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            if raw_path.startswith("~"):
                candidate = home / raw_path[2:]
            else:
                candidate = cwd / raw_path
        return candidate.resolve()

    def resolve_targets(self, target: str, *, base_dir: Path) -> list[Path]:
        explicit = Path(target).expanduser()
        if explicit.is_absolute() and explicit.exists():
            return [explicit.resolve()]

        relative_candidate = (base_dir / target).expanduser()
        if relative_candidate.exists():
            return [relative_candidate.resolve()]

        return [path.resolve() for path in self._search_engine.search(base_dir, target)]

    def ensure_directory(self, destination: Path) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def plan_transfer(
        self, paths: list[Path], destination_dir: Path
    ) -> list[dict[str, str | bool]]:
        return [
            {
                "original_path": str(path),
                "destination_path": str(destination_dir / path.name),
                "will_overwrite": (destination_dir / path.name).exists(),
            }
            for path in paths
        ]

    def move(self, paths: list[Path], destination_dir: Path) -> list[dict[str, str]]:
        destination_dir = self.ensure_directory(destination_dir)
        items: list[dict[str, str]] = []
        for path in paths:
            destination = destination_dir / path.name
            shutil.move(str(path), str(destination))
            items.append({"original_path": str(path), "destination_path": str(destination)})
        return items

    def copy(self, paths: list[Path], destination_dir: Path) -> list[dict[str, str]]:
        destination_dir = self.ensure_directory(destination_dir)
        items: list[dict[str, str]] = []
        for path in paths:
            destination = destination_dir / path.name
            if path.is_dir():
                shutil.copytree(path, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(path, destination)
            items.append({"original_path": str(path), "destination_path": str(destination)})
        return items

    def undo_move(self, items: list[dict[str, str]]) -> None:
        for item in reversed(items):
            destination = Path(item["destination_path"])
            original = Path(item["original_path"])
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(original))
