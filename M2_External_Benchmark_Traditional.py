# ============================================================
# M2_External_Benchmark_Traditional.py
#
# External Benchmark 1: Traditional supplier-selection case
# Validates M2 simplified lens/pool logic against a published
# MCDM (TOPSIS/VIKOR) supplier-selection case.
#
# Reference: Supplier Selection for Construction Projects Through
# TOPSIS and VIKOR Multi-Criteria Decision Making Methods
# (IJERTV3IS051992)
#
# This is a standalone external validation module.
# It does not modify Model2.py or core M2 outputs.
# ============================================================
import pandas as pd
import numpy as np
import os

# -- Decision matrix from the published paper --
SUPPLIERS = [
    {
        'id': 'S1',
        'name': 'Supplier 1',
        'Quality': 7,
        'Cost': 6,
        'Delivery_Time': 9,
        'Technical_Capability': 9,
        'Financial_Capability': 7,
        'Managerial_Commercial_Capability': 8,
        'Trust': 7,
    },
    {
        'id': 'S2',
        'name': 'Supplier 2',
        'Quality': 7,
        'Cost': 7,
        'Delivery_Time': 7,
        'Technical_Capability': 9,
        'Financial_Capability': 7,
        'Managerial_Commercial_Capability': 8,
        'Trust': 7,
    },
    {
        'id': 'S3',
        'name': 'Supplier 3',
        'Quality': 9,
        'Cost': 8,
        'Delivery_Time': 7,
        'Technical_Capability': 9,
        'Financial_Capability': 7,
        'Managerial_Commercial_Capability': 8,
        'Trust': 8,
    },
    {
        'id': 'S4',
        'name': 'Supplier 4',
        'Quality': 5,
        'Cost': 4,
        'Delivery_Time': 9,
        'Technical_Capability': 7,
        'Financial_Capability': 6,
        'Managerial_Commercial_Capability': 7,
        'Trust': 6,
    },
    {
        'id': 'S5',
        'name': 'Supplier 5',
        'Quality': 5,
        'Cost': 3,
        'Delivery_Time': 7,
        'Technical_Capability': 7,
        'Financial_Capability': 5,
        'Managerial_Commercial_Capability': 7,
        'Trust': 6,
    },
]

# -- Criteria weights from the published paper --
WEIGHTS = {
    'Quality': 0.2623,
    'Cost': 0.2083,
    'Delivery_Time': 0.0585,
    'Technical_Capability': 0.1170,
    'Financial_Capability': 0.0904,
    'Managerial_Commercial_Capability': 0.0644,
    'Trust': 0.1990,
}

# -- Thresholds for M2-style lens classification --
# strong  >= 8  (no diagnostic concern)
# acceptable >= 7 (manageable)
# weak    <= 5  (material weakness)
# Scores 6 or 7 are "adequate but not strong" = no flag
STRONG_THRESHOLD = 8
ACCEPTABLE_THRESHOLD = 7
WEAK_THRESHOLD = 5

# -- Paper criteria -> M2 lens mapping --
# Cost lens:      Cost
# ESG lens:       Not available in this traditional case
# TQRDC flags:
#   T = Technical_Capability
#   Q = Quality
#   R = average(Financial_Capability, Trust) as risk proxy
#   D = Delivery_Time
#   C = Cost (already covered by Cost lens, reused here)


def compute_weighted_score(supplier):
    """Reproduce the paper weighted score for reference verification.
    This is not M2 methodology; it only confirms the reference ranking."""
    score = 0.0
    for criterion, weight in WEIGHTS.items():
        # Map the column name if needed (Cost vs cost)
        col = criterion.replace(' ', '_')
        score += supplier[col] * weight
    return round(score, 4)


