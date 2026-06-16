# ==========================================
# Model2.py - M2 Strategic Scoring Engine
#
# Revised M2 headline flow:
#   Step 1: Cost-ESG Shortlist (Cost + ESG define the shortlist path)
#   Step 2: TQRDC Diagnostic Profile (TQRDC as diagnostic lens, not weighted score)
#   Step 3: Shortlist Stability (4 scenario views: management preference, not weight proof)
#
# Legacy outputs (behind RUN_LEGACY_M2=False):
#   - AHP dual-mode scoring
#   - Old 5-dimension ranking + radar charts
#   - Archived to archive/legacy_m2_outputs/
# ==========================================
from copy import deepcopy
import pandas as pd
import numpy as np
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
from strategy_config import M2_CONFIG, SUB_WEIGHTS
import os
import glob

# Synced with Model1, using dynamic year
CURRENT_YEAR = pd.Timestamp.today().year

# Gate for legacy outputs (AHP dual-mode, radar, old 5-dim ranking)
RUN_LEGACY_M2 = False


# ==========================================
# AHP Weight Calculation
# ==========================================
def calculate_ahp_weights(matrix, dimension_names=None):
    """Compute AHP eigenvector weights with consistency ratio validation.

    Args:
        matrix: NxN pairwise comparison matrix
        dimension_names: List of N dimension names (for display)

    Returns:
        weights: Normalized weight array
    """
    mat = np.array(matrix, dtype=float)
    n = mat.shape[0]
    eigenvalues, eigenvectors = np.linalg.eig(mat)
    max_idx = np.argmax(eigenvalues)
    lambda_max = np.real(eigenvalues[max_idx])
    weights = np.real(eigenvectors[:, max_idx])
    weights = weights / weights.sum()

    # Consistency ratio (CR)
    RI = {1: 0, 2: 0, 3: 0.58, 4: 0.9, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    ci = (lambda_max - n) / (n - 1)
    cr = ci / RI.get(n, 1.49)
    if cr < 0.1:
        cr_status = "OK"
    elif cr < 0.2:
        cr_status = "MARGINAL"
    else:
        cr_status = "FAIL"

    if dimension_names:
        print(f"    AHP Weights: " + " | ".join(
            f"{n}:{w:.1%}" for n, w in zip(dimension_names, weights)
        ))
        print(f"    Consistency: lambda_max={lambda_max:.3f}, CI={ci:.4f}, CR={cr:.4f} [{cr_status}]")

    return weights


# ==========================================
# Radar Chart Drawing
# ==========================================
def draw_radar_chart(df, title, filename=None, top_n=5):
    """Draw polar radar chart for Top N suppliers across 5 dimensions.

    Args:
        df: DataFrame with Cost_Score, ESG_Score, Risk_Score, LeadTime_Score, Tech_Score
        title: Chart title
        filename: Output path (None = auto-generate)
        top_n: Number of suppliers to plot

    Returns:
        filepath: PNG file path
    """
    categories = ['Cost', 'ESG', 'Risk', 'Lead Time', 'Tech']
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    colors = plt.get_cmap('tab10')(np.linspace(0, 0.5, top_n))

    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
    top_df = df.sort_values('Final_Score', ascending=False).head(top_n) if 'Final_Score' in df.columns else df.head(top_n)

    for i, (_, row) in enumerate(top_df.iterrows()):
        vals = [row[c] for c in score_cols]
        vals += vals[:1]
        label = f"{row.get('Supplier', row.get('supplier_name', f'S{i}'))} ({row['Final_Score']:.3f})" if 'Final_Score' in df.columns else f"{row.get('Supplier', row.get('supplier_name', f'S{i}'))}"
        ax.plot(angles, vals, color=colors[i], linewidth=2, label=label)
        ax.fill(angles, vals, color=colors[i], alpha=0.08)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8)
    ax.legend(bbox_to_anchor=(1.2, 1.05), loc='upper left', fontsize=10)
    ax.set_title(title, size=14, fontweight='bold', pad=20)
    plt.tight_layout()

    if filename is None:
        safe_title = title.replace(' ', '_').replace(':', '')[:40]
        filename = f"radar_{safe_title}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [Radar] Saved: {filename}")
    return filename


def generate_category_ranking_and_radar(scored_df, tier_df=None, save_csv=True, save_radar=True):
    """Generate category-level ranking tables and radar charts for procurement decisions.

    Does NOT re-score or re-rank. Uses existing Final_Score, Global_Rank, Category_Rank.

    Display rules per category:
      - Key_Component, Critical_Raw: Top 5 (or all if fewer)
      - General_Comp, General_Raw: Top 10 (or all if fewer)
      - Radar chart: Top 3 per category
      - Optional: Overall Top 5 radar

    When tier_df is provided, enriches CSVs with Strategic_Tier, M1_Status, Recommended_Action.

    Args:
        scored_df: DataFrame from run_m2_scoring with Final_Score and all dimension scores.
        tier_df: Optional DataFrame from run_m2_strategic_tiering with tier classification.
        save_csv: Whether to write category ranking CSV files.
        save_radar: Whether to generate and save radar chart PNGs.

    Returns:
        dict: {category_name: {ranking_df, radar_path}} for each category.
    """
    result = {}
    categories = scored_df['category'].unique()

    _display_top = {
        'Key_Component': 5,
        'Critical_Raw': 5,
        'General_Comp': 10,
        'General_Raw': 10,
    }

    _rank_cols = ['supplier_id', 'supplier_name', 'country', 'category',
                  'Strategic_Tier', 'M1_Status', 'Recommended_Action',
                  'Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score',
                  'Final_Score', 'Global_Rank', 'Category_Rank', 'Tier_Rationale']

    # Compute ranks from the full dataset (run_m2_scoring does not output rank columns)
    df = scored_df.copy()
    if 'Global_Rank' not in df.columns:
        df['Global_Rank'] = df['Final_Score'].rank(ascending=False, method='min').astype(int)
    if 'Category_Rank' not in df.columns:
        df['Category_Rank'] = df.groupby('category')['Final_Score'].rank(ascending=False, method='min').astype(int)

    # Merge tier data for CSV enrichment
    if tier_df is not None:
        _merge_cols = ['supplier_id']
        for col in ['Strategic_Tier', 'Recommended_Action', 'Tier_Rationale']:
            if col in tier_df.columns:
                _merge_cols.append(col)
        df = df.merge(tier_df[_merge_cols], on='supplier_id', how='left')

    # Reorder columns to match _rank_cols (keep only those present in df)
    _rank_cols = [c for c in _rank_cols if c in df.columns]

    # --- Category-level ranking tables ---
    for cat in categories:
        top_n = _display_top.get(cat, 10)
        cat_df = df[df['category'] == cat].sort_values('Final_Score', ascending=False)
        display_df = cat_df.head(top_n).reset_index(drop=True)

        out_cols = [c for c in _rank_cols if c in display_df.columns]
        result[cat] = {'ranking_df': display_df[out_cols]}

        if save_csv:
            safe_cat = cat.replace(' ', '_').replace('/', '_')
            csv_path = f'M2_Category_Ranking_{safe_cat}.csv'
            display_df[out_cols].to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"  [Category Ranking] {cat}: {len(display_df)} suppliers -> {csv_path}")

    # --- Category-level radar charts ---
    if save_radar:
        for cat in categories:
            cat_df = scored_df[scored_df['category'] == cat].sort_values('Final_Score', ascending=False)
            top3 = cat_df.head(min(3, len(cat_df)))
            if len(top3) == 0:
                continue
            safe_cat = cat.replace(' ', '_').replace('/', '_')
            radar_path = f'radar_m2_category_{safe_cat}.png'
            draw_radar_chart(top3, f"M2 Category: {cat} (Top 3)", filename=radar_path)
            result[cat]['radar_path'] = radar_path

        # --- Overall Top 5 radar (management overview) ---
        overall_top5 = scored_df.sort_values('Final_Score', ascending=False).head(5)
        overall_path = 'radar_m2_overall_top5.png'
        draw_radar_chart(overall_top5, "M2 Overall Top 5 Suppliers", filename=overall_path)
        result['_overall'] = {'radar_path': overall_path}

    return result


# ==========================================
# Helper Functions
# ==========================================
def _cert_level(cert):
    """Map certification type to technology level [1-5] (from config)."""
    if pd.isna(cert):
        return M2_CONFIG['CERT_LEVEL_DEFAULT']
    for keyword, level in M2_CONFIG['CERT_LEVEL_MAP'].items():
        if keyword in str(cert):
            return level
    return M2_CONFIG['CERT_LEVEL_DEFAULT']


# ==========================================
# Cost Sub-Indicators (C1, C2, C3)
# ==========================================
def _map_cost_indicators(df, carbon_tax=None):
    """Map cost sub-indicators to [1,5]; 1=lowest cost (best), 5=highest cost (worst).

    C1_Base_Cost_Proxy        — category-internal contract value percentile ranking
    C2_Transport_Landed_Proxy — country landed-cost tier (farther = more expensive)
    C3_Carbon_Cost_Proxy      — category-internal carbon intensity rank (incl. carbon tax)

    Note: carbon_tax is a uniform multiplier across all suppliers;
    the category-internal quintile rank is unaffected by uniform scaling.
    For carbon tax shock analysis, use the carbon_exposure_raw column.

    Legacy sub-indicators removed: C2(payment_terms), C3(cooperation_years), C5(assembly_value_add).
    """
    mapper = df.copy()

    # C1: Base Cost Proxy — category-internal contract value percentile rank
    mapper['C1'] = mapper.groupby('category')['annual_contract_value_usd'] \
        .transform(lambda x: pd.qcut(x.rank(method='first'), q=5,
                                     labels=[1, 2, 3, 4, 5]).astype(int))
    mapper['C1'] = mapper['C1'].fillna(3)

    # C2: Transport/Landed Proxy — country landed cost
    mapper['C2'] = mapper['country'].map(M2_CONFIG['REGION_COST_MAP']).fillna(3)

    # C3: Carbon Cost Proxy — category-internal carbon cost rank
    # Uses carbon_intensity x carbon_tax to simulate carbon cost, then ranks within category
    _carbon_tax = carbon_tax if carbon_tax is not None else M2_CONFIG['CARBON_TAX_PER_TON']
    mapper['_carbon_cost'] = mapper['carbon_intensity'].fillna(
        mapper.groupby('category')['carbon_intensity'].transform('median')
    ) * _carbon_tax

    # Output carbon exposure raw value for scenario use (unaffected by ranking)
    mapper['carbon_exposure_raw'] = mapper['_carbon_cost']

    def _rank_to_1_5(s):
        if s.nunique() <= 1:
            return pd.Series(3, index=s.index)
        ranks = s.rank(method='first')
        pct = (ranks - 1) / (len(ranks) - 1)
        return pd.cut(pct, bins=M2_CONFIG['RANK_PCT_BINS'],
                      labels=M2_CONFIG['RANK_PCT_LABELS']).astype(int)

    mapper['C3'] = mapper.groupby('category')['_carbon_cost'] \
        .transform(_rank_to_1_5).fillna(3).astype(int)
    mapper.drop(columns=['_carbon_cost'], inplace=True)

    return mapper


# ==========================================
# Risk Sub-Indicators (R1, R2, R3, R4)
# ==========================================
def _map_risk_indicators(df):
    """Map risk sub-indicators to [1,5]; higher = higher risk (worse).

    R1 Country_Risk_Proxy:          merged legacy supply disruption + geopolitical (avg)
    R2 Financial_Risk:              Altman Z-score bins
    R3 Quality_Risk:                defect_rate_ppm
    R4 Single_Source_Dependency:    sub_category supplier count (fewer = higher risk)

    Legacy R3(rating) removed — moved to Tech(T2).
    """
    mapper = df.copy()

    # R1: Country Risk Proxy — average of supply disruption + geopolitical
    mapper['R1'] = mapper['country'].map(M2_CONFIG['COUNTRY_RISK_MAP']).fillna(
        M2_CONFIG['COUNTRY_RISK_DEFAULT']
    )

    # R2: Financial Risk — Altman Z, lower Z = higher risk
    mapper['R2'] = pd.cut(mapper['altman_z_score'],
                          bins=M2_CONFIG['Z_SCORE_BINS'],
                          labels=M2_CONFIG['Z_SCORE_LABELS']).astype(int)

    # R3: Quality Risk — defect_rate_ppm, higher = higher risk
    mapper['R3'] = mapper['defect_rate_ppm'].fillna(mapper['defect_rate_ppm'].median())
    mapper['R3'] = pd.qcut(mapper['R3'].rank(method='first'),
                           q=5, labels=[1, 2, 3, 4, 5]).astype(int)

    # R4: Single Source Dependency — fewer sub_category suppliers = higher risk
    subcat_counts = mapper['sub_category'].map(mapper['sub_category'].value_counts())
    mapper['R4'] = pd.cut(subcat_counts,
                          bins=M2_CONFIG['SINGLE_SOURCE_BINS'],
                          labels=M2_CONFIG['SINGLE_SOURCE_LABELS']).astype(int)

    return mapper


# ==========================================
# LeadTime Sub-Indicators (L1, L2, L3)
# ==========================================
def _map_leadtime_indicators(df):
    """Map lead-time sub-indicators to [1,5]; higher = longer lead time (worse)."""
    mapper = df.copy()

    # L1: Target-capped lead time — inside target=1, >=3x target=5 capped
    lt_target = M2_CONFIG['LT_TARGET_DAYS']
    def _lt_score(row):
        target = lt_target.get(row['category'], 30)
        actual = row['lead_time_days']
        if pd.isna(actual):
            return 3
        ratio = actual / target
        if ratio <= 1.0:
            return 1
        elif ratio >= 3.0:
            return 5
        elif ratio <= 2.0:
            return round(1 + 2 * (ratio - 1.0))
        else:
            return round(3 + 2 * (ratio - 2.0))
    mapper['L1'] = mapper.apply(_lt_score, axis=1)

    # L2: Logistics complexity — EU perspective (from config lane groups)
    lane_groups = M2_CONFIG['EU_LANE_GROUPS']
    lane_default = M2_CONFIG['EU_LANE_DEFAULT']
    l2_map = M2_CONFIG['EU_LANE_L2_MAP']
    l2_default = M2_CONFIG['EU_LANE_L2_DEFAULT']

    def _get_lane_group(country):
        for group, countries in lane_groups.items():
            if country in countries:
                return group
        return lane_default

    mapper['_lane_group'] = mapper['country'].apply(_get_lane_group)
    mapper['L2'] = mapper['_lane_group'].map(l2_map).fillna(l2_default).astype(int)

    # L3: Customs complexity — EU perspective (from config lane groups)
    l4_map = M2_CONFIG['EU_LANE_L4_MAP']
    l4_default = M2_CONFIG['EU_LANE_L4_DEFAULT']
    mapper['L3'] = mapper['_lane_group'].map(l4_map).fillna(l4_default).astype(int)

    # Drop temporary working columns
    mapper.drop(columns=['_lane_group'], inplace=True)

    return mapper


