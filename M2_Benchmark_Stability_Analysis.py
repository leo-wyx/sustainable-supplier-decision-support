# ==========================================
# M2_Benchmark_Stability_Analysis.py
#
# Validates the next-stage M2 Strategic Pool against
# the previous revised shortlist logic, and tests
# Strategic Pool stability under scenario variations.
#
# Part 1: Old-vs-New Benchmark
# Part 2: Pool Stability / Agility-Readiness Analysis
# Part 3: Summary Markdown
# ==========================================
import pandas as pd
import numpy as np
import os

# == Pool hierarchy for ordinal comparisons ==
POOL_ORDER = {
    'Preferred': 0,
    'Core': 1,
    'Conditional': 2,
    'Restricted': 3,
    'Not Priority': 4,
}

OLD_RECOMMENDED = {'Preferred shortlist', 'Shortlist with warning'}
NEW_RECOMMENDED = {'Preferred', 'Core'}


# ==========================================
# Part 1: Old-vs-New Benchmark
# ==========================================

def compute_benchmark(shortlist_csv='M2_Cost_ESG_Shortlist.csv',
                      pool_csv='M2_Strategic_Pool_View.csv',
                      diag_csv='M2_Supplier_Diagnostic_Profile.csv',
                      adj_cost_csv='M2_Adjusted_Cost_Index.csv',
                      esg_csv='M2_ESG_Strategic_Fit.csv'):
    """Compare old shortlist vs new Strategic Pool and produce overlap + migration outputs."""
    print(f"\n{'='*70}")
    print("Part 1: Old-vs-New Benchmark")
    print(f"{'='*70}")

    sl = pd.read_csv(shortlist_csv)
    pool = pd.read_csv(pool_csv)
    diag = pd.read_csv(diag_csv)
    adj = pd.read_csv(adj_cost_csv)
    esg_fit = pd.read_csv(esg_csv)

    # == Merge all sources into a single frame ==
    merged = sl[['supplier_id', 'supplier_name', 'category', 'M1_Status',
                 'shortlist_status', 'shortlist_reason']].copy()
    merged = merged.merge(
        pool[['supplier_id', 'Strategic_Pool', 'cost_quartile', 'ESG_Position_Tier',
              'risk_level', 'delivery_risk', 'T_capability_flag',
              'Q_quality_warning', 'C_cost_warning', 'Adjusted_Cost_Index']],
        on='supplier_id', how='left', suffixes=('', '_pool')
    )
    # Fill missing pool fields (should not happen)
    merged['Strategic_Pool'] = merged['Strategic_Pool'].fillna('Not Priority')
    merged['cost_quartile'] = merged['cost_quartile'].fillna('Q3')

    # == Old recommended set ==
    old_rec = merged[merged['shortlist_status'].isin(OLD_RECOMMENDED)]
    old_ids = set(old_rec['supplier_id'])

    # == New recommended set ==
    new_rec = merged[merged['Strategic_Pool'].isin(NEW_RECOMMENDED)]
    new_ids = set(new_rec['supplier_id'])

    overlap_ids = old_ids & new_ids
    only_old = old_ids - new_ids
    only_new = new_ids - old_ids

    print(f"  Old recommended count: {len(old_ids)}")
    print(f"  New recommended count: {len(new_ids)}")
    print(f"  Overlap count:         {len(overlap_ids)}")
    print(f"  Only in old:           {only_old}")
    print(f"  Only in new:           {only_new}")

    # == Build Overlap Report ==
    overlap_rate_old = round(len(overlap_ids) / len(old_ids) * 100, 1) if old_ids else 0
    overlap_rate_new = round(len(overlap_ids) / len(new_ids) * 100, 1) if new_ids else 0

    overlap_rows = []
    for sid in overlap_ids:
        row = merged[merged['supplier_id'] == sid].iloc[0]
        overlap_rows.append({
            'supplier_id': sid,
            'supplier_name': row['supplier_name'],
            'category': row['category'],
            'old_shortlist_status': row['shortlist_status'],
            'new_Strategic_Pool': row['Strategic_Pool'],
        })
    df_overlap = pd.DataFrame(overlap_rows)

    only_old_rows = []
    for sid in only_old:
        row = merged[merged['supplier_id'] == sid].iloc[0]
        only_old_rows.append({
            'supplier_id': sid,
            'supplier_name': row['supplier_name'],
            'category': row['category'],
            'old_shortlist_status': row['shortlist_status'],
            'new_Strategic_Pool': row['Strategic_Pool'],
        })
    df_only_old = pd.DataFrame(only_old_rows)

    only_new_rows = []
    for sid in only_new:
        row = merged[merged['supplier_id'] == sid].iloc[0]
        only_new_rows.append({
            'supplier_id': sid,
            'supplier_name': row['supplier_name'],
            'category': row['category'],
            'old_shortlist_status': row['shortlist_status'],
            'new_Strategic_Pool': row['Strategic_Pool'],
        })
    df_only_new = pd.DataFrame(only_new_rows)

    # Write overlap report
    with open('M2_Benchmark_Overlap_Report.csv', 'w', encoding='utf-8-sig') as f:
        f.write("Metric,Value\n")
        f.write(f"Old recommended count,{len(old_ids)}\n")
        f.write(f"New recommended count,{len(new_ids)}\n")
        f.write(f"Overlap count,{len(overlap_ids)}\n")
        f.write(f"Overlap rate (based on old),{overlap_rate_old}%\n")
        f.write(f"Overlap rate (based on new),{overlap_rate_new}%\n\n")
        f.write("Suppliers in overlap\n")
        if df_overlap.shape[0] > 0:
            df_overlap.to_csv(f, index=False)
        f.write("\nSuppliers only in old recommended\n")
        if df_only_old.shape[0] > 0:
            df_only_old.to_csv(f, index=False)
        else:
            f.write("supplier_id,supplier_name,category,old_shortlist_status,new_Strategic_Pool\n")
        f.write("\nSuppliers only in new recommended\n")
        if df_only_new.shape[0] > 0:
            df_only_new.to_csv(f, index=False)
        else:
            f.write("supplier_id,supplier_name,category,old_shortlist_status,new_Strategic_Pool\n")

    print(f"\n  => M2_Benchmark_Overlap_Report.csv saved")

    # == Build Migration Analysis ==
    def _determine_movement(row):
        old = str(row['shortlist_status'])
        new = str(row['Strategic_Pool'])
        m1 = str(row['M1_Status'])
        old_rec_flag = old in OLD_RECOMMENDED
        new_rec_flag = new in NEW_RECOMMENDED

        # M1 restricted
        if m1 != 'PASS':
            if old_rec_flag or new_rec_flag:
                return ('Restricted by M1', f'M1_Status={m1}; supplier restricted regardless of score')
            return ('Restricted by M1', f'M1_Status={m1}')

        # Stable recommended
        if old_rec_flag and new_rec_flag:
            return ('Stable recommended', 'Consistent recommendation across shortlist and Strategic Pool')

        # Stable non-recommended
        if not old_rec_flag and not new_rec_flag:
            return ('Stable non-recommended', 'Not recommended in either framework')

        # Upgraded
        if not old_rec_flag and new_rec_flag:
            # Determine why
            cost_q = str(row.get('cost_quartile', ''))
            esg_tier = str(row.get('ESG_Position_Tier', ''))
            reasons = []
            if cost_q in ('Q1_Best', 'Q2'):
                reasons.append(f'cost_quartile={cost_q}')
            if esg_tier in ('ESG Leader', 'ESG Compliant'):
                reasons.append(f'ESG tier={esg_tier}')
            diag_cnt = _count_diags(row)
            if diag_cnt == 0:
                reasons.append('no high diagnostic flags')
            reason_str = '; '.join(reasons) if reasons else 'Strategic Pool criteria match'
            return ('Upgraded', reason_str)

        # Downgraded
        if old_rec_flag and not new_rec_flag:
            cost_q = str(row.get('cost_quartile', ''))
            esg_tier = str(row.get('ESG_Position_Tier', ''))
            risk = str(row.get('risk_level', ''))
            delivery = str(row.get('delivery_risk', ''))
            diag_cnt = _count_diags(row)
            reasons = []
            if cost_q == 'Q4_Worst':
                reasons.append(f'cost_quartile={cost_q}')
            if esg_tier == 'ESG Monitor':
                reasons.append(f'ESG tier={esg_tier}')
            if risk == 'high':
                reasons.append(f'risk_level=High')
            if delivery == 'high':
                reasons.append('delivery_risk=High')
            if row.get('T_capability_flag') == 'Capability gap':
                reasons.append('capability gap')
            if str(row.get('Q_quality_warning', '')) != 'No quality concern':
                reasons.append('quality concern')
            if diag_cnt >= 2:
                reasons.append(f'{diag_cnt} high diagnostic flags')
            reason_str = '; '.join(reasons) if reasons else 'Does not meet Strategic Pool criteria'
            return ('Downgraded', reason_str)

        return ('Unclassified', 'Check individual supplier logic')

    def _count_diags(row):
        cnt = 0
        if str(row.get('risk_level', '')).lower() == 'high':
            cnt += 1
        if str(row.get('delivery_risk', '')).lower() == 'high':
            cnt += 1
        if str(row.get('T_capability_flag', '')) == 'Capability gap':
            cnt += 1
        q = str(row.get('Q_quality_warning', ''))
        if q not in ('', 'No quality concern'):
            cnt += 1
        return cnt

    movements = merged.apply(_determine_movement, axis=1)
    merged['movement_type'] = [m[0] for m in movements]
    merged['movement_reason'] = [m[1] for m in movements]

    migration_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                      'shortlist_status', 'Strategic_Pool',
                      'movement_type', 'movement_reason']
    migration = merged[migration_cols].sort_values(
        ['movement_type', 'category', 'supplier_id']
    ).reset_index(drop=True)
    migration.columns = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                         'old_shortlist_status', 'new_Strategic_Pool',
                         'movement_type', 'movement_reason']

    migration.to_csv('M2_Pool_Migration_Analysis.csv', index=False, encoding='utf-8-sig')

    print(f"  => M2_Pool_Migration_Analysis.csv saved ({len(migration)} suppliers)")
    print(f"  Movement type counts:")
    for mt in ['Stable recommended', 'Stable non-recommended', 'Upgraded',
               'Downgraded', 'Restricted by M1', 'Diagnostic escalation',
               'Cost-driven change', 'ESG-driven change']:
        cnt = (migration['movement_type'] == mt).sum()
        if cnt:
            print(f"    {mt}: {cnt}")

    return merged


