# Contributing

## Development Setup

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check stoat tests
uv run black --check stoat tests
```

Optional local LLM support:

```bash
uv sync --extra dev --extra llm
```

## Change Expectations

- Keep Stoat usable without any LLM dependency.
- Preserve the safe local-operations model.
- Add or update tests for behavior changes.
- Keep JSON output stable for automation.

## Release Notes

- Update `CHANGELOG.md` for user-visible changes.
- Keep the version in `pyproject.toml` aligned with release tags.
- See `docs/releasing.md` for the release process.
