#!/bin/bash
# Install the optional Ollama backend for Stoat semantic parsing.

set -e

MODEL="${STOAT_OLLAMA_MODEL:-llama3.2:3b-instruct-q4_K_M}"

echo "Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

echo "Pulling model: ${MODEL}"
ollama pull "${MODEL}"

echo "Ollama install complete."
echo "If the Ollama service is not already running, start it with:"
echo "  ollama serve"
echo
echo "Then configure Stoat with:"
echo "  [parser]"
echo "  mode = \"hybrid\""
echo
echo "  [llm]"
echo "  provider = \"ollama\""
echo "  model = \"${MODEL}\""

echo "Stoat can now use the optional Ollama backend."
