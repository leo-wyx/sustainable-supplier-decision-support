#!/usr/bin/env python3
"""
M4_Resilience_Scenario.py
Resilience and ESG scenario stress-test layer for Key_Component.

Reads M2 pool classification and M3 base allocation as baseline.
Applies 4 stress scenarios across 4 allocation policies and compares
pre-stress vs post-stress allocation patterns.

Scenarios:
  A. Demand_Surge_50    - demand +50% ($10M -> $15M)
  B. Preferred_Disruption - top Preferred supplier capacity -70%
  C. EU_Carbon_Pressure  - carbon-intensive suppliers face cost +15% and
                           pool downgrade (if not ESG Leader)
  D. Malaysia_Backup_Node - add hypothetical backup node

M4 is a LIGHTWEIGHT scenario stress-test LAYER, not a MILP optimizer.
Does not modify M1 / M2 / M3 logic or output files.
Capacity and demand are illustrative assumptions, not real enterprise data.
"""

import numpy as np
import pandas as pd

CATEGORY = 'Key_Component'
BASELINE_DEMAND = 10_000_000

# =====================================================================
# 1. READ INPUT FILES
# =====================================================================
pool_view = pd.read_csv('M2_Strategic_Pool_View.csv', encoding='utf-8')
suppliers_raw = pd.read_csv('suppliers_data.csv', encoding='utf-8')

# Key_Component suppliers with M2 pool classification
kc = pool_view[pool_view['category'] == CATEGORY].copy()
kc = pd.merge(
    kc,
    suppliers_raw[['supplier_id', 'annual_contract_value_usd', 'carbon_intensity']],
    on='supplier_id', how='left'
)
kc.rename(columns={
    'Strategic_Pool': 'pool',
    'Adjusted_Cost_Index': 'cost_index',
    'ESG_Position_Tier': 'esg_tier',
}, inplace=True)

kc = kc[['supplier_id', 'supplier_name', 'category', 'pool',
         'cost_index', 'risk_level', 'delivery_risk', 'esg_tier',
         'annual_contract_value_usd', 'carbon_intensity']].copy()

# Quarterly capacity = annual_contract / 4
kc['capacity'] = (kc['annual_contract_value_usd'] / 4).fillna(1_000_000).clip(lower=500_000)
N_SUPPLIERS_BASE = len(kc)

# Baseline allocation (M3 result) for before/after comparison
baseline_alloc = pd.read_csv('M3_Key_Category_Allocation_Result.csv', encoding='utf-8')

