# Usage Examples

These examples reflect the currently implemented CLI behavior.

## File Search

```bash
stoat run "find report"
stoat run "find pdf files"
stoat run "find my latest download"
stoat run "find all my movies"
stoat run "where did i save my screenshot"
stoat run --json "i saved a file named abc, find it"
```

## File Operations

```bash
stoat run --dry-run "move report.pdf from Downloads to Documents"
stoat run --dry-run "move my latest screenshot to Desktop"
stoat run "copy all my movies to archive"
stoat run "copy report.txt from source to backup"
stoat run "delete the movie avengers"
stoat run "delete old.log from logs"
stoat undo --yes
stoat history
```

## Ambiguity Resolution

```bash
stoat run "delete the movie avengers"
```

If multiple files match, Stoat shows numbered options in text mode and lets you choose one path
before continuing. In JSON mode it returns candidate matches and copy-pasteable suggestions.

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