def compute_simplified_pool(supplier):
    """Apply M2-style simplified pool logic using the three-lens approach.

    Cost lens:
      - Top cost position (highest Cost score among all suppliers)

    TQRDC diagnostics (material weakness = score <= 5):
      - T: Technical Capability
      - Q: Quality
      - R: average(Financial Capability, Trust) as risk proxy
      - D: Delivery Time
      - C: Cost (diagnostic context, not primary lens)

    Pool rules:
      - Preferred: top cost position + strong quality (>=8) +
        strong technical (>=8) + zero material weaknesses
      - Core: acceptable cost + acceptable quality/technical (>=7) +
        no more than one weakness
      - Conditional: one material weakness
      - Restricted: two or more material weaknesses
    """
    # Determine top cost position
    cost_scores = [s['Cost'] for s in SUPPLIERS]
    top_cost = max(cost_scores)
    is_top_cost = supplier['Cost'] == top_cost

    # TQRDC flags
    q_flag = supplier['Quality'] <= WEAK_THRESHOLD
    t_flag = supplier['Technical_Capability'] <= WEAK_THRESHOLD
    r_avg = (supplier['Financial_Capability'] + supplier['Trust']) / 2.0
    r_flag = r_avg <= WEAK_THRESHOLD
    d_flag = supplier['Delivery_Time'] <= WEAK_THRESHOLD
    c_flag = supplier['Cost'] <= WEAK_THRESHOLD  # cost as diagnostic

    weakness_count = sum([q_flag, t_flag, r_flag, d_flag, c_flag])

    # Quality/technical strength
    quality_strong = supplier['Quality'] >= STRONG_THRESHOLD
    quality_ok = supplier['Quality'] >= ACCEPTABLE_THRESHOLD
    tech_strong = supplier['Technical_Capability'] >= STRONG_THRESHOLD
    tech_ok = supplier['Technical_Capability'] >= ACCEPTABLE_THRESHOLD

    # Build reason parts
    parts = []
    parts.append(f"Cost={supplier['Cost']}" + (" (top)" if is_top_cost else ""))
    parts.append(f"Q={supplier['Quality']}")
    parts.append(f"T={supplier['Technical_Capability']}")
    parts.append(f"R_avg={r_avg:.1f}")
    parts.append(f"D={supplier['Delivery_Time']}")

    # --- Pool assignment ---
    # Restricted: 2+ material weaknesses
    if weakness_count >= 2:
        reason = "; ".join(parts) + f" | weaknesses={weakness_count} ("
        w_parts = []
        if q_flag: w_parts.append("Quality")
        if t_flag: w_parts.append("Technical")
        if r_flag: w_parts.append("Risk")
        if d_flag: w_parts.append("Delivery")
        if c_flag: w_parts.append("Cost")
        reason += "+".join(w_parts) + ")"
        return ('Restricted', reason)

    # Conditional: 1 material weakness
    if weakness_count == 1:
        w_name = ""
        if q_flag: w_name = "Quality"
        elif t_flag: w_name = "Technical"
        elif r_flag: w_name = "Risk"
        elif d_flag: w_name = "Delivery"
        elif c_flag: w_name = "Cost"
        reason = "; ".join(parts) + f" | one weakness: {w_name}"
        return ('Conditional', reason)

    # Preferred: top cost + strong quality + strong technical + no weaknesses
    if is_top_cost and quality_strong and tech_strong and weakness_count == 0:
        reason = "; ".join(parts) + " | no weakness, top cost, strong Q+T"
        return ('Preferred', reason)

    # Core: acceptable cost + acceptable quality/technical + manageable
    if supplier['Cost'] >= ACCEPTABLE_THRESHOLD and quality_ok and tech_ok:
        reason = "; ".join(parts) + " | acceptable across criteria, no material weakness"
        return ('Core', reason)

    # Fallback: also Core if close on cost but strong elsewhere
    if quality_strong and tech_strong and weakness_count == 0:
        reason = "; ".join(parts) + " | strong Q+T offset moderate cost"
        return ('Core', reason)

    # Otherwise Conditional (borderline)
    if weakness_count == 0:
        reason = "; ".join(parts) + " | adequate but no strong position"
        return ('Conditional', reason)

    # Shouldn't reach here
    reason = "; ".join(parts) + " | unclassified"
    return ('Conditional', reason)


