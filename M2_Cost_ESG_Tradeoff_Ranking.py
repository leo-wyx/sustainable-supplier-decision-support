# ============================================================
# M2_Cost_ESG_Tradeoff_Ranking.py
#
# M2 post-processing module: Cost-ESG Trade-off Ranking
#
# Core principles:
#   - Adjusted_Cost_Index is the primary sort basis
#   - ESG enters through required cost premium, not arbitrary weight
#   - TQRDC is diagnostic risk profile, not hard penalty
#   - Strategic Pool is a management label, not the sole output
#
# This module does NOT modify Model2.py or any M1/M3/M4 logic.
# ============================================================
import pandas as pd
import numpy as np
import os

# ============================================================
# 1. Load input files
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pool = pd.read_csv(os.path.join(BASE_DIR, 'M2_Strategic_Pool_View.csv'))
cost_idx = pd.read_csv(os.path.join(BASE_DIR, 'M2_Adjusted_Cost_Index.csv'))
diag = pd.read_csv(os.path.join(BASE_DIR, 'M2_Supplier_Diagnostic_Profile.csv'))

# ============================================================
# 2. Merge into unified dataframe
# ============================================================
# Start from Strategic_Pool_View as the anchor (has all key fields)
keep_cols = [
    'supplier_id', 'supplier_name', 'category', 'M1_Status',
    'Adjusted_Cost_Index', 'cost_quartile', 'cost_position',
    'ESG_Position_Tier', 'risk_level', 'delivery_risk',
    'T_capability_flag', 'Q_quality_warning', 'C_cost_warning',
    'Strategic_Pool', 'pool_reason'
]

df = pool[keep_cols].copy()

# ============================================================
# 3. Cost baseline ranking (per category)
# ============================================================
# Sort by Adjusted_Cost_Index ascending within each category
df = df.sort_values(['category', 'Adjusted_Cost_Index']).reset_index(drop=True)

df['cost_rank'] = df.groupby('category')['Adjusted_Cost_Index'].rank(method='min', ascending=True).astype(int)

def calc_cost_rank_pct_series(ranks):
    """Convert cost_rank to percent rank within a category group."""
    n = len(ranks)
    if n <= 1:
        return pd.Series(0.0, index=ranks.index)
    return (ranks - 1) / (n - 1) * 100

df['cost_rank_pct'] = (
    df.groupby('category')['cost_rank']
    .transform(calc_cost_rank_pct_series)
    .round(1)
)

def label_cost_baseline(pct):
    if pct <= 25.0:
        return 'Cost Tier 1'
    elif pct <= 50.0:
        return 'Cost Tier 2'
    elif pct <= 75.0:
        return 'Cost Tier 3'
    else:
        return 'Cost Tier 4'

df['cost_baseline_label'] = df['cost_rank_pct'].apply(label_cost_baseline)

# ============================================================
# 4. ESG tier numeric mapping
# ============================================================
esg_tier_map = {
    'ESG Leader': 3,
    'ESG Compliant': 2,
    'ESG Monitor': 1,
}

df['esg_tier_numeric'] = df['ESG_Position_Tier'].map(esg_tier_map).fillna(1)

# ============================================================
# 5. ESG required premium calculation
# ============================================================
def compute_esg_premium_for_group(group):
    """Within a category group, compute required ESG premium for each supplier."""
    result = group.copy()
    result['reference_supplier_id'] = ''
    result['reference_supplier_cost'] = np.nan
    result['reference_supplier_esg'] = ''
    result['required_esg_premium_pct'] = 0.0
    result['tradeoff_case'] = ''

    if len(group) <= 1:
        result['tradeoff_case'] = 'no_lower_cost_lower_esg_reference'
        return result

    group_sorted = group.sort_values('Adjusted_Cost_Index').reset_index(drop=True)

    for idx, row in group_sorted.iterrows():
        candidates = group_sorted[
            (group_sorted['Adjusted_Cost_Index'] < row['Adjusted_Cost_Index']) &
            (group_sorted['esg_tier_numeric'] < row['esg_tier_numeric'])
        ]

        if len(candidates) == 0:
            result.loc[result['supplier_id'] == row['supplier_id'], 'tradeoff_case'] = 'no_lower_cost_lower_esg_reference'
            continue

        result.loc[result['supplier_id'] == row['supplier_id'], 'tradeoff_case'] = 'has_lower_cost_lower_esg_reference'

        candidates = candidates.copy()
        candidates['premium'] = (row['Adjusted_Cost_Index'] - candidates['Adjusted_Cost_Index']) / candidates['Adjusted_Cost_Index']
        best = candidates.loc[candidates['premium'].idxmin()]

        premium_pct = round(best['premium'] * 100, 2)
        result.loc[result['supplier_id'] == row['supplier_id'], 'required_esg_premium_pct'] = premium_pct
        result.loc[result['supplier_id'] == row['supplier_id'], 'reference_supplier_id'] = best['supplier_id']
        result.loc[result['supplier_id'] == row['supplier_id'], 'reference_supplier_cost'] = best['Adjusted_Cost_Index']
        result.loc[result['supplier_id'] == row['supplier_id'], 'reference_supplier_esg'] = best['ESG_Position_Tier']

    return result

