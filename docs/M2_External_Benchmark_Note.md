# M2 External Benchmark Note

## Overview

M2 uses an external-data validation strategy with two benchmarks:

| Benchmark | Suppliers | Criteria | Method | Status |
|-----------|-----------|----------|--------|--------|
| **Green Supplier** (main) | 10 | 17 GSCM | Fuzzy AHP + TOPSIS | Primary validation benchmark |
| **Mini Traditional** (sanity) | 5 | 7 | TOPSIS / VIKOR | Traditional MCDM sanity check |

The **10-supplier green supplier selection benchmark** is the main external
data benchmark for M2. It validates whether a simplified M2-style pool logic
can reproduce or explain supplier priorities from a published green supplier
selection case. The 5-supplier traditional case is retained only as a mini
sanity check for method agreement.

This note validates **directional pool classification**, not exact enterprise
premium tolerance. The current project does not claim that a public paper case
can validate company-specific cost-premium thresholds such as 5%, 10%, or 15%.

---

## Main Green Supplier Benchmark

### Source Data

**Reference paper:**

Uppala, A.K., Sharma, R., Raj, H., Kumar, R.M., Selvam, D.P., Manupati, V.
(2016). "Selection of Green suppliers based on GSCM practices: Using fuzzy MCDM
approach." Proceedings of the 2016 International Conference on Industrial
Engineering and Operations Management (IEOM), Detroit, Michigan, USA. Paper
#206.

**Original data source:**

Kannan, D., Jabbour, A.B.L.S., Jabbour, C.J.C. (2014). "Selecting green
suppliers based on GSCM practices: Using fuzzy TOPSIS applied to a Brazilian
electronics company." European Journal of Operational Research, 233(2),
432-447.

### Dataset

- 10 suppliers: A1 through A10
- 17 GSCM criteria
- Criteria weights from fuzzy AHP
- Supplier-criteria priority matrix from the published case
- Reference ranking from fuzzy TOPSIS

### Methodology

1. Use the paper's Alternative Priority Weights as the reference ranking.
2. Recompute a weighted green score as a consistency check.
3. Count weak criteria for each supplier using bottom-quartile criterion
   performance.
4. Assign a simplified M2-style pool:

| Pool | Criteria |
|------|----------|
| Restricted | weak_criteria_count > 6 or bottom 20% by green score |
| Preferred | top 20% by green score and weak_criteria_count <= 2 |
| Core | rank 3-5 and weak_criteria_count <= 4 |
| Conditional | all remaining suppliers |

### Results

| Pool | Suppliers | Weak Count |
|------|-----------|------------|
| Preferred | A3, A10 | 0, 1 |
| Core | A4, A5 | 0, 0 |
| Conditional | A7 | 5 |
| Restricted | A1, A2, A6, A8, A9 | 17, 10, 14, 13, 11 |

Key validation results:

- Paper #1 supplier A10 maps to `Preferred`.
- Top/bottom tier alignment = 6/6 (100%).
- Full directional alignment = 6/10 (60%).
- Different-but-explainable cases are mid-ranked suppliers where the pool's
  non-compensatory weak-criteria rule intentionally diverges from aggregate
  fuzzy TOPSIS ranking.

The green benchmark therefore supports the directional logic of the M2 pool:
strong suppliers cluster in Preferred/Core, while structurally weak suppliers
fall into Restricted.

---

## Mini Traditional Benchmark

**File:** `M2_External_Benchmark_Traditional.py`

This benchmark uses a 5-supplier, 7-criterion traditional MCDM case with TOPSIS
and VIKOR results. It is retained as a lightweight sanity check, not as the main
M2 validation case because it does not contain ESG criteria.

The script writes its detailed note to:

```text
docs/M2_External_Benchmark_Traditional_Note.md
```

This separation prevents the traditional benchmark from overwriting the main
green benchmark note.

---

## Boundary

- This benchmark layer does not modify `Model2.py`.
- It does not modify core M2 output CSVs.
- It does not affect M3 or M4 logic.
- It is not an industry ground-truth validation.
- It validates directional classification against published case data.
- It does not validate exact enterprise premium tolerance.

## Files

| File | Description |
|------|-------------|
| `M2_External_Benchmark_Green.py` | Main green benchmark script |
| `M2_External_Benchmark_Green_Result.csv` | Green benchmark result |
| `M2_External_Benchmark_Traditional.py` | Traditional mini benchmark script |
| `M2_External_Benchmark_Traditional_Result.csv` | Traditional benchmark result |
| `docs/M2_External_Benchmark_Traditional_Note.md` | Traditional benchmark detail note |
