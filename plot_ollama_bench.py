#!/usr/bin/env python3
import sys
import re
import matplotlib.pyplot as plt
import numpy as np

def parse_raw_bench():
    content = sys.stdin.read()
    if not content.strip():
        print("❌ Error: No data received via standard input.")
        return None

    # Track data maps dynamically
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
            # Parse the step name
            step_match = re.search(r'step=(\w+)', line)
            if not step_match:
                continue
            step = step_match.group(1)

            # Extract numbers out of trailing metrics
            parts = line.split()

            if step == "prefill":
                # parts[-4] is ns/token, parts[-2] is token/sec
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

    if len(models) < 2:
        print("❌ Error: Could not find at least 2 distinct models to compare.")
        return None

    # Compute Averages (Mean) for the comparison charts
    m1, m2 = models[0], models[1]

    # Safely get geomean helper or simple average for step sets
    def avg(lst): return np.mean(lst) if lst else 0.0
    def geomean(lst1, lst2): return np.sqrt(avg(lst1) * avg(lst2))

    data = {
        "models": [m1, m2],
        "sec_token": {
            "labels": ['Prefill', 'Generate', 'Geomean'],
            "m1": [avg(raw_metrics[m1]["prefill_ms"]), avg(raw_metrics[m1]["generate_ms"]), geomean(raw_metrics[m1]["prefill_ms"], raw_metrics[m1]["generate_ms"])],
            "m2": [avg(raw_metrics[m2]["prefill_ms"]), avg(raw_metrics[m2]["generate_ms"]), geomean(raw_metrics[m2]["prefill_ms"], raw_metrics[m2]["generate_ms"])]
        },
        "token_sec": {
            "labels": ['Prefill', 'Generate', 'Geomean'],
            "m1": [avg(raw_metrics[m1]["prefill_tps"]), avg(raw_metrics[m1]["generate_tps"]), geomean(raw_metrics[m1]["prefill_tps"], raw_metrics[m1]["generate_tps"])],
            "m2": [avg(raw_metrics[m2]["prefill_tps"]), avg(raw_metrics[m2]["generate_tps"]), geomean(raw_metrics[m2]["prefill_tps"], raw_metrics[m2]["generate_tps"])]
        },
        "sec_op": {
            "labels": ['TTFT', 'Load', 'Total', 'Geomean'],
            "m1": [avg(raw_metrics[m1]["ttft_ms"]), avg(raw_metrics[m1]["load_ms"]), avg(raw_metrics[m1]["total_ms"]), np.cbrt(avg(raw_metrics[m1]["ttft_ms"])*avg(raw_metrics[m1]["load_ms"])*avg(raw_metrics[m1]["total_ms"]))],
            "m2": [avg(raw_metrics[m2]["ttft_ms"]), avg(raw_metrics[m2]["load_ms"]), avg(raw_metrics[m2]["total_ms"]), np.cbrt(avg(raw_metrics[m2]["ttft_ms"])*avg(raw_metrics[m2]["load_ms"])*avg(raw_metrics[m2]["total_ms"]))]
        }
    }
    return data

def generate_plot(data):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    width = 0.35
    m1_label, m2_label = data["models"][0], data["models"][1]

    # Chart 1: Latency (ms/token)
    x1 = np.arange(len(data["sec_token"]["labels"]))
    axes[0].bar(x1 - width/2, data["sec_token"]["m1"], width, label=m1_label, color='#1f77b4')
    axes[0].bar(x1 + width/2, data["sec_token"]["m2"], width, label=m2_label, color='#ff7f0e')
    axes[0].set_ylabel('ms / token')
    axes[0].set_title('Latency (ms/token)\nLower is better')
    axes[0].set_xticks(x1)
    axes[0].set_xticklabels(data["sec_token"]["labels"])
    axes[0].legend()
    axes[0].grid(axis='y', linestyle='--', alpha=0.7)

    # Chart 2: Throughput (token/sec)
    x2 = np.arange(len(data["token_sec"]["labels"]))
    axes[1].bar(x2 - width/2, data["token_sec"]["m1"], width, label=m1_label, color='#1f77b4')
    axes[1].bar(x2 + width/2, data["token_sec"]["m2"], width, label=m2_label, color='#ff7f0e')
    axes[1].set_ylabel('tokens / sec')
    axes[1].set_title('Throughput (token/sec)\nHigher is better')
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels(data["token_sec"]["labels"])
    axes[1].legend()
    axes[1].grid(axis='y', linestyle='--', alpha=0.7)

    # Chart 3: Operation Latency (ms/op)
    x3 = np.arange(len(data["sec_op"]["labels"]))
    axes[2].bar(x3 - width/2, data["sec_op"]["m1"], width, label=m1_label, color='#1f77b4')
    axes[2].bar(x3 + width/2, data["sec_op"]["m2"], width, label=m2_label, color='#ff7f0e')
    axes[2].set_ylabel('ms / op')
    axes[2].set_title('Operation Latency (ms/op)\nLower is better')
    axes[2].set_xticks(x3)
    axes[2].set_xticklabels(data["sec_op"]["labels"])
    axes[2].legend()
    axes[2].grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_png = 'ollama_benchmark_comparison.png'
    plt.savefig(output_png, dpi=300)
    print(f"📊 Chart successfully generated for {m1_label} vs {m2_label}!")
    print(f"📁 Saved plot to disk as '{output_png}'")

if __name__ == "__main__":
    bench_data = parse_raw_bench()
    if bench_data:
        generate_plot(bench_data)