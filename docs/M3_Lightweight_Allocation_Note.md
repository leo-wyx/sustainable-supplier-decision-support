# M3 Lightweight Resource Pool Allocation Note

## Overview

M3 is a lightweight single-category allocation simulator that reads M2 output CSVs and runs 4 allocation policies for comparison.

**Status:** Standalone module. Reads M2 outputs but does not modify M1/M2/M4 logic or output files.

**Boundary:** M3 is a lightweight allocation **simulator**, not a MILP optimizer. Scenario stress testing (demand shocks, capacity disruptions) is reserved for M4 Resilience Simulation.

**Note on model scope:** M3 is an extension layer. The core decision model of this project is the **M2 Cost-ESG Trade-off Ranking + Strategic Pool Classification** (see `M2_Cost_ESG_Tradeoff_Ranking.csv` and [M2_Cost_ESG_Tradeoff_Methodology.md](M2_Cost_ESG_Tradeoff_Methodology.md)). M3 demonstrates a downstream use of the M2 pool output but does not modify M1 or M2 logic, and its allocation policies are illustrative assumptions for the Key_Component category only.

---

## Data Pipeline

```
M2_Strategic_Pool_View.csv  ----+   (M2 output: pool classification,
                                  |    cost index, risk, ESG tier)
suppliers_data.csv  ------------+   (annual_contract_value_usd as capacity proxy)
                                |
                                v
                     M3_Lightweight_Allocation.py
                                |
                    +-----------+-----------+
                    |           |           |
                    v           v           v
              Result.csv   Summary.csv   Scenario_Assumptions.csv
```

**Input CSVs read:**
- `M2_Strategic_Pool_View.csv` - supplier pool classification, cost index, risk level, delivery risk, ESG tier
- `suppliers_data.csv` - annual contract value (used as capacity proxy)

**Capacity and demand are illustrative assumptions, not real enterprise data.**
- Demand: $10M quarterly (single illustrative value)
- Capacity: annual_contract_value_usd / 4 (quarterly proxy, not confirmed with procurement)

The following TBD placeholder files are NOT modified:
- `M3_Category_Demand_Plan.csv`
- `M3_Supplier_Capacity_Assumption.csv`
- `M3_Allocation_Policy.csv`

---

## Supplier Pool (Key_Component, 9 suppliers)

| Supplier | M2 Pool | Cost Index | Risk | Delivery Risk | ESG Tier | Quarterly Capacity |
|----------|---------|-----------|------|---------------|----------|-------------------|
| S11 | Preferred | 0.302 | medium | medium | ESG Leader | $4,890,500 |
| S08 | Preferred | 0.371 | medium | low | ESG Leader | $5,992,750 |
| S07 | Preferred | 0.400 | medium | low | ESG Compliant | $4,358,250 |
| S03 | Preferred | 0.418 | medium | low | ESG Compliant | $5,669,500 |
| S05 | Core | 0.420 | low | low | ESG Leader | $8,471,500 |
| S04 | Core | 0.427 | medium | low | ESG Compliant | $4,767,250 |
| S09 | Conditional | 0.600 | low | low | ESG Leader | $13,254,250 |
| S02 | Conditional | 0.678 | low | low | ESG Leader | $12,439,500 |
| S10 | Restricted | 0.331 | medium | low | ESG Compliant | $7,064,750 |

9 suppliers were identified with M2 pool classification. 3 additional suppliers (S01, S06, S12) exist in `suppliers_data.csv` with `category=Key_Component` but have no M2 Strategic Pool assignment and are excluded from allocation.

---

## Allocation Rules

| Rule | Preferred_First | Balanced_Core | Cost_Minimized | Risk_Controlled |
|------|----------------|---------------|----------------|-----------------|
| Restricted allocation | 0% | 0% | 0% | 0% |
| Conditional cap | 10% | 5% | 5% | 5% |
| Single-supplier max | 45% | 40% | 40% | 40% (low risk) |
| Medium-risk cap | n/a | n/a | n/a | **30% each** |
| Sort order | Pool rank, then cost | Pool rank, then cost | Cost only (cheapest first) | Low risk first, then cost |

### Policy Descriptions

