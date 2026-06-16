# M1: Supplier Qualification Gate

## 1. M1 Purpose

M1 is a **Supplier Qualification Gate** with a single responsibility: answer whether a supplier enters the normal sourcing candidate pool.

```
PASS    → 正常采购候选池 (ACTIVE_POOL)
LIMITED → 受限使用 (CONDITIONAL_POOL: cap + penalty)
FAIL    → 备胎/参考池 (RESERVE_POOL: retained, not activated)
```

**M1 does NOT:**
- Score or rank suppliers (that is M2)
- Make allocation decisions (that is M3/MILP)
- Activate reserve suppliers (that is a downstream sourcing review decision)
- Replace real enterprise due diligence

M1 is the **first filter** in a multi-stage decision system. Suppliers that pass M1 enter the scoring and shortlisting pipeline (M2). Suppliers that fail are excluded from normal sourcing but retained in a reserve/reference pool for scenario analysis.

---

## 2. Input Data

| Item | Detail |
|---|---|
| Source file | `suppliers_data.csv` (synthetic dataset) |
| Supplier count | 50 |
| Categories | 4 (Key_Component, Critical_Raw, General_Comp, General_Raw) |

### Data Disclaimer

**`suppliers_data.csv` is a synthetic dataset.** All supplier names, personnel, countries, cities, contract values, and risk indicators are fabricated. It is designed for:
- Reproducibility (fixed seed 42 + archetype-based generation)
- Coverage of diverse risk scenarios (normal suppliers + landmine cases)
- Testing M1 six-gate logic

**Archetype design** ensures each supplier has a coherent profile (e.g. tier-1 leader, emerging supplier, problem supplier). **Landmine suppliers** (S01, S12, S18, S19, S26, S50) are intentionally seeded with extreme values to verify gate detection.

In real enterprise use, this data would be replaced by actual supplier master data, procurement records, audit results, and third-party risk assessments.

---

## 3. Six Qualification Gates

All six gates are computed in full (no short-circuit), then the decision hierarchy determines the final status.

### Gate Descriptions

| Gate | Field(s) | What It Checks |
|---|---|---|
| **Finance** | `status`, `altman_z_score` | Active status + Altman Z score |
| **Quality** | `category`, `yield_rate`, `cert_type`, `cert_expiry_year` | Yield rate + certification type & expiry |
| **Tech** | `rating`, `cert_type`, `export_control_restricted`, `category` | Technical rating + export control + IATF bypass |
| **Ethics** | `country` (CPI map), `cmrt_audit` | Country CPI proxy + CMRT audit bonus |
| **Compliance** | `category`, `cmrt_audit` | CMRT audit required for critical categories |
| **Labor** | `forced_labor_risk`, `cert_type`, `rba_audit_pass` | Forced labor check + IATF/RBA certification |

### Proxy Warnings

- **Export control** (Tech gate): Currently placed under Tech as an MVP proxy. In real enterprise use, export control review is typically handled by Compliance/Legal, not R&D assessment. M1 retains it as a qualification warning/constraint for now.
- **Country CPI** (Ethics gate): CPI score is a country-level corruption perception proxy, not a firm-level audit conclusion. Real enterprise replacement: supplier audit results, sanctions screening, third-party due diligence reports.
- **CMRT audit bonus** (Ethics gate): Simplified evidence signal. Real enterprise replacement: actual CMRT reports, compliance evidence chain.
- **Capacity / Demand coverage**: Uses `annual_contract_value * DEMAND_RATIO` as a **scenario proxy**, not a real demand forecast. Real enterprise use should replace with procurement plan / demand forecast / MRP / ERP data.

---

## 4. Decision Hierarchy

### Priority Levels

```
P0 — Hard Exclusion (immediate FAIL, no remediation path)
P1 — Limited Use (FAIL or LIMITED depending on severity)
P2 — Limited Ethics (FAIL or LIMITED depending on gate combination)
```

### Gate → Priority Mapping