# ==========================================
# Tech Sub-Indicators (T1, T2, T3, T4)
# ==========================================
def _map_tech_indicators(df):
    """Map tech sub-indicators to [1,5]; higher = stronger tech capability (better).

    T1 Certification_Level:           cert hierarchy (IATF=5 > ISO14001=4 > ISO9001=3 > other=1)
    T2 Supplier_Rating:               rating score (moved from legacy R3 to Tech for clarity)
    T3 Category_Technical_Complexity: category-level tech complexity from config
    T4 Specialization_Scarcity:       fewer peer suppliers in sub_category = scarcer

    Note: T4 and R4 share the same raw field (sub_category count) but differ in interpretation.
      R4: supply dependency risk (fewer = higher risk, same direction)
      T4: tech scarcity (fewer = scarcer/higher value, opposite direction)
      The scoring direction is handled by separate bin/label mappings.
    """
    mapper = df.copy()

    # T1: Certification Level — IATF=5, ISO14001=4, ISO9001=3, other=1
    mapper['T1'] = mapper['cert_type'].apply(_cert_level)

    # T2: Supplier Rating — higher rating = better (moved from legacy R3)
    mapper['T2'] = pd.cut(mapper['rating'],
                          bins=M2_CONFIG['RATING_BINS'],
                          labels=[1, 2, 3, 5]).astype(int)

    # T3: Category technical complexity (from config)
    mapper['T3'] = mapper['category'].map(M2_CONFIG['CAT_TECH_COMPLEXITY_MAP']).fillna(
        M2_CONFIG['CAT_TECH_COMPLEXITY_DEFAULT']
    )

    # T4: Specialization/Scarcity — fewer suppliers in sub_category = scarcer (higher tech value)
    # Direction opposite to R4: R4 scores few suppliers as high-risk(5), T4 scores them as high-value(5)
    subcat_counts = mapper['sub_category'].map(mapper['sub_category'].value_counts())
    mapper['T4'] = pd.cut(subcat_counts,
                          bins=M2_CONFIG['T4_SINGLE_SOURCE_BINS'],
                          labels=M2_CONFIG['T4_SINGLE_SOURCE_LABELS']).astype(int)

    return mapper


# ==========================================
# ESG Sub-Indicators (E1, E2, E3, E4)
# ==========================================
def _map_esg_indicators(df, current_year=None):
    """Map ESG sub-indicators to [1,5]; higher = stronger ESG performance (better).

    E1 Carbon_Intensity:          lower carbon_intensity = better
    E2 PCF_Commitment:            carbon footprint transparency, pcf_commitment=True
    E3 Certification_Compliance:  cert_type represents management system maturity
    E4 Labor_Governance:          country-based labor/governance proxy (merged E4+E8)

    Legacy removals:
      E6(community), E7(coop_years), E11(contract_value), E12(cert_type duplicate with T1).
      E13(CMRT), E14(PCF) retained as reference only, not in main scoring.
    """
    mapper = df.copy()

    # E1: Carbon Intensity — CO2 emission, lower is better
    ci_filled = mapper['carbon_intensity'].fillna(mapper['carbon_intensity'].median())
    mapper['E1'] = pd.qcut(ci_filled.rank(method='first'),
                           q=5, labels=[5, 4, 3, 2, 1]).astype(int)

    # E2: PCF Commitment — carbon footprint transparency
    mapper['E2'] = mapper['pcf_commitment'].astype(int) * 4
    mapper['E2'] = mapper['E2'].replace(0, 2)

    # E3: Certification / Compliance — cert_type management system maturity
    mapper['E3'] = mapper['cert_type'].apply(
        lambda c: M2_CONFIG['E5_IATF_SCORE']
        if pd.notna(c) and 'IATF' in str(c)
        else M2_CONFIG['E5_DEFAULT_SCORE']
    )
    # Fine-grained adjustment: IATF=5, ISO14001=4, ISO9001=3
    mapper['E3'] = mapper.apply(
        lambda r: 5 if (pd.notna(r['cert_type']) and 'IATF' in str(r['cert_type']))
        else (4 if (pd.notna(r['cert_type']) and '14001' in str(r['cert_type']))
              else (3 if (pd.notna(r['cert_type']) and '9001' in str(r['cert_type']))
                    else r['E3'])),
        axis=1
    )

    # E4: Labor & Governance — country-based proxy (merged E4 labor + E8 anti-corruption)
    mapper['E4'] = mapper['country'].map(M2_CONFIG['LABOR_GOV_MAP']).fillna(
        M2_CONFIG['LABOR_GOV_DEFAULT']
    )

    return mapper


# ==========================================
# Geographic Concentration Penalty
# ==========================================

def _apply_geo_penalty(df):
    """Check top 10 candidate concentration per category by region.

    If > DOMINANT_THRESHOLD of top 10 candidates per category come from the same Region,
    apply a -PENALTY_AMOUNT penalty to Risk_Score for all suppliers from that dominant region.

    Region groups (from M2_CONFIG.REGION_GROUPS):
      CN (China), MY (Malaysia), JP_KR (Japan/Korea), EU_OC (Germany/Australia/Chile), SEA_AF (Indonesia/South Africa/DRC)
    """
    # Build reverse map: country -> region_group
    region_map = {}
    for group, countries in M2_CONFIG['REGION_GROUPS'].items():
        for c in countries:
            region_map[c] = group
    dominant_threshold = M2_CONFIG['GEO_PENALTY_DOMINANT_THRESHOLD']
    penalty_amount = M2_CONFIG['GEO_PENALTY_AMOUNT']

    df = df.copy()
    df['Region'] = df['country'].map(region_map).fillna('ROW')

    for cat in df['category'].unique():
        mask = df['category'] == cat
        cat_df = df[mask].copy()

        cat_df['_prelim'] = (
            cat_df.get('Cost_Score', 0) +
            cat_df.get('ESG_Score', 0) +
            cat_df.get('Risk_Score', 0) +
            cat_df.get('LeadTime_Score', 0) +
            cat_df.get('Tech_Score', 0)
        ) / 5

        top_n = cat_df.sort_values('_prelim', ascending=False).head(10)
        if len(top_n) < 3:
            continue

        region_ratios = top_n['Region'].value_counts(normalize=True)
        dominant_region = region_ratios.index[0]
        dominant_pct = region_ratios.iloc[0]

        if dominant_pct > dominant_threshold:
            penalize_mask = mask & (df['Region'] == dominant_region)
            n_penalized = penalize_mask.sum()
            df.loc[penalize_mask, 'Risk_Score'] = (df.loc[penalize_mask, 'Risk_Score'] - penalty_amount).clip(0, 1)
            print(f"  [GeoPenalty] {cat}: {dominant_region} dominates top {len(top_n)} "
                  f"({dominant_pct:.0%}) → -{penalty_amount} Risk_Score for {n_penalized} suppliers")

    return df


# ==========================================
# 5-Dimension Scoring Pipeline
# ==========================================
def run_m2_scoring(df, carbon_tax=None, config_overrides=None,
                   sub_weights_override=None, save_subindicator_csv=True,
                   current_year=None):
    """Score M1-qualified suppliers across 5 dimensions.

    Scoring pipeline:
      1. Sub-indicator mapping (C1-C3, R1-R4, L1-L3, T1-T4, E1-E4)
      2. Weighted aggregation (weights from strategy_config.SUB_WEIGHTS, supports override)
      3. M1 soft penalty (LIMITED suppliers: Cost_Score / M1_Penalty)
      4. Geographic concentration penalty on Risk_Score
      5. Normalize 5-dimension scores to [0,1] (higher = better)

    Args:
        df: Supplier DataFrame (post-M1: PASS + LIMITED)
        carbon_tax: Carbon tax override (None = config default). Uniform scaling does not change rank-based C3 scores.
        config_overrides: Deep override for M2_CONFIG entries (e.g. {'CARBON_TAX_PER_TON': 200})
        sub_weights_override: SUB_WEIGHTS override for sensitivity analysis (e.g. {'Cost': {'C3_Carbon_Cost_Proxy': 0.30}})
        save_subindicator_csv: Save M2_SubIndicator_Scores.csv (False for sensitivity runs)
        current_year: Simulation year (None = system current year)

    Returns: scored_df
        Columns: ['supplier_id', 'supplier_name', 'country', 'category',
                  'Cost_Score', 'ESG_Score', 'Risk_Score',
                  'LeadTime_Score', 'Tech_Score']
    """
    df = df.copy()

    # Allow M4 injection — carbon_tax affects C3 carbon cost
    _carbon_tax = carbon_tax if carbon_tax is not None else M2_CONFIG['CARBON_TAX_PER_TON']

    # config_overrides: temporarily patch M2_CONFIG (try/finally ensures restore)
    _sentinel = object()
    _old_config_values = {}
    if config_overrides:
        for k, v in config_overrides.items():
            _old_config_values[k] = M2_CONFIG.get(k, _sentinel)
            M2_CONFIG[k] = v
    try:
        # sub_weights_override: scoped weight overrides, does not modify global SUB_WEIGHTS
        _sw = deepcopy(SUB_WEIGHTS)
        if sub_weights_override:
            for dim, overrides in sub_weights_override.items():
                if dim in _sw:
                    _sw[dim] = dict(_sw[dim])
                    _sw[dim].update(overrides)

        df = _map_cost_indicators(df, carbon_tax=_carbon_tax)
        df = _map_risk_indicators(df)
        df = _map_leadtime_indicators(df)
        df = _map_tech_indicators(df)
        df = _map_esg_indicators(df, current_year=current_year)

        # ========== 5-dimension weighted aggregation (weights from _sw, supports override) ==========
        def _weighted_score(row, cols, weights):
            """Weighted average, skips missing indicators."""
            total_w = 0.0
            score = 0.0
            for c, w in zip(cols, weights):
                v = row.get(c)
                if pd.notna(v):
                    score += v * w
                    total_w += w
            return score / total_w if total_w > 0 else 3.0

        sw = _sw  # Use _sw (may contain overrides; does not modify global SUB_WEIGHTS)

        # Cost: 5=most expensive (worst), reversed to [0,1]
        cost_cols = ['C1', 'C2', 'C3']
        cost_w = [sw['Cost']['C1_Base_Cost_Proxy'],
                  sw['Cost']['C2_Transport_Landed_Proxy'],
                  sw['Cost']['C3_Carbon_Cost_Proxy']]
        df['Cost_Score'] = df.apply(lambda r: (5 - _weighted_score(r, cost_cols, cost_w)) / 4, axis=1).clip(0, 1)

        # ESG: 5=best, positive direction to [0,1]
        esg_cols = ['E1', 'E2', 'E3', 'E4']
        esg_w = [sw['ESG']['E1_Carbon_Intensity'],
                 sw['ESG']['E2_PCF_Commitment'],
                 sw['ESG']['E3_Certification_Compliance'],
                 sw['ESG']['E4_Labor_Governance']]
        df['ESG_Score'] = df.apply(lambda r: (_weighted_score(r, esg_cols, esg_w) - 1) / 4, axis=1).clip(0, 1)

        # Risk: 5=highest risk (worst), reversed to [0,1]
        risk_cols = ['R1', 'R2', 'R3', 'R4']
        risk_w = [sw['Risk']['R1_Country_Risk'],
                  sw['Risk']['R2_Financial_Risk'],
                  sw['Risk']['R3_Quality_Risk'],
                  sw['Risk']['R4_Single_Source_Dependency']]
        df['Risk_Score'] = df.apply(lambda r: (5 - _weighted_score(r, risk_cols, risk_w)) / 4, axis=1).clip(0, 1)

        # LeadTime: 5=slowest (worst), reversed to [0,1]
        lt_cols = ['L1', 'L2', 'L3']
        lt_w = [sw['LeadTime']['L1_Target_Capped'],
                sw['LeadTime']['L2_Logistics_Complexity'],
                sw['LeadTime']['L3_Customs_Complexity']]
        df['LeadTime_Score'] = df.apply(lambda r: (5 - _weighted_score(r, lt_cols, lt_w)) / 4, axis=1).clip(0, 1)

        # Tech: 5=best, positive direction to [0,1]
        tech_cols = ['T1', 'T2', 'T3', 'T4']
        tech_w = [sw['Tech']['T1_Certification_Level'],
                  sw['Tech']['T2_Supplier_Rating'],
                  sw['Tech']['T3_Category_Complexity'],
                  sw['Tech']['T4_Specialization_Scarcity']]
        df['Tech_Score'] = df.apply(lambda r: (_weighted_score(r, tech_cols, tech_w) - 1) / 4, axis=1).clip(0, 1)

        # ========== Unified-direction sub-indicator display columns (5=best, 1=poor) ==========
        # Internal Cost/Risk/LeadTime: 1=best, 5=worst -> reverse for display
        # Internal ESG/Tech: 5=best, 1=worst -> keep as-is
        df['C1_Base_Cost_Proxy'] = 6 - df['C1']
        df['C2_Transport_Landed_Proxy'] = 6 - df['C2']
        df['C3_Carbon_Cost_Proxy'] = 6 - df['C3']
        df['E1_Carbon_Intensity'] = df['E1']
        df['E2_PCF_Commitment'] = df['E2']
        df['E3_Certification_Compliance'] = df['E3']
        df['E4_Labor_Governance'] = df['E4']
        df['R1_Country_Risk'] = 6 - df['R1']
        df['R2_Financial_Risk'] = 6 - df['R2']
        df['R3_Quality_Risk'] = 6 - df['R3']
        df['R4_Single_Source_Dependency'] = 6 - df['R4']
        df['L1_Target_Capped_LeadTime'] = 6 - df['L1']
        df['L2_EU_Logistics_Complexity'] = 6 - df['L2']
        df['L3_Customs_Complexity'] = 6 - df['L3']
        df['T1_Certification_Level'] = df['T1']
        df['T2_Supplier_Rating'] = df['T2']
        df['T3_Category_Technical_Complexity'] = df['T3']
        df['T4_Specialization_Scarcity'] = df['T4']

        # carbon_exposure_raw: raw carbon cost for external analysis (not part of scoring)
        if '_carbon_cost' in df.columns:
            df['carbon_exposure_raw'] = df['_carbon_cost']

        # ========== M1 soft penalty — LIMITED suppliers: Cost_Score / Penalty ==========
        if 'M1_Penalty' in df.columns:
            penalty_mask = df['M1_Penalty'].notna() & (df['M1_Penalty'] > 1.0)
            n_penalized = penalty_mask.sum()
            if n_penalized > 0:
                df['Cost_Score'] = (df['Cost_Score'] / df['M1_Penalty']).clip(0, 1)
                print(f"  [M1 Penalty] {n_penalized} LIMITED suppliers Cost_Score penalized "
                      f"(Quality/Tech: /1.15, Ethics: /1.40)")

        # ========== Geographic concentration penalty ==========
        df = _apply_geo_penalty(df)

        # Unified output (includes M1 decision fields for M3/dashboard use)
        out_cols = ['supplier_id', 'supplier_name', 'country', 'category',
                    'Cost_Score', 'ESG_Score', 'Risk_Score',
                    'LeadTime_Score', 'Tech_Score',
                    # Display-direction sub-indicators (5 = best)
                    'C1_Base_Cost_Proxy', 'C2_Transport_Landed_Proxy', 'C3_Carbon_Cost_Proxy',
                    'E1_Carbon_Intensity', 'E2_PCF_Commitment', 'E3_Certification_Compliance', 'E4_Labor_Governance',
                    'R1_Country_Risk', 'R2_Financial_Risk', 'R3_Quality_Risk', 'R4_Single_Source_Dependency',
                    'L1_Target_Capped_LeadTime', 'L2_EU_Logistics_Complexity', 'L3_Customs_Complexity',
                    'T1_Certification_Level', 'T2_Supplier_Rating', 'T3_Category_Technical_Complexity', 'T4_Specialization_Scarcity',
                    # Carbon exposure raw (for external carbon-cost analysis)
                    'carbon_exposure_raw',
                    ]
        m1_forward = ['M1_Status', 'M1_Penalty', 'M1_Capacity_Cap', 'M1_Is_Reserve',
                      'M1_Risk_Type', 'M1_Risk_Vector', 'M1_Risk_Exposure',
                      'M1_Penalty_Adjusted_Spend', 'M1_Decision_Reason']
        for col in m1_forward:
            if col in df.columns:
                out_cols.append(col)
        scored_df = df[out_cols].reset_index(drop=True)
        scored_df['Supplier'] = scored_df['supplier_name']

        # Save sub-indicator detail CSV (skip when False, e.g. sensitivity analysis calls)
        if save_subindicator_csv:
            # Ensure M1_Risk_Type / M1_Risk_Vector display as 'None' not NaN
            for _na_col in ['M1_Risk_Type', 'M1_Risk_Vector']:
                if _na_col in scored_df.columns:
                    scored_df[_na_col] = scored_df[_na_col].fillna('None').replace('', 'None')
            _csv_path = 'M2_SubIndicator_Scores.csv'
            scored_df.to_csv(_csv_path, index=False, encoding='utf-8-sig')
            print(f"  [M2] Sub-indicator scores saved -> {_csv_path}  "
                  f"({len(scored_df)} suppliers, {len(out_cols)} columns, "
                  f"18 display-direction sub-indicators + carbon_exposure_raw)")

        return scored_df

    finally:
        # Restore config_overrides to avoid polluting global M2_CONFIG
        for k, old_v in _old_config_values.items():
            if old_v is _sentinel:
                M2_CONFIG.pop(k, None)
            else:
                M2_CONFIG[k] = old_v


