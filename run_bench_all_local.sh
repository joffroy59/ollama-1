#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_BENCH_SCRIPT="$SCRIPT_DIR/run_bench.sh"

if ! command -v ollama >/dev/null 2>&1; then
    echo "Error: 'ollama' command not found in PATH."
    exit 1
fi

if [ ! -x "$RUN_BENCH_SCRIPT" ]; then
    echo "Error: '$RUN_BENCH_SCRIPT' not found or not executable."
    exit 1
fi

MODELS=$(ollama list | awk 'NR > 1 && NF > 0 { print $1 }' | paste -sd, -)

if [ -z "$MODELS" ]; then
    echo "No local models found from 'ollama list'."
    exit 1
fi

echo "Detected local models:"
echo "$MODELS" | tr ',' '\n' | sed 's/^/  - /'

LOG_FILE="${1:-}"

if [ -n "$LOG_FILE" ]; then
    "$RUN_BENCH_SCRIPT" "$MODELS" "$LOG_FILE"
else
    "$RUN_BENCH_SCRIPT" "$MODELS"
fi