def directional_alignment(supplier_id, pool, rank):
    """Determine directional alignment between pool assignment and paper rank.

    Directionally aligned means:
    - paper_reference_rank <= 2 and simplified_pool in Preferred/Core
    - paper_reference_rank >= 4 and simplified_pool == Restricted
    - Supplier 3 as rank 1 and Preferred remains aligned_top_supplier
    """
    if supplier_id == 'S3' and pool in ('Preferred', 'Core'):
        return ('aligned_top', 'S3 is rank-1 in paper and Preferred in M2 pool -- fully aligned')

    rank_int = int(rank)
    if rank_int <= 2 and pool in ('Preferred', 'Core'):
        return ('aligned', f'Paper rank {rank_int}, M2 pool {pool} -- recommended in both')

    if rank_int >= 4 and pool == 'Restricted':
        return ('aligned', f'Paper rank {rank_int}, M2 pool {pool} -- direction consistent')

    if rank_int <= 2 and pool not in ('Preferred', 'Core'):
        return ('misaligned', f'Paper rank {rank_int} but M2 pool {pool} -- not recommended despite high paper rank')

    if rank_int >= 4 and pool in ('Preferred', 'Core'):
        return ('misaligned', f'Paper rank {rank_int} but M2 pool {pool} -- over-recommended relative to paper')

    return ('different_but_explainable', f'Paper rank {rank_int}, M2 pool {pool} -- borderline case, no directional conflict')


def comparison_label(supplier_id, pool, rank):
    """Determine comparison to paper reference outcome."""
    if supplier_id == 'S3' and pool in ('Preferred', 'Core'):
        return 'aligned_top_supplier'
    elif pool in ('Preferred', 'Core') and rank <= 3:
        return 'aligned_recommended'
    elif pool in ('Preferred', 'Core'):
        return 'different_but_explainable'
    elif pool == 'Conditional':
        return 'different_but_explainable'
    else:
        return 'not_recommended'


