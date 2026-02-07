# Usage Guide

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

## Notes

- Parsing is currently rule-based for launch and close intents.
- Unknown requests return a guidance message.
