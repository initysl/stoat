# Usage Examples

These examples reflect the currently implemented CLI behavior.

## File Search

```bash
stoat run "find report"
stoat run "find pdf files"
stoat run "find my latest download"
stoat run "where did i save my screenshot"
stoat run --json "i saved a file named abc, find it"
```

## File Operations

```bash
stoat run --dry-run "move report.pdf from Downloads to Documents"
stoat run "copy report.txt from source to backup"
stoat run "delete old.log from logs"
stoat undo --yes
stoat history
```

## Application Management

```bash
stoat run "open firefox"
stoat run --yes "close firefox"
stoat run --json "open definitely-not-a-real-app"
```

## Diagnostics

```bash
stoat doctor
stoat doctor --json
```

## System Information

```bash
stoat run "show disk usage"
stoat run "what's using my ram"
stoat run "battery status"
```

## Notes

- Broad or unsupported requests return a guidance message instead of guessing.
- Optional LLM support is not required for the current release.
