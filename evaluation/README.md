# IntelliDesk IEEE Benchmark & Evaluation Suite

This directory contains the experimental evaluation harness, benchmark definitions, statistical calculation scripts, and publication-ready figures for the research paper on **IntelliDesk**.

## Directory Structure

```
evaluation/
├── benchmark.py              # Benchmark task catalog (10 categories, multi-phrasing, ground truth)
├── collect_environment.py    # Hardware, OS, Python, and dependency environment collector
├── run_evaluation.py         # Master evaluation harness (B0, B1, B2, B3, MCP overhead, OCR test)
├── calculate_statistics.py   # Statistical computation (Wilson 95% CIs, descriptive stats, taxonomy)
├── analyze_results.py        # Publication-quality figure generation (PNG 300 DPI & vector PDF)
├── README.md                 # Evaluation documentation and reproduction instructions
└── results/
    ├── environment.txt       # Measured machine specifications and package versions
    ├── raw_results.csv       # Complete trial-by-trial dataset (every single run recorded)
    ├── summary.csv           # Performance summary table by configuration
    ├── latency_summary.csv   # Latency metrics across all execution stages
    ├── failure_analysis.csv  # Standardized failure taxonomy breakdown
    ├── mcp_overhead.csv      # Direct Python vs MCP stdio invocation latency trials
    ├── ocr_accuracy.csv      # Ground-truth character-level & word-level OCR evaluation
    ├── statistics.json       # Structured metrics and confidence intervals
    ├── FINAL_REPORT.md       # Comprehensive experimental evaluation report
    └── figures/              # Publication-ready figures (PNG & PDF)
        ├── tsr_by_configuration.png / .pdf
        ├── intent_accuracy_by_configuration.png / .pdf
        ├── cra_b1_vs_b2.png / .pdf
        ├── latency_breakdown.png / .pdf
        ├── failure_distribution.png / .pdf
        ├── latency_distribution_boxplot.png / .pdf
        └── mcp_overhead_comparison.png / .pdf
```

## Evaluated Configurations

- **B0**: Rule / keyword pattern-matching baseline for direct commands (no LLM, no context).
- **B1**: LLM intent generation (`openai/gpt-oss-120b` via Groq) **WITHOUT** session context.
- **B2**: LLM intent generation **WITH** session context and pronoun resolution.
- **B3**: LLM + session context + EasyOCR for screen-dependent tasks.

## Reproduction Instructions

To execute the complete evaluation from scratch:

```powershell
# 1. Collect environment details
.\venv\Scripts\python.exe evaluation/collect_environment.py

# 2. Run the evaluation harness (executes real trials, measures latencies and resources)
.\venv\Scripts\python.exe evaluation/run_evaluation.py

# 3. Calculate metrics and 95% Wilson confidence intervals
.\venv\Scripts\python.exe evaluation/calculate_statistics.py

# 4. Generate IEEE publication figures
.\venv\Scripts\python.exe evaluation/analyze_results.py
```
