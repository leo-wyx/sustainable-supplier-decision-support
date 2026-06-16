# Repository File Classification and Cleanup Plan

This document classifies the current repository files by module and purpose.
It is intended for GitHub cleanup and portfolio presentation. It does not
change model logic.

## 1. Root-Level Project Entry Files

| File | Category | Keep? | Notes |
|------|----------|-------|-------|
| `README.md` | GitHub entry | Yes | Main project homepage. |
| `requirements.txt` | Environment | Yes | Minimal dependency list. |
| `run_all.py` | Reproducibility | Yes | One-command workflow runner. |
| `.gitignore` | Git hygiene | Yes | Excludes local/cache/log files. |
| `.openclaude-profile.json` | Local tool config | No for GitHub | Local OpenClaude setting; keep locally, do not commit. |

## 2. Source Scripts

### Core Pipeline

| File | Module | Keep? | Notes |
|------|--------|-------|-------|
| `generate_data.py` | Data generation | Yes | Generates or supports supplier dataset creation. |
| `Model1.py` | M1 | Yes | Supplier qualification gate. |
| `Model2.py` | M2 | Yes | Adjusted cost, ESG fit, diagnostics, strategic pool. |
| `M2_Cost_ESG_Tradeoff_Ranking.py` | M2 | Yes | Core M2 post-processing and portfolio highlight. |
| `strategy_config.py` | Config | Yes | Shared model configuration. |

### Validation Scripts

| File | Module | Keep? | Notes |
|------|--------|-------|-------|
| `M2_Benchmark_Stability_Analysis.py` | M2 validation | Yes | Pool stability and internal transition check. |
| `M2_External_Benchmark_Green.py` | External validation | Yes | Main green supplier benchmark. |
| `M2_External_Benchmark_Traditional.py` | External validation | Yes | Mini traditional MCDM sanity benchmark. |

### Extension Scripts

| File | Module | Keep? | Notes |
|------|--------|-------|-------|
| `M3_Lightweight_Allocation.py` | M3 extension | Yes | Single-category allocation demonstration. |
| `M4_Resilience_Scenario.py` | M4 extension | Yes | Scenario stress-test demonstration. |

## 3. Input and Active Data Files

| File | Module | Keep? | Notes |
|------|--------|-------|-------|
| `suppliers_data.csv` | Input data | Yes | Main supplier dataset. |
| `supplier_reserve_pool.csv` | M1 output / M2 reference | Yes | Generated from M1; useful for qualification story. |
| `config/parameter_config.csv` | Config / assumptions | Yes | Parameter and replacement-path register. |

## 4. M2 Output Files

### Core M2 Outputs

| File | Keep? | Notes |
|------|-------|-------|
| `M2_Adjusted_Cost_Index.csv` | Yes | Main adjusted cost output. |
| `M2_ESG_Strategic_Fit.csv` | Yes | ESG tier output. |
| `M2_Supplier_Diagnostic_Profile.csv` | Yes | TQRDC diagnostic output. |
| `M2_Strategic_Pool_View.csv` | Yes | Main strategic pool output. |
| `M2_Cost_ESG_Tradeoff_Ranking.csv` | Yes | Main portfolio ranking output. |
| `M2_Cost_ESG_Tradeoff_Summary.csv` | Yes | Summary table for README/interview. |

### Supporting / Historical M2 Outputs

| File | Keep? | Recommendation |
|------|-------|----------------|
| `M2_Cost_ESG_Shortlist.csv` | Keep but mark continuity | Previous shortlist output retained for traceability. |
| `M2_Shortlist_Stability_Report.csv` | Keep but mark historical | Older shortlist stability view. |
| `M2_Revised_Decision_View.csv` | Keep but mark dashboard-facing reference | Useful but not core final story. |
| `M2_SubIndicator_Scores.csv` | Keep | Useful for audit/debug. |

## 5. M2 Validation Outputs

| File | Keep? | Notes |
|------|-------|-------|
| `M2_Pool_Stability_Report.csv` | Yes | Main pool stability output. |
| `M2_Pool_Migration_Analysis.csv` | Yes | Explains movement from previous shortlist to current pool. |
| `M2_Benchmark_Overlap_Report.csv` | Yes | Internal transition/overlap output. |
| `M2_External_Benchmark_Green_Result.csv` | Yes | Main external benchmark output. |
| `M2_External_Benchmark_Traditional_Result.csv` | Yes | Mini benchmark output. |

## 6. M3 Files

### Active M3 Outputs

| File | Keep? | Notes |
|------|-------|-------|
| `M3_Key_Category_Allocation_Result.csv` | Yes | Per-supplier allocation details. |
| `M3_Key_Category_Allocation_Summary.csv` | Yes | Main M3 summary output. |
| `M3_Scenario_Assumptions_Key_Component.csv` | Yes | Transparent assumption record. |

### M3 Placeholder Templates

| File | Keep? | Recommendation |
|------|-------|----------------|
| `M3_Category_Demand_Plan.csv` | Keep as template | Future enterprise demand input template. |
| `M3_Supplier_Capacity_Assumption.csv` | Keep as template | Future supplier capacity input template. |
| `M3_Allocation_Policy.csv` | Keep as template | Future allocation policy input template. |

