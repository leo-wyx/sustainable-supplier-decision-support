# M2 Pool Stability and Validation Note

## 1. Purpose

This note validates the robustness of the M2 Strategic Pool classification through
two lenses:

1. **Pool stability / agility-readiness** (primary): Whether the Preferred / Core
   recommended set is stable under reasonable cost, carbon, ESG, and risk-control
   scenario variations. This is the main validation criterion for the current M2.
2. **Future external paper-data benchmarks** (roadmap): Plan to validate pool
   assignment against published supplier-selection datasets from academic literature.

The previous Cost-ESG shortlist is not used as a validation benchmark for the
current M2. It is kept only as an optional historical transition reference
(Section 4) to explain changes between model iterations.

## 2. Pool Stability Findings

| Stability Label | Count | Percentage |
|-----------------|-------|------------|
| Stable | 30 | 81.1% |
| Moderate | 4 | 10.8% |
| Sensitive | 3 | 8.1% |

### Scenario pool composition

| Scenario | Preferred | Core | Conditional | Restricted | Not Priority |
|----------|-----------|------|-------------|------------|--------------|
| Base | 4 | 14 | 8 | 11 | 0 |
| Cost pressure | 4 | 14 | 8 | 11 | 0 |
| Carbon pressure | 3 | 7 | 13 | 14 | 0 |
| Risk control | 4 | 7 | 15 | 11 | 0 |
| Strict ESG | 4 | 14 | 8 | 11 | 0 |

### Non-recommended / scenario-vulnerable suppliers (3)

These suppliers are already below Preferred/Core in the base scenario or fail to reach the Preferred/Core threshold in most scenarios. They are non-recommended or scenario-vulnerable and may require closer monitoring:

- S23 (Supplier_S23)  -- base: Conditional, Preferred/Core in 0/5 scenarios
- S24 (Supplier_S24)  -- base: Conditional, Preferred/Core in 0/5 scenarios
- S38 (Supplier_S38)  -- base: Conditional, Preferred/Core in 0/5 scenarios


## 3. External Paper-Data Benchmark Plan

The current M2 Strategic Pool framework should next be validated against
external published supplier-selection datasets to confirm classification
robustness beyond internal consistency checks.

### Proposed validation datasets

**a) Traditional supplier selection case**
A multi-criteria supplier evaluation dataset from the manufacturing or
automotive sector (e.g., a published AHP/TOPSIS case study with known
supplier rankings). The M2 three-lens classification (cost quartile,
ESG tier, diagnostic flags) would be applied independently, and the
resulting Preferred / Core set would be compared against the top-ranked
suppliers in the original study.

Expected outcome: Pool assignment should agree with the top-2 tiers of
the reference method in at least 70% of cases, confirming that the
simplified lens-based approach captures the same underlying trade-offs
as a full multi-criteria decision model.

**b) Resilient / agility supplier selection case**
A dataset or case study that incorporates supply chain resilience
criteria (disruption risk, geographic concentration, substitutability)
alongside cost and quality. This would test whether the diagnostic
flag system (risk_level, delivery_risk, T_capability_flag, Q_quality_warning)
can adequately proxy for resilience considerations in pool assignment.

Expected outcome: The risk-control scenario in the pool stability
analysis serves as an internal proxy; external validation would confirm
that the Restricted / Conditional boundary aligns with resilience-aware
sourcing decisions documented in the literature.

### Implementation notes

- Both validations are standalone analyses that read M2 output CSVs
  and compare against external reference classifications.
- They do not require changes to Model2.py or the core M2 pipeline.
- Dataset selection should prioritise open-access publications with
  full supplier-by-criteria matrices so that M2 lenses can be mapped
  onto the original decision criteria.

## 4. Historical Transition Check (Optional)

**Note:** The previous Cost-ESG shortlist is not used as a validation
benchmark for the current M2. It is kept only as an optional historical
transition reference to explain model evolution between iterations.

This section documents how the new Strategic Pool compares with the
prior shortlist-based methodology. The comparison is provided for
transparency -- it measures consistency between model iterations, not
accuracy against an external standard.

| Metric | Value |
|--------|-------|
| Old recommended count (Preferred shortlist / Shortlist with warning) | 13 |
| New recommended count (Preferred / Core) | 18 |
| Overlap count | 9 |
| Overlap rate (based on old recommended set) | 69.2% |
| Overlap rate (based on new recommended set) | 50.0% |

### Suppliers only in old recommended (4)
- S09 (Supplier_S09)  -- Shortlist with warning
- S25 (Supplier_S25)  -- Shortlist with warning
- S45 (Supplier_S45)  -- Shortlist with warning
- S46 (Supplier_S46)  -- Shortlist with warning

