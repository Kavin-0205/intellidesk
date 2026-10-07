"""
IntelliDesk Publication-Quality Figure Generator for IEEE Conference Paper.
Reads evaluation/results/statistics.json and raw CSVs to generate:
1. tsr_by_configuration (PNG & PDF)
2. intent_accuracy_by_configuration (PNG & PDF)
3. cra_b1_vs_b2 (PNG & PDF)
4. latency_breakdown (PNG & PDF)
5. failure_distribution (PNG & PDF)
6. latency_distribution_boxplot (PNG & PDF)
7. mcp_overhead_comparison (PNG & PDF)
"""

import json
import csv
from pathlib import Path
from typing import Tuple
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
STATS_JSON = RESULTS_DIR / "statistics.json"
RAW_CSV = RESULTS_DIR / "raw_results.csv"
MCP_CSV = RESULTS_DIR / "mcp_overhead.csv"

# IEEE Style Settings
plt.rcParams.update({
    "font.size": 10,
    "font.family": "serif",
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 12,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "lines.linewidth": 1.5,
    "grid.alpha": 0.4,
    "grid.linestyle": "--",
})


def parse_ci_range(ci_str: str) -> Tuple[float, float]:
    """Parse '[low, high]' string into (low, high) float tuple."""
    clean = ci_str.strip("[] ").split(",")
    return float(clean[0]), float(clean[1])


