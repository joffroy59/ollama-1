#!/usr/bin/env python3
import sys
import re
import argparse
import os
import matplotlib.pyplot as plt
import numpy as np

REPORT_DIR = "cmd/bench/report"

def parse_raw_bench():
    content = sys.stdin.read()
    if not content.strip():
        print("❌ Error: No data received via standard input.")
        return None

    models = []
    # Structure: { model_name: { step_name: [list_of_values] } }
    raw_metrics = {}
    current_model = None

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 1. Capture Model Names from the comment tags
        if line.startswith("# Model:"):
            match = re.search(r'# Model:\s*([^\s│|]+)', line)
            if match:
                current_model = match.group(1)
                if current_model not in models:
                    models.append(current_model)
                if current_model not in raw_metrics:
                    raw_metrics[current_model] = {
                        "prefill_ms": [], "prefill_tps": [],
                        "generate_ms": [], "generate_tps": [],
                        "ttft_ms": [], "load_ms": [], "total_ms": []
                    }
            continue

        # 2. Extract values from benchmark metrics lines
        if "BenchmarkModel/name=" in line and current_model:
            step_match = re.search(r'step=(\w+)', line)
            if not step_match:
                continue
            step = step_match.group(1)
            parts = line.split()

            if step == "prefill":
                ns_token = float(parts[-4])
                tps = float(parts[-2])
                raw_metrics[current_model]["prefill_ms"].append(ns_token / 1_000_000.0)
                raw_metrics[current_model]["prefill_tps"].append(tps)

            elif step == "generate":
                ns_token = float(parts[-4])
                tps = float(parts[-2])
                raw_metrics[current_model]["generate_ms"].append(ns_token / 1_000_000.0)
                raw_metrics[current_model]["generate_tps"].append(tps)

            elif step == "ttft":
                ns_op = float(parts[-2])
                raw_metrics[current_model]["ttft_ms"].append(ns_op / 1_000_000.0)

            elif step == "load":
                ns_op = float(parts[-2])
                raw_metrics[current_model]["load_ms"].append(ns_op / 1_000_000.0)

            elif step == "total":
                ns_op = float(parts[-2])
                raw_metrics[current_model]["total_ms"].append(ns_op / 1_000_000.0)

    if not models:
        print("❌ Error: Could not find any valid models in the stream.")
        return None

    def avg(lst): return np.mean(lst) if lst else 0.0
    def geomean(lst1, lst2): return np.sqrt(avg(lst1) * avg(lst2))

    # Compile dataset dynamically for every model detected
    processed_data = {
        "models": models,
        "labels_token": ['Prefill', 'Generate', 'Geomean'],
        "labels_op": ['TTFT', 'Load', 'Total', 'Geomean'],
        "metrics": {}
    }

    for model in models:
        p_ms = avg(raw_metrics[model]["prefill_ms"])
        g_ms = avg(raw_metrics[model]["generate_ms"])

        p_tps = avg(raw_metrics[model]["prefill_tps"])
        g_tps = avg(raw_metrics[model]["generate_tps"])

        t_ms = avg(raw_metrics[model]["ttft_ms"])
        l_ms = avg(raw_metrics[model]["load_ms"])
        tot_ms = avg(raw_metrics[model]["total_ms"])

        processed_data["metrics"][model] = {
            "sec_token": [p_ms, g_ms, np.sqrt(p_ms * g_ms)],
            "token_sec": [p_tps, g_tps, np.sqrt(p_tps * g_tps)],
            "sec_op": [t_ms, l_ms, tot_ms, np.cbrt(t_ms * l_ms * tot_ms)]
        }

    return processed_data

def generate_plot(data, output_filename=None):
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    models = data["models"]
    num_models = len(models)

    # Dynamically scale bar widths to fit gracefully
    total_width = 0.8
    bar_width = total_width / num_models

    # Use a standard qualitative color palette
    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    # Helper plotting loop for the 3 subplots
    metrics_keys = ["sec_token", "token_sec", "sec_op"]
    titles = [
        'Latency (ms/token)\nLower is better',
        'Throughput (token/sec)\nHigher is better',
        'Operation Latency (ms/op)\nLower is better'
    ]
    y_labels = ['ms / token', 'tokens / sec', 'ms / op']

    for i, key in enumerate(metrics_keys):
        labels = data["labels_op"] if key == "sec_op" else data["labels_token"]
        x_indexes = np.arange(len(labels))

        # Plot bars for each model side-by-side
        for idx, model in enumerate(models):
            # Calculate offset shift per model relative to group center
            offset = (idx - (num_models - 1) / 2) * bar_width
            axes[i].bar(
                x_indexes + offset,
                data["metrics"][model][key],
                bar_width,
                label=model,
                color=colors[idx % 10]
            )

        axes[i].set_ylabel(y_labels[i])
        axes[i].set_title(titles[i], fontsize=12, fontweight='bold')
        axes[i].set_xticks(x_indexes)
        axes[i].set_xticklabels(labels)
        axes[i].grid(axis='y', linestyle='--', alpha=0.5)
        if i == 0:  # Put the legend on the first chart
            axes[i].legend(loc='upper left')

    plt.tight_layout()

    # Determine fallback filename dynamically from all models tested
    if not output_filename:
        sanitized_names = [re.sub(r'[^a-zA-Z0-9_-]', '_', m) for m in models]
        output_filename = f"{'_vs_'.join(sanitized_names)}.png"
        # Truncate filename if it gets crazily long
        if len(output_filename) > 120:
            output_filename = "ollama_multi_model_comparison.png"

        output_filename = os.path.join(REPORT_DIR, output_filename)

    output_dir = os.path.dirname(output_filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    plt.savefig(output_filename, dpi=300)
    print(f"📊 Chart successfully generated for: {', '.join(models)}")
    print(f"📁 Saved plot to disk as '{output_filename}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dynamic multi-model benchmark charts.")
    parser.add_argument('-o', '--output', type=str, help="Custom filename for the output PNG image.")
    args = parser.parse_args()

    bench_data = parse_raw_bench()
    if bench_data:
        generate_plot(bench_data, output_filename=args.output)