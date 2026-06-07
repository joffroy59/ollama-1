#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

# Configuration
MODELS="gemma3:12b,gemma4,gemma4:e2b,gemma4:e4b,gemma3n:latest"
EPOCHS=6
MAX_TOKENS=100
PROMPT="Write me a short story"
LOG_FILE="gemma3.bench"
PLOT_SCRIPT="plot_ollama_bench.py"

echo "🚀 Starting Ollama Benchmark for 5 models..."
echo "📋 Models: $MODELS"
echo "🔢 Epochs: $EPOCHS | Max Tokens: $MAX_TOKENS"
echo "--------------------------------------------------"

# Ensure the python script is executable
if [ -f "$PLOT_SCRIPT" ]; then
    chmod +x "$PLOT_SCRIPT"
else
    echo "❌ Error: $PLOT_SCRIPT not found in the current directory!"
    exit 1
fi

# Execute benchmark, save logs, and plot dynamically via stdin
./ollama-bench -model "$MODELS" -epochs "$EPOCHS" -max-tokens "$MAX_TOKENS" -p "$PROMPT" \
    | tee "$LOG_FILE" \
    | python3 "$PLOT_SCRIPT"

echo "--------------------------------------------------"
echo "✅ Workflow complete! Logs saved to '$LOG_FILE'."

# Optional: Create a generic symlink to the latest generated chart for quick viewing
GENERATED_CHART="gemma3_12b_vs_gemma4_vs_gemma4_e2b_vs_gemma4_e4b_vs_gemma3n_latest.png"
if [ -f "$GENERATED_CHART" ]; then
    ln -sf "$GENERATED_CHART" latest_comparison.png
    echo "🔗 Linked '$GENERATED_CHART' -> 'latest_comparison.png'"
fi