# ==========================================
# Part 2: Pool Stability / Agility-Readiness
# ==========================================

def compute_pool_stability(pool_csv='M2_Strategic_Pool_View.csv',
                           esg_csv='M2_ESG_Strategic_Fit.csv',
                           diag_csv='M2_Supplier_Diagnostic_Profile.csv'):
    """Generate 5 scenario pool views and a stability report."""
    print(f"\n{'='*70}")
    print("Part 2: Pool Stability / Agility-Readiness Analysis")
    print(f"{'='*70}")

    pool = pd.read_csv(pool_csv).copy()
    esg_fit = pd.read_csv(esg_csv).copy()
    diag = pd.read_csv(diag_csv).copy()

    # Merge additional fields needed for scenarios
    df = pool.merge(
        esg_fit[['supplier_id', 'carbon_intensity', 'carbon_performance_level']],
        on='supplier_id', how='left'
    )
    # Ensure diagnostic fields are present
    for col in ['risk_level', 'delivery_risk']:
        if col not in df.columns:
            df = df.merge(diag[['supplier_id', col]], on='supplier_id', how='left')

    # Standardize
    df['risk_level'] = df['risk_level'].str.lower().str.strip()
    df['delivery_risk'] = df['delivery_risk'].str.lower().str.strip()

    # == Helper: downgrade one level ==
    def _downgrade(pool_val, restrict_if_none=False):
        """Move down one pool level. If already Restricted or lower, stay."""
        order = ['Preferred', 'Core', 'Conditional', 'Restricted', 'Not Priority']
        try:
            idx = order.index(pool_val)
        except ValueError:
            return pool_val
        if idx >= len(order) - 2:  # Restricted or Not Priority -> stay
            return pool_val
        return order[idx + 1]

    # == Scenario 1: Base (current) ==
    df['s1_base'] = df['Strategic_Pool']

    # == Scenario 2: Cost pressure ==
    # Suppliers with Q4_Worst cost are treated as at least Conditional
    def _cost_pressure(row):
        base = row['Strategic_Pool']
        q = str(row.get('cost_quartile', ''))
        if q == 'Q4_Worst':
            order = ['Preferred', 'Core', 'Conditional', 'Restricted', 'Not Priority']
            try:
                idx = order.index(base)
            except ValueError:
                return base
            # If currently Preferred or Core, drop to Conditional
            if idx <= 1:  # Preferred (0) or Core (1)
                return 'Conditional'
            # Otherwise stay as-is
        return base

    df['s2_cost'] = df.apply(_cost_pressure, axis=1)

    # == Scenario 3: Carbon pressure ==
    # High carbon intensity OR weak ESG tier -> downgrade one level if not Restricted
    def _carbon_pressure(row):
        base = row['Strategic_Pool']
        carb_perf = str(row.get('carbon_performance_level', '')).strip()
        esg_tier = str(row.get('ESG_Position_Tier', '')).strip()

        trigger = False
        if carb_perf == 'High':
            trigger = True
        if esg_tier in ('ESG Monitor', 'ESG Gap'):
            trigger = True

        if trigger:
            return _downgrade(base)
        return base

    df['s3_carbon'] = df.apply(_carbon_pressure, axis=1)

    # == Scenario 4: Risk-control ==
    # risk_level=High OR delivery_risk=High -> downgrade one level if not Restricted
    def _risk_control(row):
        base = row['Strategic_Pool']
        risk = str(row.get('risk_level', '')).lower().strip()
        delivery = str(row.get('delivery_risk', '')).lower().strip()

        if risk == 'high' or delivery == 'high':
            return _downgrade(base)
        return base

    df['s4_risk'] = df.apply(_risk_control, axis=1)

    # == Scenario 5: Strict ESG ==
    # ESG Monitor -> cannot be Preferred (downgrade to Core at highest)
    # ESG Gap -> Conditional or Restricted depending on diagnostics
    def _strict_esg(row):
        base = row['Strategic_Pool']
        esg_tier = str(row.get('ESG_Position_Tier', '')).strip()
        m1 = str(row.get('M1_Status', ''))

        if m1 != 'PASS':
            return 'Restricted'

        if esg_tier == 'ESG Monitor':
            # Cannot be Preferred; if Preferred, drop to Core
            if base == 'Preferred':
                return 'Core'
            return base

        if esg_tier == 'ESG Gap':
            # Count diagnostics
            cnt = 0
            if str(row.get('risk_level', '')).lower() == 'high':
                cnt += 1
            if str(row.get('delivery_risk', '')).lower() == 'high':
                cnt += 1
            if str(row.get('T_capability_flag', '')) == 'Capability gap':
                cnt += 1
            qw = str(row.get('Q_quality_warning', ''))
            if qw not in ('', 'No quality concern'):
                cnt += 1

            if cnt >= 2 or base == 'Restricted':
                return 'Restricted'
            return 'Conditional'

        return base

    df['s5_esg'] = df.apply(_strict_esg, axis=1)

    # == Compute stability metrics ==
    scenario_cols = ['s1_base', 's2_cost', 's3_carbon', 's4_risk', 's5_esg']

    def _preferred_core_count(row):
        return sum(1 for c in scenario_cols if str(row[c]) in NEW_RECOMMENDED)

    def _pool_change_count(row):
        base = row['s1_base']
        return sum(1 for c in scenario_cols[1:] if str(row[c]) != base)

    def _stability_label(row):
        pc = row['_preferred_core']
        changes = row['_pool_changes']

        # Sensitive: moves to Restricted from Preferred/Core in any scenario
        base = str(row['s1_base'])
        if base in NEW_RECOMMENDED:
            for c in scenario_cols:
                if str(row[c]) == 'Restricted':
                    return 'Sensitive'

        # Stable: no changes OR Preferred/Core in >= 4 scenarios
        if changes == 0 or pc >= 4:
            return 'Stable'

        # Moderate: Preferred/Core in 2-3 scenarios
        if pc >= 2:
            return 'Moderate'

        # Sensitive: Preferred/Core in 0-1
        return 'Sensitive'

    df['_preferred_core'] = df.apply(_preferred_core_count, axis=1)
    df['_pool_changes'] = df.apply(_pool_change_count, axis=1)
    df['stability_label'] = df.apply(_stability_label, axis=1)

    def _stability_comment(row):
        base = str(row['Strategic_Pool'])
        pc = row['_preferred_core']
        changes = row['_pool_changes']
        label = row['stability_label']

        if label == 'Stable':
            if changes == 0:
                return 'Unchanged across all 5 scenarios'
            return f'Preferred/Core in {pc}/5 scenarios; resilient to scenario shocks'
        elif label == 'Moderate':
            return f'Preferred/Core in {pc}/5 scenarios; vulnerable under {5-pc} scenario(s)'
        else:
            return f'Preferred/Core in only {pc}/5 scenarios; high sensitivity to scenario conditions'

    df['stability_comment'] = df.apply(_stability_comment, axis=1)

    # Build scenario columns for output
    df['base_pool'] = df['s1_base']
    df['cost_pressure_pool'] = df['s2_cost']
    df['carbon_pressure_pool'] = df['s3_carbon']
    df['risk_control_pool'] = df['s4_risk']
    df['strict_esg_pool'] = df['s5_esg']
    df['preferred_core_count'] = df['_preferred_core']
    df['pool_change_count'] = df['_pool_changes']

    out_cols = ['supplier_id', 'supplier_name', 'category',
                'base_pool', 'cost_pressure_pool', 'carbon_pressure_pool',
                'risk_control_pool', 'strict_esg_pool',
                'preferred_core_count', 'pool_change_count',
                'stability_label', 'stability_comment']

    stability = df[out_cols].sort_values(
        ['stability_label', 'category', 'supplier_id']
    ).reset_index(drop=True)

    stability.to_csv('M2_Pool_Stability_Report.csv', index=False, encoding='utf-8-sig')

    print(f"  => M2_Pool_Stability_Report.csv saved ({len(stability)} suppliers)")
    print(f"\n  Stability breakdown:")
    for lbl in ['Stable', 'Moderate', 'Sensitive']:
        cnt = (stability['stability_label'] == lbl).sum()
        pct = round(cnt / len(stability) * 100, 1)
        print(f"    {lbl}: {cnt} ({pct}%)")

    # Scenario pool composition
    print(f"\n  Scenario pool composition:")
    for alias, col in [('Base', 'base_pool'), ('Cost pressure', 'cost_pressure_pool'),
                       ('Carbon pressure', 'carbon_pressure_pool'),
                       ('Risk control', 'risk_control_pool'),
                       ('Strict ESG', 'strict_esg_pool')]:
        counts = stability[col].value_counts()
        print(f"    {alias}: Preferred={counts.get('Preferred',0)}, Core={counts.get('Core',0)}, "
              f"Conditional={counts.get('Conditional',0)}, Restricted={counts.get('Restricted',0)}")

    return stability


