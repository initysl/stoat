#!/bin/bash
# Setup development environment

set -e

echo "Setting up Stoat development environment..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.11+ required, found $python_version"
    exit 1
fi

# Install Poetry if not installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Setup pre-commit hooks (optional)
poetry run pre-commit install 2>/dev/null || true

echo "✓ Development environment ready!"
echo ""
echo "Quick commands:"
echo "  poetry run stoat --help"
echo "  poetry run pytest"
echo "  poetry run black ."
