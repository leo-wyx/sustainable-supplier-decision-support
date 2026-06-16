# Final Model Overview

## Decision Pipeline

```
suppliers_data.csv (50 suppliers, 4 categories)
       |
       v
+------------------+
|  M1 Qualification |  6-Gate: Quality, Finance, Tech, Labor, Compliance, Ethics
|  Gate             |  Output: PASS (32), LIMITED (5), FAIL (13)
+------------------+
       |
       +-- PASS ----------> ACTIVE_POOL
       +-- LIMITED --------> CONDITIONAL_POOL    |
       +-- FAIL ----------> RESERVE_POOL         +---> M2 input (37)
       |
       v
+------------------------------------------+
|  M2 Cost-led ESG Trade-off Ranking       |
|  + Strategic Pool Classification         |
+------------------------------------------+
  |-- Adjusted Cost Index (category-relative)
  |-- ESG Strategic Fit (Leader/Compliant/Monitor/Gap)
  |-- Supplier Diagnostic / TQRDC (management flags)
  |-- Strategic Pool (Preferred/Core/Conditional/Restricted)
  |-- Cost-ESG Trade-off Ranking (cost-primary sort with ESG premium tolerance)
       |
       v
+------------------------------------------+
|  M3 Lightweight Allocation Extension     |
|  (single-category simulator, 4 policies) |
+------------------------------------------+
       |
       v
+------------------------------------------+
|  M4 Resilience Scenario Extension        |
|  (4 disruption scenarios x 4 policies)   |
+------------------------------------------+
       |
       v
+------------------------------------------+
|  Validation Layer                        |
|  - Pool stability analysis               |
|  - External green-supplier benchmark     |
|  - Traditional mini benchmark (sanity)   |
+------------------------------------------+
```

## Module Summary

| Module | Role | Key Outputs |
|--------|------|-------------|
| **M1** | Six-gate qualification gate | Supplier pool assignment (Active / Conditional / Reserve) |
| **M2** | Cost-led ESG trade-off ranking + strategic pool classification | Adjusted Cost Index, ESG Fit, Diagnostic Profile, Strategic Pool View, Cost-ESG Trade-off Ranking |
| **M3** | Lightweight allocation simulator (4 policies, single category) | Allocation result, summary, assumption register |
| **M4** | Resilience stress-test (4 scenarios x 4 policies) | Scenario allocation, summary, supplier stress impact |
| **Validation** | Pool stability + external benchmarks | Stability report, green supplier benchmark result, traditional mini benchmark |

## Core Decision Model

The core decision model is **M2 Cost-ESG Trade-off Ranking + Strategic Pool Classification**. M3 and M4 are extension layers that demonstrate downstream applications of the M2 pool output. They do not modify M1 or M2 logic.

### M2 Four-Lens Design

1. **Adjusted Cost Index** -- Category-relative economic positioning (base + logistics + carbon costs). Lower index = cheaper within category.
2. **ESG Strategic Fit** -- Independent ESG tier classification (Leader / Compliant / Monitor / Gap), not weighted together with cost.
3. **Supplier Diagnostic (TQRDC)** -- Technology, Quality, Risk, Delivery, Cost diagnostic flags for management review.
4. **Strategic Pool Classification** -- Merged decision view: Preferred, Core, Conditional, Restricted.

### Cost-ESG Trade-off Ranking

The M2 Cost-ESG Trade-off Ranking integrates all four lenses into a single explainable ranking. Cost is the primary sort dimension. ESG premium tolerance is expressed as the extra cost management must accept to select a higher-ESG supplier. This avoids the double-counting and opacity problems of a traditional weighted-score approach.

## Validation

| Layer | Method | Status |
|-------|--------|--------|
| Pool stability | 5 scenarios, Preferred/Core composition stability | 81.1% stable, 10.8% moderate, 8.1% sensitive |
| External benchmark (green) | 10-supplier GSCM case, Fuzzy AHP + TOPSIS | Validates directional pool classification |
| External benchmark (traditional) | 5-supplier MCDM sanity check, TOPSIS + VIKOR | Retained for backwards compatibility |

## File Map

See [Final_File_Index.md](Final_File_Index.md) for the complete file listing.
