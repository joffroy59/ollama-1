#!/usr/bin/env python3
import os
import re
import matplotlib.pyplot as plt
import numpy as np

def parse_bench_file(filepath):
    if not os.path.exists(filepath):
        print(f"❌ Error: The file '{filepath}' was not found.")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Find the models from the first header row containing "sec/token"
    model_names = []
    for line in lines:
        if "sec/token" in line:
            # Extract names surrounding '│' characters
            parts = [p.strip() for p in line.split("│") if p.strip()]
            # Filter out the unit column if it slipped in
            model_names = [p for p in parts if "sec/token" not in p]
            break

    # Fallback to generic names if headers parsing failed
    if len(model_names) < 2:
        model_names = ["Model A", "Model B"]

    data = {
        "models": model_names,
        "sec_token": {"labels": [], "m1": [], "m2": []},
        "token_sec": {"labels": [], "m1": [], "m2": []},
        "sec_op":    {"labels": [], "m1": [], "m2": []}
    }

    def clean_val(val_str):
        multiplier = 1.0
        if 'm' in val_str:
            val_str = val_str.replace('m', '')
        elif '.' in val_str and val_str.replace('.','',1).isdigit():
            multiplier = 1000.0 # Convert total raw seconds to ms

        val_str = val_str.split('±')[0].strip()
        try:
            return float(val_str) * multiplier
        except ValueError:
            return 0.0

    current_metric = None
    for line in lines:
        if "sec/token" in line:
            current_metric = "sec_token"
            continue
        elif "token/sec" in line:
            current_metric = "token_sec"
            continue
        elif "sec/op" in line:
            current_metric = "sec_op"
            continue

        if current_metric and ("Model/step=" in line or "geomean" in line):
            # Split line while preserving structural alignment tokens
            parts = [p.strip() for p in line.split() if p.strip()]
            if len(parts) >= 3:
                label = parts[0].replace("Model/step=", "").capitalize()

                # Separate out the values across ± boundaries safely
                if "±" in line:
                    sub_parts = line.split("±")
                    m1_val = clean_val(sub_parts[0].split()[-1])
                    m2_val = clean_val(sub_parts[1].split()[-1])
                else:
                    m1_val = clean_val(parts[1])
                    m2_val = clean_val(parts[2])

                data[current_metric]["labels"].append(label)
                data[current_metric]["m1"].append(m1_val)
                data[current_metric]["m2"].append(m2_val)

    return data

def generate_plot(data):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    width = 0.35
    m1_label, m2_label = data["models"][0], data["models"][1]

    # Chart 1: Latency (sec/token)
    x1 = np.arange(len(data["sec_token"]["labels"]))
    axes[0].bar(x1 - width/2, data["sec_token"]["m1"], width, label=m1_label, color='#1f77b4')
    axes[0].bar(x1 + width/2, data["sec_token"]["m2"], width, label=m2_label, color='#ff7f0e')
    axes[0].set_ylabel('ms / token')
    axes[0].set_title('Latency (sec/token in ms)\nLower is better')
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

    # Chart 3: Operation Latency (sec/op)
    x3 = np.arange(len(data["sec_op"]["labels"]))
    axes[2].bar(x3 - width/2, data["sec_op"]["m1"], width, label=m1_label, color='#1f77b4')
    axes[2].bar(x3 + width/2, data["sec_op"]["m2"], width, label=m2_label, color='#ff7f0e')
    axes[2].set_ylabel('ms / op')
    axes[2].set_title('Operation Latency (sec/op in ms)\nLower is better')
    axes[2].set_xticks(x3)
    axes[2].set_xticklabels(data["sec_op"]["labels"])
    axes[2].legend()
    axes[2].grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_png = 'ollama_benchmark_comparison.png'
    plt.savefig(output_png, dpi=300)
    print(f"📊 Chart successfully updated for {m1_label} vs {m2_label}!")
    print(f"📁 Saved as '{output_png}'")

if __name__ == "__main__":
    bench_data = parse_bench_file('gemma.bench')
    if bench_data:
        generate_plot(bench_data)