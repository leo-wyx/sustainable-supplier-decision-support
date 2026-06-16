# M2 Cost-ESG Trade-off Ranking: Methodology

## Purpose

The M2 Cost-ESG Trade-off Ranking is an M2 post-processing layer that
integrates Adjusted Cost ranking, ESG premium tolerance, TQRDC risk
profile, and Strategic Pool label into a single, explainable ranking
view. It does not replace or modify the existing M2 Strategic Pool,
nor does it alter M1/M3/M4 core logic.

## Why Cost Is Primary

Cost is established as the primary sorting dimension for two reasons:

1. **Adjusted_Cost_Index already embeds multiple cost dimensions**
   (base, logistics, carbon -- see below). It is the most
   comprehensive single cost metric in the model.

2. **ESG should be quantifiable in cost terms.** Rather than asking
   "how much weight should ESG get in a composite score," the
   trade-off ranking answers: "how much cost premium must management
   accept to select a higher-ESG supplier?"

## What Adjusted_Cost_Index Already Includes

The Adjusted_Cost_Index is computed in M2 and includes:

| Component | Description |
|-----------|-------------|
| Base cost | Supplier's raw unit price or contract cost |
| Logistics cost | Transport, warehousing, duties allocated per supplier |
| Carbon cost | Estimated CO2e cost at a shadow carbon price |

These three components are weighted by category-specific weights and
summed into a single Adjusted_Cost_Index. No additional ESG or
TQRDC adjustment is applied to this index.

## Why ESG Is Not Added as Arbitrary Weight

A typical "weighted-score" approach would assign, for example,
70% cost + 30% ESG and produce a blended score. This has known
problems:

- **Double-counting carbon.** Carbon is already in Adjusted_Cost_Index,
  and ESG ratings often include environmental criteria. A weighted
  blend would count carbon twice -- once in cost, once in ESG.
- **Opacity.** A blended score hides the magnitude of the
  cost-vs-ESG trade-off. Management cannot see whether they are
  paying 2% or 20% more for ESG.
- **False precision.** Arbitrary weights (70/30, 60/40, etc.)
  create an illusion of objectivity while masking subjective
  weight choices.

Instead, this module keeps cost and ESG separate and makes the
trade-off explicit.

## How Required ESG Premium Is Calculated

For each supplier within a category, the module searches for
suppliers that simultaneously have:

- A **lower** Adjusted_Cost_Index (cheaper)
- A **lower** ESG tier (worse ESG standing)

If such a supplier exists, the required ESG premium is:

```
premium_pct = (supplier_cost - lower_cost_supplier_cost)
              / lower_cost_supplier_cost * 100
```

This answers: "How much more does this supplier cost, in percentage
terms, compared to a cheaper, lower-ESG alternative?"

If multiple such suppliers exist, the one with the smallest premium
(the closest cost competitor) is used as the reference.

If no such supplier exists, the premium is 0 and the case is
labelled as "no lower cost + lower ESG reference" -- meaning the
supplier either is the lowest-cost option, or the cheaper
alternatives have equal or better ESG standing.

## Meaning of 0/5/10/15 Tolerance Scenarios

The four tolerance thresholds answer:

| Tolerance | Question |
|-----------|----------|
| 0% | "Are we willing to pay any premium at all for ESG?" |
| 5% | "Are we willing to pay up to 5% more?" |
| 10% | "Are we willing to pay up to 10% more?" |
| 15% | "Are we willing to pay up to 15% more?" |

Each supplier is classified as:

- **Yes**: required_esg_premium_pct <= tolerance
- **No**: required_esg_premium_pct > tolerance
- **Not applicable**: no lower-cost lower-ESG reference exists
  (the supplier is already cost-competitive or ESG-efficient)

These scenarios are not predictions. They are decision-support
tool: management selects a tolerance and immediately sees which
suppliers are ESG-justified under that policy.

## Category Summary Intervals

