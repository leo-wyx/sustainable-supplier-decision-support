# Final File Index

## Core Model Files

| File | Role |
|------|------|
| `Model1.py` | M1 Six-Gate Qualification (Quality, Finance, Tech, Labor, Compliance, Ethics) |
| `Model2.py` | M2 scoring: Adjusted Cost Index, ESG Strategic Fit, TQRDC Diagnostic, Strategic Pool |
| `M2_Cost_ESG_Tradeoff_Ranking.py` | M2 post-processing: cost-primary trade-off ranking with ESG premium tolerance |
| `M2_Benchmark_Stability_Analysis.py` | Pool stability analysis across 5 scenarios |
| `M2_External_Benchmark_Green.py` | 10-supplier green supplier selection benchmark (Fuzzy AHP + TOPSIS) |
| `M2_External_Benchmark_Traditional.py` | 5-supplier traditional MCDM benchmark (TOPSIS + VIKOR) |
| `generate_data.py` | Supplier data generation script |
| `strategy_config.py` | Strategy configuration parameters |
| `suppliers_data.csv` | Core supplier dataset (50 suppliers, 4 categories) |

## M2 Output Files

| File | Content |
|------|---------|
| `M2_Adjusted_Cost_Index.csv` | Category-level normalized cost index with base/logistics/carbon components |
| `M2_ESG_Strategic_Fit.csv` | ESG tier classification (Leader/Compliant/Monitor/Gap) |
| `M2_Supplier_Diagnostic_Profile.csv` | TQRDC diagnostic profile with management action recommendations |
| `M2_Strategic_Pool_View.csv` | Supplier strategic pool assignment with sourcing recommendation |
| `M2_Cost_ESG_Tradeoff_Ranking.csv` | Cost-primary ranking with ESG premium tolerance and pool label |
| `M2_Cost_ESG_Tradeoff_Summary.csv` | Summary of trade-off ranking: premium tiers and supplier counts |
| `M2_Cost_ESG_Shortlist.csv` | Revised Cost-ESG shortlist (retained for continuity) |
| `M2_Shortlist_Stability_Report.csv` | Shortlist stability (historical reference) |
| `M2_Revised_Decision_View.csv` | Dashboard-facing decision view |
| `M2_SubIndicator_Scores.csv` | Sub-indicator scoring detail |
| `M2_Pool_Stability_Report.csv` | Pool stability scenario analysis |
| `M2_Pool_Migration_Analysis.csv` | Pool migration between cost scenarios |
| `M2_Benchmark_Overlap_Report.csv` | Benchmark overlap analysis |

## M3 Extension (Lightweight Allocation Simulator)

| File | Role |
|------|------|
| `M3_Lightweight_Allocation.py` | Single-category allocation simulator, 4 policies |
| `M3_Key_Category_Allocation_Result.csv` | Per-supplier allocation detail |
| `M3_Key_Category_Allocation_Summary.csv` | Summary by policy |
| `M3_Scenario_Assumptions_Key_Component.csv` | Assumption register for M3 scenario |
| `M3_Category_Demand_Plan.csv` | Demand plan placeholder (TBD) |
| `M3_Supplier_Capacity_Assumption.csv` | Capacity assumption placeholder (TBD) |
| `M3_Allocation_Policy.csv` | Allocation policy placeholder (TBD) |

## M4 Extension (Resilience Scenario Simulation)

| File | Role |
|------|------|
| `M4_Resilience_Scenario.py` | Stress-test layer: 4 scenarios x 4 policies |
| `M4_Scenario_Allocation_Result.csv` | Per-supplier allocation before/after stress |
| `M4_Scenario_Summary.csv` | One-row-per-scenario-policy summary |
| `M4_Supplier_Stress_Impact.csv` | Per-supplier delta across scenarios |

## Validation Outputs

| File | Content |
|------|---------|
| `M2_Pool_Stability_Report.csv` | Pool composition by scenario |
| `M2_Benchmark_Overlap_Report.csv` | Pool-benchmark classification alignment |
| `M2_External_Benchmark_Green_Result.csv` | Green supplier benchmark scores and rankings |
| `M2_External_Benchmark_Traditional_Result.csv` | Traditional MCDM benchmark scores and rankings |
| `docs/M2_External_Benchmark_Note.md` | Main external benchmark narrative, focused on green supplier validation |
| `docs/M2_External_Benchmark_Traditional_Note.md` | Traditional MCDM mini benchmark detail note |
| `docs/portfolio_project_brief.md` | Resume and interview-oriented project brief |
| `docs/demo_summary.md` | Short demo narrative for project presentation |
| `docs/repository_file_classification.md` | Repository cleanup and file classification plan |

## Historical / Legacy Files

| File | Note |
|------|------|
| `archive/legacy_m2_outputs/M2_Category_Ranking_*.csv` | Pre-revision category rankings (3 categories) |
| `archive/legacy_m2_outputs/M2_ESG_Scenario_Scores.csv` | Previous ESG sensitivity scores |
| `archive/legacy_m2_outputs/M2_ESG_Sensitivity_Report.csv` | Previous ESG sensitivity report |
| `archive/legacy_m2_outputs/M2_Strategic_Scenario_Scores.csv` | Previous strategic scenario scores |
| `archive/legacy_m2_outputs/M2_Strategic_Sensitivity_Report.csv` | Previous strategic sensitivity report |
| `archive/legacy_m2_outputs/M2_Strategic_Tier.csv` | Previous strategic tier assignment |
| `archive/legacy_m2_outputs/M2_TCO_Scenario_Scores.csv` | Previous TCO scenario scores |
| `archive/legacy_m2_outputs/M2_TCO_Sensitivity_Report.csv` | Previous TCO sensitivity report |
| `docs/M2_Revised_Target_Design.md` (in `docs/archive/`) | Stale design proposal (superseded) |
| `docs/archive/Model_Design_Journey_before_section15.docx` | Pre-section-15 design journey snapshot |
| `docs/archive/old_code.py.txt` | Original prototype single-script |
| `docs/archive/思考_legacy.docx` | Legacy notes (Chinese) |
