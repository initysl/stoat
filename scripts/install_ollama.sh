#!/bin/bash
# Install Ollama and required models

set -e

echo "Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

echo "Pulling Llama 3.2 3B model..."
ollama pull llama3.2:3b-instruct-q4_K_M

echo "✓ Ollama setup complete!"
echo "Starting Ollama service..."
ollama serve &

echo "✓ Ready to use Stoat!"
