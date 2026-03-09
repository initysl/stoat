"""Tests for undo journal history reads."""

from datetime import UTC, datetime, timedelta

from stoat.utils.undo_stack import UndoOperation, UndoStack


def test_list_recent_returns_newest_first(temp_dir) -> None:
    stack = UndoStack(temp_dir)
    stack.record(
        UndoOperation(
            operation_id="1",
            action="move",
            items=[{"original_path": "/tmp/a", "destination_path": "/tmp/b"}],
            created_at=(datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
        )
    )
    stack.record(
        UndoOperation(
            operation_id="2",
            action="delete",
            items=[{"original_path": "/tmp/c", "trash_path": "/tmp/t"}],
            created_at=datetime.now(UTC).isoformat(),
        )
    )

    operations = stack.list_recent()

    assert [operation.operation_id for operation in operations] == ["2", "1"]


def test_list_recent_applies_retention_days(temp_dir) -> None:
    stack = UndoStack(temp_dir)
    stack.record(
        UndoOperation(
            operation_id="old",
            action="move",
            items=[{"original_path": "/tmp/a", "destination_path": "/tmp/b"}],
            created_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
        )
    )
    stack.record(
        UndoOperation(
            operation_id="new",
            action="delete",
            items=[{"original_path": "/tmp/c", "trash_path": "/tmp/t"}],
            created_at=datetime.now(UTC).isoformat(),
        )
    )

    operations = stack.list_recent(retention_days=7)

    assert [operation.operation_id for operation in operations] == ["new"]
