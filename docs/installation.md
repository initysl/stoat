# Installation Guide

## Prerequisites

- Linux (Ubuntu 22.04+, Fedora 39+, Arch, etc.)
- Python 3.11 or higher
- `uv` for from-source development, or `pipx` for installed usage

## Install Stoat

### Installed usage

```bash
pipx install stoat-linux
```

Optional LLM backend support:

```bash
pipx install "stoat-linux[llm]"
```

Verify the install:

```bash
stoat version
stoat doctor
```

### Development from source

```bash
git clone https://github.com/initysl/stoat.git
cd stoat
uv sync --extra dev
```

Optional local LLM dependencies during development:

```bash
uv sync --extra dev --extra llm
```

Verify the development setup:

```bash
uv run stoat version
uv run pytest -q
uv build
```
