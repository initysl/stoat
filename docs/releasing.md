# Releasing Stoat

This project currently uses:

- Semantic version tags like `v0.1.0`
- `pyproject.toml` as the package version source of truth
- `CHANGELOG.md` for human-readable release notes
- GitHub Actions to test, build, smoke-install, publish, and create a GitHub release

## Release Checklist

1. Make sure the branch is clean and merged.
2. Run the local verification commands:
```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check stoat tests
uv run python -Im build --sdist --wheel --outdir dist
```
3. Update the version in `pyproject.toml`.
4. Move relevant items from `Unreleased` in `CHANGELOG.md` into a new version section.
5. Commit the release prep.
6. Create and push the tag:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## What CI Does On Tag Push

When a tag matching `v*` is pushed, the release workflow:

1. Verifies the tag version matches `pyproject.toml`.
2. Verifies the changelog contains that version heading.
3. Runs the test suite.
4. Builds source and wheel distributions.
5. Smoke-installs the wheel into a fresh environment.
6. Publishes to PyPI.
7. Creates a GitHub release with the built artifacts.

## Notes

- Use `uv run python -Im build --sdist --wheel --outdir dist` locally to mirror the release
  workflow. The `-I` flag avoids local path shadowing from the repo's `build/` directory.
- Optional LLM support is not required for the main release artifact.
- Do not create release tags before the changelog and version are updated together.
