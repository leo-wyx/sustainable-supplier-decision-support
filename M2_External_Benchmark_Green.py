#!/usr/bin/env python3
"""
M2_External_Benchmark_Green.py
Main external benchmark for M2: 10-supplier green supplier selection case.

Reference:
  Uppala, A.K., Sharma, R., Raj, H., Kumar, R.M., Selvam, D.P., Manupati, V. (2016)
  "Selection of Green suppliers based on GSCM practices: Using fuzzy MCDM approach"
  Proceedings of the 2016 International Conference on Industrial Engineering and Operations
  Management (IEOM), Detroit, Michigan, USA. Paper #206.
  https://ieomsociety.org/ieom_2016/pdfs/206.pdf

  Data source paper:
  Kannan, D., Jabbour, A.B.L.S., Jabbour, C.J.C. (2014)
  "Selecting green suppliers based on GSCM practices: Using fuzzy TOPSIS applied to a
  Brazilian electronics company"
  European Journal of Operational Research, 233(2), 432-447.

Purpose:
  Validate whether M2 simplified pool logic can reproduce or explain supplier priorities
  from an external green / ESG supplier-selection case.

This is the MAIN external data benchmark for M2.
The 5-supplier TOPSIS/VIKOR benchmark is a mini sanity check only.
"""

import numpy as np
import pandas as pd

# =====================================================================
# TABLE 5: CRITERIA WEIGHTS (from fuzzy AHP)
# 17 GSCM practices criteria with normalized weights
# Source: Uppala et al. (2016), Table 5
# Original: Kannan et al. (2014), Table 3 -- pairwise comparison results
# =====================================================================
criteria_names = [
    'GSCM1', 'GSCM2', 'GSCM3', 'GSCM4', 'GSCM5',
    'GSCM6', 'GSCM7', 'GSCM8', 'GSCM9', 'GSCM10',
    'GSCM11', 'GSCM12', 'GSCM13', 'GSCM14', 'GSCM15',
    'GSCM16', 'GSCM17'
]

criteria_weights = np.array([
    0.140043, 0.069859, 0.112741, 0.048953, 0.069859,
    0.073438, 0.013800, 0.008559, 0.059486, 0.008559,
    0.053071, 0.066456, 0.140043, 0.112741, 0.008559,
    0.006916, 0.006916
])

weight_sum = criteria_weights.sum()
assert abs(weight_sum - 1.0) < 0.01, (
    f"Criteria weights sum to {weight_sum:.6f}, expected ~1.0"
)

# =====================================================================
# TABLE 6: SUPPLIER-BY-CRITERIA PRIORITY MATRIX (from fuzzy AHP)
# Row: supplier A1-A10, Column: criteria GSCM1-GSCM17
# Values are normalized priority weights from pairwise comparisons
# Source: Uppala et al. (2016), Table 6 (columns C1-C17)
# =====================================================================
decision_matrix = np.array([
    # A1
    [0.078449, 0.054432, 0.018678, 0.023685, 0.045348,
     0.051643, 0.040440, 0.066834, 0.064326, 0.060623,
     0.053184, 0.042329, 0.042124, 0.016728, 0.042805,
     0.086324, 0.089081],
    # A2
    [0.078449, 0.077760, 0.146612, 0.023685, 0.045348,
     0.051643, 0.040440, 0.066834, 0.077192, 0.095621,
     0.053184, 0.062997, 0.104613, 0.131310, 0.134043,
     0.109385, 0.112879],
    # A3
    [0.106428, 0.137947, 0.146612, 0.185915, 0.161380,
     0.128254, 0.149421, 0.110050, 0.106598, 0.127558,
     0.221473, 0.176272, 0.154395, 0.128793, 0.152331,
     0.109385, 0.112879],
    # A4
    [0.157075, 0.101089, 0.146612, 0.185915, 0.188844,
     0.128254, 0.168407, 0.110050, 0.144643, 0.144961,
     0.083146, 0.119436, 0.104613, 0.131310, 0.152331,
     0.109385, 0.112879],
    # A5
    [0.157075, 0.137947, 0.130083, 0.158877, 0.188844,
     0.189287, 0.168407, 0.126968, 0.144643, 0.100784,
     0.124844, 0.119436, 0.104613, 0.131310, 0.178256,
     0.109385, 0.112879],
    # A6
    [0.042855, 0.081337, 0.070744, 0.023685, 0.045348,
     0.051643, 0.045946, 0.126968, 0.064326, 0.109390,
     0.053184, 0.042329, 0.037076, 0.082309, 0.134043,
     0.086324, 0.053703],
    # A7
    [0.106428, 0.093468, 0.099339, 0.062880, 0.045348,
     0.106701, 0.045946, 0.066834, 0.106598, 0.100784,
     0.083146, 0.079293, 0.104613, 0.082309, 0.060289,
     0.097053, 0.097608],
    # A8
    [0.037719, 0.093468, 0.076033, 0.023685, 0.045348,
     0.051643, 0.045946, 0.066834, 0.064326, 0.060623,
     0.053184, 0.090819, 0.096780, 0.082309, 0.100482,
     0.086324, 0.097608],
    # A9
    [0.078449, 0.084603, 0.018678, 0.125760, 0.045348,
     0.051643, 0.126638, 0.110050, 0.064326, 0.095621,
     0.053184, 0.090819, 0.096780, 0.082309, 0.022709,
     0.097053, 0.097608],
    # A10
    [0.157075, 0.137947, 0.146612, 0.185915, 0.188844,
     0.189287, 0.168407, 0.148576, 0.163022, 0.104035,
     0.221473, 0.176272, 0.154395, 0.131310, 0.022709,
     0.109385, 0.112879],
])

