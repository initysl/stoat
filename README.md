# Stoat 🦡 

**Offline AI Assistant for Linux** - Smart, Quick, Local

Stoat is a privacy-first, offline AI assistant for Linux that lets you control your system using natural language. No cloud, no telemetry, just fast local processing.

## Features

- 🔒 **100% Offline** - All processing happens locally on your machine
- ⚡ **Fast** - Powered by optimized local LLM (Llama 3.2 3B)
- 🎯 **Precise** - Advanced intent parsing for accurate command execution
- 🛡️ **Safe** - Built-in safety checks and confirmations for destructive operations
- 🔄 **Undo** - Roll back file operations with full undo support

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

### Installation
```bash
# Install Ollama and download model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b-instruct-q4_K_M

# Install Stoat
pip install stoat

# Or install from source
git clone https://github.com/yourusername/stoat.git
cd stoat
poetry install
```

### Usage
```bash
# Launch an application
stoat run "open firefox"

# Find files
stoat run "find my tax documents from last year"

# Organize files
stoat run "move all PDFs from Downloads to Documents"

# Close applications
stoat run "close all chrome windows"

# Check system info
stoat run "what's using all my RAM?"
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Examples](docs/examples.md)
- [Current Usage](docs/usage.md)
- [Execution Roadmap](docs/roadmap.md)
- [Configuration](docs/configuration.md)
- [Safety Features](docs/safety.md)

## Development
```bash
# Setup development environment
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black .
poetry run ruff check .
```

## License

MIT License - See [LICENSE](LICENSE) for details

## Contributing

Contributions welcome! Please read our contributing guidelines first.
