#!/usr/bin/env python3
"""
Run the full reproducible workflow for the supplier decision-support project.

The script keeps the existing project layout intact and runs the modules in the
same order as the final model story:

M1 -> M2 -> M2 trade-off ranking -> validation -> M3 -> M4
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

STEPS = [
    ("M1 Qualification Gate", "Model1.py"),
    ("M2 Strategic Pool Outputs", "Model2.py"),
    ("M2 Cost-ESG Trade-off Ranking", "M2_Cost_ESG_Tradeoff_Ranking.py"),
    ("M2 Pool Stability Validation", "M2_Benchmark_Stability_Analysis.py"),
    ("M2 External Green Benchmark", "M2_External_Benchmark_Green.py"),
    ("M2 Traditional Benchmark Sanity Check", "M2_External_Benchmark_Traditional.py"),
    ("M3 Lightweight Allocation Extension", "M3_Lightweight_Allocation.py"),
    ("M4 Resilience Scenario Extension", "M4_Resilience_Scenario.py"),
]

EXPECTED_OUTPUTS = [
    "supplier_reserve_pool.csv",
    "M2_Strategic_Pool_View.csv",
    "M2_Cost_ESG_Tradeoff_Ranking.csv",
    "M2_Cost_ESG_Tradeoff_Summary.csv",
    "M2_Pool_Stability_Report.csv",
    "M2_External_Benchmark_Green_Result.csv",
    "M2_External_Benchmark_Traditional_Result.csv",
    "docs/M2_External_Benchmark_Note.md",
    "docs/M2_External_Benchmark_Traditional_Note.md",
    "M3_Key_Category_Allocation_Summary.csv",
    "M4_Scenario_Summary.csv",
]


def run_step(label: str, script: str) -> None:
    print("\n" + "=" * 78)
    print(f"RUNNING: {label}", flush=True)
    print(f"SCRIPT : {script}", flush=True)
    print("=" * 78, flush=True)

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"[FAIL] {script} exited with code {result.returncode}")

    print(f"[PASS] {label}")


def verify_outputs() -> None:
    print("\n" + "=" * 78)
    print("VERIFYING EXPECTED OUTPUTS")
    print("=" * 78)

    missing = [name for name in EXPECTED_OUTPUTS if not (ROOT / name).exists()]
    if missing:
        for name in missing:
            print(f"[MISSING] {name}")
        raise SystemExit("[FAIL] Missing expected output files")

    for name in EXPECTED_OUTPUTS:
        print(f"[OK] {name}")


def main() -> None:
    print("Supplier Decision-Support Workflow")
    print(f"Project root: {ROOT}")

    for label, script in STEPS:
        run_step(label, script)

    verify_outputs()
    print("\nAll workflow steps completed successfully.")


if __name__ == "__main__":
    main()