def main():
    if not STATS_JSON.exists():
        print(f"Error: {STATS_JSON} not found. Run calculate_statistics.py first.")
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_JSON, "r", encoding="utf-8") as f:
        stats = json.load(f)

    cfgs = stats["configurations"]

    # =========================================================================
    # 1. TASK SUCCESS RATE BY CONFIGURATION
    # =========================================================================
    fig, ax = plt.subplots(figsize=(5.5, 3.5), tight_layout=True)
    cfg_names = [c for c in ["B0", "B1", "B2", "B3"] if c in cfgs]
    tsr_vals = [cfgs[c]["tsr_pct"] for c in cfg_names]
    
    # Calculate asymmetric error bars from Wilson CI
    yerr_lower = []
    yerr_upper = []
    for c in cfg_names:
        val = cfgs[c]["tsr_pct"]
        ci_str = cfgs[c]["tsr_ci_95"]
        if ci_str != "NA":
            low, high = [float(x.strip("[] ")) for x in ci_str.split(",")]
            yerr_lower.append(max(0, val - low))
            yerr_upper.append(max(0, high - val))
        else:
            yerr_lower.append(0)
            yerr_upper.append(0)

    bars = ax.bar(cfg_names, tsr_vals, yerr=[yerr_lower, yerr_upper], capsize=4, color="#2b5c8f", edgecolor="#1a365d", width=0.55)
    ax.set_ylabel("Task Success Rate (%)")
    ax.set_xlabel("Configuration")
    ax.set_title("Task Success Rate by Configuration (95% CI)")
    ax.set_ylim(0, 105)
    ax.grid(axis="y")

    for bar, val in zip(bars, tsr_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{val:.1f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    fig.savefig(FIGURES_DIR / "tsr_by_configuration.png")
    fig.savefig(FIGURES_DIR / "tsr_by_configuration.pdf")
    plt.close(fig)

    # =========================================================================
    # 2. INTENT ACCURACY BY CONFIGURATION
    # =========================================================================
    fig, ax = plt.subplots(figsize=(5.5, 3.5), tight_layout=True)
    intent_vals = [cfgs[c]["intent_accuracy_pct"] for c in cfg_names]
    
    yerr_lower = []
    yerr_upper = []
    for c in cfg_names:
        val = cfgs[c]["intent_accuracy_pct"]
        ci_str = cfgs[c]["intent_ci_95"]
        if ci_str != "NA":
            low, high = [float(x.strip("[] ")) for x in ci_str.split(",")]
            yerr_lower.append(max(0, val - low))
            yerr_upper.append(max(0, high - val))
        else:
            yerr_lower.append(0)
            yerr_upper.append(0)

    bars = ax.bar(cfg_names, intent_vals, yerr=[yerr_lower, yerr_upper], capsize=4, color="#1e7e34", edgecolor="#155724", width=0.55)
    ax.set_ylabel("Intent Accuracy (%)")
    ax.set_xlabel("Configuration")
    ax.set_title("Intent Classification Accuracy (95% CI)")
    ax.set_ylim(0, 105)
    ax.grid(axis="y")

    for bar, val in zip(bars, intent_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{val:.1f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    fig.savefig(FIGURES_DIR / "intent_accuracy_by_configuration.png")
    fig.savefig(FIGURES_DIR / "intent_accuracy_by_configuration.pdf")
    plt.close(fig)

    # =========================================================================
    # 3. CONTEXT RESOLUTION ACCURACY: B1 vs B2 (RQ2)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(4.8, 3.5), tight_layout=True)
    cra_cfgs = ["B1 (No Context)", "B2 (With Context)"]
    cra_b1 = cfgs.get("B1", {}).get("cra_pct", 0.0)
    cra_b2 = cfgs.get("B2", {}).get("cra_pct", 0.0)
    cra_vals = [float(cra_b1) if cra_b1 != "NA" else 0.0, float(cra_b2) if cra_b2 != "NA" else 0.0]

    colors = ["#dc3545", "#28a745"]
    bars = ax.bar(cra_cfgs, cra_vals, color=colors, edgecolor="#333333", width=0.5)
    ax.set_ylabel("Context Resolution Accuracy (%)")
    ax.set_title("RQ2: Context Resolution Accuracy (B1 vs B2)")
    ax.set_ylim(0, 110)
    ax.grid(axis="y")

    for bar, val in zip(bars, cra_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{val:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.savefig(FIGURES_DIR / "cra_b1_vs_b2.png")
    fig.savefig(FIGURES_DIR / "cra_b1_vs_b2.pdf")
    plt.close(fig)

    # =========================================================================
    # 4. LATENCY BREAKDOWN ACROSS PROCESSING STAGES
    # =========================================================================
    lat = stats["latency_breakdown"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8), tight_layout=True)
    stages = ["llm_inference", "intent_routing", "desktop_execution", "ocr_processing", "end_to_end"]
    stage_labels = ["LLM API", "Routing", "Execution", "OCR", "End-to-End"]
    means = [lat.get(s, {}).get("mean", 0.0) for s in stages]
    medians = [lat.get(s, {}).get("median", 0.0) for s in stages]
    stds = [lat.get(s, {}).get("std", 0.0) for s in stages]

    x = np.arange(len(stages))
    width = 0.35

    rects1 = ax.bar(x - width/2, means, width, label="Mean", color="#0056b3", yerr=stds, capsize=3)
    rects2 = ax.bar(x + width/2, medians, width, label="Median", color="#17a2b8")

    ax.set_ylabel("Latency (ms)")
    ax.set_title("Latency Breakdown by Processing Stage")
    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels)
    ax.legend()
    ax.grid(axis="y")

    fig.savefig(FIGURES_DIR / "latency_breakdown.png")
    fig.savefig(FIGURES_DIR / "latency_breakdown.pdf")
    plt.close(fig)

    # =========================================================================
    # 5. FAILURE CATEGORY DISTRIBUTION
    # =========================================================================
    fail_data = stats["failure_taxonomy"]
    fail_filtered = [f for f in fail_data if f["failure_category"] != "None (Success)" and f["count"] > 0]
    
    fig, ax = plt.subplots(figsize=(5.5, 3.5), tight_layout=True)
    if fail_filtered:
        cat_labels = [f["failure_category"] for f in fail_filtered]
        cat_counts = [f["count"] for f in fail_filtered]
        ax.barh(cat_labels, cat_counts, color="#d9534f", edgecolor="#b52b27")
        ax.set_xlabel("Occurrences")
        ax.set_title("Failure Category Distribution")
        ax.grid(axis="x")
        for i, v in enumerate(cat_counts):
            ax.text(v + 0.2, i, str(v), va="center", fontsize=8.5)
    else:
        ax.text(0.5, 0.5, "No Failures Observed Across Evaluation Trials", ha="center", va="center", fontsize=11)
        ax.set_title("Failure Distribution")
        ax.axis("off")

    fig.savefig(FIGURES_DIR / "failure_distribution.png")
    fig.savefig(FIGURES_DIR / "failure_distribution.pdf")
    plt.close(fig)

    # =========================================================================
    # 6. LATENCY BOXPLOT DISTRIBUTION
    # =========================================================================
    if RAW_CSV.exists():
        llm_lats = []
        e2e_lats = []
        with open(RAW_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r["configuration"] != "B0" and r["llm_latency_ms"] not in ("NA", "0.0"):
                    llm_lats.append(float(r["llm_latency_ms"]))
                if r["end_to_end_latency_ms"] not in ("NA", "0.0"):
                    e2e_lats.append(float(r["end_to_end_latency_ms"]))

        if llm_lats and e2e_lats:
            fig, ax = plt.subplots(figsize=(5.0, 3.5), tight_layout=True)
            box_data = [llm_lats, e2e_lats]
            ax.boxplot(box_data, tick_labels=["LLM Inference", "End-to-End"], patch_artist=True,
                       boxprops=dict(facecolor="#d1ecf1", color="#0c5460"),
                       medianprops=dict(color="#b21f2d", linewidth=2))
            ax.set_ylabel("Latency (ms)")
            ax.set_title("Latency Distribution (Box Plot)")
            ax.grid(axis="y")
            fig.savefig(FIGURES_DIR / "latency_distribution_boxplot.png")
            fig.savefig(FIGURES_DIR / "latency_distribution_boxplot.pdf")
            plt.close(fig)

    # =========================================================================
    # 7. MCP OVERHEAD COMPARISON
    # =========================================================================
    mcp_st = stats.get("mcp_overhead", {})
    if mcp_st and "direct" in mcp_st and "mcp" in mcp_st:
        fig, ax = plt.subplots(figsize=(5.0, 3.5), tight_layout=True)
        mcp_cats = ["Direct Python", "MCP Protocol"]
        mcp_means = [mcp_st["direct"]["mean"], mcp_st["mcp"]["mean"]]
        mcp_stds = [mcp_st["direct"]["std"], mcp_st["mcp"]["std"]]

        bars = ax.bar(mcp_cats, mcp_means, yerr=mcp_stds, capsize=4, color=["#6c757d", "#fd7e14"], edgecolor="#333333", width=0.45)
        ax.set_ylabel("Execution Latency (ms)")
        ax.set_title("MCP Invocation Protocol Overhead")
        ax.grid(axis="y")

        for bar, val in zip(bars, mcp_means):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{val:.2f} ms", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

        fig.savefig(FIGURES_DIR / "mcp_overhead_comparison.png")
        fig.savefig(FIGURES_DIR / "mcp_overhead_comparison.pdf")
        plt.close(fig)

    print(f"All publication-quality IEEE figures successfully generated in: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
