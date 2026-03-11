"""Tests for file operations and undo."""

from pathlib import Path

from stoat.core.context import ExecutionContext
from stoat.core.intent_schema import FileFilters, Intent, IntentAction, TargetType
from stoat.handlers.file_operations import FileOperationsHandler
from stoat.integrations.file_system import FileSystem
from stoat.integrations.search_engine import SearchEngine
from stoat.integrations.trash_manager import TrashManager
from stoat.safety.permissions import PermissionGuard
from stoat.utils.undo_stack import UndoStack


def _build_handler(root: Path, *, max_batch_size: int = 100) -> FileOperationsHandler:
    storage_path = root / ".stoat"
    search_engine = SearchEngine(index_hidden_files=True, max_results=50)
    return FileOperationsHandler(
        file_system=FileSystem(search_engine=search_engine),
        trash_manager=TrashManager(storage_path),
        undo_stack=UndoStack(storage_path),
        permission_guard=PermissionGuard([str(root / "protected")]),
        max_batch_size=max_batch_size,
        enable_undo=True,
    )


def test_move_and_undo_restore_file(temp_dir) -> None:
    source = temp_dir / "source"
    destination = temp_dir / "dest"
    source.mkdir()
    destination.mkdir()
    file_path = source / "report.txt"
    file_path.write_text("hello")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir, skip_confirmations=True)
    move_intent = Intent(
        action=IntentAction.MOVE,
        target_type=TargetType.FILE,
        target="report.txt",
        source=str(source),
        destination=str(destination),
        confidence=0.95,
        raw_text="move report.txt from source to dest",
    )

    move_result = handler.handle(move_intent, context)
    undo_result = handler.handle(
        Intent(
            action=IntentAction.UNDO,
            target_type=TargetType.FILE,
            target="last_operation",
            requires_confirmation=True,
            confidence=1.0,
            raw_text="undo",
        ),
        context.with_confirmation(),
    )

    assert move_result.success is True
    assert (destination / "report.txt").exists() is False
    assert undo_result.success is True
    assert file_path.exists() is True


def test_copy_file_to_destination(temp_dir) -> None:
    source = temp_dir / "source"
    destination = temp_dir / "backup"
    source.mkdir()
    file_path = source / "report.txt"
    file_path.write_text("hello")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir)
    intent = Intent(
        action=IntentAction.COPY,
        target_type=TargetType.FILE,
        target="report.txt",
        source=str(source),
        destination=str(destination),
        confidence=0.95,
        raw_text="copy report.txt from source to backup",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert (destination / "report.txt").read_text() == "hello"
    assert file_path.exists() is True


def test_dry_run_move_previews_without_mutation(temp_dir) -> None:
    source = temp_dir / "source"
    destination = temp_dir / "dest"
    source.mkdir()
    destination.mkdir()
    file_path = source / "report.txt"
    file_path.write_text("hello")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir, dry_run=True)
    intent = Intent(
        action=IntentAction.MOVE,
        target_type=TargetType.FILE,
        target="report.txt",
        source=str(source),
        destination=str(destination),
        confidence=0.95,
        raw_text="move report.txt from source to dest",
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert result.details["dry_run"] is True
    assert file_path.exists() is True
    assert (destination / "report.txt").exists() is False


def test_delete_and_undo_restore_file(temp_dir) -> None:
    source = temp_dir / "source"
    source.mkdir()
    file_path = source / "old.log"
    file_path.write_text("hello")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir).with_confirmation()
    delete_intent = Intent(
        action=IntentAction.DELETE,
        target_type=TargetType.FILE,
        target="old.log",
        source=str(source),
        confidence=0.95,
        raw_text="delete old.log from source",
        requires_confirmation=True,
    )

    delete_result = handler.handle(delete_intent, context)
    undo_result = handler.handle(
        Intent(
            action=IntentAction.UNDO,
            target_type=TargetType.FILE,
            target="last_operation",
            requires_confirmation=True,
            confidence=1.0,
            raw_text="undo",
        ),
        context,
    )

    assert delete_result.success is True
    assert undo_result.success is True
    assert file_path.exists() is True


