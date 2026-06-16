#!/usr/bin/env python3
"""
M3_Lightweight_Allocation.py
Lightweight Resource Pool Allocation simulation for M3.

Reads M2 output CSVs to obtain supplier pool classification, cost index,
risk level, and ESG tier.  Filters to one category (Key_Component) and runs
4 allocation policies for comparison.

Policies:
  1. Preferred_First   - Preferred suppliers allocated first (cheapest within pool);
                         Core fills residual; Conditional capped at 10%.
  2. Balanced_Core     - Core suppliers receive a reserved allocation window
                         before Preferred; Preferred fills remainder.
                         Business rationale: preserve Core supplier availability
                         and reduce single-source reliance on Preferred pool.
  3. Cost_Minimized    - All non-Restricted suppliers sorted by Adjusted Cost Index
                         (cheapest first), ignoring pool priority.
  4. Risk_Controlled   - Low-risk suppliers allocated first; medium-risk second;
                         high-risk excluded.

M3 is a LIGHTWEIGHT allocation SIMULATOR, not a MILP optimizer.
Scenario stress testing (demand / capacity shocks) is reserved for M4.
Does not modify M1 / M2 / M4 logic or output files.
"""

import numpy as np
import pandas as pd

# =====================================================================
# 1. READ M2 OUTPUT CSVs
# =====================================================================
pool_view = pd.read_csv('M2_Strategic_Pool_View.csv', encoding='utf-8')
suppliers_raw = pd.read_csv('suppliers_data.csv', encoding='utf-8')

# Filter to Key_Component and merge with suppliers_data for capacity proxy
kc_pool = pool_view[pool_view['category'] == 'Key_Component'].copy()

# Merge with suppliers_data for annual_contract_value_usd (capacity proxy)
kc = pd.merge(
    kc_pool,
    suppliers_raw[['supplier_id', 'annual_contract_value_usd']],
    on='supplier_id',
    how='left'
)

# Rename fields for clarity
kc.rename(columns={
    'Strategic_Pool': 'pool',
    'Adjusted_Cost_Index': 'cost_index',
    'ESG_Position_Tier': 'esg_tier',
}, inplace=True)

# Keep required fields
kc = kc[[
    'supplier_id', 'supplier_name', 'category', 'pool',
    'cost_index', 'risk_level', 'delivery_risk', 'esg_tier',
    'annual_contract_value_usd'
]].copy()

# Canonicalise pool names
pool_map = {
    'Preferred': 'Preferred', 'Core': 'Core',
    'Conditional': 'Conditional', 'Restricted': 'Restricted'
}
kc['pool'] = kc['pool'].map(pool_map).fillna(kc['pool'])

N_SUPPLIERS = len(kc)

# =====================================================================
# 2. SCENARIO ASSUMPTIONS (illustrative, not real enterprise data)
#
# Demand:    $10M quarterly for Key_Component
# Capacity:  annual_contract_value_usd / 4 as quarterly proxy
#            (illustrative - not confirmed with procurement)
#
# The three TBD placeholder files are NOT modified:
#   M3_Category_Demand_Plan.csv
#   M3_Supplier_Capacity_Assumption.csv
#   M3_Allocation_Policy.csv
# =====================================================================
DEMAND = 10_000_000  # $10M quarterly illustrative demand

# Quarterly capacity proxy = annual contract value / 4
kc['capacity'] = (kc['annual_contract_value_usd'] / 4).fillna(1_000_000).clip(lower=500_000)

capacity_dict = dict(zip(kc['supplier_id'], kc['capacity']))