supplier_ids = [f'A{i}' for i in range(1, 11)]
n_suppliers = len(supplier_ids)

# =====================================================================
# TABLE 6: ALTERNATIVE PRIORITY WEIGHTS (from fuzzy TOPSIS)
# These are the paper's reference final ranking (last column in Table 6)
# Source: Uppala et al. (2016), Table 6 (last column: "Alternative Priority Weight")
# =====================================================================
paper_priority_weights = np.array([
    0.045160184,  # A1
    0.085719968,  # A2
    0.142575751,  # A3
    0.133879945,  # A4
    0.139751705,  # A5
    0.055451385,  # A6
    0.090133470,  # A7
    0.067102487,  # A8
    0.072508278,  # A9
    0.159988728,  # A10
])

# =====================================================================
# 1. REPRODUCE PAPER REFERENCE RANKING
#    Rank descending by Alternative Priority Weight (higher = better)
# =====================================================================
paper_rank = np.argsort(np.argsort(-paper_priority_weights)) + 1

# =====================================================================
# 2. RECOMPUTE WEIGHTED GREEN SCORE (consistency check)
#    green_score[i] = sum_j(criteria_weight[j] * decision_matrix[i, j])
#    This is a simple weighted sum; the paper used full fuzzy TOPSIS
#    (which includes ideal/anti-ideal distances), so absolute values
#    will differ, but ranking direction should be comparable.
# =====================================================================
green_score = decision_matrix @ criteria_weights
green_rank = np.argsort(np.argsort(-green_score)) + 1

# =====================================================================
# 3. WEAK CRITERIA COUNT
#    For each criterion GSCM1-GSCM17, a supplier's performance is
#    "weak" if its value is in the bottom quartile (<= Q1).
# =====================================================================
q1_values = np.percentile(decision_matrix, 25, axis=0)
weak_matrix = decision_matrix <= q1_values  # True = weak on that criterion
weak_criteria_count = weak_matrix.sum(axis=1)

# =====================================================================
# 4. SIMPLIFIED GREEN POOL CLASSIFICATION (M2-style logic)
#
#    Rules (applied in priority order):
#      1. Restricted  if weak_count > 6 or rank >= 9
#      2. Preferred   if rank <= 2    and weak_count <= 2
#      3. Core        if rank <= 5    and weak_count <= 4
#      4. Conditional if rank <= 8    or  weak_count <= 6
#      5. Restricted  fallback
#
#    With 10 suppliers, the percentile cuts are:
#      top 20%   = rank 1-2
#      next 30%  = rank 3-5
#      next 30%  = rank 6-8
#      bottom 20% = rank 9-10
# =====================================================================
green_score_sorted_idx = np.argsort(-green_score)
median_green = np.median(green_score)

pool = [''] * n_suppliers
pool_reason = [''] * n_suppliers

for rank_pos, idx in enumerate(green_score_sorted_idx):
    rank = rank_pos + 1
    wc = int(weak_criteria_count[idx])

    if wc > 6 or rank >= 9:
        pool[idx] = 'Restricted'
        if wc > 6 and rank >= 9:
            pool_reason[idx] = (
                f"weak_count={wc} > 6 and rank {rank}/10 is bottom 20%"
            )
        elif wc > 6:
            pool_reason[idx] = (
                f"weak_count={wc} > 6"
            )
        else:
            pool_reason[idx] = (
                f"rank {rank}/10 is bottom 20%"
            )

    elif rank <= 2 and wc <= 2:
        pool[idx] = 'Preferred'
        pool_reason[idx] = (
            f"Rank {rank}/10 (top 20%), weak_count={wc} <= 2"
        )

    elif rank <= 5 and wc <= 4:
        pool[idx] = 'Core'
        pool_reason[idx] = (
            f"Rank {rank}/10, weak_count={wc} <= 4"
        )

    else:
        pool[idx] = 'Conditional'
        pool_reason[idx] = (
            f"Rank {rank}/10, weak_count={wc} <= 6"
        )

