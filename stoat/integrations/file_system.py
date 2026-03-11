"""Filesystem abstraction for Stoat's file operations."""

from __future__ import annotations

from pathlib import Path
import shutil

from stoat.core.intent_schema import FileFilters
from stoat.integrations.search_engine import SearchEngine


class FileSystem:
    """Encapsulates path resolution and local file mutations."""

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
        fallback_roots: list[str] | None = None,
    ) -> None:
        self._search_engine = search_engine or SearchEngine()
        self._fallback_roots = fallback_roots or []

    def resolve_path(self, raw_path: str | None, *, cwd: Path, home: Path) -> Path:
        if not raw_path:
            return cwd
        if raw_path == "~":
            candidate = home
        elif raw_path.startswith("~/"):
            candidate = home / raw_path[2:]
        else:
            candidate = Path(raw_path).expanduser()
            if not candidate.is_absolute():
                candidate = cwd / raw_path
        return candidate.resolve()

    def resolve_search_roots(
        self,
        *,
        base_dir: Path,
        home: Path,
        filters: FileFilters | None = None,
        explicit_source: bool,
    ) -> list[Path]:
        if explicit_source:
            return [base_dir]

        roots: list[Path] = []
        if filters and filters.preferred_roots:
            for raw_root in filters.preferred_roots:
                roots.append(self.resolve_path(raw_root, cwd=home, home=home))

        roots.append(base_dir)

        unique_roots: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            if root in seen:
                continue
            seen.add(root)
            unique_roots.append(root)
        return unique_roots

    def search_matches(
        self,
        target: str,
        *,
        base_dir: Path,
        home: Path,
        filters: FileFilters | None = None,
        explicit_source: bool,
    ):
        search_roots = self.resolve_search_roots(
            base_dir=base_dir,
            home=home,
            filters=filters,
            explicit_source=explicit_source,
        )
        matches = self._search_engine.search_many(search_roots, target, filters)
        if (
            not matches
            and not explicit_source
            and self._fallback_roots
        ):
            fallback_roots = [
                self.resolve_path(raw_root, cwd=home, home=home)
                for raw_root in self._fallback_roots
            ]
            search_roots = [
                *search_roots,
                *[root for root in fallback_roots if root not in search_roots],
            ]
            matches = self._search_engine.search_many(search_roots, target, filters)
        return matches, search_roots

    def resolve_exact_target(self, target: str, *, base_dir: Path) -> Path | None:
        explicit = Path(target).expanduser()
        if explicit.is_absolute() and explicit.exists():
            return explicit.resolve()
        relative_candidate = (base_dir / target).expanduser()
        if relative_candidate.exists():
            return relative_candidate.resolve()
        return None

    def resolve_targets(
        self,
        target: str,
        *,
        base_dir: Path,
        home: Path,
        filters: FileFilters | None = None,
        explicit_source: bool,
    ) -> list[Path]:
        exact_target = self.resolve_exact_target(target, base_dir=base_dir)
        if exact_target is not None:
            return [exact_target]

        matches, _ = self.search_matches(
            target,
            base_dir=base_dir,
            home=home,
            filters=filters,
            explicit_source=explicit_source,
        )
        return [match.path.resolve() for match in matches]

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
