"""Persistent undo journal for reversible file operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class UndoOperation:
    """Journal entry for one reversible operation."""

    operation_id: str
    action: str
    items: list[dict[str, str]]
    created_at: str


class UndoStack:
    """Stores undoable file operations in a JSON journal."""

    def __init__(self, storage_path: Path, max_history: int = 50) -> None:
        self._storage_path = storage_path.expanduser()
        self._max_history = max_history
        self._journal_path = self._storage_path / "operations.json"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def record(self, operation: UndoOperation) -> None:
        entries = self._read_entries()
        entries.append(asdict(operation))
        self._write_entries(entries[-self._max_history :])

    def peek_last(self) -> UndoOperation | None:
        entries = self._read_entries()
        if not entries:
            return None
        return self._from_dict(entries[-1])

    def pop_last(self) -> UndoOperation | None:
        entries = self._read_entries()
        if not entries:
            return None
        payload = entries.pop()
        self._write_entries(entries)
        return self._from_dict(payload)

    def _read_entries(self) -> list[dict[str, Any]]:
        if not self._journal_path.exists():
            return []
        return json.loads(self._journal_path.read_text())

    def _write_entries(self, entries: list[dict[str, Any]]) -> None:
        self._journal_path.write_text(json.dumps(entries, indent=2))

    def _from_dict(self, payload: dict[str, Any]) -> UndoOperation:
        return UndoOperation(
            operation_id=str(payload["operation_id"]),
            action=str(payload["action"]),
            items=[dict(item) for item in payload["items"]],
            created_at=str(payload["created_at"]),
        )