1. **Preferred_First**: Preferred suppliers allocated in cost order (cheapest within pool), up to 45% each. Core fills residual if Preferred capacity is exhausted. Conditional capped at 10%. This is the baseline policy reflecting standard pool priority.

2. **Balanced_Core**: Core suppliers receive a reserved allocation window (20% each) before Preferred suppliers (~60% target). Preferred fills remainder (up to 40% each). Conditional capped at 5%. **Business rationale:** This policy sacrifices some cost efficiency (higher weighted cost index) to maintain Core pool engagement and reduce over-reliance on Preferred suppliers. Core suppliers may serve as strategic backup capacity; keeping them active prevents atrophied relationships and capacity attrition.

3. **Cost_Minimized**: All non-Restricted suppliers sorted purely by Adjusted Cost Index (cheapest first), ignoring pool priority. Conditional capped at 5%. This is the cost-optimal benchmark.

4. **Risk_Controlled**: Low-risk suppliers allocated first (up to 40% each). Medium-risk suppliers capped at **30% each** to limit risk exposure. Conditional capped at 5%. High-risk and Restricted are excluded.

---

## Results

### Policy Comparison

| Policy | Allocated | Unmet | P% | C% | Cd% | R% | Suppliers Used | Weighted Cost | Risk Profile |
|--------|-----------|-------|----|----|-----|----|---------------|--------------|-------------|
| Preferred_First | $10M | $0 | 100% | 0% | 0% | 0% | 3 | 0.3426 | medium=3 |
| Balanced_Core | $10M | $0 | 60% | 40% | 0% | 0% | 4 | 0.3641 | low=1, medium=3 |
| Cost_Minimized | $10M | $0 | 100% | 0% | 0% | 0% | 3 | 0.3490 | medium=3 |
| Risk_Controlled | $10M | $0 | 50% | 40% | 10% | 0% | 5 | 0.3965 | low=3, medium=2 |

### Policy Differentiation

**Preferred_First, Cost_Minimized converge** because Preferred suppliers are the cheapest (S11 cost=0.302, S08 cost=0.371) and have sufficient combined capacity ($20.9M) to cover the $10M demand alone. S11, S08, and S07 fill 100% of demand before cheaper cost order matters between them.

**Balanced_Core diverges** by reserving a 20% allocation window for each Core supplier (S05, S04) before Preferred suppliers are considered. This produces a ~60% Preferred / ~40% Core split at weighted cost 0.3641 (vs 0.3426 for Preferred_First) -- a moderate premium for maintaining Core pool engagement.

**Risk_Controlled diverges most** by prioritising low-risk suppliers first (S05, S09, S02) and capping medium-risk at 30% each. S11 (Preferred, medium) receives only $3M (30% cap) instead of $4.5M. This brings in 5 suppliers at weighted cost 0.3965 -- the broadest supply base and highest cost, reflecting the risk premium.

### Unmet Demand

All 4 policies achieve 100% allocation with $0 unmet demand under the current assumptions. Total non-Restricted capacity is approximately $60M against $10M demand. Unmet demand would appear under:
- Higher demand scenarios ($15M+)
- Capacity-constrained scenarios (supplier disruptions)
- Stricter Conditional/Restricted policies

These stress scenarios are reserved for M4.

---

## Boundary

- M3 does **not** modify `Model2.py` or any M2 output CSVs.
- M3 does **not** affect M1 (signal processing) or M4 (resilience simulation).
- M3 does **not** run MILP optimization or cross-category trade-off analysis.
- Capacity and demand are illustrative assumptions, not real enterprise data.
- The 3 TBD placeholder CSV files (`M3_Allocation_Policy.csv`, `M3_Category_Demand_Plan.csv`, `M3_Supplier_Capacity_Assumption.csv`) remain unmodified.

---

## Files

| File | Description |
|------|-------------|
| `M3_Lightweight_Allocation.py` | Main allocation script |
| `M3_Scenario_Assumptions_Key_Component.csv` | Transparent assumptions (demand, capacity, policy params) |
| `M3_Key_Category_Allocation_Result.csv` | Per-supplier allocation detail, 4 policies x 9 suppliers |
| `M3_Key_Category_Allocation_Summary.csv` | Policy-level summary |
| `docs/M3_Lightweight_Allocation_Note.md` | This document |