def test_copy_collision_is_blocked(temp_dir) -> None:
    source = temp_dir / "source"
    destination = temp_dir / "dest"
    source.mkdir()
    destination.mkdir()
    (source / "report.txt").write_text("new")
    (destination / "report.txt").write_text("existing")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir)
    intent = Intent(
        action=IntentAction.COPY,
        target_type=TargetType.FILE,
        target="report.txt",
        source=str(source),
        destination=str(destination),
        confidence=0.95,
        raw_text="copy report.txt from source to dest",
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert "already exist" in result.message.lower()


def test_protected_path_is_blocked(temp_dir) -> None:
    protected_dir = temp_dir / "protected"
    protected_dir.mkdir()
    blocked = protected_dir / "secret.txt"
    blocked.write_text("secret")
    destination = temp_dir / "dest"
    destination.mkdir()

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir)
    intent = Intent(
        action=IntentAction.MOVE,
        target_type=TargetType.FILE,
        target="secret.txt",
        source=str(protected_dir),
        destination=str(destination),
        confidence=0.95,
        raw_text="move secret.txt from protected to dest",
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert "protected path" in result.message.lower()


def test_batch_limit_is_enforced(sample_files) -> None:
    destination = sample_files / "dest"
    destination.mkdir()

    handler = _build_handler(sample_files, max_batch_size=1)
    context = ExecutionContext(cwd=sample_files, home=sample_files)
    intent = Intent(
        action=IntentAction.MOVE,
        target_type=TargetType.FILE,
        target="*",
        source=str(sample_files),
        destination=str(destination),
        confidence=0.95,
        raw_text="move all files to dest",
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert "safety limit" in result.message.lower()


def test_broad_delete_requires_explicit_confirmation(sample_files) -> None:
    handler = _build_handler(sample_files)
    intent = Intent(
        action=IntentAction.DELETE,
        target_type=TargetType.FILE,
        target="*",
        source=str(sample_files),
        confidence=0.95,
        raw_text="delete all files",
        requires_confirmation=True,
    )

    result = handler.handle(intent, ExecutionContext(cwd=sample_files, home=sample_files))

    assert result.success is False
    assert "explicit confirmation" in result.message.lower()


def test_semantic_delete_resolves_single_movie_match(temp_dir) -> None:
    videos = temp_dir / "Videos"
    videos.mkdir()
    movie = videos / "Avengers.mp4"
    movie.write_text("assembled")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir).with_confirmation()
    intent = Intent(
        action=IntentAction.DELETE,
        target_type=TargetType.FILE,
        target="avengers",
        target_items=["avengers"],
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads", "~/Desktop"],
        ),
        confidence=0.95,
        raw_text="delete the movie avengers",
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert movie.exists() is False
    assert result.details["requested_targets"] == ["avengers"]


def test_semantic_delete_reports_ambiguous_target(temp_dir) -> None:
    videos = temp_dir / "Videos"
    downloads = temp_dir / "Downloads"
    videos.mkdir()
    downloads.mkdir()
    (videos / "Avengers.mp4").write_text("movie")
    (downloads / "Avengers.mkv").write_text("movie")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir).with_confirmation()
    intent = Intent(
        action=IntentAction.DELETE,
        target_type=TargetType.FILE,
        target="avengers",
        target_items=["avengers"],
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads", "~/Desktop"],
        ),
        confidence=0.95,
        raw_text="delete the movie avengers",
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == "ambiguous_target"
    assert result.details["ambiguous_targets"][0]["query"] == "avengers"


def test_semantic_delete_resolves_multiple_movie_targets(temp_dir) -> None:
    videos = temp_dir / "Videos"
    videos.mkdir()
    avengers = videos / "Avengers.mp4"
    power_rangers = videos / "Power Rangers.mp4"
    avengers.write_text("movie")
    power_rangers.write_text("movie")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir).with_confirmation()
    intent = Intent(
        action=IntentAction.DELETE,
        target_type=TargetType.FILE,
        target="*",
        target_items=["avengers", "power rangers"],
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads", "~/Desktop"],
        ),
        confidence=0.95,
        raw_text="delete the movies avengers and power rangers",
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert avengers.exists() is False
    assert power_rangers.exists() is False


def test_semantic_move_resolves_single_movie_match(temp_dir) -> None:
    videos = temp_dir / "Videos"
    destination = temp_dir / "backup"
    videos.mkdir()
    destination.mkdir()
    movie = videos / "Avengers.mp4"
    movie.write_text("assembled")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir).with_confirmation()
    intent = Intent(
        action=IntentAction.MOVE,
        target_type=TargetType.FILE,
        target="avengers",
        target_items=["avengers"],
        destination=str(destination),
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads", "~/Desktop"],
        ),
        confidence=0.95,
        raw_text="move the movie avengers to backup",
        requires_confirmation=True,
    )

    result = handler.handle(intent, context)

    assert result.success is True
    assert movie.exists() is False
    assert (destination / "Avengers.mp4").exists() is True


def test_semantic_copy_reports_ambiguous_target(temp_dir) -> None:
    videos = temp_dir / "Videos"
    downloads = temp_dir / "Downloads"
    destination = temp_dir / "archive"
    videos.mkdir()
    downloads.mkdir()
    destination.mkdir()
    (videos / "Avengers.mp4").write_text("movie")
    (downloads / "Avengers.mkv").write_text("movie")

    handler = _build_handler(temp_dir)
    context = ExecutionContext(cwd=temp_dir, home=temp_dir)
    intent = Intent(
        action=IntentAction.COPY,
        target_type=TargetType.FILE,
        target="avengers",
        target_items=["avengers"],
        destination=str(destination),
        filters=FileFilters(
            category="video",
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm"],
            preferred_roots=["~/Videos", "~/Downloads", "~/Desktop"],
        ),
        confidence=0.95,
        raw_text="copy the movie avengers to archive",
    )

    result = handler.handle(intent, context)

    assert result.success is False
    assert result.details["error_code"] == "ambiguous_target"
    assert result.details["requested_targets"] == ["avengers"]
    assert result.details["ambiguous_targets"][0]["suggestions"]
    assert "stoat run" in result.details["ambiguous_targets"][0]["suggestions"][0]