# =====================================================================
# 2. ALLOCATION ENGINE
# =====================================================================
def allocate(df, demand, policy_cfg):
    """Allocate demand across suppliers. Returns (detail_df, summary_dict)."""
    out = df.copy()
    out['allocation'] = 0.0
    remaining = demand
    max_single = policy_cfg['max_share'] * demand
    cond_cap = policy_cfg.get('cond_cap', 0.0) * demand
    med_cap = demand if policy_cfg.get('med_cap') is None else policy_cfg['med_cap'] * demand

    # Sort
    if policy_cfg.get('sort_col') == 'cost_index':
        if policy_cfg.get('order') is not None:
            pool_rank = {p: i for i, p in enumerate(policy_cfg['order'])}
            out['_prio'] = out['pool'].map(pool_rank).fillna(99)
            out = out.sort_values(['_prio', 'cost_index'])
        else:
            out = out.sort_values('cost_index')
    elif policy_cfg.get('sort_col') == 'risk':
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        out['_prio'] = out['risk_level'].map(risk_order).fillna(99)
        if policy_cfg.get('order') is not None:
            pool_rank2 = {p: i for i, p in enumerate(policy_cfg['order'])}
            out['_pool_prio'] = out['pool'].map(pool_rank2).fillna(99)
            out = out.sort_values(['_pool_prio', '_prio', 'cost_index'])
        else:
            out = out.sort_values(['_prio', 'cost_index'])

    # Balanced_Core two-phase
    if policy_cfg.get('core_first_share') is not None and policy_cfg['core_first_share'] > 0:
        core_max = policy_cfg['core_first_share'] * demand
        for idx, row in out.iterrows():
            if remaining <= 1:
                break
            if row['pool'] != 'Core':
                continue
            cap = min(row.get('capacity', 1e9), core_max)
            alloc = min(cap, remaining)
            out.at[idx, 'allocation'] = alloc
            remaining -= alloc

    # Standard allocation for remaining
    for idx, row in out.iterrows():
        if remaining <= 1:
            out.at[idx, 'allocation'] = out.at[idx, 'allocation'] or 0.0
            continue
        if row['pool'] == 'Restricted':
            out.at[idx, 'allocation'] = out.at[idx, 'allocation'] or 0.0
            continue
        if policy_cfg.get('core_first_share') and row['pool'] == 'Core' and out.at[idx, 'allocation'] > 0:
            continue  # already done in phase 1

        cap = min(row.get('capacity', 1e9), max_single)
        if row['pool'] == 'Conditional':
            cap = min(cap, cond_cap)
        if policy_cfg.get('med_cap') and row.get('risk_level') == 'medium':
            cap = min(cap, med_cap)

        alloc = min(cap, remaining)
        out.at[idx, 'allocation'] = (out.at[idx, 'allocation'] or 0.0) + alloc
        remaining -= alloc

    # Cleanup
    for c in ['_prio', '_pool_prio']:
        if c in out.columns:
            out.drop(columns=[c], inplace=True)

    total_alloc = out['allocation'].sum()
    unmet = demand - total_alloc
    pref = out[out['pool'] == 'Preferred']['allocation'].sum()
    core = out[out['pool'] == 'Core']['allocation'].sum()
    cond = out[out['pool'] == 'Conditional']['allocation'].sum()
    rest = out[out['pool'] == 'Restricted']['allocation'].sum()
    allocated = out[out['allocation'] > 0]
    w_cost = np.average(allocated['cost_index'], weights=allocated['allocation']) if len(allocated) > 0 else 0.0
    risk_tiers = allocated['risk_level'].value_counts()
    risk_parts = []
    for t in ['low', 'medium', 'high']:
        if t in risk_tiers.index:
            risk_parts.append(f'{t}={int(risk_tiers[t])}')
    risk_notes = ', '.join(risk_parts) if risk_parts else 'none'

    summary = dict(
        total_demand=round(demand),
        allocated_amount=round(total_alloc),
        unmet_demand=round(unmet),
        preferred_share=round(pref / demand * 100, 1),
        core_share=round(core / demand * 100, 1),
        conditional_share=round(cond / demand * 100, 1),
        restricted_share=round(rest / demand * 100, 1),
        weighted_cost_index=round(w_cost, 4),
        supplier_count_used=int((out['allocation'] > 0).sum()),
        risk_notes=risk_notes,
    )
    return out, summary


# =====================================================================
# 3. POLICY CONFIGURATIONS (mirrors M3)
# =====================================================================
POLICIES = {
    'Preferred_First': dict(
        max_share=0.45, cond_cap=0.10, order=['Preferred', 'Core', 'Conditional'],
        sort_col='cost_index'),
    'Balanced_Core': dict(
        max_share=0.40, core_first_share=0.20, cond_cap=0.05,
        order=['Core', 'Preferred', 'Conditional'], sort_col='cost_index'),
    'Cost_Minimized': dict(
        max_share=0.40, cond_cap=0.05, order=None, sort_col='cost_index'),
    'Risk_Controlled': dict(
        max_share=0.40, cond_cap=0.05, med_cap=0.30, order=None, sort_col='risk'),
}


# =====================================================================
# 4. BUILD BASELINE (for before/after comparison)
# =====================================================================
def build_baseline_dict():
    """Build {supplier_id: {policy: allocation}} dict from M3 result."""
    result = {}
    for _, row in baseline_alloc.iterrows():
        sid = row['supplier_id']
        if sid not in result:
            result[sid] = {}
        result[sid][row['policy']] = row['allocation_amount']
    return result

baseline_dict = build_baseline_dict()


# =====================================================================
# 5. SCENARIO DEFINITIONS
# =====================================================================
def scenario_demand_surge():
    """A. Demand +50%"""
    df = kc.copy()
    demand = 15_000_000
    stress_reason = 'Demand surge +50%: $10M to $15M'
    return df, demand, stress_reason