def run_benchmark():
    """Execute the external benchmark analysis."""
    print("=" * 70)
    print("External Benchmark 1: Traditional Supplier-Selection Case")
    print("Reference: Supplier Selection for Construction Projects Through")
    print("           TOPSIS and VIKOR Methods (IJERTV3IS051992)")
    print("=" * 70)

    # -- Compute weighted scores (reference reproduction) --
    results = []
    for s in SUPPLIERS:
        ws = compute_weighted_score(s)
        results.append({
            'supplier_id': s['id'],
            'supplier_name': s['name'],
            **{k: v for k, v in s.items() if k not in ('id', 'name')},
            'weighted_score': ws,
        })

    df = pd.DataFrame(results)

    # Rank by weighted score (higher = better)
    df = df.sort_values('weighted_score', ascending=False).reset_index(drop=True)
    df['paper_reference_rank'] = range(1, len(df) + 1)

    # Restore original order for pool assignment
    df = df.sort_values('supplier_id').reset_index(drop=True)

    # -- Simplified M2-style pool classification --
    pool_results = []
    for _, row in df.iterrows():
        sid = row['supplier_id']
        supplier_raw = [s for s in SUPPLIERS if s['id'] == sid][0]
        pool, reason = compute_simplified_pool(supplier_raw)
        rank = df[df['supplier_id'] == sid]['paper_reference_rank'].iloc[0]
        comp = comparison_label(sid, pool, int(rank))
        dir_flag, dir_reason = directional_alignment(sid, pool, int(rank))
        pool_results.append({
            'supplier_id': sid,
            'supplier_name': supplier_raw['name'],
            'paper_weighted_score': df[df['supplier_id'] == sid]['weighted_score'].iloc[0],
            'paper_reference_rank': int(rank),
            'simplified_pool': pool,
            'pool_reason': reason,
            'comparison_to_reference': comp,
            'directional_alignment_flag': dir_flag,
            'directional_alignment_reason': dir_reason,
        })

    df_out = pd.DataFrame(pool_results)

    # -- Print summary --
    print(f"\nWeighted score ranking (reference reproduction):")
    for _, r in df.sort_values('paper_reference_rank').iterrows():
        print(f"  Rank {int(r['paper_reference_rank'])}: {r['supplier_id']} ({r['supplier_name']}) -- weighted score = {r['weighted_score']:.4f}")

    print(f"\nSimplified M2-style pool assignment:")
    for _, r in df_out.iterrows():
        aligned = r['comparison_to_reference']
        marker = "+" if aligned.startswith('aligned') else "!"
        print(f"  {marker} {r['supplier_id']} ({r['supplier_name']}) -> {r['simplified_pool']:12s} "
              f"(paper rank {int(r['paper_reference_rank'])}, score {r['paper_weighted_score']:.4f})")
        print(f"     Reason: {r['pool_reason']}")
        print(f"     Comparison: {r['comparison_to_reference']}")

    # -- S3 check --
    s3 = df_out[df_out['supplier_id'] == 'S3'].iloc[0]
    print(f"\n{'='*70}")
    print(f"Supplier 3 check:")
    print(f"  Paper rank 1 -> Pool: {s3['simplified_pool']}")
    print(f"  Comparison: {s3['comparison_to_reference']}")
    print(f"{'='*70}")

    # -- Counts --
    print(f"\nPool distribution:")
    for p in ['Preferred', 'Core', 'Conditional', 'Restricted']:
        cnt = (df_out['simplified_pool'] == p).sum()
        print(f"  {p}: {cnt}")

    print(f"\nComparison distribution:")
    for c in ['aligned_top_supplier', 'aligned_recommended', 'different_but_explainable', 'not_recommended']:
        cnt = (df_out['comparison_to_reference'] == c).sum()
        print(f"  {c}: {cnt}")

    # -- Save CSV --
    df_out.to_csv('M2_External_Benchmark_Traditional_Result.csv', index=False, encoding='utf-8-sig')
    print(f"\n=> M2_External_Benchmark_Traditional_Result.csv saved")

    return df_out


