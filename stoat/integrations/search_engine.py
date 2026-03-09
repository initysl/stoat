"""Simple local search engine for file discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stoat.core.intent_schema import FileFilters


@dataclass(frozen=True, slots=True)
class SearchMatch:
    """Ranked file search match."""

    path: Path
    score: int


class SearchEngine:
    """Find files by glob or case-insensitive name matching."""

    def __init__(self, index_hidden_files: bool = False, max_results: int = 50) -> None:
        self._index_hidden_files = index_hidden_files
        self._max_results = max_results

    def search(
        self, base_dir: Path, query: str, filters: FileFilters | None = None
    ) -> list[SearchMatch]:
        if not base_dir.exists():
            return []

        if self._looks_like_glob(query):
            matches = self._search_by_glob(base_dir, query, filters)
        else:
            matches = self._search_by_score(base_dir, query, filters)

        if filters and filters.sort_by == "modified":
            matches.sort(
                key=lambda match: (
                    (
                        -int(match.path.stat().st_mtime)
                        if filters.descending
                        else int(match.path.stat().st_mtime)
                    ),
                    -match.score,
                    len(match.path.parts),
                )
            )
        else:
            matches.sort(
                key=lambda match: (-match.score, len(match.path.parts), match.path.name.lower())
            )

        limit = filters.limit if filters and filters.limit is not None else self._max_results
        return matches[:limit]

    def _search_by_glob(
        self,
        base_dir: Path,
        query: str,
        filters: FileFilters | None,
    ) -> list[SearchMatch]:
        matches: list[SearchMatch] = []
        for path in base_dir.rglob(query):
            if self._is_candidate(path, filters):
                matches.append(SearchMatch(path=path, score=90))
        return matches

    def _search_by_score(
        self,
        base_dir: Path,
        query: str,
        filters: FileFilters | None,
    ) -> list[SearchMatch]:
        matches: list[SearchMatch] = []
        needle = query.lower()
        if self._looks_like_glob(query):
            return self._search_by_glob(base_dir, query, filters)
        for path in base_dir.rglob("*"):
            if not self._is_candidate(path, filters):
                continue
            score = self._score_match(path, needle)
            if score > 0:
                matches.append(SearchMatch(path=path, score=score))
        return matches

    def _looks_like_glob(self, query: str) -> bool:
        return any(token in query for token in "*?[]")

    def _is_candidate(self, path: Path, filters: FileFilters | None) -> bool:
        if not path.is_file():
            return False
        if not self._is_visible(path):
            return False
        if filters is None:
            return True
        allowed_extensions = set()
        if filters.extension:
            allowed_extensions.add(filters.extension.lower())
        if filters.extensions:
            allowed_extensions.update(extension.lower() for extension in filters.extensions)
        if allowed_extensions and path.suffix.lower() not in allowed_extensions:
            return False
        if filters.name_contains and filters.name_contains.lower() not in path.name.lower():
            return False
        return True

    def _is_visible(self, path: Path) -> bool:
        if self._index_hidden_files:
            return True
        return not any(part.startswith(".") for part in path.relative_to(path.anchor or "/").parts)

    def _score_match(self, path: Path, needle: str) -> int:
        if not needle or needle == "*":
            return 60
        name = path.name.lower()
        stem = path.stem.lower()
        full_path = str(path).lower()

        if name == needle:
            return 120
        if stem == needle:
            return 110
        if name.startswith(needle):
            return 95
        if stem.startswith(needle):
            return 90
        if needle in name:
            return 80
        if needle in stem:
            return 75
        if needle in full_path:
            return 50
        return 0
