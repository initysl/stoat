# Stoat Execution Roadmap

This roadmap is ordered to keep momentum while preventing architecture drift.

## Phase 1: MVP Command Loop (Complete in this branch)

Goal: make `stoat run "<text>"` execute at least one real action safely.

Steps:
1. Implement parser for launch/close app intents.
2. Route intents to an app-management handler.
3. Integrate Linux process launching and stopping.
4. Add confirmation gate for risky actions.
5. Add unit and integration tests for this vertical slice.

Exit criteria:
- `stoat run "open firefox"` attempts launch.
- `stoat run "close firefox"` asks confirmation by default.
- Parser, safety, and routing tests pass.

## Phase 2: File Operations + Undo

Goal: safe local file manipulation (move/copy/delete) with rollback support.

Steps:
1. Implement `file_operations` handler with strict argument validation.
2. Add path safety checks via protected paths and allowlists.
3. Build trash-based delete and operation journal in `undo_stack`.
4. Add undo command: `stoat undo`.
5. Add batch operation limits and dry-run mode.

Exit criteria:
- Move/copy/delete intents work on test fixtures.
- Undo restores last destructive file operation.
- Protected paths cannot be modified.

## Phase 3: Search and Indexing

Goal: reliable file/app search with consistent ranking and filters.

Steps:
1. Implement search integration (`locate` fallback to filesystem scan).
2. Add fuzzy matcher scoring and type/date filters.
3. Standardize response formatting for top-N results.
4. Add performance benchmarks on large directories.

Exit criteria:
- Search queries return ranked relevant results.
- Hidden-file and result-limit config values are enforced.

## Phase 4: LLM-Assisted Intent Parsing

Goal: support broader language while preserving deterministic safety.

Steps:
1. Keep rule-based parser as primary fast path.
2. Add Ollama-backed parser fallback for unknown intents.
3. Validate LLM output against strict intent schema.
4. Add confidence threshold and clarification prompts.
5. Log parser decisions for debugging.

Exit criteria:
- Unknown intents can resolve through Ollama with schema-safe output.
- Unsafe/ambiguous intents are rejected or require clarification.

## Phase 5: Observability and Reliability

Goal: production quality behavior and diagnosability.

Steps:
1. Implement structured logging and rotating log files.
2. Add command history with replay metadata.
3. Add error taxonomy and user-facing remediation messages.
4. Add property tests for parser and safety boundaries.
5. Add CI gates for lint, typing, tests, and coverage threshold.

Exit criteria:
- Failures are actionable from logs.
- CI blocks regressions on parsing and safety logic.

## Phase 6: Packaging and Release

Goal: make installation and updates predictable for users.

Steps:
1. Finalize package metadata (authors, repo URL, classifiers).
2. Add semantic versioning and changelog process.
3. Publish signed releases to PyPI and GitHub Releases.
4. Validate installation on Ubuntu/Fedora/Arch matrices.

Exit criteria:
- Release pipeline produces installable artifacts.
- `pip install stoat` and `stoat version` work on clean machines.

## Suggested Weekly Cadence

1. Week 1: Phase 2 core + tests.
2. Week 2: Phase 2 undo hardening + Phase 3 baseline search.
3. Week 3: Phase 4 LLM fallback with strict schema validation.
4. Week 4: Phase 5/6 release hardening and public alpha.
