# Stoat

**Safe local Linux operations engine** with a natural-language CLI.

Stoat turns short English requests into constrained local actions like finding files, moving/copying/deleting them safely, launching apps, undoing Stoat-managed changes, and showing recent history. It is terminal-first, Linux-only, and designed around confirmation, auditability, and reversible operations.

## Features

- Safe local file operations with confirmation, protected paths, and batch limits
- Natural-language file search with rule-based parsing
- App launch and close support for Linux desktop workflows
- Undo and history for Stoat-managed reversible operations
- Pretty JSON output for scripting and future integrations
- Optional diagnostics with `stoat doctor`

## Quick Start

### Prerequisites

- Linux
- Python 3.11+

### Installation
```bash
# Install Stoat for normal use
pip install stoat
```

Optional LLM support is not required for the current rule-based product. If you want the optional parser backend later:
```bash
pip install "stoat[llm]"
```

### Usage
```bash
stoat run "open firefox"
stoat run "find my latest download"
stoat run --dry-run "move report.pdf from Downloads to Documents"
stoat run "delete old.log from logs"
stoat history
stoat undo --yes
stoat doctor
```

### From Source
```bash
git clone https://github.com/initysl/stoat.git
cd stoat
uv sync --extra dev

# Run from the project environment while developing
uv run stoat run "find report"

# Optional local LLM support while developing
uv sync --extra dev --extra llm
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Examples](docs/examples.md)
- [Current Usage](docs/usage.md)
- [Execution Roadmap](docs/roadmap.md)
- [Configuration](docs/configuration.md)
- [Safety Features](docs/safety.md)
- [Release Process](docs/releasing.md)
- [Changelog](CHANGELOG.md)

## Development
```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check stoat tests
uv run black --check stoat tests
uv build
```

## License

MIT License - See [LICENSE](LICENSE) for details

## Contributing

Contributions welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.
