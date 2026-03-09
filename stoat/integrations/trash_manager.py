"""Trash-based delete support for reversible file operations."""

from __future__ import annotations

import shutil
from pathlib import Path
import uuid


class TrashManager:
    """Moves deleted paths into Stoat-managed trash storage."""

    def __init__(self, storage_path: Path) -> None:
        self._trash_root = storage_path.expanduser() / "trash"
        self._trash_root.mkdir(parents=True, exist_ok=True)

    def stage(self, paths: list[Path]) -> tuple[str, list[dict[str, str]]]:
        operation_id = uuid.uuid4().hex
        operation_root = self._trash_root / operation_id
        operation_root.mkdir(parents=True, exist_ok=True)

        items: list[dict[str, str]] = []
        for index, path in enumerate(paths):
            staged_name = f"{index}_{path.name}"
            staged_path = operation_root / staged_name
            shutil.move(str(path), str(staged_path))
            items.append({"original_path": str(path), "trash_path": str(staged_path)})

        return operation_id, items

    def restore(self, trash_path: Path, original_path: Path) -> None:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash_path), str(original_path))