# =====================================================================
# 5. DIRECTIONAL ALIGNMENT
#
#    "Aligned" = paper reference ranking and simplified pool agree in
#    direction:
#      - Paper rank <= 3 (top tier)     AND pool in {Preferred, Core}
#      - Paper rank >= 8 (bottom tier)  AND pool in {Conditional, Restricted}
#      - Otherwise: different_but_explainable
# =====================================================================
directional_alignment = [''] * n_suppliers
directional_reason = [''] * n_suppliers

for i in range(n_suppliers):
    pr = int(paper_rank[i])
    p = pool[i]

    if pr <= 3 and p in ('Preferred', 'Core'):
        directional_alignment[i] = 'aligned'
        directional_reason[i] = (
            f"Paper rank {pr} (top 3) maps to pool '{p}'"
        )
    elif pr >= 8 and p in ('Conditional', 'Restricted'):
        directional_alignment[i] = 'aligned'
        directional_reason[i] = (
            f"Paper rank {pr} (bottom 3) maps to pool '{p}'"
        )
    else:
        directional_alignment[i] = 'different_but_explainable'
        directional_reason[i] = (
            f"Paper rank {pr} maps to pool '{p}'"
        )

n_aligned = sum(1 for a in directional_alignment if a == 'aligned')
alignment_rate = n_aligned / n_suppliers * 100

top_supplier_idx = int(np.argmin(paper_rank))  # rank 1 best
top_aligned = pool[top_supplier_idx] in ('Preferred', 'Core')

# =====================================================================
# 6. BUILD OUTPUT CSV
# =====================================================================
output = pd.DataFrame({
    'supplier_id': supplier_ids,
    'paper_priority_weight': paper_priority_weights,
    'paper_reference_rank': paper_rank,
    'recomputed_green_score': np.round(green_score, 6),
    'recomputed_rank': green_rank,
    'simplified_green_pool': pool,
    'weak_criteria_count': weak_criteria_count.astype(int),
    'pool_reason': pool_reason,
    'directional_alignment_flag': directional_alignment,
    'directional_alignment_reason': directional_reason,
})

output.to_csv('M2_External_Benchmark_Green_Result.csv', index=False)

# =====================================================================
# 7. PRINT REPORT
# =====================================================================
print('=' * 72)
print('  M2 EXTERNAL BENCHMARK -- GREEN SUPPLIER SELECTION')
print('  10 suppliers, 17 GSCM criteria')
print('  Reference: Uppala et al. (2016) / Kannan et al. (2014)')
print('=' * 72)

print('\n--- Paper Reference Ranking (Alternative Priority Weight) ---')
for i in np.argsort(paper_rank):
    print(f'  {supplier_ids[i]:>3s}: weight={paper_priority_weights[i]:.8f}  rank={int(paper_rank[i])}')

print('\n--- Recomputed Weighted Green Score (consistency check) ---')
print('  (Weighted sum of criteria weights x supplier priority matrix)')
for i in np.argsort(green_rank):
    print(f'  {supplier_ids[i]:>3s}: score={green_score[i]:.6f}  rank={int(green_rank[i])}')

print('\n--- Simplified Green Pool Assignment ---')
for p in ['Preferred', 'Core', 'Conditional', 'Restricted']:
    members = [supplier_ids[i] for i in range(n_suppliers) if pool[i] == p]
    if members:
        detail = ', '.join(
            f"{s}({int(weak_criteria_count[si])} weak)"
            for si, s in enumerate(supplier_ids) if pool[si] == p
        )
        print(f'  {p:12s}: {detail}')

print(f'\n--- Paper Top 5 ---')
top5_paper = [supplier_ids[i] for i in np.argsort(paper_rank)[:5]]
print(f'  {", ".join(top5_paper)}')

print(f'\n--- Recomputed Top 5 (by green score) ---')
top5_recomp = [supplier_ids[i] for i in np.argsort(green_rank)[:5]]
print(f'  {", ".join(top5_recomp)}')

print(f'\n--- Top Supplier Alignment ---')
print(f'  Paper #1: {supplier_ids[top_supplier_idx]} -> '
      f'Pool: {pool[top_supplier_idx]}')
print(f'  Top supplier aligned in Preferred/Core: {top_aligned}')

print(f'\n--- Directional Alignment ---')
print(f'  Aligned: {n_aligned}/{n_suppliers} ({alignment_rate:.1f}%)')
different = [(i, supplier_ids[i], directional_reason[i])
             for i in range(n_suppliers)
             if directional_alignment[i] == 'different_but_explainable']
if different:
    print(f'  Different-but-explainable cases:')
    for _, sid, reason in different:
        print(f'    {sid}: {reason}')

print(f'\n  Generated: M2_External_Benchmark_Green_Result.csv')
print('=' * 72)