## 7. M4 Files

| File | Keep? | Notes |
|------|-------|-------|
| `M4_Scenario_Allocation_Result.csv` | Yes | Per-supplier scenario output. |
| `M4_Scenario_Summary.csv` | Yes | Main M4 summary output. |
| `M4_Supplier_Stress_Impact.csv` | Yes | Supplier-level stress impact. |

## 8. Documentation Files

### Final / Portfolio Documentation

| File | Keep? | Notes |
|------|-------|-------|
| `docs/Final_Model_Overview.md` | Yes | Final model overview. |
| `docs/Final_File_Index.md` | Yes | High-level file map. |
| `docs/demo_summary.md` | Yes | Presentation/demo summary. |
| `docs/portfolio_project_brief.md` | Yes | Resume/interview brief. |
| `docs/repository_file_classification.md` | Yes | This cleanup classification document. |

### Methodology and Validation Docs

| File | Keep? | Notes |
|------|-------|-------|
| `docs/M1_Qualification_Logic.md` | Yes | M1 logic explanation. |
| `docs/M2_Cost_ESG_Tradeoff_Methodology.md` | Yes | Core methodology. |
| `docs/M2_Implementation_Validation_Summary.md` | Yes | M2 validation summary. |
| `docs/M2_Benchmark_Stability_Note.md` | Yes | Stability note. |
| `docs/M2_External_Benchmark_Note.md` | Yes | Main benchmark note. |
| `docs/M2_External_Benchmark_Traditional_Note.md` | Yes | Traditional mini benchmark detail. |
| `docs/M3_Lightweight_Allocation_Note.md` | Yes | M3 extension note. |
| `docs/M4_Resilience_Scenario_Note.md` | Yes | M4 scenario note. |
| `docs/Parameter_Assumption_Register.md` | Yes | Parameter assumption and replacement path. |

### Long-Form / Process Docs

| File | Keep? | Recommendation |
|------|-------|----------------|
| `docs/model_design_journey.md` | Keep optional | Useful process narrative, not required for first GitHub read. |
| `docs/changelog.md` | Keep optional | Useful if maintained. |
| `docs/*.docx` | Optional | Good for submission/reporting, but not ideal for GitHub browsing. |

## 9. Archived / Legacy Files

| Path | Keep? | Notes |
|------|-------|-------|
| `docs/archive/architecture.md` | Archive | Superseded architecture doc. |
| `docs/archive/M2_Revised_Logic.md` | Archive | Superseded M2 logic doc. |
| `docs/archive/M2_Revised_Target_Design.md` | Archive | Superseded target design. |
| `docs/archive/old_code.py.txt` | Archive | Original prototype. |
| `docs/archive/*.docx` | Archive | Historical design materials. |
| `archive/legacy_m2_outputs/*` | Archive | Legacy M2 outputs and radar charts. |

## 10. Local / Generated / Do Not Commit

These are local environment or generated cache files. They should not be
committed to GitHub.

| Path | Action |
|------|--------|
| `.codex_deps/` | Ignore |
| `.idea/` | Ignore |
| `.openclaude/` | Ignore |
| `.openclaude-profile.json` | Ignore or keep local only |
| `logs/` | Ignore |
| `__pycache__/` | Ignore |
| `scripts/__pycache__/` | Ignore |
| `*.pyc` | Ignore |

## 11. Scripts Folder

The `scripts/` folder contains report-generation and document-maintenance
helpers. It is not part of the core model pipeline.

| File Pattern | Recommendation |
|-------------|----------------|
| `scripts/create_lca_*.py` | Keep if LCA/report generation is still relevant; otherwise archive. |
| `scripts/build_*.py` | Keep if doc regeneration is needed; otherwise archive. |
| `scripts/fix_*.py` | Archive after final report is stable. |
| `scripts/md_to_docx.py` | Keep if converting docs to Word. |
| `scripts/extract_docx_images.py` / `inspect_docx_image_order.py` | Archive unless needed for report images. |

## 12. Recommended GitHub Structure

For the least-risk cleanup, keep scripts at root for now because existing paths
assume root-level CSVs. Use documentation to explain the layout.

For a later cleaner release, consider:

```text
data/
  suppliers_data.csv

src/
  Model1.py
  Model2.py
  M2_Cost_ESG_Tradeoff_Ranking.py
  M2_Benchmark_Stability_Analysis.py
  M2_External_Benchmark_Green.py
  M2_External_Benchmark_Traditional.py
  M3_Lightweight_Allocation.py
  M4_Resilience_Scenario.py

outputs/
  m1/
  m2/
  m3/
  m4/
  validation/

docs/
  final and methodology notes
```

That refactor should only be done after adding path handling to all scripts.

## 13. Immediate Cleanup Recommendation

No core model file needs deletion. The safest next cleanup is:

1. Keep root scripts and output CSVs as-is for reproducibility.
2. Keep archived docs and legacy M2 outputs where they are.
3. Do not commit ignored local folders.
4. Optionally move non-core `scripts/fix_*`, `scripts/create_lca_*`, and
   old `.docx` files into archive if the GitHub repo should look leaner.

The current repository is functionally ready. The main remaining choice is how
minimal the public GitHub version should be.