def scenario_preferred_disruption():
    """B. Top Preferred supplier capacity -70%"""
    df = kc.copy()
    demand = BASELINE_DEMAND

    # Identify largest Preferred supplier by baseline allocation
    pref_baseline = {}
    for sid, pol_dict in baseline_dict.items():
        for pol, amt in pol_dict.items():
            if amt > 0:
                pref_baseline.setdefault(sid, 0)
                pref_baseline[sid] += amt
    # Among Preferred pool, pick the one with highest total baseline allocation
    pref_suppliers = df[df['pool'] == 'Preferred']['supplier_id'].tolist()
    top_pref = max(pref_suppliers, key=lambda s: pref_baseline.get(s, 0))
    # Also check cost order - S11 is cheapest, would get most in Preferred_First
    # S11 has $4.5M in Preferred_First baseline
    # Reduce capacity by 70%
    df.loc[df['supplier_id'] == top_pref, 'capacity'] *= 0.30

    stress_reason = f'Preferred disruption: {top_pref} capacity -70%'
    return df, demand, stress_reason

def scenario_eu_carbon():
    """C. EU carbon pressure: cost +15%, pool downgrade for non-ESG-Leader"""
    df = kc.copy()
    demand = BASELINE_DEMAND

    # Median carbon_intensity for Key_Component
    ci_vals = df['carbon_intensity'].dropna()
    median_ci = ci_vals.median() if len(ci_vals) > 0 else 0.5

    # Affected: carbon_intensity >= median OR NaN, AND not ESG Leader -> downgrade
    # All affected get cost +15%
    pool_downgrade_map = {
        'Preferred': 'Core',
        'Core': 'Conditional',
        'Conditional': 'Restricted',
        'Restricted': 'Restricted',
    }

    affected_suppliers = []
    for idx, row in df.iterrows():
        ci = row['carbon_intensity']
        above_median = pd.isna(ci) or ci >= median_ci

        if above_median:
            # Cost +15% for all affected
            df.at[idx, 'cost_index'] = row['cost_index'] * 1.15
            affected_suppliers.append(row['supplier_id'])

            # Pool downgrade for non-ESG-Leader
            if row['esg_tier'] != 'ESG Leader':
                df.at[idx, 'pool'] = pool_downgrade_map.get(row['pool'], row['pool'])

    affected_str = ', '.join(affected_suppliers)
    stress_reason = f'EU carbon pressure: cost +15% on {affected_str}; non-ESG-Leader pool downgrade'
    return df, demand, stress_reason

def scenario_malaysia_backup():
    """D. Malaysia backup node"""
    df = kc.copy()
    demand = BASELINE_DEMAND

    # Compute Core average cost index
    core_suppliers = df[df['pool'] == 'Core']
    core_avg_cost = core_suppliers['cost_index'].mean() if len(core_suppliers) > 0 else 0.45
    backup_cost = core_avg_cost * 1.05
    backup_ci = 0.300  # below Key_Component median

    backup = pd.DataFrame([dict(
        supplier_id='MY_Backup_Node',
        supplier_name='MY_Backup_Node',
        category=CATEGORY,
        pool='Core',
        cost_index=backup_cost,
        risk_level='low',
        delivery_risk='medium',
        esg_tier='ESG Compliant',
        annual_contract_value_usd=16_000_000,
        carbon_intensity=backup_ci,
        capacity=4_000_000,
    )])
    df = pd.concat([df, backup], ignore_index=True)

    stress_reason = 'Malaysia backup node added: MY_Backup_Node (Core, cost={:.4f}, capacity=$4M)'.format(backup_cost)
    return df, demand, stress_reason


# =====================================================================
# 6. RUN ALL SCENARIO x POLICY COMBINATIONS
# =====================================================================
SCENARIOS = {
    'Demand_Surge_50': scenario_demand_surge,
    'Preferred_Disruption': scenario_preferred_disruption,
    'EU_Carbon_Pressure': scenario_eu_carbon,
    'Malaysia_Backup_Node': scenario_malaysia_backup,
}

all_result_rows = []
all_summ_rows = []
all_impact_rows = []

