# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## Unreleased

### Added

- Structured JSON output across CLI commands.
- Dry-run previews for file operations.
- Structured error codes and JSONL logging.
- Release smoke checks in CI.

### Changed

- Rule-based parser expanded for conversational file-search requests.
- Package metadata aligned with the current CLI-first product.

## 0.1.3 - 2025-04-13

### Fixed

- Ollama availability check in `stoat doctor` (missing `/api/tags` endpoint)

## 0.1.2 - 2025-04-13

### Changed

- Moved ollama to main dependencies (was optional)
- Added psutil as core dependency for process management

### Added

- pipx installation support

## 0.1.1 - 2025-04-13

### Added

- Initial public alpha for Stoat as a safe local Linux operations engine.
- Natural-language CLI for:
  - app launch and close
  - file search
  - file move, copy, and delete
  - undo and history
- Safety controls:
  - confirmation prompts
  - protected path blocking
  - batch limits
  - dry-run previews
- Diagnostics via `stoat doctor`.
- `uv`-based development and CI workflow.