The M2_Cost_ESG_Tradeoff_Summary.csv uses interval-based (not
cumulative) supplier counts for ESG justification:

| Column | tradeoff_status | Premium range |
|--------|-----------------|---------------|
| suppliers_esg_justified_0_5pct | esg_justified_under_5pct | 0% < premium <= 5% |
| suppliers_esg_justified_5_10pct | esg_justified_under_10pct | 5% < premium <= 10% |
| suppliers_esg_justified_10_15pct | esg_justified_under_15pct | 10% < premium <= 15% |
| suppliers_esg_not_justified_over_15pct | esg_not_justified_cost_gap_too_high | premium > 15% |

These are mutually exclusive buckets. Each supplier with a valid
reference appears in exactly one interval. Suppliers without a
lower-cost lower-ESG reference are excluded from all four columns
(they have no premium to classify) but may appear in the
no_tradeoff_needed or lower_esg_or_no_esg_advantage statuses.

The key_finding field in the summary describes each interval in
natural language, and always refers to the interval range (e.g.
"3 supplier(s) ESG-justified (5-10% premium)") rather than
cumulative totals, so the reader can immediately see the
distribution shape.

## Why TQRDC Is Diagnostic Risk Profile, Not a Hard Penalty

TQRDC warnings (Technology, Quality, Risk, Delivery, Cost) are
deliberately excluded from the cost-ESG ranking formula for two
reasons:

1. **TQRDC flags are noisy in small datasets.** A single
   high-risk-level flag on a small supplier pool can
   disproportionately distort ranking scores.

2. **Penalty conversion requires enterprise data.** Converting a
   TQRDC warning into a precise cost penalty (e.g., "a high-risk
   supplier costs 3% more in expediting") requires historical
   contract-performance data, which this model does not have.

Instead, TQRDC is presented as a diagnostic overlay:

| Warning count | Label |
|---------------|-------|
| 0 | Low diagnostic concern |
| 1 | Moderate diagnostic concern |
| >=2 | High diagnostic concern |

Management can review high-TQRDC suppliers separately and, where
enterprise data exists, convert warnings to contract-level
penalties (see Future Work).

## How management_rank Differs from a Weighted Score

A weighted-score approach produces a single blended number that
obscures trade-offs. The management_rank is an **ordering**, not
a score:

1. M1_Status: PASS suppliers are ranked above LIMITED/FAIL.
2. Strategic_Pool priority: Preferred > Core > Conditional > Restricted.
3. cost_rank: within same pool label, cheaper suppliers rank first.
4. ESG tier: higher ESG breaks ties.
5. TQRDC warnings: fewer warnings breaks remaining ties.

This prioritisation is transparent -- each step is a decision
criterion that management can challenge or adjust. No hidden
weights.

## How Strategic Pool Should Be Interpreted

The Strategic Pool is a **management label**, not an algorithmic
output. The original M2 Strategic_Pool assignment already
incorporates cost quartile, ESG tier, and diagnostic flags.
Trade-off ranking respects this label but adds a finer-grained
view: a "Core" supplier with a 20% required ESG premium is
different from a "Core" supplier with a 2% required premium.

Management should use the Strategic Pool for broad portfolio
segmentation and the trade-off ranking for individual supplier
evaluation and negotiation strategy.

## Boundary and Future Work

**Boundaries:**

- This module requires all three input CSVs to exist and have
  consistent supplier_id and category values.
- The model is run on static data (cross-section, not time series).
- Premium calculation is intra-category only. No cross-category
  comparison is made (each category has different cost structures).

**Future work when real enterprise data exists:**

- Convert TQRDC warnings to expected cost penalties at the
  contract level (e.g., quality warnings -> expected rework cost;
  delivery risk -> expected expediting cost).
- Incorporate contract-level negotiation data (e.g., actual price
  reduction achieved) to adjust premium calculations.
- Time-series tracking of premium changes across re-sourcing
  cycles.