for sc_name, sc_fn in SCENARIOS.items():
    sc_df, sc_demand, sc_reason = sc_fn()

    for pname, pcfg in POLICIES.items():
        result, summary = allocate(sc_df, sc_demand, pcfg)
        summary['scenario'] = sc_name
        summary['policy'] = pname
        summary['stress_reason'] = sc_reason
        all_summ_rows.append(summary)

        # Per-supplier detail rows
        for _, r in result.iterrows():
            sid = r['supplier_id']
            before_alloc = baseline_dict.get(sid, {}).get(pname, 0.0) if sc_demand == BASELINE_DEMAND else None

            # For demand surge, baseline is the scoped demand, so we compute
            # before/after differently
            before_val = 0.0
            if sc_name == 'Demand_Surge_50':
                # Compare against same-policy baseline at $10M
                before_val = baseline_dict.get(sid, {}).get(pname, 0.0)
            else:
                before_val = baseline_dict.get(sid, {}).get(pname, 0.0)

            # For MY_Backup_Node, no baseline
            if sid == 'MY_Backup_Node':
                before_val = 0.0

            # Pool before (baseline)
            base_pool = kc.loc[kc['supplier_id'] == sid, 'pool'].values
            pool_before = base_pool[0] if len(base_pool) > 0 else r['pool']

            # Find original cost index for before
            orig_cost = kc.loc[kc['supplier_id'] == sid, 'cost_index'].values
            cost_before = orig_cost[0] if len(orig_cost) > 0 else r['cost_index']

            # Original capacity for before
            orig_cap = kc.loc[kc['supplier_id'] == sid, 'capacity'].values
            cap_before = orig_cap[0] if len(orig_cap) > 0 else r.get('capacity', 0)

            all_result_rows.append(dict(
                scenario=sc_name,
                policy=pname,
                supplier_id=sid,
                supplier_name=r.get('supplier_name', sid),
                category=CATEGORY,
                pool_before=pool_before,
                pool_after=r['pool'],
                allocation_before=round(before_val, 2),
                allocation_after=round(r['allocation'], 2),
                allocation_change=round(r['allocation'] - before_val, 2),
                capacity_before=round(cap_before, 2),
                capacity_after=round(r.get('capacity', 0), 2),
                adjusted_cost_before=round(cost_before, 6),
                adjusted_cost_after=round(r['cost_index'], 6),
                risk_level=r['risk_level'] if pd.notna(r.get('risk_level')) else '',
                delivery_risk=r['delivery_risk'] if pd.notna(r.get('delivery_risk')) else '',
                esg_tier=r['esg_tier'] if pd.notna(r.get('esg_tier')) else '',
                stress_reason=sc_reason,
                notes='' if r['allocation'] > 0 else 'Not allocated',
            ))

            # Impact rows (one per scenario-supplier)
            cap_change_pct = round((r.get('capacity', 0) - cap_before) / cap_before * 100, 1) if cap_before > 0 else 0.0
            cost_change_pct = round((r['cost_index'] - cost_before) / cost_before * 100, 1) if cost_before > 0 else 0.0
            all_impact_rows.append(dict(
                scenario=sc_name,
                policy=pname,
                supplier_id=sid,
                supplier_name=r.get('supplier_name', sid),
                base_pool=pool_before,
                scenario_pool=r['pool'],
                capacity_change_pct=cap_change_pct,
                cost_change_pct=cost_change_pct,
                allocation_change_total=round(r['allocation'] - before_val, 2),
                stress_reason=sc_reason,
            ))

# =====================================================================
# 7. KEY FINDINGS PER SCENARIO-POLICY
# =====================================================================
def compute_key_finding(scenario, policy, summary):
    """Generate a concise key finding per (scenario, policy)."""
    unmet = summary['unmet_demand']
    alloc_pct = summary['allocated_amount'] / summary['total_demand'] * 100
    p = summary['preferred_share']
    c = summary['core_share']
    cd = summary['conditional_share']
    r = summary['restricted_share']
    used = summary['supplier_count_used']

    if scenario == 'Demand_Surge_50':
        if unmet > 0:
            return f'Demand +50%: unmet ${unmet:,} ({100-alloc_pct:.1f}%). {used} suppliers used.'
        else:
            return f'Demand +50%: fully covered by {used} suppliers. P={p}% C={c}%. No gap.'
    elif scenario == 'Preferred_Disruption':
        if unmet > 0:
            return f'Preferred disruption: unmet ${unmet:,}. P={p}% C={c}% shift.'
        else:
            return f'Preferred disruption: absorbed by C={c}% shift. {used} suppliers.'
    elif scenario == 'EU_Carbon_Pressure':
        return f'EU carbon: P={p}% C={c}% Cd={cd}%. Cost escalation absorbed.'
    elif scenario == 'Malaysia_Backup_Node':
        if c > 0:
            return f'Backup node is used under Core-reserving policy; Preferred concentration reduced to {p}%.'
        else:
            return 'Backup node available but idle under this policy; Preferred pool still covers demand.'
    return ''


