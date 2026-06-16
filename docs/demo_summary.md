# Demo Summary

## One-Minute Project Pitch

This project builds a modular supplier decision-support system for an EV battery
supply-chain sourcing scenario. It starts with supplier qualification gates,
then ranks M1-qualified suppliers through a cost-led ESG trade-off method,
classifies suppliers into strategic sourcing pools, and demonstrates downstream
allocation and resilience scenarios.

The key modelling choice is that ESG is not hidden inside an arbitrary weighted
score. Instead, the model quantifies the adjusted-cost premium required to select
a higher-ESG supplier over a cheaper lower-ESG alternative.

## Business Question

How should a sourcing team choose suppliers when cost pressure, ESG
requirements, diagnostic supplier risk, and supply resilience all matter?

## Final Logic

```text
M1: Qualification Gate
    PASS / LIMITED / FAIL

M2: Cost-led ESG Trade-off Ranking
    Adjusted Cost Index
    ESG premium tolerance
    TQRDC diagnostic label
    Strategic Pool

M3: Lightweight Allocation Extension
    Four allocation policies for Key_Component

M4: Resilience Scenario Extension
    Four disruption scenarios x four policies

Validation:
    Pool stability + external green supplier benchmark
```

## Core M2 Output

M2 evaluates 37 active suppliers:

| Strategic Pool | Count |
|----------------|------:|
| Preferred | 4 |
| Core | 14 |
| Conditional | 8 |
| Restricted | 11 |

The Cost-ESG trade-off ranking shows:

| Trade-off Status | Count |
|------------------|------:|
| No trade-off needed | 16 |
| Lower ESG or no ESG advantage | 10 |
| ESG justified under 5% premium | 4 |
| ESG justified under 15% premium | 3 |
| ESG not justified over 15% premium | 4 |

## M3 Key Message

M3 is a lightweight extension, not a MILP optimizer. It uses the M2 Strategic
Pool to compare four allocation policies for the Key_Component category:

- `Preferred_First`
- `Balanced_Core`
- `Cost_Minimized`
- `Risk_Controlled`

All four policies meet the illustrative $10M quarterly demand. The policy
comparison shows a visible trade-off between cost efficiency and supplier-base
diversification.

## M4 Key Message

M4 tests the supplier pool under four scenarios:

- Demand surge +50%
- Preferred supplier disruption
- EU carbon pressure
- Malaysia backup node

All 16 scenario-policy combinations cover demand under the current illustrative
assumptions. `Balanced_Core` provides a more diversified allocation profile,
while pure Preferred-first policies can create concentration exposure.

## Benchmark Message

The external green supplier benchmark uses a 10-supplier, 17-criterion published
GSCM case. The simplified M2-style pool logic captures the top and bottom tiers:

- Top/bottom tier alignment: 6/6 (100%)
- Full directional alignment: 6/10 (60%)

The benchmark validates directional classification, not exact enterprise
premium tolerance.

## Limitations to State Proactively

- Supplier data is project/simulation data, not confidential company data.
- M3 demand and capacity are illustrative assumptions.
- M4 stress parameters are scenario assumptions, not forecasts.
- TQRDC diagnostics are not monetized without contract-level penalty data.

## Best Files to Show

1. `docs/Final_Model_Overview.md`
2. `docs/M2_Cost_ESG_Tradeoff_Methodology.md`
3. `M2_Cost_ESG_Tradeoff_Summary.csv`
4. `M2_Strategic_Pool_View.csv`
5. `docs/M2_External_Benchmark_Note.md`
6. `M4_Scenario_Summary.csv`