# =====================================================================
# 3. ALLOCATION POLICIES
# =====================================================================
POLICY = {
    'Preferred_First': {
        'label': 'Preferred First',
        'short_label': 'Preferred priority allocation',
        'desc': 'Preferred allocated in cost order (cheapest first), up to 45% '
                'each; Core fills residual; Conditional capped at 10%; Restricted excluded.',
        'max_share': 0.45,
        'cond_cap':  0.10,
        'order':     ['Preferred', 'Core', 'Conditional'],
        'sort_col':  'cost_index',
    },
    'Balanced_Core': {
        'label': 'Balanced Core',
        'short_label': '60/40 Preferred-Core balanced allocation',
        'desc': 'Core suppliers receive a reserved allocation window (20% each) '
                'before Preferred (~60% target); Preferred fills remainder (up to 40% '
                'each). Conditional capped at 5%.  Rationale: preserve Core pool '
                'availability and reduce over-reliance on Preferred tier.',
        'max_share': 0.40,
        'core_first_share': 0.20,
        'cond_cap':  0.05,
        'order':     ['Core', 'Preferred', 'Conditional'],
        'sort_col':  'cost_index',
    },
    'Cost_Minimized': {
        'label': 'Cost Minimized',
        'short_label': 'Lowest adjusted cost first',
        'desc': 'All non-Restricted suppliers sorted by cost index (cheapest first); '
                'Conditional capped at 5%; Restricted excluded.',
        'max_share': 0.40,
        'cond_cap':  0.05,
        'order':     None,
        'sort_col':  'cost_index',
    },
    'Risk_Controlled': {
        'label': 'Risk Controlled',
        'short_label': 'Low-risk first, medium-risk capped',
        'desc': 'Low-risk suppliers allocated first (up to 40% each); medium-risk '
                'capped at 30% each; Conditional capped at 5%; high-risk and Restricted '
                'excluded.',
        'max_share': 0.40,
        'med_cap':   0.30,
        'cond_cap':  0.05,
        'order':     None,
        'sort_col':  'risk',
    },
}


def allocate(policy_name):
    """Run one policy allocation. Returns (detail_df, summary_dict)."""
    cfg = POLICY[policy_name]
    df = kc.copy()
    df['capacity'] = df['supplier_id'].map(capacity_dict)
    df['allocation'] = 0.0
    remaining = DEMAND
    max_single = cfg['max_share'] * DEMAND
    cond_max = cfg['cond_cap'] * DEMAND
    med_cap = cfg.get('med_cap', 1.0) * DEMAND if policy_name == 'Risk_Controlled' else 1e15

    # --- sort order ---
    if cfg['sort_col'] == 'cost_index':
        # Sort by pool priority (if order defined), then cost_index
        if cfg['order'] is not None:
            pool_rank = {p: i for i, p in enumerate(cfg['order'])}
            df['_prio'] = df['pool'].map(pool_rank).fillna(99)
            df = df.sort_values(['_prio', 'cost_index'])
        else:
            df = df.sort_values('cost_index')
    elif cfg['sort_col'] == 'risk':
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        df['_prio'] = df['risk_level'].map(risk_order).fillna(99)
        if cfg['order'] is not None:
            pool_rank2 = {p: i for i, p in enumerate(cfg['order'])}
            df['_pool_prio'] = df['pool'].map(pool_rank2).fillna(99)
            df = df.sort_values(['_pool_prio', '_prio', 'cost_index'])
        else:
            df = df.sort_values(['_prio', 'cost_index'])

    # --- Balanced_Core two-phase allocation ---
    if policy_name == 'Balanced_Core':
        core_max = cfg['core_first_share'] * DEMAND
        # Phase 1: Core suppliers only
        for idx, row in df.iterrows():
            if remaining <= 1:
                df.at[idx, 'allocation'] = 0.0
                continue
            if row['pool'] == 'Restricted':
                df.at[idx, 'allocation'] = 0.0
                continue
            if row['pool'] != 'Core':
                continue  # skip non-Core in phase 1

            cap = min(row['capacity'], core_max)
            if row['pool'] == 'Conditional':
                cap = min(cap, cond_max)
            alloc = min(cap, remaining)
            df.at[idx, 'allocation'] = alloc
            remaining -= alloc

        # Phase 2: remaining suppliers (Preferred, Conditional)
        for idx, row in df.iterrows():
            if remaining <= 1:
                df.at[idx, 'allocation'] = df.at[idx, 'allocation'] or 0.0
                continue
            if row['pool'] == 'Restricted':
                df.at[idx, 'allocation'] = df.at[idx, 'allocation'] or 0.0
                continue
            if row['pool'] == 'Core':
                continue  # already done

            cap = min(row['capacity'], max_single)
            if row['pool'] == 'Conditional':
                cap = min(cap, cond_max)
            alloc = min(cap, remaining)
            df.at[idx, 'allocation'] = (df.at[idx, 'allocation'] or 0.0) + alloc
            remaining -= alloc

    else:
        # --- standard single-phase allocation ---
        for idx, row in df.iterrows():
            if remaining <= 1:
                df.at[idx, 'allocation'] = 0.0
                continue
            if row['pool'] == 'Restricted':
                df.at[idx, 'allocation'] = 0.0
                continue

            cap = min(row['capacity'], max_single)
            if row['pool'] == 'Conditional':
                cap = min(cap, cond_max)
            if policy_name == 'Risk_Controlled' and row['risk_level'] == 'medium':
                cap = min(cap, med_cap)

            alloc = min(cap, remaining)
            df.at[idx, 'allocation'] = alloc
            remaining -= alloc

    # --- derived fields ---
    df['pct_of_demand'] = np.round(df['allocation'] / DEMAND * 100, 2)
    df['capacity_util'] = np.where(
        df['capacity'] > 0,
        np.round(df['allocation'] / df['capacity'] * 100, 1),
        0.0
    )

    # drop helpers
    for c in ['_prio', '_pool_prio']:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    total_alloc = df['allocation'].sum()
    unmet = DEMAND - total_alloc

    # Pool share amounts
    pref_amt = df.loc[df['pool'] == 'Preferred', 'allocation'].sum()
    core_amt = df.loc[df['pool'] == 'Core', 'allocation'].sum()
    cond_amt = df.loc[df['pool'] == 'Conditional', 'allocation'].sum()
    rest_amt = df.loc[df['pool'] == 'Restricted', 'allocation'].sum()

    # Weighted average cost index among allocated suppliers
    allocated = df[df['allocation'] > 0]
    if len(allocated) > 0:
        weighted_cost = np.average(
            allocated['cost_index'],
            weights=allocated['allocation']
        )
    else:
        weighted_cost = 0.0

    # Risk notes
    risk_tiers = allocated['risk_level'].value_counts()
    risk_notes_parts = []
    for tier in ['low', 'medium', 'high']:
        if tier in risk_tiers.index:
            risk_notes_parts.append(f'{tier}={int(risk_tiers[tier])}')
    risk_notes = ', '.join(risk_notes_parts) if risk_notes_parts else 'none'

    summary = dict(
        policy=policy_name,
        label=cfg['label'],
        category='Key_Component',
        total_demand=DEMAND,
        allocated_amount=round(total_alloc),
        unmet_demand=round(unmet),
        preferred_share=round(pref_amt / DEMAND * 100, 1),
        core_share=round(core_amt / DEMAND * 100, 1),
        conditional_share=round(cond_amt / DEMAND * 100, 1),
        restricted_share=round(rest_amt / DEMAND * 100, 1),
        weighted_cost_index=round(weighted_cost, 4),
        supplier_count_used=int((df['allocation'] > 0).sum()),
        risk_notes=risk_notes,
    )
    return df, summary


