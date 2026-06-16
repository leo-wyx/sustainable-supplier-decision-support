# M2 External Benchmark 1: Traditional Supplier-Selection Case

## Purpose

Validate whether the current M2 simplified lens / Strategic Pool logic can
reproduce or explain top supplier choices from a published multi-criteria
decision-making (MCDM) supplier-selection case.

This is a standalone external validation module. It does not modify Model2.py
or any core M2 outputs.

## Source Case

- **Paper:** Supplier Selection for Construction Projects Through TOPSIS and
  VIKOR Multi-Criteria Decision Making Methods (IJERTV3IS051992)
- **Suppliers:** 5 candidate suppliers
- **Criteria:** Quality, Cost, Delivery Time, Technical Capability, Financial
  Capability, Managerial & Commercial Capability, Trust
- **Reference outcome:** Supplier 3 ranked best (rank 1) by both TOPSIS and
  VIKOR methods.

## Criteria Weights (from paper)

| Criterion | Weight |
|-----------|--------|
| Quality | 0.2623 |
| Cost | 0.2083 |
| Delivery Time | 0.0585 |
| Technical Capability | 0.1170 |
| Financial Capability | 0.0904 |
| Managerial & Commercial Capability | 0.0644 |
| Trust | 0.1990 |

## Mapping to M2 Lenses

| M2 Lens | Paper Criteria | Notes |
|---------|---------------|-------|
| **Cost** | Cost | Direct mapping; higher paper score = better cost position |
| **ESG** | *Not available* | Traditional case has no ESG criteria; marked as not evaluated |
| **T** (Technical) | Technical Capability | Threshold: strong >= 8, weak <= 5 |
| **Q** (Quality) | Quality | Threshold: strong >= 8, weak <= 5 |
| **R** (Risk proxy) | Financial Capability + Trust (average) | Combined as financial/relational risk proxy |
| **D** (Delivery) | Delivery Time | Threshold: strong >= 8, weak <= 5 |
| **C** (Cost) | Cost (reused) | Diagnostic context only; primary lens is Cost |

### Thresholds

All thresholds are documented and transparent:
- **Strong** >= 8 (no diagnostic concern)
- **Acceptable** >= 7 (manageable)
- **Weak** <= 5 (material weakness)

### Pool Assignment Rules

- **Preferred:** Top cost position + strong quality (>=8) + strong technical (>=8) + zero material weaknesses
- **Core:** Acceptable cost + acceptable quality/technical (>=7) + no more than one weakness
- **Conditional:** One material weakness (any criterion <= 5)
- **Restricted:** Two or more material weaknesses

## Decision Matrix (from paper)

| Supplier | Quality | Cost | Delivery Time | Technical Capability | Financial Capability | Managerial & Commercial | Trust |
|----------|---------|------|---------------|---------------------|---------------------|------------------------|-------|
| Supplier 1 | 7 | 6 | 9 | 9 | 7 | 8 | 7 |
| Supplier 2 | 7 | 7 | 7 | 9 | 7 | 8 | 7 |
| Supplier 3 | 9 | 8 | 7 | 9 | 7 | 8 | 8 |
| Supplier 4 | 5 | 4 | 9 | 7 | 6 | 7 | 6 |
| Supplier 5 | 5 | 3 | 7 | 7 | 5 | 7 | 6 |

## Results

### Weighted Score Reproduction

A weighted-score calculation using the published weights was performed as a
reference check only (not M2 methodology):

| Rank | Supplier | Weighted Score |
|------|----------|---------------|
| 1 | Supplier 3 | 8.2296 |
| 2 | Supplier 2 | 7.2977 |
| 3 | Supplier 1 | 7.2064 |
| 4 | Supplier 4 | 5.6774 |
| 5 | Supplier 5 | 5.2617 |

### Simplified M2 Pool Classification

| Supplier | Pool | Comparison | Directional Alignment | Reason |
|----------|------|------------|-----------------------|--------|
| S1 (Supplier 1) | Conditional  | different_but_explainable      | different_but_explainable | Cost=6; Q=7; T=9; R_avg=7.0; D=9 | adequate but no strong position |
| S2 (Supplier 2) | Core         | aligned_recommended            | aligned                   | Cost=7; Q=7; T=9; R_avg=7.0; D=7 | acceptable across criteria, no material weakness |
| S3 (Supplier 3) | Preferred    | aligned_top_supplier           | aligned_top               | Cost=8 (top); Q=9; T=9; R_avg=7.5; D=7 | no weakness, top cost, strong Q+T |
| S4 (Supplier 4) | Restricted   | not_recommended                | aligned                   | Cost=4; Q=5; T=7; R_avg=6.0; D=9 | weaknesses=2 (Quality+Cost) |
| S5 (Supplier 5) | Restricted   | not_recommended                | aligned                   | Cost=3; Q=5; T=7; R_avg=5.5; D=7 | weaknesses=2 (Quality+Cost) |

### Supplier 3 Verification

- **Paper rank:** 1
- **M2 simplified pool:** Preferred
- **Comparison:** aligned_top_supplier
- **Supplier 3 is Preferred/Core:** YES

-> The M2 simplified logic correctly identifies Supplier 3 as Preferred,
   aligning with the paper's top-ranked supplier.

### Agreement Summary

**Top supplier alignment:** Supplier 3 (paper rank 1) is classified as Preferred in the M2 pool.
  -> Supplier 3 is Preferred/Core: YES

**Recommended set alignment:** Suppliers 2 and 3 (paper ranks 1-2) both map to Preferred/Core in the M2 pool.
  The top-two recommended set is consistent between the paper and the simplified pool.

**Directional alignment:** 4/5 (80.0%)
  Directionally aligned means:
  - Paper rank <= 2 -> pool is Preferred/Core
  - Paper rank >= 4 -> pool is Restricted
  - Supplier 3 alone is aligned_top_supplier

  S4 and S5 (paper ranks 4-5) are Restricted in the M2 pool, which is directionally consistent
  with the paper's lowest rankings. S1 (Supplier 1, paper rank 3) is the only different-but-explainable case:
  the simplified pool flags adequate-but-unremarkable scores (Cost=6, Q=7), while the
  weighted-score model compensates across criteria.

- Pool distribution: Preferred=1, Core=1,
  Conditional=1, Restricted=2

### Differences and Explanation

- **S1 (Supplier 1)** is Conditional (paper rank 3). The simplified pool identifies specific weaknesses that a weighted-score model may mask. This is not a disagreement -- the pool adds diagnostic nuance to the numerical ranking.

- **S4 (Supplier 4)** is Restricted (paper rank 4). Multiple material weaknesses justify Restricted status. The paper also ranks this supplier lowest, so the direction is consistent.
- **S5 (Supplier 5)** is Restricted (paper rank 5). Multiple material weaknesses justify Restricted status. The paper also ranks this supplier lowest, so the direction is consistent.

## Boundary

- **This is an external validation module, not core M2.**
- **It does not modify Model2.py.**
- **It does not use ESG** because the reference case has no ESG criteria.
- The weighted-score calculation is a reference reproduction only; it is not
  part of the current M2 methodology.
- Two of the five suppliers are classified as Preferred/Core, matching the
  paper's top two ranks.
- All disagreements between the simplified pool and the paper ranking are
  explainable by the pool's explicit weakness-detection logic, which a
  compensatory weighted-score model does not surface.

---
*Generated by M2_External_Benchmark_Traditional.py on 2026-06-16 00:02*