### Suppliers only in new recommended (9)
- S03 (Supplier_S03)  -- Preferred
- S07 (Supplier_S07)  -- Preferred
- S08 (Supplier_S08)  -- Preferred
- S27 (Supplier_S27)  -- Core
- S29 (Supplier_S29)  -- Core
- S30 (Supplier_S30)  -- Core
- S36 (Supplier_S36)  -- Core
- S39 (Supplier_S39)  -- Core
- S44 (Supplier_S44)  -- Core

### Movement explanation

Suppliers moved between old shortlist and new Strategic Pool for the following reasons:

- **Stable recommended**: 9 suppliers
- **Stable non-recommended**: 10 suppliers
- **Upgraded**: 9 suppliers
- **Downgraded**: 4 suppliers
- **Restricted by M1**: 5 suppliers

#### Upgraded suppliers (9)

These suppliers were not in the old recommended set but qualify as Preferred or Core under the new Strategic Pool:

- S27 (Supplier_S27)  -- old: Conditional shortlist -> new: Core. Reason: cost_quartile=Q2; no high diagnostic flags
- S29 (Supplier_S29)  -- old: Not shortlisted -> new: Core. Reason: Strategic Pool criteria match
- S30 (Supplier_S30)  -- old: Not shortlisted -> new: Core. Reason: cost_quartile=Q1_Best; no high diagnostic flags
- S36 (Supplier_S36)  -- old: Not shortlisted -> new: Core. Reason: cost_quartile=Q2
- S39 (Supplier_S39)  -- old: Not shortlisted -> new: Core. Reason: Strategic Pool criteria match
- S44 (Supplier_S44)  -- old: Not shortlisted -> new: Core. Reason: cost_quartile=Q1_Best; no high diagnostic flags
- S03 (Supplier_S03)  -- old: Not shortlisted -> new: Preferred. Reason: cost_quartile=Q2; ESG tier=ESG Compliant; no high diagnostic flags
- S07 (Supplier_S07)  -- old: Not shortlisted -> new: Preferred. Reason: cost_quartile=Q2; ESG tier=ESG Compliant; no high diagnostic flags
- S08 (Supplier_S08)  -- old: Not shortlisted -> new: Preferred. Reason: cost_quartile=Q1_Best; ESG tier=ESG Leader; no high diagnostic flags

#### Downgraded suppliers (4)

These suppliers were in the old recommended set but fall to Conditional or below under the new Strategic Pool:

- S25 (Supplier_S25)  -- old: Shortlist with warning -> new: Conditional. Reason: cost_quartile=Q4_Worst
- S45 (Supplier_S45)  -- old: Shortlist with warning -> new: Restricted. Reason: ESG tier=ESG Monitor; risk_level=High; capability gap; 2 high diagnostic flags
- S46 (Supplier_S46)  -- old: Shortlist with warning -> new: Restricted. Reason: risk_level=High; capability gap; 2 high diagnostic flags
- S09 (Supplier_S09)  -- old: Shortlist with warning -> new: Conditional. Reason: cost_quartile=Q4_Worst

#### Key movement drivers

- **Adjusted cost outlier**: Suppliers with Q4_Worst cost quartile (e.g., S25, S24) are
  downgraded to Conditional regardless of ESG strength, reflecting cost pressure.
- **ESG tier separation**: ESG Monitor suppliers cannot reach Preferred, which affects
  suppliers with strong cost but moderate ESG credentials (e.g., S14, S13, S15 -> Core not Preferred).
- **Diagnostic escalation**: Suppliers with 2+ high diagnostic flags (risk, delivery,
  capability, quality) are Restricted, downgrading them from old shortlist status.
- **M1 restriction**: Any non-PASS M1 status (LIMITED_QUALITY_TECH, LIMITED_ETHICS)
  results in Restricted pool regardless of score-based performance.

## 5. Boundary

- **This is not M3 allocation.** Pool classification determines sourcing eligibility
  and priority, not allocation volume. M3 lightweight allocation can use Strategic
  Pool as one input alongside demand, capacity, and policy constraints.
- **This is not M4 external stress testing.** M4 models resilience under
  geopolitical disruption, supply shortage, and logistics failure scenarios.
  Pool stability tests internal model sensitivity, not external shock resilience.
- **This is an M2 robustness / agility-readiness validation.** It confirms that
  the Strategic Pool can withstand reasonable input variations without
  fundamentally changing sourcing recommendations.
- **Scenario Premium Layer remains disabled** until real-company replacement
  data is available. Current company-agnostic data does not support meaningful
  premium/penalty calibration.

---

*Generated by M2_Benchmark_Stability_Analysis.py on 2026-06-16 00:02*