# =====================================================================
# 4. RUN ALL POLICIES
# =====================================================================
all_detail = []
all_summ = []

for pname in POLICY:
    det, summ = allocate(pname)
    det['policy'] = pname
    all_detail.append(det)
    all_summ.append(summ)

detail_all = pd.concat(all_detail, ignore_index=True)
summary_df = pd.DataFrame(all_summ)

# =====================================================================
# 5. BUILD OUTPUT FIELDS
# =====================================================================
CATEGORY = 'Key_Component'

detail_out = detail_all[[
    'policy', 'supplier_id', 'supplier_name', 'pool',
    'cost_index', 'risk_level', 'delivery_risk', 'esg_tier',
    'capacity', 'allocation', 'pct_of_demand', 'capacity_util',
]].copy()

# Category and notes
detail_out.insert(1, 'category', CATEGORY)

# Notes field - explain non-allocation
def build_note(row):
    if row['allocation'] <= 0:
        if row['pool'] == 'Restricted':
            return 'Restricted: zero allocation by policy'
        return f'Not allocated under {row["policy"]}'
    return ''
detail_out['notes'] = detail_out.apply(build_note, axis=1)

detail_out.columns = [
    'policy', 'category', 'supplier_id', 'supplier_name', 'm2_pool',
    'adjusted_cost_index', 'risk_level', 'delivery_risk', 'esg_tier',
    'capacity_usd', 'allocation_amount', 'allocation_share',
    'capacity_util_pct', 'notes',
]

detail_out.to_csv('M3_Key_Category_Allocation_Result.csv', index=False)

summary_df.to_csv('M3_Key_Category_Allocation_Summary.csv', index=False)