# Apply per category via explicit loop to avoid pandas FutureWarning on groupby.apply
segments = []
for _, grp in df.groupby('category'):
    segments.append(compute_esg_premium_for_group(grp))
df = pd.concat(segments, ignore_index=True)

# Clean up: ensure no NaN/Inf in required_esg_premium_pct
df['required_esg_premium_pct'] = df['required_esg_premium_pct'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

# ============================================================
# 6. ESG tolerance scenarios
# ============================================================
def tolerance_check(row, tolerance_pct):
    case = row['tradeoff_case']
    if case == 'no_lower_cost_lower_esg_reference':
        return 'Not applicable'
    premium = row['required_esg_premium_pct']
    if premium <= tolerance_pct:
        return 'Yes'
    else:
        return 'No'

df['accepted_under_0pct'] = df.apply(lambda r: tolerance_check(r, 0), axis=1)
df['accepted_under_5pct'] = df.apply(lambda r: tolerance_check(r, 5), axis=1)
df['accepted_under_10pct'] = df.apply(lambda r: tolerance_check(r, 10), axis=1)
df['accepted_under_15pct'] = df.apply(lambda r: tolerance_check(r, 15), axis=1)

# ============================================================
# 7. Trade-off status
# ============================================================
def assign_tradeoff_status(row):
    case = row['tradeoff_case']
    premium = row['required_esg_premium_pct']

    if case == 'no_lower_cost_lower_esg_reference':
        # Check if this supplier is low cost = Cost Tier 1 or 2
        if row['cost_baseline_label'] in ('Cost Tier 1', 'Cost Tier 2'):
            return 'no_tradeoff_needed'
        else:
            return 'lower_esg_or_no_esg_advantage'

    # has_lower_cost_lower_esg_reference
    if premium <= 5.0:
        return 'esg_justified_under_5pct'
    elif premium <= 10.0:
        return 'esg_justified_under_10pct'
    elif premium <= 15.0:
        return 'esg_justified_under_15pct'
    else:
        return 'esg_not_justified_cost_gap_too_high'

df['tradeoff_status'] = df.apply(assign_tradeoff_status, axis=1)

# Additional status for suppliers with no ESG advantage
# If supplier is ESG Monitor and has no reference, mark as lower_esg_or_no_esg_advantage
# (already handled in the function above for non-low-cost cases)

# ============================================================
# 8. TQRDC risk profile (diagnostic only, no hard penalty)
# ============================================================
def compute_tqrdc_warnings(row):
    warnings = 0
    reasons = []

    if row['risk_level'] == 'high':
        warnings += 1
        reasons.append('high risk_level')

    if row['delivery_risk'] == 'high':
        warnings += 1
        reasons.append('high delivery_risk')

    if row['Q_quality_warning'] != 'No quality concern':
        warnings += 1
        reasons.append(f"Q: {row['Q_quality_warning']}")

    if row['C_cost_warning'] != 'No cost concern':
        warnings += 1
        reasons.append(f"C: {row['C_cost_warning']}")

    if row['T_capability_flag'] != 'Standard capability':
        warnings += 1
        reasons.append(f"T: {row['T_capability_flag']}")

    return warnings, '; '.join(reasons) if reasons else 'No diagnostic warnings'

def assign_tqrdc_label(count):
    if count == 0:
        return 'Low diagnostic concern'
    elif count == 1:
        return 'Moderate diagnostic concern'
    else:
        return 'High diagnostic concern'

warn_data = df.apply(compute_tqrdc_warnings, axis=1, result_type='expand')
df['tqrdc_warning_count'] = warn_data[0]
df['tqrdc_risk_label'] = df['tqrdc_warning_count'].apply(assign_tqrdc_label)
df['tqrdc_risk_reason'] = warn_data[1]

# ============================================================
# 9. Management ranking
# ============================================================
# Define sort priority
def m1_sort_key(status):
    if status == 'PASS':
        return 0
    else:
        return 1

pool_priority = {'Preferred': 0, 'Core': 1, 'Conditional': 2, 'Restricted': 3}

df['_m1_order'] = df['M1_Status'].apply(m1_sort_key)
df['_pool_order'] = df['Strategic_Pool'].map(pool_priority).fillna(99)

df = df.sort_values(
    ['category', '_m1_order', '_pool_order', 'cost_rank', 'esg_tier_numeric', 'tqrdc_warning_count'],
    ascending=[True, True, True, True, False, True]
).reset_index(drop=True)

# Apply management_rank per category via explicit loop
segments_mgmt = []
for _, grp in df.groupby('category'):
    seg = grp.copy()
    seg['management_rank'] = range(1, len(seg) + 1)
    segments_mgmt.append(seg)
df = pd.concat(segments_mgmt, ignore_index=True)

def build_rank_note(row):
    parts = []
    if row['M1_Status'] == 'PASS':
        parts.append('M1 PASS')
    else:
        parts.append(f"M1 {row['M1_Status']}")
    parts.append(row['Strategic_Pool'])
    parts.append(row['cost_baseline_label'])
    parts.append(row['ESG_Position_Tier'])
    parts.append(row['tqrdc_risk_label'])
    return ' | '.join(parts)

df['management_rank_note'] = df.apply(build_rank_note, axis=1)

# Drop helper columns
df = df.drop(columns=['_m1_order', '_pool_order'])

# ============================================================
# 10. Output files
# ============================================================
# A. Full ranking view
output_cols = [
    'supplier_id', 'supplier_name', 'category', 'M1_Status',
    'Adjusted_Cost_Index', 'cost_rank', 'cost_rank_pct', 'cost_baseline_label',
    'ESG_Position_Tier', 'esg_tier_numeric',
    'reference_supplier_id', 'reference_supplier_cost', 'reference_supplier_esg',
    'required_esg_premium_pct',
    'accepted_under_0pct', 'accepted_under_5pct', 'accepted_under_10pct', 'accepted_under_15pct',
    'tradeoff_case', 'tradeoff_status',
    'tqrdc_warning_count', 'tqrdc_risk_label', 'tqrdc_risk_reason',
    'Strategic_Pool', 'pool_reason',
    'management_rank', 'management_rank_note'
]

ranking_df = df[output_cols].copy()
ranking_df.to_csv(os.path.join(BASE_DIR, 'M2_Cost_ESG_Tradeoff_Ranking.csv'), index=False)

# B. Category summary
# Explicit loop per category to avoid pandas FutureWarning on groupby.apply
summary_rows = []
for cat, grp in df.groupby('category'):
    n = len(grp)

    # Suppliers with has_reference (has a lower-cost lower-ESG peer)
    ref_suppliers = grp[grp['tradeoff_case'] == 'has_lower_cost_lower_esg_reference']
    avg_premium = ref_suppliers['required_esg_premium_pct'].mean() if len(ref_suppliers) > 0 else 0.0

    # Interval-based stats (not cumulative)
    esg_0_5 = len(grp[grp['tradeoff_status'] == 'esg_justified_under_5pct'])
    esg_5_10 = len(grp[grp['tradeoff_status'] == 'esg_justified_under_10pct'])
    esg_10_15 = len(grp[grp['tradeoff_status'] == 'esg_justified_under_15pct'])
    esg_over_15 = len(grp[grp['tradeoff_status'] == 'esg_not_justified_cost_gap_too_high'])

    high_tqrdc = len(grp[grp['tqrdc_risk_label'] == 'High diagnostic concern'])

    preferred = len(grp[grp['Strategic_Pool'] == 'Preferred'])
    core = len(grp[grp['Strategic_Pool'] == 'Core'])
    conditional = len(grp[grp['Strategic_Pool'] == 'Conditional'])
    restricted = len(grp[grp['Strategic_Pool'] == 'Restricted'])

    # Key finding
    findings = []
    if esg_0_5 > 0:
        findings.append(f"{esg_0_5} supplier(s) ESG-justified (0-5% premium)")
    if esg_5_10 > 0:
        findings.append(f"{esg_5_10} supplier(s) ESG-justified (5-10% premium)")
    if esg_10_15 > 0:
        findings.append(f"{esg_10_15} supplier(s) ESG-justified (10-15% premium)")
    if esg_over_15 > 0:
        findings.append(f"{esg_over_15} supplier(s) not ESG-justified (premium > 15%)")
    if high_tqrdc > 0:
        findings.append(f"{high_tqrdc} supplier(s) with high TQRDC diagnostic concern")
    key_finding = '; '.join(findings) if findings else 'No significant ESG trade-off issues'

    summary_rows.append({
        'category': cat,
        'supplier_count': n,
        'avg_required_esg_premium_pct': round(avg_premium, 2),
        'suppliers_esg_justified_0_5pct': esg_0_5,
        'suppliers_esg_justified_5_10pct': esg_5_10,
        'suppliers_esg_justified_10_15pct': esg_10_15,
        'suppliers_esg_not_justified_over_15pct': esg_over_15,
        'high_tqrdc_risk_count': high_tqrdc,
        'preferred_count': preferred,
        'core_count': core,
        'conditional_count': conditional,
        'restricted_count': restricted,
        'key_finding': key_finding,
    })

summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv(os.path.join(BASE_DIR, 'M2_Cost_ESG_Tradeoff_Summary.csv'), index=False)

# ============================================================
# Verification prints
# ============================================================
print("=" * 60)
print("M2 Cost-ESG Trade-off Ranking - Generation Complete")
print("=" * 60)

# Check 1: no Inf/NaN in premium
assert not ranking_df['required_esg_premium_pct'].isna().any(), "NaN found in required_esg_premium_pct"
assert not np.isinf(ranking_df['required_esg_premium_pct']).any(), "Inf found in required_esg_premium_pct"
print("[PASS] required_esg_premium_pct: no NaN or Inf")

# Check 2: tolerance columns are valid
valid_tol = {'Yes', 'No', 'Not applicable'}
for col in ['accepted_under_0pct', 'accepted_under_5pct', 'accepted_under_10pct', 'accepted_under_15pct']:
    actual = set(ranking_df[col].unique())
    assert actual.issubset(valid_tol), f"{col}: unexpected values {actual - valid_tol}"
print("[PASS] tolerance columns: only Yes / No / Not applicable")

# Check 3: tqrdc_risk_label valid
valid_labels = {'Low diagnostic concern', 'Moderate diagnostic concern', 'High diagnostic concern'}
actual_labels = set(ranking_df['tqrdc_risk_label'].unique())
assert actual_labels.issubset(valid_labels), f"tqrdc_risk_label: unexpected {actual_labels - valid_labels}"
print("[PASS] tqrdc_risk_label: only Low/Moderate/High diagnostic concern")

# Check 4: management_rank 1-indexed per category
for cat, group in ranking_df.groupby('category'):
    ranks = group['management_rank'].tolist()
    expected = list(range(1, len(group) + 1))
    assert ranks == expected, f"{cat}: management_rank {ranks} != expected {expected}"
print("[PASS] management_rank: 1-indexed continuous per category")

# Check 5: reference_supplier_cost filled only when reference exists
ref_na = ranking_df[ranking_df['tradeoff_case'] == 'no_lower_cost_lower_esg_reference']
assert ref_na['reference_supplier_id'].eq('').all(), "no-reference rows should have empty reference_supplier_id"
has_ref = ranking_df[ranking_df['tradeoff_case'] == 'has_lower_cost_lower_esg_reference']
assert has_ref['reference_supplier_id'].ne('').all(), "reference rows should have non-empty reference_supplier_id"
print("[PASS] reference supplier fields: correct fill pattern")

# Check 6: output files exist
assert os.path.exists(os.path.join(BASE_DIR, 'M2_Cost_ESG_Tradeoff_Ranking.csv'))
assert os.path.exists(os.path.join(BASE_DIR, 'M2_Cost_ESG_Tradeoff_Summary.csv'))
print("[PASS] output CSV files exist")

print()
print(f"Total suppliers: {len(ranking_df)}")
print(f"Categories: {', '.join(sorted(ranking_df['category'].unique()))}")
print(f"Trade-off status distribution:")
print(ranking_df['tradeoff_status'].value_counts().to_string())
print()
print(f"TQRDC risk label distribution:")
print(ranking_df['tqrdc_risk_label'].value_counts().to_string())
print()
print("=" * 60)
print("All validations passed.")
print("=" * 60)
