# Usage Guide

## Installed Usage

If Stoat is installed normally, use:

```bash
stoat run "<your request>"
```

## Current MVP Commands

```bash
stoat run "open firefox"
stoat run "close firefox"
stoat run "find report"
stoat run "find my latest download"
stoat run --dry-run "move report.pdf from Downloads to Documents"
stoat run "copy report.txt from source to backup"
stoat run "delete old.log from logs"
stoat run "show disk usage"
stoat run "what's using my ram"
stoat run "battery status"
stoat history
stoat undo --yes
stoat doctor
```

## Confirmation Behavior

- Commands marked risky require confirmation.
- Use `--yes` to skip confirmations:

```bash
stoat run --yes "close firefox"
```

## From Source During Development

If you are running Stoat from the repository checkout, use:

```bash
uv run stoat run "<your request>"
```

## Notes

- Parsing is currently rule-based and deterministic.
- Optional LLM support is not required for the current release.
- Unknown requests return a guidance message instead of guessing.
