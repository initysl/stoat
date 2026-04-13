#!/bin/bash
# Setup development environment

set -e

echo "Setting up Stoat development environment..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.10+ required, found $python_version"
    exit 1
fi

# Install uv if not installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
echo "Installing dependencies..."
uv sync --extra dev

# Setup pre-commit hooks (optional)
uv run pre-commit install 2>/dev/null || true

echo "✓ Development environment ready!"
echo ""
echo "Quick commands:"
echo "  uv run stoat --help"
echo "  uv run pytest"
echo "  uv run black stoat tests config setup.py"
