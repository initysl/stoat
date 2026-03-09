# Installation Guide

## Prerequisites

- Linux (Ubuntu 22.04+, Fedora 39+, Arch, etc.)
- Python 3.11 or higher
- Ollama

## Step-by-Step Installation

### 1. Install Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Download LLM Model
```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```

### 3. Install Stoat

**For normal use:**
```bash
pip install stoat
```

Then run:
```bash
stoat version
```

**For development from source:**
```bash
git clone https://github.com/yourusername/stoat.git
cd stoat
uv sync --extra dev
```

### 4. Verify Installation
```bash
uv run stoat version
```

You're ready to go! 🦡
