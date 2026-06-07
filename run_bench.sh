#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

# Configuration
EPOCHS=6
MAX_TOKENS=100
PROMPT="Write me a short story"
PLOT_SCRIPT="plot_ollama_bench.py"

# Handle MODELS parameter
if [ -n "$1" ]; then
    MODELS="$1"
else
    # Prompt user for models if not provided
    read -p "📋 Enter models to benchmark (comma-separated, default: gemma4): " MODELS
    MODELS="${MODELS:-gemma4}"
fi

# Generate a clean default bench filename based on the models string
# Replaces colons and commas with underscores
CLEAN_MODELS=$(echo "$MODELS" | sed 's/[:]/_/g' | sed 's/,/_vs_/g')
DEFAULT_LOG_FILE="${CLEAN_MODELS}.bench"

# If a second parameter is passed, use it as the log filename; otherwise, use the default
LOG_FILE="${2:-$DEFAULT_LOG_FILE}"

echo "🚀 Starting Ollama Benchmark for 5 models..."
echo "📋 Models:"
echo "$MODELS" | tr ',' '\n' | sed 's/^/   • /'
echo "🔢 Epochs: $EPOCHS | Max Tokens: $MAX_TOKENS"
echo "📁 Output Log File: $LOG_FILE"
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
echo "✅ Workflow complete! Raw log data saved to '$LOG_FILE'."

# Create a generic symlink to the latest generated chart for quick viewing
GENERATED_CHART="${CLEAN_MODELS}.png"
if [ -f "$GENERATED_CHART" ]; then
    ln -sf "$GENERATED_CHART" latest_comparison.png
    echo "🔗 Linked '$GENERATED_CHART' -> 'latest_comparison.png'"
fi