# ==========================================
# AHP dual-mode scoring
# ==========================================
def run_m2_dual_mode_scoring(df, esg_weight=0.25, carbon_tax=None, save_radar=True, scored_df=None):
    """AHP dual-mode scoring: Mode 1 (AHP baseline) vs Mode 2 (manual override).

    Pipeline:
      1. Run run_m2_scoring for 5-dimension base scores
      2. Mode 1: AHP matrix -> weights -> Final_Score -> Top 5 + radar
      3. Mode 2: Manual weights -> Final_Score -> Top 5 + radar
      4. Output dual-mode ranking comparison table

    Args:
        df: M1-qualified supplier DataFrame
        esg_weight: ESG weight ratio in manual mode (default 25%)
        carbon_tax: Carbon tax override (None = config default)
        save_radar: Save radar chart PNGs
        scored_df: Optional pre-computed scores, avoids re-running run_m2_scoring

    Returns:
        dict: {mode1_top5, mode2_top5, comparison}
    """
    scored = scored_df if scored_df is not None else run_m2_scoring(df, carbon_tax=carbon_tax, save_subindicator_csv=False)
    dims = ['Cost', 'ESG', 'Risk', 'LT', 'Tech']
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']

    print(f"\n{'='*60}")
    print(f"M2 Dual-Mode Strategic Scoring")
    print(f"{'='*60}")

    # --- Mode 1: AHP Scientific Baseline ---
    ahp_weights = calculate_ahp_weights(M2_CONFIG['AHP_MATRIX'], dims)
    m1 = scored.copy()
    m1['Final_Score'] = sum(m1[col] * w for col, w in zip(score_cols, ahp_weights))
    m1['Rank_Global_AHP'] = m1['Final_Score'].rank(ascending=False).astype(int)
    m1['Rank_Category_AHP'] = m1.groupby('category')['Final_Score'].rank(ascending=False).astype(int)
    m1_top5 = m1.sort_values('Final_Score', ascending=False).head(5).reset_index(drop=True)

    print(f"\n[MODE 1] AHP Scientific Baseline (ESG weight: {ahp_weights[1]:.1%})")
    print(f"{'Supplier':<20} {'Cost':>6} {'ESG':>6} {'Risk':>6} {'LT':>6} {'Tech':>6} {'Total':>8}")
    print("-" * 64)
    for _, r in m1_top5.iterrows():
        print(f"{r.get('Supplier', r.get('supplier_name', '')):<20} {r['Cost_Score']:>6.3f} {r['ESG_Score']:>6.3f} "
              f"{r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} {r['Tech_Score']:>6.3f} {r['Final_Score']:>8.3f}")

    # Category-internal Top 3 (CLI only)
    print(f"\n-- AHP Category Top 3 --")
    for cat in sorted(m1['category'].unique()):
        cat_top3 = m1[m1['category'] == cat].sort_values('Final_Score', ascending=False).head(3)
        print(f"  [{cat}]")
        for _, r in cat_top3.iterrows():
            supplier_name = r.get('Supplier', r.get('supplier_name', ''))
            print(f"    {supplier_name:<20} Score={r['Final_Score']:.3f}  CatRank={int(r['Rank_Category_AHP'])}  GlobalRank={int(r['Rank_Global_AHP'])}")

    if save_radar:
        draw_radar_chart(m1_top5, "M2 AHP Scientific Baseline - Top 5 Supplier Profile", filename="radar_m2_mode1_ahp.png")

    # --- Mode 2: Manual Strategic Override ---
    raw = list(M2_CONFIG['MANUAL_WEIGHTS_RAW'])  # deep copy — do not pollute global config
    # Adjust ESG weight: user can pass esg_weight to override config default
    esg_idx = 1  # ESG is second dimension
    total_no_esg = sum(raw) - raw[esg_idx]
    raw[esg_idx] = esg_weight * 100
    scale = (1 - esg_weight) * 100 / total_no_esg if total_no_esg > 0 else 0
    for i in range(len(raw)):
        if i != esg_idx:
            raw[i] = raw[i] * scale

    man_weights = np.array(raw, dtype=float) / sum(raw)
    print(f"\n[MODE 2] Manual Strategic Override Weights:")
    print(f"    " + " | ".join(f"{d}:{w:.1%}" for d, w in zip(dims, man_weights)))

    m2 = scored.copy()
    m2['Final_Score'] = sum(m2[col] * w for col, w in zip(score_cols, man_weights))
    m2['Rank_Global_Manual'] = m2['Final_Score'].rank(ascending=False).astype(int)
    m2['Rank_Category_Manual'] = m2.groupby('category')['Final_Score'].rank(ascending=False).astype(int)
    m2_top5 = m2.sort_values('Final_Score', ascending=False).head(5).reset_index(drop=True)

    print(f"\n{'Supplier':<20} {'Cost':>6} {'ESG':>6} {'Risk':>6} {'LT':>6} {'Tech':>6} {'Total':>8}")
    print("-" * 64)
    for _, r in m2_top5.iterrows():
        print(f"{r.get('Supplier', r.get('supplier_name', '')):<20} {r['Cost_Score']:>6.3f} {r['ESG_Score']:>6.3f} "
              f"{r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} {r['Tech_Score']:>6.3f} {r['Final_Score']:>8.3f}")

    # Category-internal Top 3 (CLI only)
    print(f"\n-- Manual Category Top 3 --")
    for cat in sorted(m2['category'].unique()):
        cat_top3 = m2[m2['category'] == cat].sort_values('Final_Score', ascending=False).head(3)
        print(f"  [{cat}]")
        for _, r in cat_top3.iterrows():
            supplier_name = r.get('Supplier', r.get('supplier_name', ''))
            print(f"    {supplier_name:<20} Score={r['Final_Score']:.3f}  CatRank={int(r['Rank_Category_Manual'])}  GlobalRank={int(r['Rank_Global_Manual'])}")

    if save_radar:
        draw_radar_chart(m2_top5, "M2 Manual Override - Top 5 Supplier Profile", filename="radar_m2_mode2_manual.png")

    # --- Dual-Mode Ranking Comparison ---
    print(f"\n{'='*60}")
    print(f"Dual-Mode Ranking Change (AHP -> Manual)")
    print(f"{'='*60}")
    merged = m1[['Supplier', 'Rank_Global_AHP']].merge(
        m2[['Supplier', 'Rank_Global_Manual']], on='Supplier')
    merged['Rank_Change'] = merged['Rank_Global_Manual'] - merged['Rank_Global_AHP']
    merged = merged.sort_values('Rank_Global_AHP').head(10)

    print(f"{'Supplier':<20} {'AHP Rank':>8} {'Manual Rank':>10} {'Change':>6}")
    print("-" * 48)
    for _, r in merged.iterrows():
        arrow = " ↑" if r['Rank_Change'] < 0 else (" ↓" if r['Rank_Change'] > 0 else " —")
        print(f"{r['Supplier']:<20} {int(r['Rank_Global_AHP']):>8d} {int(r['Rank_Global_Manual']):>10d} "
              f"{int(r['Rank_Change']):+d}{arrow}")

    return {
        'mode1_top5': m1_top5,
        'mode2_top5': m2_top5,
        'comparison': merged,
    }


# ==========================================
# ESG weight scan
# ==========================================
def run_m2_esg_scan(df, esg_weights=(0.25, 0.15, 0.05), carbon_tax=None, scored_df=None):
    """ESG weight scan: compare Top 5 suppliers under different ESG weight scenarios.

    Args:
        df: M1-qualified supplier list
        esg_weights: Three ESG weight scenarios to test
        carbon_tax: Carbon tax override (None = config default)

    Returns:
        dict: {esg_weight: top5_df, ...}
    """
    dims = ['Cost', 'ESG', 'Risk', 'LT', 'Tech']
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']

    # One run_m2_scoring call to get 5-dimension scores
    scored = scored_df if scored_df is not None else run_m2_scoring(df, carbon_tax=carbon_tax, save_subindicator_csv=False)

    results = {}
    print(f"\n{'='*70}")
    print(f"ESG Weight Sensitivity Scan")
    print(f"{'='*70}")

    for esg_w in esg_weights:
        # Build weights: ESG = esg_w, remaining 4 dimensions split evenly (1-esg_w)/4
        other_w = (1 - esg_w) / 4
        weights = [other_w, esg_w, other_w, other_w, other_w]
        label = f"ESG={esg_w:.0%}"

        s = scored.copy()
        s['Final_Score'] = sum(s[col] * w for col, w in zip(score_cols, weights))
        top5 = s.sort_values('Final_Score', ascending=False).head(5).reset_index(drop=True)
        results[esg_w] = top5

        print(f"\n{label}")
        print(f"{'Supplier':<20} {'Cost':>6} {'ESG':>6} {'Risk':>6} {'LT':>6} {'Tech':>6} {'Total':>8}")
        print("-" * 64)
        for _, r in top5.iterrows():
            print(f"{r.get('Supplier', r.get('supplier_name', '')):<20} {r['Cost_Score']:>6.3f} {r['ESG_Score']:>6.3f} "
                  f"{r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} {r['Tech_Score']:>6.3f} {r['Final_Score']:>8.3f}")

    # --- Cross-scenario comparison ---
    print(f"\n{'='*70}")
    print(f"Cross-Scenario Top 5 Comparison")
    print(f"{'='*70}")
    all_suppliers = set()
    for w, top5 in results.items():
        for _, r in top5.iterrows():
            all_suppliers.add(r.get('Supplier', r.get('supplier_name', '')))

    # Each supplier's rank in each scenario
    rank_data = {}
    for w, top5 in results.items():
        top5['_rank'] = range(1, 6)
        for _, r in top5.iterrows():
            sup = r.get('Supplier', r.get('supplier_name', ''))
            if sup not in rank_data:
                rank_data[sup] = {}
            rank_data[sup][f"ESG{w:.0%}"] = r['_rank']

    rank_df = pd.DataFrame.from_dict(rank_data, orient='index')
    rank_df = rank_df.fillna(999)  # 999 = not in top 5, sorted last
    rank_df = rank_df.sort_values([f"ESG{w:.0%}" for w in esg_weights])

    # Display: convert 999 back to '-'
    _display = rank_df.replace(999, '-')
    print(f"\n{'Supplier':<20}", end="")
    for w in esg_weights:
        print(f" {'ESG'+f'{w:.0%}':>8}", end="")
    print()
    print("-" * 48)
    for sup, row in _display.iterrows():
        print(f"{sup:<20}", end="")
        for w in esg_weights:
            v = row[f"ESG{w:.0%}"]
            print(f" {str(v):>8}", end="")
        print()

    return results