| Priority | Gate | Failure Condition | Status | Pool |
|---|---|---|---|---|
| P0 | **Labor** | Gate=0 | FAIL | RESERVE_BLACKLIST |
| P0 | **Compliance** | Gate=0 | FAIL | RESERVE_BLACKLIST |
| P0 | **Finance** | Gate=0 | FAIL | RESERVE_FINANCE |
| P1 | **Quality** | Gate=0 | LIMITED/FAIL | CONDITIONAL/RESERVE |
| P1 | **Tech** | Gate=0 | LIMITED/FAIL | CONDITIONAL/RESERVE |
| P2 | **Ethics** | Gate=0 | LIMITED/FAIL | CONDITIONAL/RESERVE |

### Labor Failure: Important Distinction

Labor gate failures fall into two distinct business scenarios, **both output as FAIL** but with different real-world implications:

| Scenario | Flag | Meaning | Real-world action |
|---|---|---|---|
| **Confirmed forced labor** | `forced_labor_risk=True` | Hard exclusion / blacklist | Permanent exclusion, no remediation path |
| **Missing labor assurance** | `forced_labor_risk=False`, no IATF/RBA | No evidence of labor compliance | Excluded from normal sourcing **until remediation evidence is provided** |

Both resolve to the same M1 status (`FAIL`), but the downstream review path differs. Enterprise implementation should distinguish between these audit tracks.

---

## 5. Status Definitions

### PASS
- Supplier passes all six gates
- Enters **ACTIVE_POOL** (normal sourcing pool)
- No usage restrictions, no penalty
- Eligible for M2 scoring and shortlisting

### LIMITED
- Supplier fails one or more non-P0 gates, or severity does not warrant full exclusion
- Enters **CONDITIONAL_POOL** with:
  - **Capacity Cap**: Maximum allocation fraction
  - **Penalty Multiplier**: Cost penalty applied to adjusted spend
- Can be used in sourcing but with controlled exposure

### FAIL
- Supplier triggers a P0 hard exclusion (Labor/Compliance/Finance) or multi-gate failure
- Enters **RESERVE_POOL**:
  - Retained in data (not deleted)
  - Not activated by M1 (activation is a downstream sourcing team decision)
  - Available for future scenario analysis / what-if simulations
- RESERVE_BLACKLIST suppliers (Labor/Compliance) are never eligible for activation

---

## 6. What M1 Does Not Do

- **No scoring**: M1 does not assign scores to suppliers. Scoring is M2's responsibility.
- **No ranking**: M1 does not rank suppliers within or across categories.
- **No allocation**: M1 does not decide how much to order from any supplier.
- **No reserve activation**: RESERVE_POOL suppliers are retained but not activated. Activation requires a downstream sourcing review (or M3 in future architecture).
- **No MILP optimization**: Linear programming / cost optimization is outside M1 scope.
- **No demand forecasting**: The DEMAND_RATIO coverage estimate is a scenario proxy, not a demand signal.

---

## 7. Real-Company Replacement Path

The table below documents which proxy/estimate fields in M1 should be replaced in a real enterprise deployment:

| Current Proxy | Replace With |
|---|---|
| `annual_contract_value * DEMAND_RATIO` | Demand forecast, procurement plan, MRP/ERP data |
| `country_cpi_score` (Ethics) | Supplier audit results, sanctions screening, third-party due diligence |
| `cmrt_audit_bonus` (Ethics) | Actual CMRT reports, compliance evidence documentation |
| `forced_labor_risk` flag (Labor) | RBA audits, SA8000 certification, onsite investigation reports |
| `iatf_certified` / `rba_audit_available` | Verified certification records, audit evidence chain |
| `export_control_restricted` under Tech gate | Compliance/Legal export control review, license status |
| `capacity` proxy via contract value | Supplier committed capacity, production scheduling data |

---

## 8. Output Files

| File | Description | Encoding |
|---|---|---|
| `supplier_reserve_pool.csv` | FAIL suppliers with risk details | UTF-8-SIG |
| (M1 status incorporated into dataframe passed to M2) | | |

M1 status fields (`M1_Status`, `M1_Pool`, `M1_Risk_Type`, `M1_Action`, `M1_Penalty`, `M1_Capacity_Cap`, `M1_Risk_Vector`, etc.) are attached to each supplier record and consumed by M2.

---

*Document generated for portfolio / GitHub showcase. All data is synthetic.*
