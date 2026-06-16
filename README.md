# Cost-led ESG Supplier Decision Support System

## Portfolio Snapshot

**Role:** Data / supply-chain analytics project  
**Domain:** EV battery supply chain, sustainable procurement, supplier risk  
**Core method:** Cost-led ESG trade-off ranking with strategic supplier pooling  
**Main outcome:** 37 active suppliers classified into 4 Preferred, 14 Core,
8 Conditional, and 11 Restricted suppliers, with ESG premium tolerance,
allocation policy comparison, scenario stress testing, and external benchmark
validation.

This project is a modular supplier decision-support system for an EV battery
supply-chain sourcing scenario. It evaluates suppliers through qualification
gates, adjusted cost, ESG readiness, diagnostic risk signals, strategic pool
classification, lightweight allocation, resilience scenarios, and external
benchmark validation.

The core contribution is a **cost-led ESG trade-off ranking**: instead of using
an arbitrary weighted score such as `70% cost + 30% ESG`, the model asks how
much adjusted-cost premium management must accept to select a higher-ESG
supplier over a cheaper lower-ESG alternative.

## Business Problem

EV supply chains face cost pressure, carbon regulation, ESG expectations,
supplier qualification risks, and resilience concerns. A sourcing team needs a
decision system that can answer:

- Which suppliers are qualified for normal sourcing?
- Which suppliers are economically attractive after logistics and carbon cost?
- When is a higher-ESG supplier worth a cost premium?
- Which suppliers should be Preferred, Core, Conditional, or Restricted?
- How does the recommended supplier pool behave under stress scenarios?

## Why This Project Matters

Many supplier-selection models collapse cost, ESG, risk, quality, and delivery
into a single weighted score. That is easy to compute but hard to defend:
weights can be arbitrary, carbon can be double-counted, and management cannot
see how much extra cost is being paid for better ESG performance.

This project keeps the decision logic explainable:

- Cost is measured through an adjusted cost index.
- ESG is translated into required cost premium tolerance.
- TQRDC risk remains diagnostic unless enterprise penalty data exists.
- Strategic Pool labels turn model results into sourcing actions.

## Model Pipeline

```text
suppliers_data.csv
        |
        v
M1 Qualification Gate
  - Quality, Finance, Tech, Labor, Compliance, Ethics
  - PASS / LIMITED / FAIL
        |
        v
M2 Cost-led ESG Trade-off Ranking
  - Adjusted Cost Index: base + logistics + carbon
  - ESG Strategic Fit: Leader / Compliant / Monitor / Gap
  - TQRDC Diagnostic: Technology, Quality, Risk, Delivery, Cost
  - Strategic Pool: Preferred / Core / Conditional / Restricted
  - ESG premium tolerance: 0%, 5%, 10%, 15%
        |
        v
M3 Lightweight Allocation Extension
  - Key_Component category
  - Preferred_First, Balanced_Core, Cost_Minimized, Risk_Controlled
        |
        v
M4 Resilience Scenario Extension
  - Demand surge
  - Preferred supplier disruption
  - EU carbon pressure
  - Malaysia backup node
        |
        v
Validation
  - Pool stability analysis
  - External green supplier benchmark
  - Traditional MCDM sanity benchmark
```

## Key Design Choices

### 1. Cost is the primary decision line

`Adjusted_Cost_Index` is a category-relative cost index built from base cost,
logistics cost, and carbon cost. Lower values indicate cheaper suppliers within
the same category.

### 2. ESG is represented through premium tolerance

ESG is not blended into cost through an arbitrary weight. For each supplier, the
model checks whether a cheaper, lower-ESG reference supplier exists and computes:

```text
required_esg_premium_pct =
    (supplier_cost - lower_cost_lower_esg_reference_cost)
    / lower_cost_lower_esg_reference_cost
```

This produces clear management questions:

- Is the ESG improvement justified at 0% premium?
- Is it justified under a 5% premium tolerance?
- Under 10%?
- Under 15%?

### 3. TQRDC is diagnostic, not a hidden penalty

Technology, Quality, Risk, Delivery, and Cost warnings are retained as a
diagnostic risk layer. They are not converted into hard penalty cost because
contract-level delay, quality, and disruption-loss data is unavailable.

### 4. Strategic Pool is a sourcing management label

The Strategic Pool classifies suppliers into:

- `Preferred`: strong cost position, acceptable/strong ESG, clean diagnostics
- `Core`: usable and stable, but not necessarily top-tier
- `Conditional`: usable only with monitoring or constraints
- `Restricted`: not suitable for normal allocation

## Main Results

M2 processes 37 active suppliers after M1 qualification:

| Pool | Count |
|------|------:|
| Preferred | 4 |
| Core | 14 |
| Conditional | 8 |
| Restricted | 11 |

Cost-ESG trade-off summary:

| Status | Count |
|--------|------:|
| No trade-off needed | 16 |
| Lower ESG or no ESG advantage | 10 |
| ESG justified under 5% premium | 4 |
| ESG justified under 15% premium | 3 |
| ESG not justified over 15% premium | 4 |

M4 resilience scenarios show that all 16 scenario-policy combinations fully
cover demand under the current illustrative assumptions. The `Balanced_Core`
policy maintains more diversified allocation than pure Preferred-first policies.

## Validation

| Validation Layer | Result |
|------------------|--------|
| Pool stability | 30/37 suppliers stable (81.1%) |
| External green benchmark | Top/bottom tier alignment = 6/6 (100%) |
| Traditional benchmark | Retained as a mini MCDM sanity check |

The external benchmark validates directional pool classification against
published supplier-selection case data. It is not treated as industry ground
truth and does not validate exact enterprise premium tolerance.

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the full reproducible workflow:

```bash
python run_all.py
```

Or run selected modules manually:

```bash
python Model1.py
python Model2.py
python M2_Cost_ESG_Tradeoff_Ranking.py
python M2_Benchmark_Stability_Analysis.py
python M2_External_Benchmark_Green.py
python M3_Lightweight_Allocation.py
python M4_Resilience_Scenario.py
```

## Important Files

| File | Purpose |
|------|---------|
| `docs/Final_Model_Overview.md` | Final model overview |
| `docs/Final_File_Index.md` | File map by role |
| `docs/M2_Cost_ESG_Tradeoff_Methodology.md` | Core M2 methodology |
| `M2_Cost_ESG_Tradeoff_Ranking.csv` | Main M2 ranking output |
| `M2_Cost_ESG_Tradeoff_Summary.csv` | Cost-ESG premium summary |
| `M2_Strategic_Pool_View.csv` | Strategic supplier pool output |
| `M4_Scenario_Summary.csv` | Scenario-policy stress-test summary |
| `docs/portfolio_project_brief.md` | Resume and interview-oriented project brief |
| `docs/demo_summary.md` | Short demo narrative |

## Limitations

- The supplier dataset is project/simulation data, not confidential enterprise
  procurement data.
- M3 demand and capacity use illustrative assumptions.
- M4 scenario parameters are stress-test assumptions, not forecasts.
- TQRDC risks are not monetized because contract-level penalty and loss data is
  unavailable.
- The external benchmark validates directional alignment, not operational
  accuracy against a real company procurement decision.

## Future Work

- Replace M3 demand and capacity assumptions with real procurement planning and
  supplier capacity data.
- Convert TQRDC diagnostics into monetary penalties only when contract,
  quality-loss, ERP delay, or disruption-loss data is available.
- Build a dashboard for interactive pool review, ESG premium tolerance, and
  scenario comparison.
