# M4 Resilience Scenario Simulation

## Purpose

M4 is a lightweight stress-test layer on top of M2 Strategic Pool and M3 allocation
logic. It applies 4 disruption scenarios x 4 allocation policies to the
Key_Component category and measures whether the supplier base absorbs or breaks
under each shock.

No MILP, no multi-category optimization. Scenario parameter adjustments are
explicitly documented as illustrative assumptions, not real enterprise data.

**Note on model scope:** M4 is an extension layer. The core decision model of this project is the **M2 Cost-ESG Trade-off Ranking + Strategic Pool Classification** (see `M2_Cost_ESG_Tradeoff_Ranking.csv` and [M2_Cost_ESG_Tradeoff_Methodology.md](M2_Cost_ESG_Tradeoff_Methodology.md)). M4 applies stress scenarios on top of M2 pool output and M3 allocation results but does not modify M1, M2, or M3 logic. Its scenario parameters and disruption assumptions are illustrative.

## Methodology

Each scenario modifies one or more inputs (demand, capacity, cost, pool
classification) on a copy of the M2 pool data, then re-runs the same 4 allocation
policies from M3. The 3 output CSVs record:

- **M4_Scenario_Allocation_Result.csv** -- per-supplier detail: allocation before
  vs. after, cost before vs. after, pool before vs. after
- **M4_Scenario_Summary.csv** -- one row per scenario x policy: total allocated,
  pool shares, weighted cost, risk composition
- **M4_Supplier_Stress_Impact.csv** -- per-supplier across-scenario delta:
  capacity change %, cost change %, total allocation delta

## Scenarios

### A. Demand_Surge_50

| Parameter | Baseline | Stressed |
|-----------|----------|----------|
| Demand    | $10M     | $15M     |

- All 4 policies fully cover +50% demand (no unmet demand).
- Preferred_First / Cost_Minimized rely on 3 Preferred suppliers only (S08 hits
  100% capacity).
- Balanced_Core uses 4 suppliers (Core S05/S04 scale up).
- Risk_Controlled uses 5 suppliers (Conditional S09/S02 each at $750K, 5% cap).
- **Finding:** Current capacity is sufficient for a +50% surge, but Preferred_First
  pushes 2 suppliers to >90% utilization -- single-point-of-failure risk.

### B. Preferred_Disruption

| Supplier | Baseline capacity | Stressed capacity |
|----------|-------------------|-------------------|
| S11      | $4,890,500       | $1,467,150 (-70%) |

S11 is the largest Preferred supplier by baseline allocation ($4.5M in
Preferred_First). Its capacity is cut by 70%.

- All 4 policies absorb the shock fully (no unmet demand).
- Preferred_First shifts allocation to S08 ($4.5M) and S07 ($4.03M) within the
  45% cap.
- Balanced_Core is least affected: Core S05/S04 are already reserved, and S11's
  shortfall is taken up by S08 ($2M more) and S07 ($0.53M more).
- **Finding:** The 45% max-share cap in Preferred_First prevents overloading
  S08, distributing to S07 instead. Balanced_Core is the most resilient to a
  single Preferred supplier failure because Core reserve is independent of the
  disrupted supplier.

### C. EU_Carbon_Pressure

| Supplier | carbon_intensity | ESG tier | Pool change | Cost change |
|----------|-----------------|----------|-------------|-------------|
| S04      | 0.569           | Compliant| Core->Conditional | +15% |
| S07      | 0.572           | Compliant| Preferred->Core | +15% |
| S03      | NaN             | Compliant| Preferred->Core | +15% |
| S11      | 0.431           | Leader   | None        | +15% |
| S08      | 0.415           | Leader   | None        | +15% |

Threshold: carbon_intensity >= median (0.375) OR NaN. All affected get cost
+15%. Non-ESG-Leader affected suppliers are downgraded one pool level.

- All 4 policies absorb without unmet demand.
- Preferred_First shifts from S07/S03 (now Core) to S05 (Core) at $1M.
  Weighted cost rises from 0.3426 to 0.3900 (+13.8%).
- Balanced_Core becomes P=40% C=60% (was P=60% C=40%) as downgraded S07 and
  S03 are consumed as Core. Weighted cost from 0.3641 to 0.4109 (+12.9%).
- **Finding:** ESG Leaders (S11, S08) retain Preferred status despite higher
  carbon, meaning ESG tier acts as a differentiator within the affected group.
  S04 drops to Conditional and is largely unused (cost is high).

### D. Malaysia_Backup_Node

| Supplier | Pool | Cost index | Capacity | Risk |
|----------|------|-----------|----------|------|
| MY_Backup_Node | Core | 0.4442 | $4M | Low |

A virtual Malaysia-based backup node is added to the pool as a Core supplier.

- **Preferred_First / Cost_Minimized:** backup node available but idle.
  Preferred pool satisfies all demand before Core is considered, so
  MY_Backup_Node receives $0 allocation. These policies do not reserve Core
  capacity.
- **Balanced_Core:** backup node activated. Core suppliers receive a reserved
  20% allocation window each, so MY_Backup_Node gets $2M (20% share).
  Preferred concentration reduced from 60% to 40%.
- **Risk_Controlled:** backup node fully utilized. As a low-risk Core supplier,
  it receives the full $4M allocation (40% share). Preferred drops from 50%
  to 10%, risk profile shifts to low=4, medium=1.
- **Finding:** The backup node is effective only under policies that reserve or
  prioritise Core/low-risk capacity (Balanced_Core, Risk_Controlled). Under
  Preferred-first policies (Preferred_First, Cost_Minimized) it is idle because
  demand is satisfied before the Core pool is reached.

## Key Findings

1. **No policy breaks under any scenario** -- all 16 combinations achieve full
   demand coverage. The supplier base has structural slack.
2. **Preferred_First is fragile under surge** -- 2 suppliers at >90% utilization
   in Demand_Surge_50 is a concentration risk.
3. **Balanced_Core is the most robust policy** -- across all 4 scenarios it
   maintains a diversified allocation (4-5 suppliers, Core presence, minimal
   concentration).
4. **Conditional suppliers (S09, S02) are never used except under
   Risk_Controlled** -- their high cost (0.600, 0.678) makes them uncompetitive
   in cost-sorted policies.
5. **MY_Backup_Node helps only when Core allocation is reserved** -- it is
   idle under Preferred_First and Cost_Minimized but fully utilized under
   Risk_Controlled.

## Boundary Disclaimer

All demand, capacity, and cost figures are illustrative proxies derived from
annual_contract_value_usd / 4. They do not reflect actual enterprise
procurement data. Scenario parameters (70% disruption, +50% demand, +15%
carbon cost, median carbon_intensity threshold) are hypothetical stress levels
chosen for simulation purposes. Real-world application would require validated
supplier capacity data and calibrated shock magnitudes.
