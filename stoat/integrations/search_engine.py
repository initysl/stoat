"""Simple local search engine for file discovery."""

from __future__ import annotations

from pathlib import Path


class SearchEngine:
    """Find files by glob or case-insensitive name matching."""

    def __init__(self, index_hidden_files: bool = False, max_results: int = 50) -> None:
        self._index_hidden_files = index_hidden_files
        self._max_results = max_results

    def search(self, base_dir: Path, query: str) -> list[Path]:
        if not base_dir.exists():
            return []

        matches: list[Path] = []
        if self._looks_like_glob(query):
            for path in base_dir.rglob(query):
                if self._is_visible(path):
                    matches.append(path)
        else:
            needle = query.lower()
            for path in base_dir.rglob("*"):
                if not self._is_visible(path):
                    continue
                if needle in path.name.lower():
                    matches.append(path)

        matches.sort(key=lambda candidate: (len(candidate.parts), candidate.name.lower()))
        return matches[: self._max_results]

    def _looks_like_glob(self, query: str) -> bool:
        return any(token in query for token in "*?[]")

    def _is_visible(self, path: Path) -> bool:
        if self._index_hidden_files:
            return True
        return not any(part.startswith(".") for part in path.relative_to(path.anchor or "/").parts)