# ==========================================
# Cost Internal Weight Sensitivity Analysis
# ==========================================
def run_m2_cost_weight_sensitivity(df, scored_baseline=None):
    """Cost internal weight sensitivity analysis.

    Tests 5 sub-indicator weight combinations within Cost dimension.
    Validates that the Baseline_TCO weight selection is stable.

    All scenarios share the same final strategic weights:
      Balanced: Cost 0.25, ESG 0.25, Risk 0.20, LeadTime 0.15, Tech 0.15

    Args:
        df: M1-qualified supplier list
        scored_baseline: Reserved; not used (each scenario re-scores)

    Outputs:
        M2_TCO_Scenario_Scores.csv — 5 scenarios x N suppliers (long format)
        M2_TCO_Sensitivity_Report.csv — per-supplier rank stability summary
    """
    # Final strategic dimension weights (Balanced)
    FINAL_DIM_WEIGHTS = {
        'Cost': 0.25,
        'ESG': 0.25,
        'Risk': 0.20,
        'LeadTime': 0.15,
        'Tech': 0.15,
    }
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
    dim_order = ['Cost', 'ESG', 'Risk', 'LeadTime', 'Tech']
    dim_weights = [FINAL_DIM_WEIGHTS[d] for d in dim_order]

    # 5 Cost sub-indicator weight scenarios
    scenarios = {
        'Baseline_TCO': {
            'C1_Base_Cost_Proxy': 0.60,
            'C2_Transport_Landed_Proxy': 0.25,
            'C3_Carbon_Cost_Proxy': 0.15,
        },
        'Base_Heavy': {
            'C1_Base_Cost_Proxy': 0.70,
            'C2_Transport_Landed_Proxy': 0.20,
            'C3_Carbon_Cost_Proxy': 0.10,
        },
        'Logistics_Heavy': {
            'C1_Base_Cost_Proxy': 0.55,
            'C2_Transport_Landed_Proxy': 0.35,
            'C3_Carbon_Cost_Proxy': 0.10,
        },
        'Carbon_Heavy': {
            'C1_Base_Cost_Proxy': 0.50,
            'C2_Transport_Landed_Proxy': 0.20,
            'C3_Carbon_Cost_Proxy': 0.30,
        },
        'Balanced_Equal': {
            'C1_Base_Cost_Proxy': 0.34,
            'C2_Transport_Landed_Proxy': 0.33,
            'C3_Carbon_Cost_Proxy': 0.33,
        },
    }

    all_records = []
    scenario_results = {}

    print(f"\n{'='*70}")
    print(f"Cost Internal Weight Sensitivity Analysis")
    print(f"{'='*70}")
    print(f"\nFive-dimension final weights (Balanced Strategic):")
    for d, w in zip(dim_order, dim_weights):
        print(f"  {d}: {w:.0%}")

    for scenario_name, cost_weights in scenarios.items():
        print(f"\n{'─'*60}")
        print(f"Scenario: {scenario_name}")
        print(f"  Cost sub-weights: C1={cost_weights['C1_Base_Cost_Proxy']:.2f}, "
              f"C2={cost_weights['C2_Transport_Landed_Proxy']:.2f}, "
              f"C3={cost_weights['C3_Carbon_Cost_Proxy']:.2f}")

        sub_override = {'Cost': cost_weights}
        s = run_m2_scoring(df, sub_weights_override=sub_override, save_subindicator_csv=False)

        # Compute Final_Score with uniform five-dimension weights
        s['Final_Score'] = sum(s[col] * w for col, w in zip(score_cols, dim_weights))
        s['Global_Rank'] = s['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Category_Rank'] = s.groupby('category')['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Scenario'] = scenario_name

        scenario_results[scenario_name] = s

        # Collect long-format records
        for _, r in s.iterrows():
            all_records.append({
                'supplier_id': r['supplier_id'],
                'supplier_name': r['supplier_name'],
                'country': r['country'],
                'category': r['category'],
                'Scenario': scenario_name,
                'Cost_Score': r['Cost_Score'],
                'ESG_Score': r['ESG_Score'],
                'Risk_Score': r['Risk_Score'],
                'LeadTime_Score': r['LeadTime_Score'],
                'Tech_Score': r['Tech_Score'],
                'Final_Score': r['Final_Score'],
                'Global_Rank': int(r['Global_Rank']),
                'Category_Rank': int(r['Category_Rank']),
            })

        # Print Top 10
        top10 = s.sort_values('Final_Score', ascending=False).head(10)
        print(f"\n  Top 10:")
        print(f"  {'Rank':>4} {'Supplier':<20} {'Cost':>6} {'ESG':>6} "
              f"{'Risk':>6} {'LT':>6} {'Tech':>6} {'Final':>7}")
        print(f"  {'─'*4} {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*7}")
        for _, r in top10.iterrows():
            print(f"  {int(r['Global_Rank']):>4d} {r['supplier_name']:<20} {r['Cost_Score']:>6.3f} "
                  f"{r['ESG_Score']:>6.3f} {r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} "
                  f"{r['Tech_Score']:>6.3f} {r['Final_Score']:>7.3f}")

    # Save long-format scenario scores
    scenario_df = pd.DataFrame(all_records)
    scenario_df.to_csv('M2_TCO_Scenario_Scores.csv', index=False, encoding='utf-8-sig')
    print(f"\n=> M2_TCO_Scenario_Scores.csv saved ({len(scenario_df)} rows)")

    # ─── Cross-scenario Top 10 overlap ───
    baseline_top10 = set(
        scenario_results['Baseline_TCO'].sort_values('Final_Score', ascending=False)
        .head(10)['supplier_id']
    )

    print(f"\n{'='*70}")
    print(f"Cross-scenario Top 10 overlap analysis (vs Baseline_TCO)")
    print(f"{'='*70}")
    for name, s in scenario_results.items():
        top10_ids = set(s.sort_values('Final_Score', ascending=False).head(10)['supplier_id'])
        overlap = baseline_top10 & top10_ids
        print(f"  {name:<20} Overlap with Baseline Top10: {len(overlap):>2}/10")

    # ─── Sensitivity report ───
    sensitivity_records = []
    baseline_scores = scenario_results['Baseline_TCO']

    for _, r in baseline_scores.iterrows():
        sid = r['supplier_id']
        ranks = []
        cost_scores = []
        top10_count = 0

        for name, s in scenario_results.items():
            row = s[s['supplier_id'] == sid].iloc[0]
            gr = int(row['Global_Rank'])
            ranks.append(gr)
            cost_scores.append(row['Cost_Score'])
            if gr <= 10:
                top10_count += 1

        sensitivity_records.append({
            'supplier_id': sid,
            'supplier_name': r['supplier_name'],
            'country': r['country'],
            'category': r['category'],
            'Baseline_Rank': int(baseline_scores[baseline_scores['supplier_id'] == sid]['Global_Rank'].iloc[0]),
            'Best_Rank': min(ranks),
            'Worst_Rank': max(ranks),
            'Rank_Range': max(ranks) - min(ranks),
            'Rank_Std': round(float(np.std(ranks)), 2),
            'Baseline_Cost_Score': round(cost_scores[0], 4),
            'Min_Cost_Score': round(min(cost_scores), 4),
            'Max_Cost_Score': round(max(cost_scores), 4),
            'Cost_Score_Range': round(max(cost_scores) - min(cost_scores), 4),
            'Scenario_Count_Top10': top10_count,
        })

    sensitivity_df = pd.DataFrame(sensitivity_records)

    # Stability_Label
    def _stability_label(row):
        if row['Rank_Range'] <= 3:
            return 'Stable'
        elif row['Rank_Range'] <= 8:
            return 'Moderate'
        else:
            return 'Sensitive'

    sensitivity_df['Stability_Label'] = sensitivity_df.apply(_stability_label, axis=1)
    sensitivity_df = sensitivity_df.sort_values('Rank_Range', ascending=False).reset_index(drop=True)
    sensitivity_df.to_csv('M2_TCO_Sensitivity_Report.csv', index=False, encoding='utf-8-sig')
    print(f"  => M2_TCO_Sensitivity_Report.csv saved ({len(sensitivity_df)} rows)")

    # ─── Most sensitive suppliers ───
    print(f"\n{'='*70}")
    print(f"Most sensitive suppliers (Rank_Range Top 10)")
    print(f"{'='*70}")
    print(f"  {'Supplier':<20} {'Category':<15} {'BaseRank':>8} {'Best':>4} "
          f"{'Worst':>5} {'Range':>5} {'Std':>4} {'Label':<10}")
    print(f"  {'─'*20} {'─'*15} {'─'*8} {'─'*4} {'─'*5} {'─'*5} {'─'*4} {'─'*10}")
    for _, r in sensitivity_df.head(10).iterrows():
        print(f"  {r['supplier_name']:<20} {r['category']:<15} {int(r['Baseline_Rank']):>8d} "
              f"{int(r['Best_Rank']):>4d} {int(r['Worst_Rank']):>5d} {int(r['Rank_Range']):>5d} "
              f"{r['Rank_Std']:>4.1f} {r['Stability_Label']:<10}")

    # ─── Stability distribution ───
    print(f"\n  ── Stability Distribution ──")
    stab_counts = sensitivity_df['Stability_Label'].value_counts()
    total = len(sensitivity_df)
    for label in ['Stable', 'Moderate', 'Sensitive']:
        c = stab_counts.get(label, 0)
        pct = c / total * 100
        print(f"    {label:<10}: {c:>2}/{total} ({pct:.0f}%)")

    return scenario_df, sensitivity_df


# ==========================================
# ESG internal weight sensitivity analysis
# ==========================================
def run_m2_esg_internal_sensitivity(df, scored_baseline=None):
    """ESG internal weight sensitivity analysis

    Tests 5 ESG sub-indicator weight combinations to validate Baseline_ESG weight stability.
    ESG is a core dimension for EU market targeting; stability evidence required.

    All scenarios share the same 5-dimension final weights:
      Balanced strategic weights:
        Cost 0.25, ESG 0.25, Risk 0.20, LeadTime 0.15, Tech 0.15

    Args:
        df: M1-qualified supplier list
        scored_baseline: Reserved parameter, currently unused (each scenario re-scores)

    Outputs:
        M2_ESG_Scenario_Scores.csv — 5 scenarios × N suppliers long-format scores
        M2_ESG_Sensitivity_Report.csv — per-supplier rank sensitivity summary
    """
    # Five-dimension final weights (Balanced strategic weights)
    FINAL_DIM_WEIGHTS = {
        'Cost': 0.25,
        'ESG': 0.25,
        'Risk': 0.20,
        'LeadTime': 0.15,
        'Tech': 0.15,
    }
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
    dim_order = ['Cost', 'ESG', 'Risk', 'LeadTime', 'Tech']
    dim_weights = [FINAL_DIM_WEIGHTS[d] for d in dim_order]

    # 5 ESG sub-indicator weight scenarios
    scenarios = {
        'Baseline_ESG': {
            'E1_Carbon_Intensity': 0.35,
            'E2_PCF_Commitment': 0.25,
            'E3_Certification_Compliance': 0.20,
            'E4_Labor_Governance': 0.20,
        },
        'Carbon_Performance_Heavy': {
            'E1_Carbon_Intensity': 0.50,
            'E2_PCF_Commitment': 0.25,
            'E3_Certification_Compliance': 0.15,
            'E4_Labor_Governance': 0.10,
        },
        'Disclosure_Heavy': {
            'E1_Carbon_Intensity': 0.25,
            'E2_PCF_Commitment': 0.40,
            'E3_Certification_Compliance': 0.20,
            'E4_Labor_Governance': 0.15,
        },
        'Compliance_Governance_Heavy': {
            'E1_Carbon_Intensity': 0.25,
            'E2_PCF_Commitment': 0.20,
            'E3_Certification_Compliance': 0.30,
            'E4_Labor_Governance': 0.25,
        },
        'Balanced_Equal_ESG': {
            'E1_Carbon_Intensity': 0.25,
            'E2_PCF_Commitment': 0.25,
            'E3_Certification_Compliance': 0.25,
            'E4_Labor_Governance': 0.25,
        },
    }

    all_records = []
    scenario_results = {}

    print(f"\n{'='*70}")
    print(f"ESG Internal Weight Sensitivity Analysis")
    print(f"{'='*70}")
    print(f"\nFive-dimension final weights (Balanced Strategic):")
    for d, w in zip(dim_order, dim_weights):
        print(f"  {d}: {w:.0%}")

    for scenario_name, esg_weights in scenarios.items():
        print(f"\n{'─'*60}")
        print(f"Scenario: {scenario_name}")
        w_parts = [f"E{i}={list(esg_weights.values())[i-1]:.2f}" for i in range(1, 5)]
        print(f"  ESG sub-weights: {' | '.join(w_parts)}")

        sub_override = {'ESG': esg_weights}
        s = run_m2_scoring(df, sub_weights_override=sub_override, save_subindicator_csv=False)

        # Compute Final_Score with uniform five-dimension weights
        s['Final_Score'] = sum(s[col] * w for col, w in zip(score_cols, dim_weights))
        s['Global_Rank'] = s['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Category_Rank'] = s.groupby('category')['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Scenario'] = scenario_name

        scenario_results[scenario_name] = s

        # Collect long-format records
        for _, r in s.iterrows():
            all_records.append({
                'supplier_id': r['supplier_id'],
                'supplier_name': r['supplier_name'],
                'country': r['country'],
                'category': r['category'],
                'Scenario': scenario_name,
                'Cost_Score': r['Cost_Score'],
                'ESG_Score': r['ESG_Score'],
                'Risk_Score': r['Risk_Score'],
                'LeadTime_Score': r['LeadTime_Score'],
                'Tech_Score': r['Tech_Score'],
                'Final_Score': r['Final_Score'],
                'Global_Rank': int(r['Global_Rank']),
                'Category_Rank': int(r['Category_Rank']),
            })

        # Print Top 10
        top10 = s.sort_values('Final_Score', ascending=False).head(10)
        print(f"\n  Top 10:")
        print(f"  {'Rank':>4} {'Supplier':<20} {'Cost':>6} {'ESG':>6} "
              f"{'Risk':>6} {'LT':>6} {'Tech':>6} {'Final':>7}")
        print(f"  {'─'*4} {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*7}")
        for _, r in top10.iterrows():
            print(f"  {int(r['Global_Rank']):>4d} {r['supplier_name']:<20} {r['Cost_Score']:>6.3f} "
                  f"{r['ESG_Score']:>6.3f} {r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} "
                  f"{r['Tech_Score']:>6.3f} {r['Final_Score']:>7.3f}")

    # Save long-format scenario scores
    scenario_df = pd.DataFrame(all_records)
    scenario_df.to_csv('M2_ESG_Scenario_Scores.csv', index=False, encoding='utf-8-sig')
    print(f"\n=> M2_ESG_Scenario_Scores.csv saved ({len(scenario_df)} rows)")

    # ─── Cross-scenario Top 10 overlap ───
    baseline_top10 = set(
        scenario_results['Baseline_ESG'].sort_values('Final_Score', ascending=False)
        .head(10)['supplier_id']
    )

    print(f"\n{'='*70}")
    print(f"Cross-scenario Top 10 overlap analysis (vs Baseline_ESG)")
    print(f"{'='*70}")
    for name, s in scenario_results.items():
        top10_ids = set(s.sort_values('Final_Score', ascending=False).head(10)['supplier_id'])
        overlap = baseline_top10 & top10_ids
        print(f"  {name:<28} Overlap with Baseline Top10: {len(overlap):>2}/10")

    # ─── Sensitivity report ───
    sensitivity_records = []
    baseline_scores = scenario_results['Baseline_ESG']

    for _, r in baseline_scores.iterrows():
        sid = r['supplier_id']
        ranks = []
        esg_scores = []
        top10_count = 0

        for name, s in scenario_results.items():
            row = s[s['supplier_id'] == sid].iloc[0]
            gr = int(row['Global_Rank'])
            ranks.append(gr)
            esg_scores.append(row['ESG_Score'])
            if gr <= 10:
                top10_count += 1

        sensitivity_records.append({
            'supplier_id': sid,
            'supplier_name': r['supplier_name'],
            'country': r['country'],
            'category': r['category'],
            'Baseline_Rank': int(baseline_scores[baseline_scores['supplier_id'] == sid]['Global_Rank'].iloc[0]),
            'Best_Rank': min(ranks),
            'Worst_Rank': max(ranks),
            'Rank_Range': max(ranks) - min(ranks),
            'Rank_Std': round(float(np.std(ranks)), 2),
            'Baseline_ESG_Score': round(esg_scores[0], 4),
            'Min_ESG_Score': round(min(esg_scores), 4),
            'Max_ESG_Score': round(max(esg_scores), 4),
            'ESG_Score_Range': round(max(esg_scores) - min(esg_scores), 4),
            'Scenario_Count_Top10': top10_count,
        })

    sensitivity_df = pd.DataFrame(sensitivity_records)

    # Stability_Label
    def _stability_label(row):
        if row['Rank_Range'] <= 3:
            return 'Stable'
        elif row['Rank_Range'] <= 8:
            return 'Moderate'
        else:
            return 'Sensitive'

    sensitivity_df['Stability_Label'] = sensitivity_df.apply(_stability_label, axis=1)
    sensitivity_df = sensitivity_df.sort_values('Rank_Range', ascending=False).reset_index(drop=True)
    sensitivity_df.to_csv('M2_ESG_Sensitivity_Report.csv', index=False, encoding='utf-8-sig')
    print(f"  => M2_ESG_Sensitivity_Report.csv saved ({len(sensitivity_df)} rows)")

    # ─── Most sensitive suppliers ───
    print(f"\n{'='*70}")
    print(f"Most sensitive suppliers (Rank_Range Top 10)")
    print(f"{'='*70}")
    print(f"  {'Supplier':<20} {'Category':<15} {'BaseRank':>8} {'Best':>4} "
          f"{'Worst':>5} {'Range':>5} {'Std':>4} {'Label':<10}")
    print(f"  {'─'*20} {'─'*15} {'─'*8} {'─'*4} {'─'*5} {'─'*5} {'─'*4} {'─'*10}")
    for _, r in sensitivity_df.head(10).iterrows():
        print(f"  {r['supplier_name']:<20} {r['category']:<15} {int(r['Baseline_Rank']):>8d} "
              f"{int(r['Best_Rank']):>4d} {int(r['Worst_Rank']):>5d} {int(r['Rank_Range']):>5d} "
              f"{r['Rank_Std']:>4.1f} {r['Stability_Label']:<10}")

    # ─── Stability distribution ───
    print(f"\n  ── Stability Distribution ──")
    stab_counts = sensitivity_df['Stability_Label'].value_counts()
    total = len(sensitivity_df)
    for label in ['Stable', 'Moderate', 'Sensitive']:
        c = stab_counts.get(label, 0)
        pct = c / total * 100
        print(f"    {label:<10}: {c:>2}/{total} ({pct:.0f}%)")

    return scenario_df, sensitivity_df


