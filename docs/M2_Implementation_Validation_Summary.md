# M2 Implementation Validation Summary

## 1. M2 Final Positioning

M2 is not a single weighted supplier score that claims to rank suppliers on one unified metric. Instead, M2 evaluates M1-qualified suppliers through four decision lenses, producing both the Strategic Pool classification and the Cost-ESG Trade-off Ranking (`M2_Cost_ESG_Tradeoff_Ranking.csv`). The trade-off ranking integrates all four lenses into a cost-primary sort view with ESG premium tolerance. See [M2_Cost_ESG_Tradeoff_Methodology.md](M2_Cost_ESG_Tradeoff_Methodology.md) for the full ranking methodology.

| Lens | Purpose |
|---|---|
| Adjusted Cost Index | Category-relative economic positioning using Base Cost, Logistics, and Carbon. Lower = cheaper within category. This is a relative index, not true TCO. |
| ESG Strategic Fit | Independent ESG tier classification: ESG Leader, ESG Compliant, ESG Monitor, ESG Gap. It is not weighted together with cost. |
| Supplier Diagnostic / TQRDC | Technology, Quality, Risk, Delivery, and Cost diagnostic flags. This is a management review lens, not a second weighted score. |
| Strategic Pool Classification | Merged decision view combining cost position, ESG tier, and TQRDC diagnostics into a sourcing pool hierarchy. |

M2 does not implement M3 allocation or MILP. The Strategic Pool is a procurement decision-support classification, not an allocation plan.

## 2. Implemented Outputs

| File | Role |
|---|---|
| `M2_Adjusted_Cost_Index.csv` | Category-level normalized cost index with base/logistics/carbon components, cost quartile, and percentile position. Lower index = economically cheaper within category. |
| `M2_ESG_Strategic_Fit.csv` | ESG tier classification using carbon performance, PCF commitment, certification signal, and labor governance. |
| `M2_Supplier_Diagnostic_Profile.csv` | TQRDC diagnostic profile with management action recommendations. `C_cost_warning` uses Adjusted Cost Index (`Q4_Worst` or position >= 75). |
| `M2_Strategic_Pool_View.csv` | Supplier strategic pool assignment with sourcing recommendation and dashboard flag. Primary merged M2 handoff view. |
| `M2_Cost_ESG_Tradeoff_Ranking.csv` | Cost-primary ranking with ESG premium tolerance. See [M2_Cost_ESG_Tradeoff_Methodology.md](M2_Cost_ESG_Tradeoff_Methodology.md). |
| `M2_Cost_ESG_Shortlist.csv` | Revised Cost-ESG shortlist output retained for continuity with the previous M2 view. |
| `M2_Shortlist_Stability_Report.csv` | Stability report showing scenario appearance count across management-preference views. |
| `M2_Revised_Decision_View.csv` | Dashboard-facing view with `M3_eligible_flag`, `shortlist_status`, and `recommended_next_step`. |

Legacy M2 outputs are archived under `archive/legacy_m2_outputs/` and are not part of the default next-stage M2 decision line.

## 3. Strategic Pool Logic

The final decision hierarchy in `run_strategic_pool_view()` evaluates suppliers in strict order. The first matching rule determines pool assignment:

```text
1. M1_Status != PASS
   -> Restricted

2. PASS + Q1/Q2 cost + ESG Leader/Compliant + no high diagnostic
   -> Preferred

3. PASS + not Q4 + not ESG Gap + manageable diagnostics (<=1 high flag)
   -> Core

4. PASS + 2+ high diagnostic flags
   -> Restricted

5. PASS + Q4 cost OR ESG Gap OR exactly 1 high diagnostic flag
   -> Conditional

6. PASS but does not qualify for any pool above
   -> Not Priority

7. Reserve
   -> Reserved label for future M1-FAIL / resilience use, not actively assigned in current active-supplier M2 output
```

High diagnostic flags counted: `risk_level = high`, `delivery_risk = high`, `T_capability_flag = Capability gap`, or `Q_quality_warning != No quality concern`.

## 4. Validation Results

Final validation after the Strategic Pool hierarchy fix:

| Check | Result |
|---|---|
| Active suppliers processed | 37 (32 PASS + 5 LIMITED) |
| ESG Strategic Fit rows | 37 rows, 0 NaN `ESG_Position_Tier` |
| `C_cost_warning` source | Adjusted Cost Index (`Q4_Worst` / position >= 75) |
| `C_cost_warning` distribution | 25 No cost concern, 12 Adjusted cost outlier / Cost pressure |
| Strategic Pool - Preferred | 4 |
| Strategic Pool - Core | 14 |
| Strategic Pool - Conditional | 8 |
| Strategic Pool - Restricted | 11 |
| Strategic Pool - Not Priority | 0 |
| Strategic Pool - Reserve | 0 |
| S16 | Restricted (`PASS`, `Q4_Worst`, 2 high diagnostic flags) |
| S49 | Restricted (`PASS`, `Q4_Worst`, 2 high diagnostic flags) |
| All LIMITED suppliers | Restricted (5 of 5) |
| Old M2 outputs preserved | Existing continuity CSVs regenerated |
| M3/MILP output | Not generated |

## 5. Scenario Premium Layer Boundary

The Scenario Premium Layer is an optional future extension of the M2 Adjusted Cost Index. It is designed to convert selected delay, risk, or quality signals into cost-impact components only when the company has defensible replacement data.

- Registered in `config/parameter_config.csv` through disabled/pending premium parameters such as `m2_cost_premium_enabled`, `m2_delay_cost_rate`, `m2_risk_premium_schedule`, and `m2_quality_cost_rate`.
- Documented in `docs/M2_Revised_Target_Design.md` and `docs/Parameter_Assumption_Register.md` as a scenario-based extension with a real-company replacement path.
- Disabled by default. Premium weights are 0 and premium cost rates remain TBD until real company data is available.
- Not part of M1. M1 remains a qualification and risk-signal layer. It can provide signals such as `M1_Status` and `M1_Risk_Vector`, but it does not calculate premium cost.
- Gated on data availability. Delay premium should be replaced by contract penalty or ERP delay-loss records; risk premium by historical disruption loss, insurance premium, or finance-approved risk rate; quality premium by scrap, rework, return, warranty, or defect-cost records.

The separate `StrategyConfig` roadmap parameters in `strategy_config.py` remain future allocation/resilience references and should not be treated as the implemented Scenario Premium Layer.

## 6. Next Module Boundary

M3 should consume M2 outputs as allocation inputs:

| M2 output | M3 use |
|---|---|
| `M2_Strategic_Pool_View.csv` | Primary input candidate list, with `Strategic_Pool` and `dashboard_flag` guiding allocation priority. |
| `M2_Adjusted_Cost_Index.csv` | Cost input to allocation optimization. Lower index = cheaper supplier within category. |

M3 still requires external data that M2 does not provide:

- Demand: quarterly procurement plan or demand forecast per category. It must not be derived from historical contract value by a fixed ratio.
- Capacity: supplier committed capacity, production capacity, or approved allocation limit. The current annual-contract-value proxy is provisional only.
- Sourcing policy: supplier concentration policy, category sourcing rules, and risk appetite thresholds.
- Contract terms: committed volumes, prices, minimum order quantities, and allocation constraints.

MILP optimization for M3 is a separate implementation scope. M2 does not execute allocation logic.
