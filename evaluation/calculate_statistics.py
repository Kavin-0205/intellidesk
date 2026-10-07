"""
IntelliDesk Statistical Analysis & Metrics Calculator.
Reads evaluation/results/raw_results.csv, mcp_overhead.csv, and ocr_accuracy.csv.
Computes:
- Intent Accuracy with 95% Wilson Confidence Intervals
- Task Success Rate (TSR) with 95% Wilson Confidence Intervals
- Context Resolution Accuracy (CRA) comparing B1 vs B2 with 95% Wilson CI
- Fallback Usage Rate
- Latency summary statistics (mean, median, std, min, max, p95)
- MCP Overhead statistics
- Failure category taxonomy breakdown
- Peak RAM and CPU utilization
Outputs:
- evaluation/results/summary.csv
- evaluation/results/latency_summary.csv
- evaluation/results/failure_analysis.csv
- evaluation/results/statistics.json
"""

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RAW_CSV = RESULTS_DIR / "raw_results.csv"
MCP_CSV = RESULTS_DIR / "mcp_overhead.csv"
OCR_CSV = RESULTS_DIR / "ocr_accuracy.csv"

SUMMARY_CSV = RESULTS_DIR / "summary.csv"
LATENCY_CSV = RESULTS_DIR / "latency_summary.csv"
FAILURE_CSV = RESULTS_DIR / "failure_analysis.csv"
STATS_JSON = RESULTS_DIR / "statistics.json"


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Calculate Wilson score confidence interval for a proportion.
    Returns (percentage, lower_bound_pct, upper_bound_pct).
    """
    if total == 0:
        return 0.0, 0.0, 0.0
    p = successes / total
    z = 1.95996  # 95% confidence z-score
    z2 = z * z
    denom = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1 - p) / total) + (z2 / (4 * total * total)))
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return round(p * 100, 2), round(lower * 100, 2), round(upper * 100, 2)


def compute_descriptive_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
    arr = np.array(values, dtype=float)
    return {
        "count": len(arr),
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "std": round(float(np.std(arr, ddof=1 if len(arr) > 1 else 0)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
    }


def main():
    if not RAW_CSV.exists():
        print(f"Error: {RAW_CSV} not found. Run run_evaluation.py first.")
        return

    rows = []
    with open(RAW_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print(f"Loaded {len(rows)} raw trial records from {RAW_CSV}")

    # =========================================================================
    # 1. METRICS BY CONFIGURATION
    # =========================================================================
    configs = ["B0", "B1", "B2", "B3"]
    config_stats = {}

    for cfg in configs:
        cfg_rows = [r for r in rows if r["configuration"] == cfg]
        n_trials = len(cfg_rows)
        if n_trials == 0:
            continue

        # Intent Accuracy
        n_intent_ok = sum(1 for r in cfg_rows if r["failure_category"] not in ("Planning", "Network"))
        # More strictly: check task success / planning
        # If failure_category != Planning and failure_category != Network
        intent_pct, intent_low, intent_high = wilson_score_interval(n_intent_ok, n_trials)

        # Task Success Rate (TSR)
        n_tsr_ok = sum(1 for r in cfg_rows if r["task_success"] == "True")
        tsr_pct, tsr_low, tsr_high = wilson_score_interval(n_tsr_ok, n_trials)

        # Fallback Rate
        n_fallback = sum(1 for r in cfg_rows if r["fallback_used"] == "True")
        fb_rate = round((n_fallback / n_trials) * 100, 2)

        # Context Resolution Accuracy (CRA)
        ctx_rows = [r for r in cfg_rows if r["context_resolution_success"] in ("True", "False")]
        n_ctx_total = len(ctx_rows)
        n_ctx_ok = sum(1 for r in ctx_rows if r["context_resolution_success"] == "True")
        cra_pct, cra_low, cra_high = wilson_score_interval(n_ctx_ok, n_ctx_total) if n_ctx_total > 0 else ("NA", "NA", "NA")

        # Latencies
        e2e_vals = [float(r["end_to_end_latency_ms"]) for r in cfg_rows if r["end_to_end_latency_ms"] != "NA"]
        e2e_stats = compute_descriptive_stats(e2e_vals)

        # Memory & CPU
        mem_vals = [float(r["peak_ram_mb"]) for r in cfg_rows if r["peak_ram_mb"] != "NA"]
        cpu_vals = [float(r["cpu_percent"]) for r in cfg_rows if r["cpu_percent"] != "NA"]

        config_stats[cfg] = {
            "configuration": cfg,
            "trials": n_trials,
            "intent_accuracy_pct": intent_pct,
            "intent_ci_95": f"[{intent_low}, {intent_high}]",
            "tsr_pct": tsr_pct,
            "tsr_ci_95": f"[{tsr_low}, {tsr_high}]",
            "cra_pct": cra_pct,
            "cra_ci_95": f"[{cra_low}, {cra_high}]" if cra_pct != "NA" else "NA",
            "fallback_rate_pct": fb_rate,
            "mean_e2e_ms": e2e_stats["mean"],
            "median_e2e_ms": e2e_stats["median"],
            "p95_e2e_ms": e2e_stats["p95"],
            "peak_ram_mb": round(max(mem_vals), 2) if mem_vals else "NA",
            "mean_cpu_pct": round(float(np.mean(cpu_vals)), 2) if cpu_vals else "NA",
        }

    # Write summary.csv
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "configuration", "trials", "intent_accuracy_pct", "intent_ci_95",
            "tsr_pct", "tsr_ci_95", "cra_pct", "cra_ci_95", "fallback_rate_pct",
            "mean_e2e_ms", "median_e2e_ms", "p95_e2e_ms", "peak_ram_mb", "mean_cpu_pct"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cfg in configs:
            if cfg in config_stats:
                writer.writerow(config_stats[cfg])

    print(f"Saved configuration summary to: {SUMMARY_CSV}")

    # =========================================================================
    # 2. LATENCY BREAKDOWN SUMMARY
    # =========================================================================
    latency_stages = {
        "input_processing": [float(r["input_latency_ms"]) for r in rows if r["input_latency_ms"] not in ("NA", "0.0", "0")],
        "llm_inference": [float(r["llm_latency_ms"]) for r in rows if r["configuration"] != "B0" and r["llm_latency_ms"] not in ("NA", "0.0", "0")],
        "ocr_processing": [float(r["ocr_latency_ms"]) for r in rows if r["ocr_latency_ms"] not in ("NA", "0.0", "0")],
        "intent_routing": [float(r["routing_latency_ms"]) for r in rows if r["routing_latency_ms"] not in ("NA", "0.0", "0")],
        "mcp_execution": [float(r["mcp_latency_ms"]) for r in rows if r["mcp_latency_ms"] not in ("NA", "0.0", "0")],
        "desktop_execution": [float(r["execution_latency_ms"]) for r in rows if r["execution_latency_ms"] not in ("NA", "0.0", "0")],
        "end_to_end": [float(r["end_to_end_latency_ms"]) for r in rows if r["end_to_end_latency_ms"] not in ("NA", "0.0", "0")],
    }

    latency_records = []
    for stage, vals in latency_stages.items():
        st = compute_descriptive_stats(vals)
        st["stage"] = stage
        latency_records.append(st)

    with open(LATENCY_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["stage", "count", "mean", "median", "std", "min", "max", "p95"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in latency_records:
            writer.writerow(rec)

    print(f"Saved latency breakdown summary to: {LATENCY_CSV}")

    # =========================================================================
    # 3. FAILURE CLASSIFICATION TAXONOMY
    # =========================================================================
    failure_counts = {
        "None (Success)": 0,
        "Input": 0,
        "Planning": 0,
        "Context": 0,
        "OCR": 0,
        "Execution": 0,
        "Network": 0,
        "Other": 0,
    }

    def get_effective_failure_cat(r: dict) -> str:
        cat = r["failure_category"]
        pred_args = r.get("predicted_arguments", "")
        err_msg = r.get("error_message", "")
        if "429" in pred_args or "rate limit" in pred_args.lower() or "429" in err_msg or "rate limit" in err_msg.lower():
            return "Network"
        return cat

    for r in rows:
        cat = get_effective_failure_cat(r)
        if cat == "None":
            failure_counts["None (Success)"] += 1
        elif cat in failure_counts:
            failure_counts[cat] += 1
        else:
            failure_counts["Other"] += 1

    total_runs = len(rows)
    failure_records = []
    for cat, cnt in failure_counts.items():
        pct = round((cnt / total_runs) * 100, 2)
        failure_records.append({"failure_category": cat, "count": cnt, "percentage": pct})

    with open(FAILURE_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["failure_category", "count", "percentage"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in failure_records:
            writer.writerow(rec)

    print(f"Saved failure analysis to: {FAILURE_CSV}")

    # =========================================================================
    # 4. MCP OVERHEAD STATS
    # =========================================================================
    mcp_stats = {}
    if MCP_CSV.exists():
        direct_vals = []
        mcp_vals = []
        overhead_vals = []
        with open(MCP_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                direct_vals.append(float(r["direct_latency_ms"]))
                mcp_vals.append(float(r["mcp_latency_ms"]))
                overhead_vals.append(float(r["mcp_overhead_ms"]))
        mcp_stats = {
            "direct": compute_descriptive_stats(direct_vals),
            "mcp": compute_descriptive_stats(mcp_vals),
            "overhead": compute_descriptive_stats(overhead_vals),
        }

    # =========================================================================
    # 5. OCR ACCURACY STATS
    # =========================================================================
    ocr_stats = {}
    if OCR_CSV.exists():
        char_accs = []
        word_accs = []
        latencies = []
        full_matches = 0
        with open(OCR_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                char_accs.append(float(r["char_accuracy_pct"]))
                word_accs.append(float(r["word_accuracy_pct"]))
                latencies.append(float(r["ocr_latency_ms"]))
                if r["detected_full"] == "True":
                    full_matches += 1
        total_ocr_cases = len(char_accs)
        ocr_stats = {
            "total_cases": total_ocr_cases,
            "full_match_count": full_matches,
            "full_match_pct": round((full_matches / total_ocr_cases) * 100, 2) if total_ocr_cases else 0.0,
            "mean_char_acc": round(float(np.mean(char_accs)), 2) if char_accs else 0.0,
            "mean_word_acc": round(float(np.mean(word_accs)), 2) if word_accs else 0.0,
            "latency": compute_descriptive_stats(latencies),
        }

    # Save comprehensive JSON
    all_stats = {
        "configurations": config_stats,
        "latency_breakdown": {rec["stage"]: rec for rec in latency_records},
        "failure_taxonomy": failure_records,
        "mcp_overhead": mcp_stats,
        "ocr_ground_truth": ocr_stats,
        "total_trials": total_runs,
    }

    with open(STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_stats, f, indent=2)

    print(f"Saved complete statistics JSON to: {STATS_JSON}")


if __name__ == "__main__":
    main()