# ==========================================
# Five-dimension strategic weight sensitivity analysis
# ==========================================
def run_m2_strategic_weight_sensitivity(df, scored_baseline=None):
    """Five-dimension strategic weight sensitivity analysis

    Tests 5 Final_Score strategic weight combinations to validate Balanced_Strategy
    weight stability. Responds to the requirement that weights must be justified
    through stability testing, not subjective assignment.

    Note: All scenarios share the same M2 sub-indicator scores (run_m2_scoring once),
    only five-dimension weights vary, sub-indicator weights are fixed.

    Args:
        df: M1-qualified supplier list
        scored_baseline: Optional, pre-computed score DataFrame to avoid re-computation

    Outputs:
        M2_Strategic_Scenario_Scores.csv — 5 scenarios × N suppliers long-format scores
        M2_Strategic_Sensitivity_Report.csv — per-supplier rank sensitivity summary
    """
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
    dim_order = ['Cost', 'ESG', 'Risk', 'LeadTime', 'Tech']

    # 5 strategic weight scenarios
    scenarios = {
        'Balanced_Strategy': [0.25, 0.25, 0.20, 0.15, 0.15],
        'Cost_Driven':       [0.40, 0.20, 0.15, 0.15, 0.10],
        'ESG_Driven':        [0.20, 0.40, 0.20, 0.10, 0.10],
        'Risk_Resilient':    [0.20, 0.20, 0.35, 0.15, 0.10],
        'Tech_Driven':       [0.20, 0.20, 0.15, 0.10, 0.35],
    }

    # Single scoring pass, shared across all scenarios
    base_scored = run_m2_scoring(df, save_subindicator_csv=False)

    all_records = []
    scenario_results = {}

    if RUN_LEGACY_M2:
        print(f"\n{'='*70}")
        print(f"Five-Dimension Strategic Weight Sensitivity Analysis")
        print(f"{'='*70}")

    for scenario_name, weights in scenarios.items():
        s = base_scored.copy()
        s['Final_Score'] = sum(s[col] * w for col, w in zip(score_cols, weights))
        s['Global_Rank'] = s['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Category_Rank'] = s.groupby('category')['Final_Score'].rank(ascending=False, method='min').astype(int)
        s['Scenario'] = scenario_name
        scenario_results[scenario_name] = s

        # Collect long-format records
        for _, r in s.iterrows():
            all_records.append({
                'supplier_id': r['supplier_id'],
                'supplier_name': r['supplier_name'],
                'country': r['country'],
                'category': r['category'],
                'Scenario': scenario_name,
                'Cost_Score': r['Cost_Score'],
                'ESG_Score': r['ESG_Score'],
                'Risk_Score': r['Risk_Score'],
                'LeadTime_Score': r['LeadTime_Score'],
                'Tech_Score': r['Tech_Score'],
                'Final_Score': r['Final_Score'],
                'Global_Rank': int(r['Global_Rank']),
                'Category_Rank': int(r['Category_Rank']),
            })

        # Print weights and Top 10
        if RUN_LEGACY_M2:
            print(f"\n{'─'*60}")
            w_str = ' | '.join(f"{d}={w:.2f}" for d, w in zip(dim_order, weights))
            print(f"Scenario: {scenario_name} — {w_str}")

            top10 = s.sort_values('Final_Score', ascending=False).head(10)
            print(f"\n  Top 10:")
            print(f"  {'Rank':>4} {'Supplier':<20} {'Cost':>6} {'ESG':>6} "
                  f"{'Risk':>6} {'LT':>6} {'Tech':>6} {'Final':>7}")
            print(f"  {'─'*4} {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*7}")
            for _, r in top10.iterrows():
                print(f"  {int(r['Global_Rank']):>4d} {r['supplier_name']:<20} {r['Cost_Score']:>6.3f} "
                      f"{r['ESG_Score']:>6.3f} {r['Risk_Score']:>6.3f} {r['LeadTime_Score']:>6.3f} "
                      f"{r['Tech_Score']:>6.3f} {r['Final_Score']:>7.3f}")

    # Save long-format scenario scores (always computed for tier input)
    scenario_df = pd.DataFrame(all_records)
    scenario_df = pd.DataFrame(all_records)
    if RUN_LEGACY_M2:
        scenario_df.to_csv('M2_Strategic_Scenario_Scores.csv', index=False, encoding='utf-8-sig')
        print(f"\n=> M2_Strategic_Scenario_Scores.csv saved ({len(scenario_df)} rows)")

    # ─── Cross-scenario Top 10 overlap ───
    if RUN_LEGACY_M2:
        baseline_top10_ids = set(
            scenario_results['Balanced_Strategy'].sort_values('Final_Score', ascending=False)
            .head(10)['supplier_id']
        )
        baseline_top10_names = set(
            scenario_results['Balanced_Strategy'].sort_values('Final_Score', ascending=False)
            .head(10)['supplier_name']
        )

        print(f"\n{'='*70}")
        print(f"Cross-scenario Top 10 overlap analysis (vs Balanced_Strategy)")
        print(f"{'='*70}")
        for name, s in scenario_results.items():
            top10_ids = set(s.sort_values('Final_Score', ascending=False).head(10)['supplier_id'])
            overlap = baseline_top10_ids & top10_ids
            print(f"  {name:<22} Overlap with Baseline Top10: {len(overlap):>2}/10")

    # ─── Sensitivity report ───
    sensitivity_records = []
    baseline_scores = scenario_results['Balanced_Strategy']

    for _, r in baseline_scores.iterrows():
        sid = r['supplier_id']
        ranks = []
        top10_count = 0

        for name, s in scenario_results.items():
            row = s[s['supplier_id'] == sid].iloc[0]
            gr = int(row['Global_Rank'])
            ranks.append(gr)
            if gr <= 10:
                top10_count += 1

        sensitivity_records.append({
            'supplier_id': sid,
            'supplier_name': r['supplier_name'],
            'country': r['country'],
            'category': r['category'],
            'Baseline_Rank': int(baseline_scores[baseline_scores['supplier_id'] == sid]['Global_Rank'].iloc[0]),
            'Best_Rank': min(ranks),
            'Worst_Rank': max(ranks),
            'Rank_Range': max(ranks) - min(ranks),
            'Rank_Std': round(float(np.std(ranks)), 2),
            'Scenario_Count_Top10': top10_count,
        })

    sensitivity_df = pd.DataFrame(sensitivity_records)

    def _stability_label(row):
        if row['Rank_Range'] <= 3:
            return 'Stable'
        elif row['Rank_Range'] <= 8:
            return 'Moderate'
        else:
            return 'Sensitive'

    sensitivity_df['Stability_Label'] = sensitivity_df.apply(_stability_label, axis=1)
    sensitivity_df = sensitivity_df.sort_values('Rank_Range', ascending=False).reset_index(drop=True)
    if RUN_LEGACY_M2:
        sensitivity_df.to_csv('M2_Strategic_Sensitivity_Report.csv', index=False, encoding='utf-8-sig')
        print(f"  => M2_Strategic_Sensitivity_Report.csv saved ({len(sensitivity_df)} rows)")

    if RUN_LEGACY_M2:
        # ─── Most sensitive suppliers ───
        print(f"\n{'='*70}")
        print(f"Most sensitive suppliers (Rank_Range Top 10)")
        print(f"{'='*70}")
        print(f"  {'Supplier':<20} {'Category':<15} {'BaseRank':>8} {'Best':>4} "
              f"{'Worst':>5} {'Range':>5} {'Std':>4} {'Label':<10}")
        print(f"  {'─'*20} {'─'*15} {'─'*8} {'─'*4} {'─'*5} {'─'*5} {'─'*4} {'─'*10}")
        for _, r in sensitivity_df.head(10).iterrows():
            print(f"  {r['supplier_name']:<20} {r['category']:<15} {int(r['Baseline_Rank']):>8d} "
                  f"{int(r['Best_Rank']):>4d} {int(r['Worst_Rank']):>5d} {int(r['Rank_Range']):>5d} "
                  f"{r['Rank_Std']:>4.1f} {r['Stability_Label']:<10}")

        # ─── Stability distribution ───
        print(f"\n  ── Stability Distribution ──")
        stab_counts = sensitivity_df['Stability_Label'].value_counts()
        total = len(sensitivity_df)
        for label in ['Stable', 'Moderate', 'Sensitive']:
            c = stab_counts.get(label, 0)
            pct = c / total * 100
            print(f"    {label:<10}: {c:>2}/{total} ({pct:.0f}%)")

        # ─── Deep insights ───
        print(f"\n{'='*70}")
        print(f"Strategic Sensitivity Insights")
        print(f"{'='*70}")

        # Always Top 10: supplier appears in Global Top 10 across all 5 scenarios
        always_top10 = []
        for _, r in baseline_scores.iterrows():
            sid = r['supplier_id']
            in_all = True
            for name, s in scenario_results.items():
                row = s[s['supplier_id'] == sid]
                if row.empty or int(row['Global_Rank'].iloc[0]) > 10:
                    in_all = False
                    break
            if in_all:
                always_top10.append(r['supplier_name'])

        print(f"\n  Always Top 10 (supplier ranks top 10 in all strategic scenarios):")
        if always_top10:
            for sup in always_top10:
                print(f"    [+] {sup}")
        else:
            print(f"    (None)")

        # Scenario-dependent: appears in Top 10 only in certain strategic scenarios
        print(f"\n  Scenario-dependent suppliers (appears in Top 10 only in specific strategic scenarios):")
        all_in_top10 = {}
        for name, s in scenario_results.items():
            for _, r in s.sort_values('Final_Score', ascending=False).head(10).iterrows():
                sid = r['supplier_id']
                if sid not in all_in_top10:
                    all_in_top10[sid] = {'name': r['supplier_name'], 'scenarios': []}
                all_in_top10[sid]['scenarios'].append(name)

        for sid, info in sorted(all_in_top10.items(), key=lambda x: len(x[1]['scenarios'])):
            scenario_set = set(info['scenarios'])
            if 0 < len(scenario_set) < 5:
                print(f"    {info['name']:<20} -> {sorted(scenario_set)}")

        # Strategic-sensitive: Rank_Range > 8
        print(f"\n  Strategic-sensitive suppliers (Rank_Range > 8):")
        sensitive_suppliers = sensitivity_df[sensitivity_df['Stability_Label'] == 'Sensitive']
        if len(sensitive_suppliers) > 0:
            for _, r in sensitive_suppliers.iterrows():
                print(f"    [!]  {r['supplier_name']:<20} "
                      f"Baseline={int(r['Baseline_Rank']):>2d}  "
                      f"Range={int(r['Rank_Range']):>2d}")
        else:
            print(f"    (None)")

    return scenario_df, sensitivity_df


