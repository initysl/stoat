# Usage Guide

## Installed Usage

If Stoat is installed normally, use:

```bash
stoat run "<your request>"
```

## Current MVP Commands

```bash
stoat run "open firefox"
stoat run "open chrome"
stoat run "close firefox"
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

- Parsing is currently rule-based for launch and close intents.
- Unknown requests return a guidance message.