# =====================================================================
# 8. WRITE OUTPUT FILES
# =====================================================================
result_df = pd.DataFrame(all_result_rows)
summary_df = pd.DataFrame(all_summ_rows)
impact_df = pd.DataFrame(all_impact_rows)

# Add key_finding to summary
findings = []
for _, s in summary_df.iterrows():
    findings.append(compute_key_finding(s['scenario'], s['policy'], s))
summary_df['key_finding'] = findings

result_df.to_csv('M4_Scenario_Allocation_Result.csv', index=False)
summary_df.to_csv('M4_Scenario_Summary.csv', index=False)
impact_df.to_csv('M4_Supplier_Stress_Impact.csv', index=False)


# =====================================================================
# 9. REPORT
# =====================================================================
print('=' * 72)
print('  M4 RESILIENCE SCENARIO SIMULATION')
print('  Category: Key_Component  |  Baseline Demand: ${:,}'.format(BASELINE_DEMAND))
print('  Input files: M2_Strategic_Pool_View.csv, suppliers_data.csv')
print('               M3_Key_Category_Allocation_Result.csv')
print('  Scenarios: {}  |  Policies: {}'.format(len(SCENARIOS), len(POLICIES)))
print('=' * 72)

print('\n--- Baseline Pool ({} suppliers) ---'.format(N_SUPPLIERS_BASE))
for pool in ['Preferred', 'Core', 'Conditional', 'Restricted']:
    grp = kc[kc['pool'] == pool]
    parts = ', '.join('{}(cost={:.3f})'.format(r['supplier_id'], r['cost_index'])
                      for _, r in grp.iterrows())
    cap_total = int(grp['capacity'].sum())
    print('  {:<12s}: {}  (total capacity ${:,})'.format(pool, parts, cap_total))

for sc_name in SCENARIOS:
    print('\n{}'.format('=' * 72))
    print('  SCENARIO: {}'.format(sc_name))
    sc_summaries = summary_df[summary_df['scenario'] == sc_name]
    first = sc_summaries.iloc[0]
    print('  {}'.format(first['stress_reason'][:100] if 'stress_reason' in first else
                        first.get('key_finding', '')))
    print('=' * 72)

    for _, s in sc_summaries.iterrows():
        print('\n  {} | Demand=${:,}'.format(s['policy'], int(s['total_demand'])))
        print('  Alloc: ${:>9,d}  Unmet: ${:>9,d}  P={}% C={}% Cd={}% R={}%'
              .format(int(s['allocated_amount']), int(s['unmet_demand']),
                      s['preferred_share'], s['core_share'],
                      s['conditional_share'], s['restricted_share']))
        print('  Suppliers: {}  |  Wt cost: {:.4f}  |  Risk: {}'
              .format(int(s['supplier_count_used']),
                      s['weighted_cost_index'], s['risk_notes']))
        print('  Finding: {}'.format(s['key_finding']))

        # Detail
        pol_result = result_df[
            (result_df['scenario'] == sc_name) &
            (result_df['policy'] == s['policy']) &
            (result_df['allocation_after'] > 0)
        ].sort_values('allocation_after', ascending=False)
        for _, r in pol_result.iterrows():
            delta = r['allocation_change']
            delta_str = '+${:,.0f}'.format(delta) if delta > 0 else ('${:,.0f}'.format(delta) if delta < 0 else '$0')
            pool_chg = (' {}->{}'.format(r['pool_before'], r['pool_after'])
                        if r['pool_before'] != r['pool_after'] else '')
            print('    {:<3s} ({:<12s}){}: ${:>8,d} ({})'.format(
                r['supplier_id'], r['pool_after'], pool_chg,
                int(r['allocation_after']), delta_str))

    # Show non-allocated
    for _, s in sc_summaries.iterrows():
        zeros = result_df[
            (result_df['scenario'] == sc_name) &
            (result_df['policy'] == s['policy']) &
            (result_df['allocation_after'] == 0)
        ]
        if len(zeros) > 0:
            zlist = ', '.join('{} ({})'.format(r['supplier_id'], r['pool_after'])
                             for _, r in zeros.iterrows())
            print('    Not allocated [{}]: {}'.format(s['policy'], zlist))

print('\n--- Generated Files ---')
print('  M4_Scenario_Allocation_Result.csv')
print('  M4_Scenario_Summary.csv')
print('  M4_Supplier_Stress_Impact.csv')
print('=' * 72)