# ==========================================
# Part 3: Summary Markdown
# ==========================================

def generate_summary_md(benchmark_data, stability_data):
    """Write M2_Benchmark_Stability_Note.md."""
    print(f"\n{'='*70}")
    print("Part 3: Summary Markdown")
    print(f"{'='*70}")

    # Compute counts from benchmark
    sl = pd.read_csv('M2_Cost_ESG_Shortlist.csv')
    pool = pd.read_csv('M2_Strategic_Pool_View.csv')

    old_rec = sl[sl['shortlist_status'].isin(OLD_RECOMMENDED)]
    new_rec = pool[pool['Strategic_Pool'].isin(NEW_RECOMMENDED)]
    old_ids = set(old_rec['supplier_id'])
    new_ids = set(new_rec['supplier_id'])
    overlap_ids = old_ids & new_ids
    only_old = old_ids - new_ids
    only_new = new_ids - old_ids

    overlap_rate_old = round(len(overlap_ids) / len(old_ids) * 100, 1) if old_ids else 0
    overlap_rate_new = round(len(overlap_ids) / len(new_ids) * 100, 1) if new_ids else 0

    # Stability counts
    stable_cnt = (stability_data['stability_label'] == 'Stable').sum()
    moderate_cnt = (stability_data['stability_label'] == 'Moderate').sum()
    sensitive_cnt = (stability_data['stability_label'] == 'Sensitive').sum()
    total_sup = len(stability_data)

    # Migration type counts
    migration = pd.read_csv('M2_Pool_Migration_Analysis.csv')
    mig_counts = migration['movement_type'].value_counts()

    # Downgraded suppliers details
    downgraded = migration[migration['movement_type'] == 'Downgraded']
    upgraded = migration[migration['movement_type'] == 'Upgraded']

    markdown = f"""# M2 Pool Stability and Validation Note

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
| Stable | {stable_cnt} | {round(stable_cnt / total_sup * 100, 1)}% |
| Moderate | {moderate_cnt} | {round(moderate_cnt / total_sup * 100, 1)}% |
| Sensitive | {sensitive_cnt} | {round(sensitive_cnt / total_sup * 100, 1)}% |

"""
    # Scenario composition table
    markdown += "### Scenario pool composition\n\n"
    markdown += "| Scenario | Preferred | Core | Conditional | Restricted | Not Priority |\n"
    markdown += "|----------|-----------|------|-------------|------------|--------------|\n"
    for alias, col in [('Base', 'base_pool'), ('Cost pressure', 'cost_pressure_pool'),
                       ('Carbon pressure', 'carbon_pressure_pool'),
                       ('Risk control', 'risk_control_pool'),
                       ('Strict ESG', 'strict_esg_pool')]:
        counts = stability_data[col].value_counts()
        pref = counts.get('Preferred', 0)
        core = counts.get('Core', 0)
        cond = counts.get('Conditional', 0)
        restr = counts.get('Restricted', 0)
        np_cnt = counts.get('Not Priority', 0)
        markdown += f"| {alias} | {pref} | {core} | {cond} | {restr} | {np_cnt} |\n"

    # Sensitive suppliers detail
    sensitive = stability_data[stability_data['stability_label'] == 'Sensitive']
    if len(sensitive):
        markdown += f"\n### Non-recommended / scenario-vulnerable suppliers ({len(sensitive)})\n\n"
        markdown += "These suppliers are already below Preferred/Core in the base scenario or fail to reach the Preferred/Core threshold "
        markdown += "in most scenarios. They are non-recommended or scenario-vulnerable and may require closer monitoring:\n\n"
        for _, r in sensitive.iterrows():
            _base = r['base_pool']
            _pc = r['preferred_core_count']
            markdown += f"- {r['supplier_id']} ({r['supplier_name']})  -- base: {_base}, Preferred/Core in {_pc}/5 scenarios\n"

    # Build optional historical transition context (old-vs-new)
    hist_note_lines = []

    # Transition table
    hist_note_lines.append("| Metric | Value |")
    hist_note_lines.append("|--------|-------|")
    hist_note_lines.append(f"| Old recommended count (Preferred shortlist / Shortlist with warning) | {len(old_ids)} |")
    hist_note_lines.append(f"| New recommended count (Preferred / Core) | {len(new_ids)} |")
    hist_note_lines.append(f"| Overlap count | {len(overlap_ids)} |")
    hist_note_lines.append(f"| Overlap rate (based on old recommended set) | {overlap_rate_old}% |")
    hist_note_lines.append(f"| Overlap rate (based on new recommended set) | {overlap_rate_new}% |")

    hist_note_lines.append("")
    hist_note_lines.append("### Suppliers only in old recommended ({})".format(len(only_old)))
    for sid in sorted(only_old):
        r = old_rec[old_rec['supplier_id'] == sid]
        if len(r):
            hist_note_lines.append("- {} ({})  -- {}".format(sid, r.iloc[0]['supplier_name'], r.iloc[0]['shortlist_status']))

    hist_note_lines.append("")
    hist_note_lines.append("### Suppliers only in new recommended ({})".format(len(only_new)))
    for sid in sorted(only_new):
        r = new_rec[new_rec['supplier_id'] == sid]
        if len(r):
            hist_note_lines.append("- {} ({})  -- {}".format(sid, r.iloc[0]['supplier_name'], r.iloc[0]['Strategic_Pool']))

    hist_note_lines.append("")
    hist_note_lines.append("### Movement explanation")
    hist_note_lines.append("")
    hist_note_lines.append("Suppliers moved between old shortlist and new Strategic Pool for the following reasons:")
    hist_note_lines.append("")
    for mt in ['Stable recommended', 'Stable non-recommended', 'Upgraded', 'Downgraded', 'Restricted by M1']:
        cnt = mig_counts.get(mt, 0)
        hist_note_lines.append(f"- **{mt}**: {cnt} suppliers")

    if len(upgraded) > 0:
        hist_note_lines.append("")
        hist_note_lines.append("#### Upgraded suppliers ({})".format(len(upgraded)))
        hist_note_lines.append("")
        hist_note_lines.append("These suppliers were not in the old recommended set but qualify as Preferred or Core under the new Strategic Pool:")
        hist_note_lines.append("")
        for _, r in upgraded.iterrows():
            hist_note_lines.append("- {} ({})  -- old: {} -> new: {}. Reason: {}".format(
                r['supplier_id'], r['supplier_name'], r['old_shortlist_status'],
                r['new_Strategic_Pool'], r['movement_reason']))

    if len(downgraded) > 0:
        hist_note_lines.append("")
        hist_note_lines.append("#### Downgraded suppliers ({})".format(len(downgraded)))
        hist_note_lines.append("")
        hist_note_lines.append("These suppliers were in the old recommended set but fall to Conditional or below under the new Strategic Pool:")
        hist_note_lines.append("")
        for _, r in downgraded.iterrows():
            hist_note_lines.append("- {} ({})  -- old: {} -> new: {}. Reason: {}".format(
                r['supplier_id'], r['supplier_name'], r['old_shortlist_status'],
                r['new_Strategic_Pool'], r['movement_reason']))

    hist_note_lines.append("")
    hist_note_lines.append("#### Key movement drivers")
    hist_note_lines.append("")
    hist_note_lines.append("- **Adjusted cost outlier**: Suppliers with Q4_Worst cost quartile (e.g., S25, S24) are")
    hist_note_lines.append("  downgraded to Conditional regardless of ESG strength, reflecting cost pressure.")
    hist_note_lines.append("- **ESG tier separation**: ESG Monitor suppliers cannot reach Preferred, which affects")
    hist_note_lines.append("  suppliers with strong cost but moderate ESG credentials (e.g., S14, S13, S15 -> Core not Preferred).")
    hist_note_lines.append("- **Diagnostic escalation**: Suppliers with 2+ high diagnostic flags (risk, delivery,")
    hist_note_lines.append("  capability, quality) are Restricted, downgrading them from old shortlist status.")
    hist_note_lines.append("- **M1 restriction**: Any non-PASS M1 status (LIMITED_QUALITY_TECH, LIMITED_ETHICS)")
    hist_note_lines.append("  results in Restricted pool regardless of score-based performance.")

    hist_note = "\n".join(hist_note_lines)

    markdown += f"""

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

{hist_note}

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

*Generated by M2_Benchmark_Stability_Analysis.py on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*
"""
    os.makedirs('docs', exist_ok=True)
    with open('docs/M2_Benchmark_Stability_Note.md', 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"  => docs/M2_Benchmark_Stability_Note.md saved")
    return markdown


# ==========================================
# Main entry point
# ==========================================

if __name__ == '__main__':
    print("M2 Pool Stability and Validation Analysis")
    print("========================================\n")

    # Part 1
    benchmark = compute_benchmark()

    # Part 2
    stability = compute_pool_stability()

    # Part 3
    summary = generate_summary_md(benchmark, stability)

    print(f"\n{'='*70}")
    print("Analysis complete.")
    print(f"{'='*70}")
    print(f"  Generated files:")
    print(f"    M2_Benchmark_Overlap_Report.csv")
    print(f"    M2_Pool_Migration_Analysis.csv")
    print(f"    M2_Pool_Stability_Report.csv")
    print(f"    docs/M2_Benchmark_Stability_Note.md")