# =====================================================================
# 6. SCENARIO ASSUMPTIONS FILE
# =====================================================================
scenario_rows = []
scenario_rows.append(dict(
    scenario='Base', category=CATEGORY,
    parameter='quarterly_demand_usd', value=DEMAND, unit='USD',
    source='Illustrative assumption (not real enterprise data)',
    note='Quarterly demand for Key_Component allocation simulation'))
for _, r in kc.iterrows():
    cap = capacity_dict[r['supplier_id']]
    scenario_rows.append(dict(
        scenario='Base', category=CATEGORY,
        parameter=f'capacity_{r["supplier_id"]}',
        value=cap, unit='USD',
        source='annual_contract_value_usd / 4 (illustrative proxy)',
        note=f'{r["pool"]} supplier'))
for pname, cfg in POLICY.items():
    scenario_rows.append(dict(
        scenario='Base', category=CATEGORY,
        parameter=f'{pname}_max_single_share',
        value=cfg['max_share'], unit='pct_of_demand',
        source='Policy config',
        note=cfg['desc']))
    scenario_rows.append(dict(
        scenario='Base', category=CATEGORY,
        parameter=f'{pname}_conditional_cap',
        value=cfg['cond_cap'], unit='pct_of_demand',
        source='Policy config',
        note='Max allocation per Conditional supplier'))

scenario_df = pd.DataFrame(scenario_rows)
scenario_df.to_csv('M3_Scenario_Assumptions_Key_Component.csv', index=False)

# =====================================================================
# 7. REPORT
# =====================================================================
print('=' * 72)
print('  M3 LIGHTWEIGHT RESOURCE POOL ALLOCATION')
print('  Category: Key_Component  |  Quarterly Demand: ${:,}'.format(DEMAND))
print('  Input files: M2_Strategic_Pool_View.csv, suppliers_data.csv')
print('  Suppliers: {} with M2 pool classification'.format(N_SUPPLIERS))
print('=' * 72)

print('\n--- Supplier Pool Overview ---')
for pool in ['Preferred', 'Core', 'Conditional', 'Restricted']:
    grp = kc[kc['pool'] == pool]
    parts = ', '.join(
        '{}(cost={:.3f}, {})'.format(
            r['supplier_id'], r['cost_index'], r['risk_level'])
        for _, r in grp.iterrows())
    cap_total = int(sum(capacity_dict[r['supplier_id']] for _, r in grp.iterrows()))
    print('  {:<12s}: {}  (total capacity ${:,})'.format(pool, parts, cap_total))

print('\n--- Capacity Assumptions (annual_contract / 4) ---')
for _, r in kc.iterrows():
    c = capacity_dict[r['supplier_id']]
    print('  {:<3s} ({:<12s}): ${:>8,d} capacity'.format(
        r['supplier_id'], r['pool'], int(c)))

print('\n--- Policy Results ---')
for _, s in summary_df.iterrows():
    print('\n  {} - {}'.format(s['policy'], POLICY[s['policy']]['short_label']))
    print('  Allocated: ${:>9,d}  |  Unmet: ${:>9,d}'
          .format(int(s['allocated_amount']), int(s['unmet_demand'])))
    print('  Pool shares: P={}%  C={}%  Cd={}%  R={}%'
          .format(s['preferred_share'], s['core_share'],
                  s['conditional_share'], s['restricted_share']))
    print('  Suppliers used: {}  |  Weighted cost index: {:.4f}  |  Risk: {}'
          .format(int(s['supplier_count_used']),
                  s['weighted_cost_index'], s['risk_notes']))

    pol = detail_all[
        (detail_all['policy'] == s['policy']) &
        (detail_all['allocation'] > 0)
    ].sort_values('allocation', ascending=False)
    for _, r in pol.iterrows():
        print('    {:<3s} ({:<12s}): ${:>8,d} ({:>5.1f}% demand, {:>3.0f}% cap)'
              .format(r['supplier_id'], r['pool'],
                      int(r['allocation']),
                      r['pct_of_demand'], r['capacity_util']))
    zeros = detail_all[
        (detail_all['policy'] == s['policy']) &
        (detail_all['allocation'] == 0)
    ]
    for _, r in zeros.iterrows():
        print('    {:<3s} ({:<12s}): $       0  (not allocated)'.format(
            r['supplier_id'], r['pool']))

print('\n--- Generated Files ---')
print('  M3_Key_Category_Allocation_Result.csv')
print('  M3_Key_Category_Allocation_Summary.csv')
print('  M3_Scenario_Assumptions_Key_Component.csv')
print('=' * 72)