# ==========================================
# Strategic Supplier Tier classification
# ==========================================
def run_m2_strategic_tiering(df, scored_baseline=None, strategic_report=None):
    """Strategic supplier tier classification based on sensitivity analysis

    5 tiers (evaluated highest priority first, first-match wins):
      1. Restricted Supplier — conditional/capped allocation (M1 gate/score floor)
      2. Strategic Preferred — high performer (strong scores + stable + cross-scenario)
      3. Core Supplier — reliable backbone suppliers
      4. Capability Watchlist — potential with identified weaknesses
      5. Backup Supplier — lowest priority PASS suppliers

    Args:
        df: M1-qualified supplier list
        scored_baseline: run_m2_scoring() output (5-dim scores + M1 fields)
        strategic_report: sensitivity_df from run_m2_strategic_weight_sensitivity()

    Outputs:
        M2_Strategic_Tier.csv — 25-column full tier table (Strategic_Tier, Tier_Rationale, Recommended_Action)
        return tier_df
    """
    # Load scoring baseline + strategic sensitivity report
    scored = run_m2_scoring(df, save_subindicator_csv=False) if scored_baseline is None else scored_baseline.copy()
    _, sensitivity_df = run_m2_strategic_weight_sensitivity(df) if strategic_report is None else (None, strategic_report.copy())

    # Compute Balanced_Strategy Final_Score
    score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
    weights = [0.25, 0.25, 0.20, 0.15, 0.15]
    scored['Final_Score'] = sum(scored[col] * w for col, w in zip(score_cols, weights))
    scored['Baseline_Rank'] = scored['Final_Score'].rank(ascending=False, method='min').astype(int)

    # Merge sensitivity indicators
    sens_cols = ['supplier_id', 'Best_Rank', 'Worst_Rank',
                 'Rank_Range', 'Rank_Std', 'Scenario_Count_Top10', 'Stability_Label']
    sens_merge = sensitivity_df[sens_cols].copy()
    tier_df = scored.merge(sens_merge, on='supplier_id', how='left')

    # ─── Tier assignment (highest priority first, first-match wins) ───
    tier_map = {}
    dims_5 = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']

    for _, r in tier_df.iterrows():
        sid = r['supplier_id']
        rank = int(r['Baseline_Rank'])
        sc_top10 = int(r['Scenario_Count_Top10']) if pd.notna(r['Scenario_Count_Top10']) else 0
        stab = str(r['Stability_Label']) if pd.notna(r['Stability_Label']) else 'Unknown'
        m1_status = str(r.get('M1_Status', ''))
        m1_penalty = float(r.get('M1_Penalty', 1.0))
        esg = float(r['ESG_Score'])
        risk = float(r['Risk_Score'])
        cost = float(r['Cost_Score'])
        lt = float(r['LeadTime_Score'])
        tech = float(r['Tech_Score'])
        final = float(r['Final_Score'])

        # ── Priority 1: Restricted Supplier ──
        # Any non-PASS M1 status → Restricted
        if m1_status != 'PASS':
            tier_map[sid] = (1, 'Restricted Supplier',
                f"M1 conditional status: {m1_status}; restricted use due to qualification gate limitation",
                "Restricted use only / capped allocation / remediation required")
            continue

        # M1_Penalty > 1.0
        if m1_penalty > 1.0:
            tier_map[sid] = (1, 'Restricted Supplier',
                "M1 penalty > 1.0; capped or conditional allocation required",
                "Restricted use only / capped allocation / remediation required")
            continue

        # ESG_Score < 0.35
        if esg < 0.35:
            tier_map[sid] = (1, 'Restricted Supplier',
                "Low ESG score below threshold",
                "Restricted use only / capped allocation / remediation required")
            continue

        # Risk_Score < 0.30
        if risk < 0.30:
            tier_map[sid] = (1, 'Restricted Supplier',
                "Low risk resilience score below threshold",
                "Restricted use only / capped allocation / remediation required")
            continue

        # Final_Score < 0.45
        if final < 0.45:
            tier_map[sid] = (1, 'Restricted Supplier',
                "Low overall strategic score below threshold",
                "Restricted use only / capped allocation / remediation required")
            continue

        # ── Priority 2: Strategic Preferred ──
        sp_ok = True
        sp_ok = sp_ok and (sc_top10 >= 4)
        sp_ok = sp_ok and (stab in ('Stable', 'Moderate'))
        sp_ok = sp_ok and (esg >= 0.70)
        sp_ok = sp_ok and (risk >= 0.65)
        sp_ok = sp_ok and (tech >= 0.75)
        sp_ok = sp_ok and (final >= 0.65 or rank <= 8)
        sp_ok = sp_ok and all(r[d] >= 0.40 for d in dims_5)

        if sp_ok:
            tier_map[sid] = (2, 'Strategic Preferred',
                f"High performer: Rank={rank}, Final={final:.3f}, "
                f"Top10={sc_top10}/5, ESG={esg:.2f}, Risk={risk:.2f}, Tech={tech:.2f}",
                "Long-term partnership / preferred sourcing")
            continue

        # ── Priority 3: Core Supplier ──
        core_ok = True
        core_ok = core_ok and (final >= 0.58 or rank <= 15)
        core_ok = core_ok and (stab in ('Stable', 'Moderate'))
        core_ok = core_ok and (risk >= 0.50)
        core_ok = core_ok and (lt >= 0.60)

        if core_ok:
            tier_map[sid] = (3, 'Core Supplier',
                f"Solid performer: Rank={rank}, Final={final:.3f}, "
                f"Risk={risk:.2f}, LeadTime={lt:.2f}",
                "Main sourcing candidate")
            continue

        # ── Priority 4: Capability Watchlist ──
        watch_ok = True
        watch_ok = watch_ok and (tech >= 0.75 or sc_top10 >= 1)
        watch_ok = watch_ok and (final >= 0.50)
        # Must have at least one weakness
        has_weakness = (cost < 0.45 or esg < 0.55 or risk < 0.55 or stab == 'Sensitive')
        watch_ok = watch_ok and has_weakness

        if watch_ok:
            # Identify specific weaknesses
            weakness_parts = []
            if cost < 0.45:
                weakness_parts.append(f"Cost={cost:.2f}")
            if esg < 0.55:
                weakness_parts.append(f"ESG={esg:.2f}")
            if risk < 0.55:
                weakness_parts.append(f"Risk={risk:.2f}")
            if stab == 'Sensitive':
                weakness_parts.append(f"Stability=Sensitive(range={int(r['Rank_Range'])})")
            weakness_str = '; '.join(weakness_parts)
            tier_map[sid] = (4, 'Capability Watchlist',
                f"Potential with gaps: Rank={rank}, Final={final:.3f}, Weakness: {weakness_str}",
                "Develop capability / monitor risk / limited trial")
            continue

        # ── Priority 5: Backup Supplier (remaining PASS) ──
        tier_map[sid] = (5, 'Backup Supplier',
            f"Lowest priority PASS: Rank={rank}, Final={final:.3f}",
            "Backup allocation / resilience buffer")

    # ─── Assign to DataFrame ───
    tier_df['Priority'] = tier_df['supplier_id'].map(lambda x: tier_map[x][0])
    tier_df['Strategic_Tier'] = tier_df['supplier_id'].map(lambda x: tier_map[x][1])
    tier_df['Tier_Rationale'] = tier_df['supplier_id'].map(lambda x: tier_map[x][2])
    tier_df['Recommended_Action'] = tier_df['supplier_id'].map(lambda x: tier_map[x][3])
    # Compat alias for legacy field names
    tier_df['Tier'] = tier_df['Strategic_Tier']
    tier_df['Tier_Assignment_Reason'] = tier_df['Tier_Rationale']

    tier_df = tier_df.sort_values(['Priority', 'Final_Score'],
                                  ascending=[True, False]).reset_index(drop=True)

    # ─── Output CSV (25+ cols) ───
    out_cols = ['supplier_id', 'supplier_name', 'country', 'category',
                'Strategic_Tier', 'Tier', 'Priority',
                'Baseline_Rank', 'Best_Rank', 'Worst_Rank', 'Rank_Range',
                'Stability_Label', 'Scenario_Count_Top10',
                'Cost_Score', 'ESG_Score', 'Risk_Score',
                'LeadTime_Score', 'Tech_Score', 'Final_Score',
                'M1_Status', 'M1_Penalty', 'M1_Decision_Reason',
                'Tier_Rationale', 'Tier_Assignment_Reason', 'Recommended_Action']
    available_cols = [c for c in out_cols if c in tier_df.columns]
    output_df = tier_df[available_cols]
    if RUN_LEGACY_M2:
        output_df.to_csv('M2_Strategic_Tier.csv', index=False, encoding='utf-8-sig')
    print(f"\n{'='*70}")
    print(f"Strategic Supplier Tier Classification")
    print(f"{'='*70}")
    if RUN_LEGACY_M2:
        print(f"  => M2_Strategic_Tier.csv saved ({len(output_df)} rows, {len(available_cols)} cols)")
    else:
        print(f"  => Tier classification computed in memory for revised M2; CSV gated behind RUN_LEGACY_M2=True")

    # ─── Tier count distribution ───
    tier_order = ['Restricted Supplier', 'Strategic Preferred', 'Core Supplier',
                  'Capability Watchlist', 'Backup Supplier']
    print(f"\n{'─'*50}")
    print(f"Tier Count Distribution")
    print(f"{'─'*50}")
    for t in tier_order:
        c = len(tier_df[tier_df['Strategic_Tier'] == t])
        print(f"  {t:<30}: {c} supplier(s)")

    # ─── Strategic Preferred details ───
    preferred = tier_df[tier_df['Priority'] == 2]
    print(f"\n{'─'*50}")
    print(f"Strategic Preferred Suppliers")
    print(f"{'─'*50}")
    for _, r in preferred.iterrows():
        print(f"  [+] {r['supplier_name']:<20} "
              f"Final={r['Final_Score']:.3f} Rank={int(r['Baseline_Rank']):>2d} | "
              f"{r['Tier_Rationale']}")

    # ─── Capability Watchlist weakness analysis ───
    watchlist = tier_df[tier_df['Priority'] == 4]
    if len(watchlist) > 0:
        print(f"\n{'─'*50}")
        print(f"Capability Watchlist — Weaknesses & Risks")
        print(f"{'─'*50}")
        for _, r in watchlist.iterrows():
            scores = {d: r[f'{d}_Score'] for d in ['Cost', 'ESG', 'Risk', 'LeadTime', 'Tech']}
            weakest = min(scores, key=scores.get)
            strongest = max(scores, key=scores.get)
            print(f"  [!] {r['supplier_name']:<20} "
                  f"Rank={int(r['Baseline_Rank']):>2d} Final={r['Final_Score']:.3f} | "
                  f"Strong: {strongest}={scores[strongest]:.3f} Weak: {weakest}={scores[weakest]:.3f} | "
                  f"{r['Tier_Rationale']}")

    # ─── Restricted Supplier restriction reasons ───
    restricted = tier_df[tier_df['Priority'] == 1]
    if len(restricted) > 0:
        print(f"\n{'─'*50}")
        print(f"Restricted Supplier — Restriction Reasons")
        print(f"{'─'*50}")
        for _, r in restricted.iterrows():
            print(f"  [X] {r['supplier_name']:<20} — {r['Tier_Rationale']}")

    return tier_df


# ==========================================
# Revised M2: Cost-ESG Shortlist + Diagnostics
# ==========================================
M2_REVISED_SHORTLIST_SHARE = 0.40
M2_REVISED_MIN_CATEGORY_SHORTLIST = 3
M2_REVISED_STABLE_SCENARIO_COUNT = 3
M2_REVISED_SCENARIOS = {
    'Cost Priority': {'cost': 0.70, 'esg': 0.30, 'risk_min': None},
    'Balanced Cost-ESG': {'cost': 0.55, 'esg': 0.45, 'risk_min': None},
    'ESG Priority': {'cost': 0.35, 'esg': 0.65, 'risk_min': None},
    'Risk-Control View': {'cost': 0.55, 'esg': 0.45, 'risk_min': 0.50},
}


def _score_level(score, good_min=0.65, medium_min=0.45,
                 good_label='Low', medium_label='Medium', bad_label='High'):
    if pd.isna(score):
        return 'Unknown'
    if score >= good_min:
        return good_label
    if score >= medium_min:
        return medium_label
    return bad_label


def _join_parts(parts):
    clean = [str(p) for p in parts if p is not None and str(p).strip()]
    return '; '.join(clean) if clean else 'No material warning'


def generate_revised_m2_outputs(scored_df, adj_cost_df=None):
    """Generate revised M2 outputs (Step 1-3) without legacy dependencies.

    If adj_cost_df is provided, C_cost_warning in the TQRDC diagnostic profile
    uses Adjusted_Cost_Index / cost_quartile instead of the legacy Cost_Score threshold.

    Revised M2 is positioned as a three-step procurement shortlist support view:
      Step 1 - Cost-ESG Shortlist (Cost + ESG score, category-level ranking)
      Step 2 - TQRDC Diagnostic Profile (diagnostic-only, not weighted)
      Step 3 - Shortlist Stability (4 management-preference scenarios)

    No strategic tiering, AHP, or old 5-dimension sensitivity is required.

    Outputs:
      M2_Cost_ESG_Shortlist.csv
      M2_Supplier_Diagnostic_Profile.csv
      M2_Shortlist_Stability_Report.csv
      M2_Revised_Decision_View.csv
    """
    df = scored_df.copy()
    required = ['supplier_id', 'supplier_name', 'country', 'category',
                'Cost_Score', 'ESG_Score', 'Risk_Score',
                'LeadTime_Score', 'Tech_Score']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for revised M2 outputs: {missing}")

    if 'M1_Status' not in df.columns:
        df['M1_Status'] = 'UNKNOWN'
    if 'M1_Risk_Vector' not in df.columns:
        df['M1_Risk_Vector'] = 'None'

    # Build scenario shortlist membership within each category.
    scenario_membership = {}
    scenario_rank_cols = {}
    for scenario_name, cfg in M2_REVISED_SCENARIOS.items():
        score_col = f"{scenario_name.replace(' ', '_').replace('-', '_')}_Score"
        rank_col = f"{scenario_name.replace(' ', '_').replace('-', '_')}_Category_Rank"
        scenario_rank_cols[scenario_name] = rank_col

        df[score_col] = df['Cost_Score'] * cfg['cost'] + df['ESG_Score'] * cfg['esg']
        if cfg['risk_min'] is not None:
            df.loc[df['Risk_Score'] < cfg['risk_min'], score_col] = -1.0

        df[rank_col] = df.groupby('category')[score_col].rank(ascending=False, method='min').astype(int)
        members = set()
        for cat, cat_df in df.groupby('category'):
            limit = max(M2_REVISED_MIN_CATEGORY_SHORTLIST,
                        int(np.ceil(len(cat_df) * M2_REVISED_SHORTLIST_SHARE)))
            eligible = cat_df[cat_df[score_col] >= 0].sort_values(score_col, ascending=False).head(limit)
            members.update(eligible['supplier_id'].tolist())
        scenario_membership[scenario_name] = members

    balanced_score_col = 'Balanced_Cost_ESG_Score'
    balanced_rank_col = scenario_rank_cols['Balanced Cost-ESG']
    df['cost_esg_score'] = df[balanced_score_col].round(4)
    df['cost_score'] = df['Cost_Score'].round(4)
    df['esg_score'] = df['ESG_Score'].round(4)

    stability_records = []
    for _, row in df.iterrows():
        sid = row['supplier_id']
        appeared = [name for name, members in scenario_membership.items() if sid in members]
        count = len(appeared)
        stable = count >= M2_REVISED_STABLE_SCENARIO_COUNT
        if stable:
            comment = f"Stable shortlist candidate across {count}/4 revised M2 views."
        elif count > 0:
            comment = f"Context-dependent candidate; appears in {count}/4 revised M2 views."
        else:
            comment = "Not shortlisted under the current Cost-ESG scenario assumptions."
        stability_records.append({
            'supplier_id': sid,
            'supplier_name': row['supplier_name'],
            'category': row['category'],
            'appeared_in_scenarios': ', '.join(appeared) if appeared else 'None',
            'stable_shortlist_flag': 'YES' if stable else 'NO',
            'scenario_count': count,
            'stability_comment': comment,
        })
    stability_df = pd.DataFrame(stability_records)

    df = df.merge(
        stability_df[['supplier_id', 'appeared_in_scenarios',
                      'stable_shortlist_flag', 'scenario_count', 'stability_comment']],
        on='supplier_id', how='left'
    )

    # Diagnostic levels are warnings, not final procurement scores.
    df['risk_level'] = df['Risk_Score'].apply(
        lambda x: _score_level(x, good_min=0.65, medium_min=0.45,
                               good_label='Low', medium_label='Medium', bad_label='High')
    )
    df['risk_score'] = df['Risk_Score'].round(4)
    df['delivery_risk'] = df['LeadTime_Score'].apply(
        lambda x: _score_level(x, good_min=0.65, medium_min=0.45,
                               good_label='Low', medium_label='Medium', bad_label='High')
    )
    df['lead_time_score'] = df['LeadTime_Score'].round(4)
    df['tech_score'] = df['Tech_Score'].round(4)

    def _capability_flag(row):
        tech = row['Tech_Score']
        if tech >= 0.75:
            return 'Strong capability'
        if tech >= 0.50:
            return 'Standard capability'
        return 'Capability gap'

    df['capability_flag'] = df.apply(_capability_flag, axis=1)

    def _quality_warning_from_vector(row):
        rv = str(row.get('M1_Risk_Vector', ''))
        if 'Quality' in rv or 'quality' in rv:
            return 'Quality concern flagged in M1'
        return 'No quality concern'

    df['Q_quality_warning'] = df.apply(_quality_warning_from_vector, axis=1)

    def _warnings(row):
        parts = []
        if str(row.get('M1_Status', '')) != 'PASS':
            parts.append(f"M1 status {row.get('M1_Status')}")
        if row['risk_level'] == 'High':
            parts.append('high risk diagnostic')
        if row['delivery_risk'] == 'High':
            parts.append('high delivery risk')
        if row['capability_flag'] == 'Capability gap':
            parts.append('capability gap')
        if row['Q_quality_warning'] != 'No quality concern':
            parts.append('quality concern')
        if row['ESG_Score'] < 0.45:
            parts.append('ESG weakness')
        if row['Cost_Score'] < 0.45:
            parts.append('cost disadvantage')
        r1 = row.get('R1_Country_Risk')
        if pd.notna(r1) and float(r1) <= 2:
            parts.append('country/geopolitical warning')
        return _join_parts(parts)

    df['key_warning'] = df.apply(_warnings, axis=1)

    def _shortlist_status(row):
        in_balanced = row['supplier_id'] in scenario_membership['Balanced Cost-ESG']
        stable = row['stable_shortlist_flag'] == 'YES'
        warning = row.get('key_warning', '')
        has_warning = warning not in ('', 'No material warning')
        if str(row.get('M1_Status', '')) != 'PASS':
            return 'Restricted - diagnostic only'
        if in_balanced and stable:
            return 'Shortlist with warning' if has_warning else 'Preferred shortlist'
        if in_balanced or stable:
            return 'Conditional shortlist'
        return 'Not shortlisted'

    def _shortlist_reason(row):
        rank = int(row[balanced_rank_col])
        sub_counts = sum(
            1 for name in M2_REVISED_SCENARIOS
            if row['supplier_id'] in scenario_membership.get(name, set())
        )
        return (
            f"Score-based category rank {rank}, "
            f"shortlisted in {sub_counts}/{len(M2_REVISED_SCENARIOS)} Cost-ESG views."
        )

    df['shortlist_status'] = df.apply(_shortlist_status, axis=1)
    df['shortlist_reason'] = df.apply(_shortlist_reason, axis=1)

    def _diagnostic_summary(row):
        return (
            f"Risk={row['risk_level']} ({row['Risk_Score']:.2f}); "
            f"Delivery={row['delivery_risk']} ({row['LeadTime_Score']:.2f}); "
            f"Capability={row['capability_flag']} ({row['Tech_Score']:.2f}); "
            f"Quality={row['Q_quality_warning']}; "
            f"M1={row.get('M1_Status', 'UNKNOWN')}."
        )

    def _management_action(row):
        if str(row.get('M1_Status', '')) != 'PASS':
            return 'Keep as restricted candidate; require M1 remediation before normal sourcing.'
        if row['risk_level'] == 'High':
            return 'Require risk review and mitigation plan before allocation.'
        if row['delivery_risk'] == 'High':
            return 'Check logistics and delivery contingency before shortlist approval.'
        if row['capability_flag'] == 'Capability gap':
            return 'Run technical capability review before category allocation.'
        if row['Q_quality_warning'] != 'No quality concern':
            return 'Review supplier quality issue; assess impact on category allocation.'
        if row['shortlist_status'] in ('Preferred shortlist', 'Shortlist with warning'):
            return 'Proceed to M3 allocation input when demand and capacity assumptions are confirmed.'
        if row['shortlist_status'] == 'Conditional shortlist':
            return 'Keep for category manager review; compare against stable shortlist candidates.'
        return 'Keep as backup or monitoring candidate for this M2 cycle.'

    df['diagnostic_summary'] = df.apply(_diagnostic_summary, axis=1)
    df['recommended_management_action'] = df.apply(_management_action, axis=1)

    # Build adjusted cost lookup for Step 3 C_cost_warning alignment
    _adj_cost_lookup = {}
    if adj_cost_df is not None and not adj_cost_df.empty:
        for _, r in adj_cost_df.iterrows():
            _adj_cost_lookup[r['supplier_id']] = {
                'quartile': r.get('cost_quartile', ''),
                'position': r.get('cost_position', 0),
            }

    def _cost_warning(row):
        # Use Adjusted Cost Index when available
        sid = row['supplier_id']
        if sid in _adj_cost_lookup:
            info = _adj_cost_lookup[sid]
            if info['quartile'] == 'Q4_Worst' or info['position'] >= 75:
                return 'Adjusted cost outlier / Cost pressure'
            return 'No cost concern'
        # Fallback to legacy Cost_Score threshold
        if row['Cost_Score'] < 0.45:
            return 'Cost disadvantage'
        return 'No cost concern'

    def _tqrdc_diagnostic_summary(row):
        """TQRDC diagnostic summary: diagnostic lens only, not a weighted score."""
        return (
            f"T={row['T_capability_flag']}; "
            f"Q={row['Q_quality_warning']}; "
            f"R={row['R_risk_level']}; "
            f"D={row['D_delivery_risk']}; "
            f"C={row['C_cost_warning']}."
        )

    df['C_cost_warning'] = df.apply(_cost_warning, axis=1)
    df['T_capability_flag'] = df['capability_flag']
    df['R_risk_level'] = df['risk_level']
    df['D_delivery_risk'] = df['delivery_risk']
    df['tqrdc_diagnostic_summary'] = df.apply(_tqrdc_diagnostic_summary, axis=1)

    # Note: strategic_tier_reference intentionally excluded from revised M2.
    # Legacy tier depends on old five-dimension sensitivity which is not
    # generated in the default (RUN_LEGACY_M2=False) flow.

    def _m3_flag(row):
        if row['shortlist_status'] in ('Preferred shortlist', 'Shortlist with warning') and row['risk_level'] != 'High':
            return 'YES'
        if row['shortlist_status'] == 'Conditional shortlist' and str(row.get('M1_Status', '')) == 'PASS':
            return 'CONDITIONAL_REVIEW'
        return 'NO'

    def _next_step(row):
        if row['M3_eligible_flag'] == 'YES':
            return 'Use as candidate input for M3 after demand/capacity parameters are confirmed.'
        if row['M3_eligible_flag'] == 'CONDITIONAL_REVIEW':
            return 'Manager review required before M3 input; resolve diagnostic warnings first.'
        if str(row.get('M1_Status', '')) != 'PASS':
            return 'Do not use for normal M3 allocation until M1 limitation is remediated.'
        return 'Do not prioritize for M3; keep as backup or monitoring supplier.'

    df['M3_eligible_flag'] = df.apply(_m3_flag, axis=1)
    df['recommended_next_step'] = df.apply(_next_step, axis=1)

    shortlist_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                      'cost_score', 'esg_score', 'cost_esg_score',
                      'shortlist_status', 'shortlist_reason', 'key_warning']
    diagnostic_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                       'risk_score', 'risk_level', 'lead_time_score', 'delivery_risk',
                       'tech_score', 'capability_flag', 'M1_Risk_Vector',
                       'T_capability_flag', 'Q_quality_warning', 'R_risk_level',
                       'D_delivery_risk', 'C_cost_warning', 'tqrdc_diagnostic_summary',
                       'diagnostic_summary', 'recommended_management_action']
    decision_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                     'cost_score', 'esg_score', 'cost_esg_score',
                     'shortlist_status', 'risk_level',
                     'tqrdc_diagnostic_summary',
                     'M3_eligible_flag', 'recommended_next_step']

    shortlist_df = df.sort_values(['category', balanced_rank_col, 'supplier_id'])[shortlist_cols]
    diagnostic_df = df.sort_values(['category', 'risk_level', 'delivery_risk', 'supplier_id'])[diagnostic_cols]
    decision_df = df.sort_values(['category', balanced_rank_col, 'supplier_id'])[decision_cols]

    shortlist_df.to_csv('M2_Cost_ESG_Shortlist.csv', index=False, encoding='utf-8-sig')
    diagnostic_df.to_csv('M2_Supplier_Diagnostic_Profile.csv', index=False, encoding='utf-8-sig')
    stability_df.to_csv('M2_Shortlist_Stability_Report.csv', index=False, encoding='utf-8-sig')
    decision_df.to_csv('M2_Revised_Decision_View.csv', index=False, encoding='utf-8-sig')

    print(f"\n{'='*70}")
    print("Revised M2 Cost-ESG Shortlist & Diagnostic Layer")
    print(f"{'='*70}")
    print("  => M2_Cost_ESG_Shortlist.csv saved")
    print("  => M2_Supplier_Diagnostic_Profile.csv saved")
    print("  => M2_Shortlist_Stability_Report.csv saved")
    print("  => M2_Revised_Decision_View.csv saved")

    return {
        'shortlist': shortlist_df,
        'diagnostic': diagnostic_df,
        'stability': stability_df,
        'decision_view': decision_df,
    }