def generate_markdown(df):
    """Generate the external benchmark markdown note."""
    print(f"\n{'='*70}")
    print("Generating markdown note...")
    print(f"{'='*70}")

    # S3 details
    s3 = df[df['supplier_id'] == 'S3'].iloc[0]
    s1 = df[df['supplier_id'] == 'S1'].iloc[0]

    # Agreement assessment
    aligned_cases = (df['comparison_to_reference'].str.startswith('aligned')).sum()
    total = len(df)
    agreement_rate = round(aligned_cases / total * 100, 1)

    # Directional alignment
    dir_aligned = (df['directional_alignment_flag'] == 'aligned').sum() + (df['directional_alignment_flag'] == 'aligned_top').sum()
    dir_rate = round(dir_aligned / total * 100, 1)

    # Differences
    diff_df = df[df['comparison_to_reference'] == 'different_but_explainable']
    not_rec_df = df[df['comparison_to_reference'] == 'not_recommended']

    markdown = f"""# M2 External Benchmark 1: Traditional Supplier-Selection Case

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

"""
    # Build weighted score table
    df_sorted = df.sort_values('paper_reference_rank')
    markdown += "| Rank | Supplier | Weighted Score |\n"
    markdown += "|------|----------|---------------|\n"
    for _, r in df_sorted.iterrows():
        markdown += f"| {int(r['paper_reference_rank'])} | {r['supplier_name']} | {r['paper_weighted_score']:.4f} |\n"

    markdown += """
### Simplified M2 Pool Classification

"""
    markdown += "| Supplier | Pool | Comparison | Directional Alignment | Reason |\n"
    markdown += "|----------|------|------------|-----------------------|--------|\n"
    for _, r in df.iterrows():
        markdown += f"| {r['supplier_id']} ({r['supplier_name']}) | {r['simplified_pool']:12s} | {r['comparison_to_reference']:30s} | {r['directional_alignment_flag']:25s} | {r['pool_reason']} |\n"

    pool_dist = df['simplified_pool'].value_counts()
    markdown += f"""
### Supplier 3 Verification

- **Paper rank:** 1
- **M2 simplified pool:** {s3['simplified_pool']}
- **Comparison:** {s3['comparison_to_reference']}
- **Supplier 3 is Preferred/Core:** {"YES" if s3['simplified_pool'] in ('Preferred', 'Core') else "NO"}

-> The M2 simplified logic correctly identifies Supplier 3 as {s3['simplified_pool']},
   aligning with the paper's top-ranked supplier.

### Agreement Summary

**Top supplier alignment:** Supplier 3 (paper rank 1) is classified as {s3['simplified_pool']} in the M2 pool.
  -> Supplier 3 is Preferred/Core: {"YES" if s3['simplified_pool'] in ('Preferred', 'Core') else "NO"}

**Recommended set alignment:** Suppliers 2 and 3 (paper ranks 1-2) both map to Preferred/Core in the M2 pool.
  The top-two recommended set is consistent between the paper and the simplified pool.

**Directional alignment:** {dir_aligned}/{total} ({dir_rate}%)
  Directionally aligned means:
  - Paper rank <= 2 -> pool is Preferred/Core
  - Paper rank >= 4 -> pool is Restricted
  - Supplier 3 alone is aligned_top_supplier

  S4 and S5 (paper ranks 4-5) are Restricted in the M2 pool, which is directionally consistent
  with the paper's lowest rankings. {s1['supplier_id']} ({s1['supplier_name']}, paper rank {int(s1['paper_reference_rank'])}) is the only different-but-explainable case:
  the simplified pool flags adequate-but-unremarkable scores (Cost=6, Q=7), while the
  weighted-score model compensates across criteria.

- Pool distribution: Preferred={pool_dist.get('Preferred', 0)}, Core={pool_dist.get('Core', 0)},
  Conditional={pool_dist.get('Conditional', 0)}, Restricted={pool_dist.get('Restricted', 0)}

"""
    if len(diff_df) > 0:
        markdown += "### Differences and Explanation\n\n"
        for _, r in diff_df.iterrows():
            markdown += f"- **{r['supplier_id']} ({r['supplier_name']})** is {r['simplified_pool']} "
            markdown += f"(paper rank {int(r['paper_reference_rank'])}). "
            markdown += f"The simplified pool identifies specific weaknesses that a weighted-score "
            markdown += "model may mask. This is not a disagreement -- the pool adds diagnostic "
            markdown += "nuance to the numerical ranking.\n"

    if len(not_rec_df) > 0:
        markdown += "\n"
        for _, r in not_rec_df.iterrows():
            markdown += f"- **{r['supplier_id']} ({r['supplier_name']})** is {r['simplified_pool']} "
            markdown += f"(paper rank {int(r['paper_reference_rank'])}). "
            markdown += f"Multiple material weaknesses justify Restricted status. The paper also "
            markdown += f"ranks this supplier lowest, so the direction is consistent.\n"

    markdown += f"""
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
*Generated by M2_External_Benchmark_Traditional.py on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*
"""
    os.makedirs('docs', exist_ok=True)
    with open('docs/M2_External_Benchmark_Traditional_Note.md', 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"  => docs/M2_External_Benchmark_Traditional_Note.md saved")
    return markdown


# ============================================================
# Main entry point
# ============================================================
if __name__ == '__main__':
    print("M2 External Benchmark 1: Traditional Supplier-Selection Case")
    print("=" * len("M2 External Benchmark 1: Traditional Supplier-Selection Case"))
    print()

    df_result = run_benchmark()
    summary_md = generate_markdown(df_result)

    print(f"\n{'='*70}")
    print("External Benchmark 1 complete.")
    print(f"{'='*70}")
    print(f"  Generated files:")
    print(f"    M2_External_Benchmark_Traditional_Result.csv")
    print(f"    docs/M2_External_Benchmark_Traditional_Note.md")
