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

# Execute benchmark with synchronized trace and progress
# Convert comma-separated models to array
IFS=',' read -ra MODEL_ARRAY <<< "$MODELS"
TOTAL_MODELS=${#MODEL_ARRAY[@]}
CURRENT=0
BAR_WIDTH=40

draw_progress_bar() {
    local completed="$1"
    local total="$2"
    local label="$3"
    local filled=$(( completed * BAR_WIDTH / total ))
    local empty=$(( BAR_WIDTH - filled ))
    local percent=$(( completed * 100 / total ))
    local done_bar
    local todo_bar

    done_bar=$(printf '%*s' "$filled" '' | tr ' ' '#')
    todo_bar=$(printf '%*s' "$empty" '' | tr ' ' '-')
    printf "\r[%s%s] %3d%% (%d/%d) %s" "$done_bar" "$todo_bar" "$percent" "$completed" "$total" "$label"
}

run_with_progress_bar() {
    local pid="$1"
    local completed="$2"
    local total="$3"
    local model="$4"
    local percent
    local filled
    local empty
    local done_bar
    local todo_bar
    local started_at
    local now
    local elapsed

    started_at=$(date +%s)

    while kill -0 "$pid" 2>/dev/null; do
        percent=$(( completed * 100 / total ))
        filled=$(( completed * BAR_WIDTH / total ))
        empty=$(( BAR_WIDTH - filled ))
        done_bar=$(printf '%*s' "$filled" '' | tr ' ' '#')
        todo_bar=$(printf '%*s' "$empty" '' | tr ' ' '-')
        now=$(date +%s)
        elapsed=$(( now - started_at ))

        printf "\r[%s%s] %3d%% (%d/%d) Running: %s (%ss)" "$done_bar" "$todo_bar" "$percent" "$completed" "$total" "$model" "$elapsed"
        sleep 0.1
    done

    printf "\r"
}

# Clear log file
> "$LOG_FILE"
draw_progress_bar 0 "$TOTAL_MODELS" "Starting"
echo ""

for MODEL in "${MODEL_ARRAY[@]}"; do
    CURRENT=$((CURRENT + 1))
    MODEL_LOG=$(mktemp)

    echo ""
    echo "⏳ [$CURRENT/$TOTAL_MODELS] Benchmarking: $MODEL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    ./ollama-bench -model "$MODEL" -epochs "$EPOCHS" -max-tokens "$MAX_TOKENS" -p "$PROMPT" > "$MODEL_LOG" 2>&1 &
    BENCH_PID=$!
    run_with_progress_bar "$BENCH_PID" "$((CURRENT - 1))" "$TOTAL_MODELS" "$MODEL"

    if ! wait "$BENCH_PID"; then
        cat "$MODEL_LOG" >> "$LOG_FILE"
        rm -f "$MODEL_LOG"
        echo ""
        echo "❌ Failed: $MODEL"
        exit 1
    fi

    cat "$MODEL_LOG" >> "$LOG_FILE"
    rm -f "$MODEL_LOG"
    draw_progress_bar "$CURRENT" "$TOTAL_MODELS" "Completed: $MODEL"
    echo ""
    echo "✅ Completed: $MODEL"
done

echo ""
echo "📊 Generating comparison chart..."
cat "$LOG_FILE" | python3 "$PLOT_SCRIPT"

echo "--------------------------------------------------"
echo "✅ Workflow complete! Raw log data saved to '$LOG_FILE'."

# Create a generic symlink to the latest generated chart for quick viewing
GENERATED_CHART="${CLEAN_MODELS}.png"
if [ -f "$GENERATED_CHART" ]; then
    ln -sf "$GENERATED_CHART" latest_comparison.png
    echo "🔗 Linked '$GENERATED_CHART' -> 'latest_comparison.png'"
fi