# ==========================================
# Adjusted Cost Index (Next-Stage M2, Step 1)
# ==========================================

def run_adjusted_cost_index(df, carbon_tax=None, output_dir='.'):
    """Compute Adjusted Cost Index per supplier (MVP).

    Three category-normalized components:
      - Base Cost Component: annual_contract_value_usd (higher = more cost pressure)
      - Logistics/Landed Cost Component: country-based landed cost tier
      - Carbon Cost Component: carbon_intensity x carbon_tax

    Normalization: min-max per category, yielding [0,1] where 0=cheapest, 1=most expensive.
    Final index: weighted sum of normalized components.
    This is a RELATIVE index, NOT a true Total Cost of Ownership.

    Args:
        df: Supplier DataFrame (post-M1, with raw input columns preserved).
        carbon_tax: Carbon tax override (None = config default).
        output_dir: Output directory for CSV.

    Outputs:
        M2_Adjusted_Cost_Index.csv
        Returns output_df.
    """
    result = df.copy()
    _carbon_tax = carbon_tax if carbon_tax is not None else M2_CONFIG['CARBON_TAX_PER_TON']

    # ── 1. Extract raw cost components ──
    # Base Cost: annual_contract_value_usd
    result['_base_raw'] = result['annual_contract_value_usd'].fillna(
        result.groupby('category')['annual_contract_value_usd'].transform('median')
    )

    # Logistics/Landed Cost: country landed cost tier (REGION_COST_MAP)
    result['_logistics_raw'] = result['country'].map(M2_CONFIG['REGION_COST_MAP']).fillna(3)

    # Carbon Cost: carbon_intensity x carbon_tax
    ci_filled = result['carbon_intensity'].fillna(
        result.groupby('category')['carbon_intensity'].transform('median')
    )
    result['_carbon_raw'] = ci_filled * _carbon_tax

    # ── 2. Category-level min-max normalisation (0=cheapest, 1=most expensive) ──
    def _min_max_norm(s):
        if s.nunique() <= 1 or s.max() == s.min():
            return pd.Series(0.5, index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    result['base_cost_component'] = result.groupby('category')['_base_raw'].transform(_min_max_norm)
    result['logistics_cost_component'] = result.groupby('category')['_logistics_raw'].transform(_min_max_norm)
    result['carbon_cost_component'] = result.groupby('category')['_carbon_raw'].transform(_min_max_norm)

    # ── 3. Weights (category-specific overrides supported) ──
    cat_overrides = M2_CONFIG.get('ADJ_COST_CATEGORY_WEIGHTS_MAP', {})
    g_base = M2_CONFIG.get('ADJ_COST_BASE_WEIGHT', 0.60)
    g_log  = M2_CONFIG.get('ADJ_COST_LOGISTICS_WEIGHT', 0.25)
    g_carb = M2_CONFIG.get('ADJ_COST_CARBON_WEIGHT', 0.15)

    def _get_w(cat):
        ow = cat_overrides.get(cat, {})
        return (ow.get('base', g_base), ow.get('logistics', g_log), ow.get('carbon', g_carb))

    result['_wt'] = result['category'].apply(_get_w)
    result['base_cost_weight']      = result['_wt'].apply(lambda x: x[0])
    result['logistics_cost_weight'] = result['_wt'].apply(lambda x: x[1])
    result['carbon_cost_weight']    = result['_wt'].apply(lambda x: x[2])

    # ── 4. Adjusted Cost Index ──
    result['Adjusted_Cost_Index'] = (
        result['base_cost_component'] * result['base_cost_weight']
        + result['logistics_cost_component'] * result['logistics_cost_weight']
        + result['carbon_cost_component'] * result['carbon_cost_weight']
    )

    # ── 5. Cost quartile (category-level) ──
    def _cat_quartile(s):
        # Use pd.qcut with duplicates='drop' to handle edge cases
        return pd.qcut(s.rank(method='first'), q=4,
                       labels=['Q1_Best', 'Q2', 'Q3', 'Q4_Worst'],
                       duplicates='drop')

    result['cost_quartile'] = result.groupby('category')['Adjusted_Cost_Index'].transform(
        lambda x: _cat_quartile(x) if x.nunique() >= 4 else pd.Series(['N/A'] * len(x), index=x.index)
    )

    # Cost position: percentile rank within category (0=cheapest, 100=most expensive)
    result['cost_position'] = result.groupby('category')['Adjusted_Cost_Index'].transform(
        lambda x: x.rank(pct=True) * 100
    ).round(1)

    # ── 6. Cost driver summary ──
    def _driver_summary(row):
        idx = row['Adjusted_Cost_Index']
        parts = []
        if row['base_cost_component'] > 0.7:
            parts.append(f"Base Cost dominant ({row['base_cost_component']:.2f})")
        if row['logistics_cost_component'] > 0.7:
            parts.append(f"Logistics cost high ({row['logistics_cost_component']:.2f})")
        if row['carbon_cost_component'] > 0.7:
            parts.append(f"Carbon cost high ({row['carbon_cost_component']:.2f})")
        if idx <= 0.25:
            parts.append("Overall low cost (bottom quartile)")
        elif idx >= 0.75:
            parts.append("Overall high cost (top quartile)")
        return ' | '.join(parts) if parts else 'Moderate cost profile'

    result['cost_driver_summary'] = result.apply(_driver_summary, axis=1)

    # ── 7. Output CSV ──
    out_cols = [
        'supplier_id', 'supplier_name', 'country', 'category', 'M1_Status',
        'base_cost_component', 'logistics_cost_component', 'carbon_cost_component',
        'base_cost_weight', 'logistics_cost_weight', 'carbon_cost_weight',
        'Adjusted_Cost_Index', 'cost_quartile', 'cost_position', 'cost_driver_summary',
    ]
    available = [c for c in out_cols if c in result.columns]
    output_df = result[available].reset_index(drop=True)
    output_df = output_df.sort_values(['category', 'Adjusted_Cost_Index']).reset_index(drop=True)

    csv_path = os.path.join(output_dir, 'M2_Adjusted_Cost_Index.csv')
    output_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    cat_names = sorted(output_df['category'].unique())
    n_w_custom = sum(1 for c in cat_names if c in cat_overrides)
    print(f"\n{'='*70}")
    print(f"Adjusted Cost Index (MVP) — Step 1 of next-stage M2")
    print(f"{'='*70}")
    print(f"  => M2_Adjusted_Cost_Index.csv saved ({len(output_df)} suppliers, {len(cat_names)} categories)")
    print(f"  Default weights: Base Cost * {g_base:.0%} + Logistics * {g_log:.0%} + Carbon * {g_carb:.0%}")
    print(f"  Category overrides active for: {n_w_custom} category(s)")
    print(f"  NOTE: This is a RELATIVE index within each category, NOT a true Total Cost of Ownership.")
    print(f"        Lower Adjusted_Cost_Index = economically cheaper.")

    # Tidy temp columns from source df
    drops = ['_base_raw', '_logistics_raw', '_carbon_raw', '_wt']
    result.drop(columns=[c for c in drops if c in result.columns], inplace=True)

    return output_df


# ==========================================
# ESG Strategic Fit (Next-Stage M2, Step 2)
# ==========================================

def _esg_carbon_tier(series):
    """Assign carbon performance level: 3-level within active suppliers."""
    # Impute NaN with median before ranking
    s = series.fillna(series.median())
    try:
        labels = ['Low', 'Medium', 'High']
        out = pd.qcut(s.rank(method='first'), q=3, labels=labels)
        return out
    except ValueError:
        return pd.Series(['Medium'] * len(series), index=series.index)


def run_esg_strategic_fit(df):
    """Compute ESG Strategic Fit tier for each active (PASS+LIMITED) supplier.

    ESG is an independent strategic positioning dimension, NOT weighted
    with Adjusted Cost. Tiers reflect a holistic assessment of carbon
    intensity, PCF commitment, certification signal, and labor governance.

    Tiers:
      - ESG Leader:   Strong across >=3 of 4 dimensions
      - ESG Compliant: Adequate across most dimensions
      - ESG Monitor:  Weakness in 1-2 dimensions, needs observation
      - ESG Gap:      Significant gap in 2+ dimensions

    Output: M2_ESG_Strategic_Fit.csv
    """
    print(f"\n{'='*70}")
    print("ESG Strategic Fit (Next-Stage M2, Step 2)")
    print(f"{'='*70}")

    result = df[['supplier_id', 'supplier_name', 'country', 'category',
                 'M1_Status', 'carbon_intensity', 'pcf_commitment',
                 'cert_type']].copy()

    # --- Carbon performance (relative within active suppliers) ---
    result['carbon_performance_level'] = _esg_carbon_tier(result['carbon_intensity'])

    # --- PCF commitment (binary) ---
    pcf_map = {True: 'Committed', False: 'Not committed'}
    result['pcf_commitment_signal'] = result['pcf_commitment'].map(pcf_map).fillna('Not committed')

    # --- Certification signal ---
    def _cert_signal(cert):
        if pd.isna(cert):
            return 'No cert'
        cert_s = str(cert).upper()
        if '14001' in cert_s:
            return 'ISO 14001'
        if 'IATF' in cert_s:
            return 'IATF'
        if '9001' in cert_s:
            return 'ISO 9001'
        return 'Other cert'
    result['certification_signal'] = result['cert_type'].apply(_cert_signal)

    # --- Labor governance signal ---
    labor_gov = M2_CONFIG.get('LABOR_GOV_MAP', {})
    def _labor_signal(country):
        score = labor_gov.get(country, 3)
        if score >= 4:
            return 'Strong'
        if score >= 3:
            return 'Adequate'
        return 'Weak'
    result['labor_governance_signal'] = result['country'].apply(_labor_signal)

    # --- Scoring dimensions (points system) ---
    # Carbon: Low=2, Medium=1, High=0
    carbon_points = {'Low': 2, 'Medium': 1, 'High': 0}
    result['_cp'] = result['carbon_performance_level'].map(carbon_points).fillna(1).astype(float)

    # PCF: committed=2, else=0
    result['_pp'] = (result['pcf_commitment'].fillna(False).astype(int) * 2).astype(float)

    # Cert: ISO 14001=2, IATF or ISO 9001=1, else=0
    cert_points = {'ISO 14001': 2, 'IATF': 1, 'ISO 9001': 1, 'Other cert': 0, 'No cert': 0}
    result['_certp'] = result['certification_signal'].map(cert_points).fillna(0).astype(float)

    # Labor: Strong=2, Adequate=1, Weak=0
    labor_points = {'Strong': 2, 'Adequate': 1, 'Weak': 0}
    result['_lp'] = result['labor_governance_signal'].map(labor_points).fillna(1).astype(float)

    result['_esg_total'] = result['_cp'] + result['_pp'] + result['_certp'] + result['_lp']

    # --- ESG Position Tier ---
    def _esg_tier(total):
        if total >= 6:
            return 'ESG Leader'
        if total >= 4:
            return 'ESG Compliant'
        if total >= 2:
            return 'ESG Monitor'
        return 'ESG Gap'

    def _esg_reason(row):
        weak = []
        if row['carbon_performance_level'] == 'High':
            weak.append('high carbon intensity')
        if row['pcf_commitment'] != True:
            weak.append('no PCF commitment')
        if row['certification_signal'] in ('No cert', 'Other cert'):
            weak.append('no environmental cert')
        if row['labor_governance_signal'] == 'Weak':
            weak.append('weak labor governance')
        if not weak:
            return 'Strong across ESG dimensions'
        return 'Weakness: ' + ', '.join(weak)

    result['ESG_Position_Tier'] = result['_esg_total'].apply(_esg_tier)
    result['ESG_position_reason'] = result.apply(_esg_reason, axis=1)

    # --- Output ---
    out_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                'carbon_intensity', 'carbon_performance_level',
                'pcf_commitment_signal', 'certification_signal',
                'labor_governance_signal',
                'ESG_Position_Tier', 'ESG_position_reason']
    output = result[out_cols].sort_values(['category', 'ESG_Position_Tier', 'supplier_id'])
    output.to_csv('M2_ESG_Strategic_Fit.csv', index=False, encoding='utf-8-sig')

    # Tidy
    result.drop(columns=[c for c in ['_cp', '_pp', '_certp', '_lp', '_esg_total']
                         if c in result.columns], inplace=True)

    tier_counts = output['ESG_Position_Tier'].value_counts()
    print(f"  => M2_ESG_Strategic_Fit.csv saved ({len(output)} suppliers)")
    for tier in ['ESG Leader', 'ESG Compliant', 'ESG Monitor', 'ESG Gap']:
        cnt = tier_counts.get(tier, 0)
        print(f"     {tier}: {cnt}")
    return output


# ==========================================
# Strategic Pool Classification (Next-Stage M2, Step 4)
# ==========================================

def run_strategic_pool_view(adj_cost_df, esg_fit_df, diagnostic_df, scored_df):
    """Merge data sources and classify each supplier into a Strategic Pool.

    Pool hierarchy (higher = more preferred for allocation):
      Preferred   - PASS, Q1/Q2 cost, ESG Leader/Compliant, no high diagnostic
      Core        - PASS, not Q4 cost, not ESG Gap, manageable diagnostics
      Conditional - PASS but has Q4 cost OR ESG Gap OR one high diagnostic
      Restricted  - PASS but multiple high diagnostics OR M1 != PASS
      Not Priority- PASS but no other pool matches
      Reserve     - Reserved for M1 RESERVE/FAIL suppliers (label only)

    Output: M2_Strategic_Pool_View.csv
    """
    print(f"\n{'='*70}")
    print("Strategic Pool Classification (Next-Stage M2, Step 4)")
    print(f"{'='*70}")

    # --- Merge data sources ---
    pool = adj_cost_df[['supplier_id', 'supplier_name', 'category', 'M1_Status',
                        'Adjusted_Cost_Index', 'cost_quartile', 'cost_position']].copy()

    # ESG tier
    esg_map = esg_fit_df[['supplier_id', 'ESG_Position_Tier']].copy()
    pool = pool.merge(esg_map, on='supplier_id', how='left')

    # Diagnostic signals
    diag = diagnostic_df[['supplier_id', 'risk_level', 'delivery_risk',
                          'T_capability_flag', 'Q_quality_warning',
                          'C_cost_warning']].copy()
    pool = pool.merge(diag, on='supplier_id', how='left')

    # Standardize risk/delivery to uppercase for comparison
    pool['risk_level'] = pool['risk_level'].str.lower().str.strip()
    pool['delivery_risk'] = pool['delivery_risk'].str.lower().str.strip()

    # --- Helper: count high diagnostics ---
    def _count_high_diag(row):
        cnt = 0
        if row.get('risk_level') == 'high':
            cnt += 1
        if row.get('delivery_risk') == 'high':
            cnt += 1
        if row.get('T_capability_flag') == 'Capability gap':
            cnt += 1
        if row.get('Q_quality_warning', '') != 'No quality concern':
            cnt += 1
        return cnt

    pool['_diag_count'] = pool.apply(_count_high_diag, axis=1)

    cost_q = pool['cost_quartile'].fillna('Q3')
    esg_tier = pool['ESG_Position_Tier'].fillna('ESG Gap')

    # --- Classification rules (sequential) ---
    def _classify(row):
        m1 = str(row.get('M1_Status', ''))
        q = str(row.get('cost_quartile', ''))
        esg = str(row.get('ESG_Position_Tier', ''))
        d_cnt = row.get('_diag_count', 0)

        # M1 != PASS -> Restricted
        if m1 != 'PASS':
            return ('Restricted', 'Not M1-PASS; retained for diagnostic reference')

        # Preferred: Q1/Q2 cost + ESG Leader/Compliant + no high diagnostic
        if q in ('Q1_Best', 'Q2') and esg in ('ESG Leader', 'ESG Compliant') and d_cnt == 0:
            return ('Preferred', 'Strong cost position and ESG profile; no diagnostic concerns')

        # Core: not Q4 + not ESG Gap + manageable diagnostic (<=1)
        if q != 'Q4_Worst' and esg != 'ESG Gap' and d_cnt <= 1:
            return ('Core', 'Adequate cost-ESG position; minor or no diagnostic concerns')

        # Restricted (diagnostic): multiple high diagnostics
        if d_cnt >= 2:
            return ('Restricted', f'{d_cnt} high diagnostic flags; needs management review')

        # Conditional: Q4 cost OR ESG Gap OR one high diagnostic
        if q == 'Q4_Worst' or esg == 'ESG Gap' or d_cnt == 1:
            reasons = []
            if q == 'Q4_Worst':
                reasons.append('cost quartile Q4')
            if esg == 'ESG Gap':
                reasons.append('ESG Gap')
            if d_cnt == 1:
                reasons.append('1 high diagnostic flag')
            return ('Conditional', 'Conditional: ' + ', '.join(reasons))

        # Not Priority: catch-all
        return ('Not Priority', 'Not classified into higher-priority pools')

    classifications = pool.apply(_classify, axis=1)
    pool['Strategic_Pool'] = [c[0] for c in classifications]
    pool['pool_reason'] = [c[1] for c in classifications]

    # --- Sourcing recommendation ---
    pool['sourcing_recommendation'] = pool['Strategic_Pool'].map({
        'Preferred': 'Primary allocation candidate. Include in sourcing RFQ.',
        'Core': 'Valid allocation candidate. Consider for sourcing RFQ.',
        'Conditional': 'Manager review required. Conditional sourcing consideration.',
        'Restricted': 'Do not prioritize. Remediate M1 limitations or diagnostic gaps first.',
        'Not Priority': 'Hold as backup. Not recommended for current sourcing cycle.',
        'Reserve': 'Reserve pool. Activate only under supply disruption.',
    }).fillna('No recommendation')

    # --- Dashboard flag ---
    pool['dashboard_flag'] = pool['Strategic_Pool'].map({
        'Preferred': 'Green',
        'Core': 'Green',
        'Conditional': 'Amber',
        'Restricted': 'Red',
        'Not Priority': 'Grey',
        'Reserve': 'Grey',
    }).fillna('Grey')

    # --- Output ---
    out_cols = ['supplier_id', 'supplier_name', 'category', 'M1_Status',
                'Adjusted_Cost_Index', 'cost_quartile', 'cost_position',
                'ESG_Position_Tier',
                'risk_level', 'delivery_risk', 'T_capability_flag',
                'Q_quality_warning', 'C_cost_warning',
                'Strategic_Pool', 'sourcing_recommendation', 'pool_reason',
                'dashboard_flag']
    output = pool[out_cols].sort_values(
        ['category', 'Strategic_Pool', 'Adjusted_Cost_Index']
    ).reset_index(drop=True)

    output.to_csv('M2_Strategic_Pool_View.csv', index=False, encoding='utf-8-sig')

    # Tidy
    pool.drop(columns=['_diag_count'], inplace=True)

    pool_counts = output['Strategic_Pool'].value_counts()
    print(f"  => M2_Strategic_Pool_View.csv saved ({len(output)} suppliers)")
    for p in ['Preferred', 'Core', 'Conditional', 'Restricted', 'Not Priority', 'Reserve']:
        cnt = pool_counts.get(p, 0)
        print(f"     {p}: {cnt}")
    return output


# ==========================================
# CLI entry point
# ==========================================
if __name__ == "__main__":
    from Model1 import load_suppliers_data, run_m1
    import shutil

    # Archive any existing legacy output CSVs to archive/legacy_m2_outputs/
    LEGACY_ARCHIVE_DIR = os.path.join(os.path.dirname(__file__) or '.', 'archive', 'legacy_m2_outputs')
    _legacy_csv_patterns = ['M2_Category_Ranking_*.csv', 'radar_m2_*.png',
                            'M2_Strategic_Scenario_Scores.csv', 'M2_Strategic_Sensitivity_Report.csv',
                            'M2_TCO_Scenario_Scores.csv', 'M2_TCO_Sensitivity_Report.csv',
                            'M2_ESG_Scenario_Scores.csv', 'M2_ESG_Sensitivity_Report.csv',
                            'M2_Strategic_Tier.csv']
    _existing_legacy = []
    for _pattern in _legacy_csv_patterns:
        _existing_legacy.extend(glob.glob(_pattern))  # glob imported via os import at top
    if _existing_legacy:
        os.makedirs(LEGACY_ARCHIVE_DIR, exist_ok=True)
        for _f in _existing_legacy:
            _dest = os.path.join(LEGACY_ARCHIVE_DIR, os.path.basename(_f))
            shutil.move(_f, _dest)
            print(f"  [Archive] Moved {_f} -> {_dest}")

    df_raw = load_suppliers_data()
    df = run_m1(df_raw)

    # Adjusted Cost Index (next-stage M2, Step 1)
    # Called on raw df (post-M1) because annual_contract_value_usd and
    # carbon_intensity are not in run_m2_scoring output columns.
    adj_cost_df = run_adjusted_cost_index(df)

    # Single call to run_m2_scoring — both revised and legacy flows share this.
    scored = run_m2_scoring(df)

    print("\nScoring complete (18 sub-indicators -> 5 dimension scores).")
    print(f"  Suppliers scored: {len(scored)}")

    # ========== [LEGACY] Full legacy analysis (RUN_LEGACY_M2=True) ==========
    # Strategic sensitivity, strategic tiering, category ranking, radar,
    # legacy cost/ESG sensitivities. Outputs go to archive/legacy_m2_outputs/.
    if RUN_LEGACY_M2:
        print(f"\n{'='*60}")
        print(f"Legacy M2 Analysis (RUN_LEGACY_M2=True)")
        print(f"{'='*60}")

        strategic_sensitivity_scenario, strategic_sensitivity_report = run_m2_strategic_weight_sensitivity(df)
        tier_df = run_m2_strategic_tiering(df, scored_baseline=scored,
                                           strategic_report=strategic_sensitivity_report)

        _score_cols = ['Cost_Score', 'ESG_Score', 'Risk_Score', 'LeadTime_Score', 'Tech_Score']
        _dim_weights = [0.25, 0.25, 0.20, 0.15, 0.15]
        scored['Final_Score'] = sum(scored[c] * w for c, w in zip(_score_cols, _dim_weights))
        generate_category_ranking_and_radar(scored, tier_df=tier_df, save_csv=True, save_radar=True)

        run_m2_cost_weight_sensitivity(df)
        run_m2_esg_internal_sensitivity(df)

    # ========== [HEADLINE] Revised M2 Cost-ESG Shortlist & Diagnostic Layer ==========
    # Default flow: no strategic tiering, AHP, or old 5-dim sensitivity.
    revised_m2 = generate_revised_m2_outputs(scored, adj_cost_df=adj_cost_df)

    # ESG Strategic Fit (Next-Stage M2, Step 2)
    # Independent strategic positioning, not weighted with Adjusted Cost.
    esg_fit_df = run_esg_strategic_fit(df)

    # Strategic Pool Classification (Next-Stage M2, Step 4)
    # Merges Adjusted Cost + ESG Fit + Diagnostic profile into pool view.
    diagnostic_profile_df = revised_m2.get('diagnostic') if isinstance(revised_m2, dict) else None
    if diagnostic_profile_df is None:
        diagnostic_profile_df = pd.read_csv('M2_Supplier_Diagnostic_Profile.csv')
    pool_view = run_strategic_pool_view(adj_cost_df, esg_fit_df, diagnostic_profile_df, scored)

    # ========== Configuration contamination verification ==========
    print(f"\n{'='*60}")
    print(f"Configuration Contamination Verification")
    print(f"{'='*60}")

    # Verify 1: SUB_WEIGHTS deep copy protection
    _before_sub = {k: dict(v) for k, v in SUB_WEIGHTS.items()}
    run_m2_scoring(df, sub_weights_override={'Cost': {'C1_Base_Cost_Proxy': 0.5}}, save_subindicator_csv=False)
    _sub_unchanged = SUB_WEIGHTS == _before_sub
    print(f"  [SUB_WEIGHTS] Deep copy protection: {'PASS' if _sub_unchanged else 'FAIL'} (global SUB_WEIGHTS unchanged)")

    # Verify 2: config_overrides restore old value
    _carbon_before = M2_CONFIG['CARBON_TAX_PER_TON']
    run_m2_scoring(df, config_overrides={'CARBON_TAX_PER_TON': 200}, save_subindicator_csv=False)
    _carbon_after = M2_CONFIG['CARBON_TAX_PER_TON']
    _carbon_ok = _carbon_after == _carbon_before
    print(f"  [CARBON_TAX_PER_TON] Old value restored: {'PASS' if _carbon_ok else 'FAIL'} "
          f"(expected {_carbon_before}, actual {_carbon_after})")
