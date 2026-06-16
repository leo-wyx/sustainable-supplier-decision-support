# ==========================================
# Model1.py — Supplier Qualification Gate v3
#
# M1 单一职责：供应商资格审核，不评分、不分 allocation。
#   六门禁（财务/质量/技术/道德/合规/劳工）→ 三态决策:
#   PASS       → ACTIVE_POOL        (正常采购候选池)
#   LIMITED    → CONDITIONAL_POOL   (受限使用，cap + penalty)
#   FAIL       → RESERVE_POOL       (备胎/参考池，保留不激活)
# M1 不做: 评分 (M2)、分配决策 (M3/MILP)、备胎激活 (M3)
#
# 所有阈值引用 strategy_config，通过 config 统一管理。
# ==========================================
import os
import pandas as pd
import numpy as np

# 当前年份（自动适配，无需每年改代码）
CURRENT_YEAR = pd.Timestamp.today().year


def load_suppliers_data(filepath="suppliers_data.csv"):
    """读取原始供应商 CSV 并返回 DataFrame"""
    df = pd.read_csv(filepath)
    print(f"已加载 {len(df)} 家供应商数据: {filepath}")
    return df


# ==========================================
# 风险类型 → 业务影响映射
# ==========================================
RISK_BUSINESS_IMPACT = {
    'Labor':       ('供应中断',   '强制劳工风险 — 法律禁止采购，不可赦免'),
    'Compliance':  ('合规违约',   '冲突矿物合规不达标 — 面临出口管制/罚款风险'),
    'Finance':     ('财务断裂',   '供应商财务困境 — Altman Z 低于阈值，有破产风险'),
    'Quality':     ('质量事故',   '良率/认证不达标 — 可能导致产线停线或召回'),
    'Tech':        ('技术瓶颈',   '技术评分/出口管制受限 — 无法满足下一代产品需求'),
    'Ethics':      ('声誉风险',   '腐败指数超标 — 可能引发品牌声誉损失或法律调查'),
    'None':        ('无风险',     '全部门禁通过'),
}


# ==========================================
# 六门过滤 / Six Gates
# ==========================================
def _map_gates(df, strategy='Balanced', cfg=None, current_year=None):
    """计算 6 个二值门禁 + 全量风险向量 + 三态决策

    所有阈值从 strategy_config.THRESHOLDS 读取（不硬编码），
    可通过 config 实现 What-If 模拟。

    Args:
        df: 供应商 DataFrame
        strategy: 策略名称
        cfg: StrategyConfig 对象（None = 自动加载）
        current_year: 模拟年份（None = 系统当前年），可通过此参数注入

    输出附加字段:
      Gate_*          — 6 个二值门禁结果
      M1_Risk_Vector  — 全量风险向量（所有门禁失败记录）
      fail_reason_hard/soft — P0/P1 失败原因字符串
      M1_Status/M1_Risk_Type/M1_Pool/M1_Action/M1_Penalty/M1_Capacity_Cap
    """
    if cfg is None:
        from strategy_config import get_strategy
        cfg = get_strategy(strategy)
    from strategy_config import THRESHOLDS
    t = THRESHOLDS
    sim_year = current_year if current_year is not None else pd.Timestamp.today().year

    mapper = df.copy()

    # ───────── Gate_Finance (vectorized) ─────────
    min_z = t['FINANCE']['min_z_score']
    req_status = t['FINANCE']['status_required']
    mapper['Gate_Finance'] = (
        (mapper['status'] == req_status) &
        (mapper['altman_z_score'] >= min_z)
    ).astype(int)

    # ───────── Gate_Quality ─────────
    min_yield_key = t['QUALITY']['min_yield_key_component']
    min_yield_gen = t['QUALITY']['min_yield_general']
    key_cert = t['QUALITY']['key_component_cert']
    gen_cert_keywords = t['QUALITY']['general_cert_keywords']

    def evaluate_quality(r):
        cert = str(r['cert_type'])
        expiry = r['cert_expiry_year']
        if pd.isna(expiry) or expiry < sim_year:
            return 0
        if r['category'] == 'Key_Component':
            return 1 if key_cert in cert and r['yield_rate'] >= min_yield_key else 0
        if r['category'] in ('General_Comp', 'Critical_Raw', 'General_Raw'):
            cert_ok = any(kw in cert for kw in gen_cert_keywords)
            return 1 if cert_ok and r['yield_rate'] >= min_yield_gen else 0
        return 0
    mapper['Gate_Quality'] = mapper.apply(evaluate_quality, axis=1).astype(int)

    # ───────── Gate_Tech ─────────
    # 受出口管制且无 IATF → FAIL（受管制电池技术/关键矿物需 IATF 级质控）
    min_rating_map = t['TECH']['min_rating']

    def evaluate_tech(r):
        if pd.notna(r['cert_type']) and 'IATF' in str(r['cert_type']):
            return 1
        if str(r.get('export_control_restricted', False)) == 'True':
            return 0
        threshold = min_rating_map.get(r['category'])
        if threshold is None:
            print(f"  [WARNING] Gate_Tech: 未知品类 '{r['category']}', 使用默认阈值 4.5")
            threshold = 4.5
        return 1 if r['rating'] >= threshold else 0
    mapper['Gate_Tech'] = mapper.apply(evaluate_tech, axis=1).astype(int)

    # ───────── Gate_Ethics ─────────
    cpi_map = t['ETHICS']['country_cpi']
    cpi_threshold = t['ETHICS']['cpi_threshold']
    cmrt_bonus = t['ETHICS']['cmrt_bonus']

    mapper['ethics_score_raw'] = mapper['country'].map(cpi_map).fillna(0.85)
    mapper['ethics_audit_bonus'] = mapper['cmrt_audit'].astype(float) * cmrt_bonus
    mapper['Gate_Ethics'] = (mapper['ethics_score_raw'] + mapper['ethics_audit_bonus'] >= cpi_threshold).astype(int)

    # ───────── Gate_Compliance ─────────
    cmrt_categories = t['COMPLIANCE']['cmrt_required_categories']
    mapper['Gate_Compliance'] = mapper.apply(
        lambda r: 1 if r['category'] in cmrt_categories and r['cmrt_audit']
        else (1 if r['category'] not in cmrt_categories else 0),
        axis=1
    ).astype(int)

    # ───────── Gate_Labor ─────────
    mapper['Gate_Labor'] = mapper.apply(
        lambda r: 0 if r.get('forced_labor_risk', False)
        else (1 if pd.notna(r['cert_type']) and 'IATF' in str(r['cert_type'])
        else (1 if r.get('rba_audit_pass', False)
        else 0)),
        axis=1
    ).astype(int)

    # ==========================================
    # 全量风险向量 + fail_reason（所有门禁算完再组合，不短路）
    # ==========================================
    gate_names = {
        'Gate_Quality': 'Quality', 'Gate_Finance': 'Finance',
        'Gate_Tech': 'Tech', 'Gate_Ethics': 'Ethics',
        'Gate_Compliance': 'Compliance', 'Gate_Labor': 'Labor',
    }
    # 所有门禁列
    gate_cols = list(gate_names.keys())
    failed = (1 - mapper[gate_cols]).astype(bool)
    failed = failed.rename(columns=gate_names)

    # M1_Risk_Vector: 结构化的全量风险记录
    mapper['M1_Risk_Vector'] = failed.apply(
        lambda row: '|'.join([col for col in failed.columns if row[col]]),
        axis=1
    )
    mapper['M1_Risk_Vector'] = mapper['M1_Risk_Vector'].replace('', 'None')

    # fail_reason_hard / soft（向后兼容）
    hard_names = ['Labor', 'Compliance', 'Finance']
    soft_names = ['Quality', 'Tech', 'Ethics']
    mapper['fail_reason_hard'] = failed[hard_names].apply(
        lambda r: '|'.join([c for c in hard_names if r[c]]), axis=1
    )
    mapper['fail_reason_soft'] = failed[soft_names].apply(
        lambda r: '|'.join([c for c in soft_names if r[c]]), axis=1
    )
    mapper['fail_reason'] = (
        mapper['fail_reason_hard'] + '|' + mapper['fail_reason_soft']
    ).str.strip('|').replace('', 'PASS')

    # ==========================================
    # M1_Status 五维决策 + 资源池分配
    # ==========================================
    def decide_status_v2(r, gate_cols=gate_cols, current_cfg=cfg):
        """返回 (status, risk_type, pool, action, penalty, capacity_cap, decision_reason, business_impact, risk_level)

        全量门禁已算完，此处只做优先级判定，不再短路门禁计算。
        penalty/cap 全部从 strategy_config 读取，拒绝硬编码。
        """
        # P0 零容忍 → FAIL
        # 注意：forced_labor_risk=True = 确认存在强制劳工风险 → 硬排除/blacklist
        #       forced_labor_risk=False 但无 IATF/RBA = 缺少劳工合规证明 → 排除至提交整改证据
        # 两种场景业务含义不同，但 M1 输出同为 FAIL（企业应区分审计路径）
        if r['Gate_Labor'] == 0:
            if r.get('forced_labor_risk', False):
                reason = ('Confirmed forced labor risk / 确认存在强制劳工风险 → excluded (hard exclusion)')
            else:
                reason = ('Missing labor assurance: no IATF or RBA audit evidence / '
                          '缺少劳工合规保障：无 IATF 或 RBA 审计证明 → excluded until remediation evidence provided')
            return ('FAIL', 'Labor', 'RESERVE_BLACKLIST', 'Excluded', 0.0, 0.0,
                    reason,
                    RISK_BUSINESS_IMPACT['Labor'][1], 'CRITICAL')
        if r['Gate_Compliance'] == 0:
            return ('FAIL', 'Compliance', 'RESERVE_BLACKLIST', 'Excluded', 0.0, 0.0,
                    f'Compliance audit failed: CMRT missing or not approved / '
                    f'合规审计失败：CMRT 缺失或未通过 (cmrt_audit={r["cmrt_audit"]}) → excluded',
                    RISK_BUSINESS_IMPACT['Compliance'][1], 'CRITICAL')
        if r['Gate_Finance'] == 0:
            z = r['altman_z_score']
            return ('FAIL', 'Finance', 'RESERVE_FINANCE', 'Override required', 0.0, 0.0,
                    f'Financial distress risk: Altman Z below threshold / '
                    f'财务风险：Altman Z 低于准入阈值 (Altman Z={z:.2f}) → reserve review',
                    RISK_BUSINESS_IMPACT['Finance'][1], 'HIGH')
        # P1 可整改 → LIMITED_QUALITY_TECH  (penalty/cap from strategy config)
        if r['Gate_Quality'] == 0:
            return ('LIMITED_QUALITY_TECH', 'Quality', 'CONDITIONAL_POOL',
                    f'Limited allocation (cap={current_cfg.quality_tech_cap:.0%}) + cost penalty x{current_cfg.quality_tech_penalty:.2f}',
                    current_cfg.quality_tech_penalty, current_cfg.quality_tech_cap,
                    f'Quality gate failed: yield or certification below requirement / '
                    f'质量门禁未通过：良率或认证未达要求 (yield={r["yield_rate"]:.2f}, cert={r["cert_type"]}) → limited allocation',
                    RISK_BUSINESS_IMPACT['Quality'][1], 'MEDIUM')
        if r['Gate_Tech'] == 0:
            return ('LIMITED_QUALITY_TECH', 'Tech', 'CONDITIONAL_POOL',
                    f'Limited allocation (cap={current_cfg.quality_tech_cap:.0%}) + cost penalty x{current_cfg.quality_tech_penalty:.2f}',
                    current_cfg.quality_tech_penalty, current_cfg.quality_tech_cap,
                    f'Technology gate failed: rating or export-control below requirement / '
                    f'技术门禁未通过：评级或出口管制条件未达要求 (rating={r["rating"]:.1f}, export_control={r.get("export_control_restricted", False)}) → limited allocation',
                    RISK_BUSINESS_IMPACT['Tech'][1], 'MEDIUM')
        # P2 道德 → LIMITED_ETHICS  (penalty/cap from strategy config)
        if r['Gate_Ethics'] == 0:
            return ('LIMITED_ETHICS', 'Ethics', 'CONDITIONAL_POOL',
                    f'Backup only (cap={current_cfg.ethics_cap:.0%}) + high cost penalty x{current_cfg.ethics_penalty:.2f}',
                    current_cfg.ethics_penalty, current_cfg.ethics_cap,
                    f'Ethics risk: CPI and audit score below threshold / '
                    f'道德风险：CPI 与审计加分后仍低于阈值 (CPI={r.get("ethics_score_raw", 0):.2f}) → backup only',
                    RISK_BUSINESS_IMPACT['Ethics'][1], 'LOW')
        return ('PASS', 'None', 'ACTIVE_POOL', 'Full allocation', 1.0, 1.0,
                'All qualification gates passed / 全部门禁通过 → full allocation',
                RISK_BUSINESS_IMPACT['None'][1], 'NONE')

    mapper[['M1_Status', 'M1_Risk_Type', 'M1_Pool', 'M1_Action',
            'M1_Penalty', 'M1_Capacity_Cap',
            'M1_Decision_Reason', 'M1_Business_Impact', 'M1_Risk_Level']] = \
        mapper.apply(decide_status_v2, axis=1, result_type='expand')

    # 备胎标记 — M1 不激活，保留供下游 scenario analysis 使用
    mapper['M1_Is_Reserve'] = False

    # 惩罚后实际成本 (Penalty-Adjusted Spend) — 供下游采购决策参考
    mapper['M1_Penalty_Adjusted_Spend'] = mapper['M1_Penalty'] * mapper['annual_contract_value_usd']

    # 真实风险敞口 (Risk Exposure) — 供应商不可用的潜在损失
    #   PASS    = 0                            (无风险)
    #   LIMITED = annual_contract * (penalty-1) (额外成本 uplift)
    #   FAIL    = annual_contract              (全部不可用)
    mapper['M1_Risk_Exposure'] = np.where(
        mapper['M1_Status'] == 'PASS', 0,
        np.where(mapper['M1_Penalty'] > 1.0,
                 mapper['annual_contract_value_usd'] * (mapper['M1_Penalty'] - 1),
                 mapper['annual_contract_value_usd'])
    )

    return mapper


# ==========================================
# M1 主入口 — 资格审核 + 风险分类 + 资源池分配
# ==========================================
def run_m1(df, strategy='Balanced', config_overrides=None, reserve_prefix='', current_year=None):
    """供应商资格审核与风险控制

    M1 单一职责: 门禁计算 → 三态决策 → 资源池分配
    不做: 评分 (M2)、分配决策 (M3/MILP)

    Parameters
    ----------
    df : DataFrame
        原始供应商数据
    strategy : str
        策略名称（影响 penalty/cap 参数）
    config_overrides : dict or None
        策略配置覆盖（供 M4 压力测试注入）
    reserve_prefix : str
        备胎池 CSV 文件名前缀（供 M4 并发多策略使用），
        如 'Cost_Focused' → 'Cost_Focused_reserve_pool.csv'
    current_year : int or None
        模拟年份（None = 系统当前年），M4 通过此参数注入

    Returns
    -------
    DataFrame : 仅 PASS + LIMITED（FAIL 已分流至 Reserve Pool CSV）
    """
    from strategy_config import get_strategy
    cfg = get_strategy(strategy)

    # M4 压力测试注入：允许覆盖策略配置参数（如 penalty/cap）
    if config_overrides:
        for k, v in config_overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
                print(f"  [M4 Override] {k} = {v}")

    df = df.copy()
    df = _map_gates(df, strategy, cfg, current_year=current_year)

    gates = ['Gate_Quality', 'Gate_Finance', 'Gate_Tech',
             'Gate_Ethics', 'Gate_Compliance', 'Gate_Labor']

    total = len(df)
    pass_ct = (df['M1_Status'] == 'PASS').sum()
    cond_qt = (df['M1_Status'] == 'LIMITED_QUALITY_TECH').sum()
    cond_et = (df['M1_Status'] == 'LIMITED_ETHICS').sum()
    fail_ct = (df['M1_Status'] == 'FAIL').sum()

    print(f"\nM1 Supplier Qualification Result / M1 供应商资质审核结果")
    print(f"  PASS={pass_ct} | LIMITED_QT={cond_qt} | LIMITED_ETH={cond_et} | FAIL={fail_ct} | 总计={total}")

    # 各门禁通过率
    print(f"\n  门禁通过率 / Gate pass rates:")
    for g in gates:
        rate = df[g].mean()
        flag = '[!]' if rate < 0.60 else ('[-]' if rate < 0.80 else '[OK]')
        print(f"    {flag} {g}: {rate:.1%} ({int(df[g].sum())}/{total})")

    # 删除门禁辅助列
    drop_cols = [c for c in gates if c in df.columns] + \
                ['fail_reason', 'fail_reason_hard', 'fail_reason_soft', 'ethics_score_raw', 'ethics_audit_bonus']
    result = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

    # 构造动态备胎文件名（M4 多策略并发时通过 reserve_prefix 区分）
    # M4 多策略: 传 reserve_prefix 区分文件名; 缺省兼容旧调用
    _reserve_csv = f"{reserve_prefix}_reserve_pool.csv" if reserve_prefix else "supplier_reserve_pool.csv"

    # ── FAIL → Reserve Pool CSV ──
    fail_df = result[result['M1_Status'] == 'FAIL'].copy()
    if len(fail_df) > 0:
        reserve_cols = ['supplier_id', 'supplier_name', 'M1_Status', 'M1_Risk_Type',
                        'M1_Risk_Vector',
                        'M1_Pool', 'M1_Action', 'M1_Decision_Reason',
                        'M1_Business_Impact', 'M1_Risk_Level',
                        'country', 'category', 'sub_category', 'material_service',
                        'rating', 'annual_contract_value_usd',
                        'yield_rate', 'defect_rate_ppm', 'lead_time_days',
                        'cert_type', 'cert_expiry_year', 'altman_z_score',
                        'cmrt_audit', 'rba_audit_pass', 'forced_labor_risk',
                        'carbon_intensity', 'pcf_commitment', 'export_control_restricted',
                        'M1_Penalty', 'M1_Capacity_Cap', 'M1_Risk_Exposure',
                        'M1_Penalty_Adjusted_Spend']
        reserve_df = fail_df[[c for c in reserve_cols if c in fail_df.columns]].copy()
        reserve_df.loc[:, 'override_flag'] = False
        reserve_df.loc[:, 'override_reason'] = ''
        reserve_df = reserve_df.astype({'override_flag': 'bool', 'override_reason': 'object'})
        reserve_df.to_csv(_reserve_csv, index=False, encoding='utf-8-sig')
        print(f"\n  [Reserve Pool] {len(fail_df)} 家 FAIL 已写入 {_reserve_csv}")

    # ── PASS + LIMITED 进入候选池（不含 FAIL）──
    active = result[result['M1_Status'] != 'FAIL'].reset_index(drop=True)

    return active


# ==========================================
# TRIGGERS — 标准化触发条件（阈值全部来自 strategy_config）
# ==========================================
def _make_triggers(overrides=None):
    """从 config 读取阈值，构造标准化触发条件 dict

    返回 dict[str, callable]，每个 callable 接受指标值 → bool
    加新触发 = 加一行配置 + 加一行 lambda，不改逻辑

    Parameters
    ----------
    overrides : dict or None
        M4 压力测试注入的阈值覆盖（如 {'fail_critical_pct': 30}）
    """
    from strategy_config import TRIGGER_THRESHOLDS as T
    if overrides:
        T = dict(T)
        T.update(overrides)
    return {
        'coverage_low':      lambda v: v < T['coverage_low_pct'],
        'fail_high':         lambda v: v > T['fail_high_pct'],
        'fail_critical':     lambda v: v > T['fail_critical_pct'],
        'concentration_high': lambda v: v > T['concentration_high_pct'],
        'cost_high':         lambda v: v > T['cost_high_pct'],
        'sys_cost_acceptable': lambda v: v < T['sys_cost_acceptable_pct'],
        'high_risk_category_count': lambda v: v >= T['high_risk_category_count'],
    }


def _category_actions(cat_name, cat_data, trigger_overrides=None):
    """品类级触发评估：指标 → 结构化决策建议

    Parameters
    ----------
    cat_name : str
    cat_data : dict
        品类分析数据（from _category_analysis）
    trigger_overrides : dict or None
        M4 压力测试注入的阈值覆盖
    """
    triggers = _make_triggers(overrides=trigger_overrides)
    actions = []

    coverage = cat_data['coverage_pct']
    fail_rate_pct = cat_data['fail_rate'] * 100  # 0.60 → 60% 匹配配置
    cost_up = cat_data['cost_uplift_pct']
    concentration = cat_data['top_country_share_pct']
    main_risk = cat_data['main_risk_type']

    from strategy_config import TRIGGER_THRESHOLDS as TT

    # 1) 覆盖率低 → 补供应商
    if triggers['coverage_low'](coverage):
        gap = max(1, int((100 - coverage) / 20))
        actions.append({
            'type': 'ONBOARD_SUPPLIER',
            'priority': 'HIGH' if triggers['fail_high'](fail_rate_pct) else 'MEDIUM',
            'target': gap,
            'rationale': f'coverage={coverage:.0f}% < {TT["coverage_low_pct"]}%',
        })

    # 2) FAIL 率超高 → 升级人类决策
    if triggers['fail_critical'](fail_rate_pct):
        actions.append({
            'type': 'ESCALATE',
            'priority': 'CRITICAL',
            'issue': f'{cat_name}: fail_rate={fail_rate_pct:.0f}%',
            'rationale': '系统无法自行解决，需要采购团队决策',
        })

    # 3) FAIL 率高 → reserve pool 保留供 sourcing team review
    if triggers['fail_high'](fail_rate_pct) and main_risk != '—':
        if main_risk in ('Finance', 'Quality', 'Tech', 'Ethics'):
            actions.append({
                'type': 'RESERVE_REVIEW_AVAILABLE',
                'priority': 'HIGH',
                'constraint': f'{main_risk} only',
                'rationale': f'fail_rate={fail_rate_pct:.0f}%, reserve pool retained for sourcing team review',
            })

    # 4) 成本增幅大 → 审查
    if triggers['cost_high'](cost_up):
        actions.append({
            'type': 'REVIEW_COST',
            'priority': 'HIGH',
            'threshold_exceeded_pct': cost_up,
            'rationale': f'cost_uplift={cost_up:.1f}% > {TT["cost_high_pct"]}%',
        })

    # 5) 国家集中度高 → 多元化建议
    if triggers['concentration_high'](concentration) and cat_data['top_country'] not in ('—',):
        actions.append({
            'type': 'DIVERSIFY_SOURCE',
            'priority': 'MEDIUM',
            'dominant_country': cat_data['top_country'],
            'current_share_pct': int(concentration),
            'rationale': f'{cat_data["top_country"]} 占 {concentration:.0f}%, '
                         f'超过 {TT["concentration_high_pct"]}% 阈值',
        })

    return actions


def _system_actions(diagnostics, trigger_overrides=None):
    """系统级触发评估"""
    from strategy_config import TRIGGER_THRESHOLDS as TT
    triggers = _make_triggers(overrides=trigger_overrides)
    actions = []
    overview = diagnostics['overview']

    # 高风险品类数
    cat_detail = diagnostics.get('categories', {})
    high_risk_count = sum(
        1 for ci in cat_detail.values() if ci.get('shortage_risk') == 'HIGH'
    )

    if triggers['high_risk_category_count'](high_risk_count):
        actions.append({
            'type': 'ESCALATE',
            'priority': 'CRITICAL',
            'issue': f'{high_risk_count} 个品类处于 HIGH 短缺风险',
            'rationale': f'≥{TT["high_risk_category_count"]} 个 HIGH 风险品类需要管理干预',
        })

    # 成本影响
    cost = diagnostics.get('cost_impact', {})
    cost_pct = cost.get('estimated_cost_increase_pct', 0)
    if triggers['sys_cost_acceptable'](cost_pct):
        actions.append({
            'type': 'ACCEPT_COST',
            'priority': 'LOW',
            'estimated_increase_pct': cost_pct,
            'rationale': f'系统成本上升 +{cost_pct:.1f}%, 在 {TT["sys_cost_acceptable_pct"]}% 可接受范围内',
        })

    # 总敞口通报
    exp = diagnostics.get('exposure', {})
    actions.append({
        'type': 'INFO',
        'priority': 'INFO',
        'message': f'总风险敞口 ${exp.get("total", 0)/1e6:.1f}M, '
                   f'PASS {exp.get("pass_share", 0):.0f}% + LIMITED {exp.get("limited_share", 0):.0f}%',
    })

    return actions


# ==========================================
# M1 Impact Analysis — 决策建议层
# ==========================================
def m1_impact_analysis(raw_df, active_df, reserve_csv='supplier_reserve_pool.csv', trigger_overrides=None):
    """M1 影响分析 + 决策建议

    Parameters
    ----------
    trigger_overrides : dict or None
        M4 压力测试注入的阈值覆盖

    输出结构以 actions 为核心，diagnostics 为证据支撑：
      actions           — 系统级决策建议（给管理层）
      category_actions  — 品类级决策建议（给采购/分析师）
      diagnostics       — 原始诊断数据（给分析师）

    Parameters
    ----------
    raw_df : DataFrame
        原始全量供应商数据（含 FAIL）
    active_df : DataFrame
        run_m1 返回的活跃池（PASS + LIMITED）
    reserve_csv : str
        备胎池 CSV 路径

    Returns
    -------
    dict : {actions, category_actions, diagnostics}
    """
    from strategy_config import DEMAND_RATIO, TRIGGER_THRESHOLDS as T
    import math

    # 读取备胎池
    try:
        fail_df = pd.read_csv(reserve_csv)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        fail_df = pd.DataFrame()

    # DEMAND_RATIO ≈ scenario proxy (不是真实企业需求预测)
    # 在真实企业环境中应由 procurement plan / MRP / ERP 数据替代
    cat_totals = raw_df.groupby('category')['annual_contract_value_usd'].sum()

    diagnostics = {'overview': {}, 'categories': {}, 'cost_impact': {}, 'exposure': {}}

    # ─── 系统概览 ───
    n_pass = int((active_df['M1_Status'] == 'PASS').sum())
    n_lim = int(active_df['M1_Status'].isin(['LIMITED_QUALITY_TECH', 'LIMITED_ETHICS']).sum())
    n_fail = len(fail_df)
    total = n_pass + n_lim + n_fail
    diagnostics['overview'] = {
        'total': total, 'pass': n_pass, 'limited': n_lim, 'fail': n_fail,
        'pass_rate': round(n_pass / total, 3) if total > 0 else 0,
    }

    # ─── 品类级诊断 ───
    categories = sorted(raw_df['category'].unique())
    for cat in categories:
        cat_active = active_df[active_df['category'] == cat]
        cat_fail = fail_df[fail_df['category'] == cat] if len(fail_df) > 0 else pd.DataFrame()

        n_cat_pass = int((cat_active['M1_Status'] == 'PASS').sum())
        n_cat_lim = int(cat_active['M1_Status'].isin(['LIMITED_QUALITY_TECH', 'LIMITED_ETHICS']).sum())
        n_cat_fail = len(cat_fail)
        cat_total = n_cat_pass + n_cat_lim + n_cat_fail
        pass_rate = n_cat_pass / cat_total if cat_total > 0 else 0
        fail_rate = n_cat_fail / cat_total if cat_total > 0 else 0

        # 短缺风险
        if fail_rate >= 0.40:
            shortage_risk = 'HIGH'
        elif fail_rate >= 0.20:
            shortage_risk = 'MEDIUM'
        else:
            shortage_risk = 'LOW'

        # 产能覆盖率估算 (scenario proxy — 基于历史合同金额 × DEMAND_RATIO 估算)
        # 在真实企业环境中应由 supplier committed capacity / 采购计划数据替代
        active_capacity = cat_active['annual_contract_value_usd'].sum()
        total_demand_estimate = cat_totals.get(cat, 0) * DEMAND_RATIO
        coverage_pct = round(active_capacity / total_demand_estimate * 100, 1) if total_demand_estimate > 0 else 0

        # 成本增幅
        cat_limited = cat_active[cat_active['M1_Penalty'] > 1.0]
        if len(cat_limited) > 0:
            avg_penalty = cat_limited['M1_Penalty'].mean()
            limited_share = cat_limited['annual_contract_value_usd'].sum() / cat_active['annual_contract_value_usd'].sum() if cat_active['annual_contract_value_usd'].sum() > 0 else 0
            cost_uplift = round((avg_penalty - 1.0) * limited_share * 100, 1)
        else:
            cost_uplift = 0.0

        # 主要风险类型
        main_risk = cat_fail['M1_Risk_Type'].value_counts().index[0] if len(cat_fail) > 0 else '—'
        impact_label = RISK_BUSINESS_IMPACT.get(main_risk, ('未知', ''))[0] if main_risk != '—' else '—'

        # 国家集中度
        countries = cat_active['country'].value_counts()
        top_country = countries.index[0] if len(countries) > 0 else '—'
        top_country_share = round(countries.iloc[0] / countries.sum() * 100, 0) if len(countries) > 0 else 0

        # 业务叙事
        if fail_rate >= 0.30:
            narrative = (
                f"仅 {pass_rate:.0%} PASS 率 → {shortage_risk} 短缺风险。"
                f"{int(n_cat_fail)}/{cat_total} 供应商 FAIL（{main_risk}: {impact_label}）。"
                f"有效产能覆盖需求 {coverage_pct:.0f}%"
            )
        elif n_cat_lim > 0:
            narrative = (
                f"{pass_rate:.0%} PASS 率，{int(n_cat_lim)} 家 LIMITED。"
                f"成本预估上升 {cost_uplift:.1f}%，集中度风险: {top_country}({top_country_share:.0f}%)"
            )
        else:
            narrative = f"健康品类: {pass_rate:.0%} PASS 率，产能充足，无集中度风险"

        diagnostics['categories'][cat] = {
            'pass': n_cat_pass, 'limited': n_cat_lim, 'fail': n_cat_fail,
            'total': cat_total,
            'pass_rate': round(pass_rate, 3), 'fail_rate': round(fail_rate, 3),
            'shortage_risk': shortage_risk, 'coverage_pct': coverage_pct,
            'cost_uplift_pct': cost_uplift, 'main_risk_type': main_risk,
            'main_risk_impact': impact_label,
            'top_country': top_country, 'top_country_share_pct': int(top_country_share),
            'narrative': narrative,
        }

    # ─── 系统级成本影响 ───
    limited_all = active_df[active_df['M1_Penalty'] > 1.0]
    if len(limited_all) > 0:
        avg_penalty_all = limited_all['M1_Penalty'].mean()
        limited_value_share = limited_all['annual_contract_value_usd'].sum() / active_df['annual_contract_value_usd'].sum() if active_df['annual_contract_value_usd'].sum() > 0 else 0
        sys_cost_uplift = round((avg_penalty_all - 1.0) * limited_value_share * 100, 1)
    else:
        avg_penalty_all = 1.0
        sys_cost_uplift = 0.0

    diagnostics['cost_impact'] = {
        'limited_count': int(len(limited_all)),
        'limited_avg_penalty': round(avg_penalty_all, 3),
        'limited_value_share': round(limited_value_share, 3) if len(limited_all) > 0 else 0,
        'estimated_cost_increase_pct': sys_cost_uplift,
    }

    # ─── 风险敞口分析 ───
    total_exposure = active_df['M1_Risk_Exposure'].sum()
    lim_exposure = active_df[active_df['M1_Penalty'] > 1.0]['M1_Risk_Exposure'].sum()
    fail_exposure = fail_df['M1_Risk_Exposure'].sum() if len(fail_df) > 0 else 0
    total_exposure_with_fail = total_exposure + fail_exposure

    combined_risk = pd.concat([
        active_df[['supplier_id', 'supplier_name', 'country', 'category',
                    'M1_Status', 'M1_Penalty', 'annual_contract_value_usd',
                    'M1_Risk_Exposure', 'M1_Penalty_Adjusted_Spend']],
        fail_df[['supplier_id', 'supplier_name', 'M1_Status', 'M1_Risk_Type', 'M1_Risk_Vector',
                 'M1_Pool', 'M1_Action', 'M1_Decision_Reason',
                 'M1_Business_Impact', 'M1_Risk_Level',
                 'country', 'category',
                 'annual_contract_value_usd', 'M1_Penalty', 'M1_Capacity_Cap',
                 'M1_Risk_Exposure', 'M1_Penalty_Adjusted_Spend']]
    ], ignore_index=True) if len(fail_df) > 0 else active_df.copy()

    top_risk = combined_risk.nlargest(10, 'M1_Risk_Exposure')[
        ['supplier_id', 'supplier_name', 'country', 'category',
         'M1_Status', 'M1_Penalty', 'annual_contract_value_usd', 'M1_Risk_Exposure',
         'M1_Penalty_Adjusted_Spend']
    ]

    diagnostics['exposure'] = {
        'total': round(total_exposure_with_fail, 0),
        'limited_share': round(lim_exposure / total_exposure_with_fail * 100, 1) if total_exposure_with_fail > 0 else 0,
        'fail_share': round(fail_exposure / total_exposure_with_fail * 100, 1) if total_exposure_with_fail > 0 else 0,
        'top_10_suppliers': top_risk.to_dict('records'),
    }

    # ===================================================================
    # 决策建议层 — 以 actions 为核心输出
    # ===================================================================

    # 品类级 actions
    category_actions = {}
    for cat in categories:
        cat_data = diagnostics['categories'][cat]
        acts = _category_actions(cat, cat_data, trigger_overrides=trigger_overrides)
        if acts:
            category_actions[cat] = acts

    # 系统级 actions
    actions = _system_actions(diagnostics, trigger_overrides=trigger_overrides)

    # ─── CLI 输出：先打 actions，再打 diagnostics ───
    print(f"\n{'='*90}")
    print(f"  [M1 决策建议 / Decision Recommendations]")
    print(f"{'='*90}")

    if not actions and not category_actions:
        print(f"  [OK] 未触发任何动作 — 系统状态正常")
    else:
        # 系统级
        for a in actions:
            tag = '[!]' if a['priority'] in ('CRITICAL', 'HIGH') else ('[-]' if a['priority'] == 'MEDIUM' else ('[$]' if a['type'] == 'ACCEPT_COST' else '[*]'))
            if a['type'] == 'ACCEPT_COST':
                print(f"  {tag} {a['rationale']}")
            elif a['type'] == 'INFO':
                print(f"  {tag} {a['message']}")
            elif a['type'] == 'ESCALATE':
                print(f"  {tag} [升级] {a['issue']} — {a['rationale']}")
            else:
                print(f"  {tag} [{a['type']}] {a.get('rationale', '')}")

        # 品类级
        for cat, acts in category_actions.items():
            ci = diagnostics['categories'][cat]
            flag = '[!]' if ci['shortage_risk'] == 'HIGH' else ('[-]' if ci['shortage_risk'] == 'MEDIUM' else '[OK]')
            print(f"\n  {flag} {cat} ({ci['shortage_risk']} 风险, PASS={ci['pass']}/{ci['total']})")
            for a in acts:
                tag = '[!]' if a['priority'] in ('CRITICAL', 'HIGH') else '[-]'
                if a['type'] == 'ONBOARD_SUPPLIER':
                    print(f"    {tag} 新增供应商: 建议补 {a['target']} 家 (覆盖率 {ci['coverage_pct']:.0f}%)")
                elif a['type'] == 'RESERVE_REVIEW_AVAILABLE':
                    print(f"    {tag} 备胎池: sourcing team 可评估激活 {a['constraint']} ({a['rationale']})")
                elif a['type'] == 'REVIEW_COST':
                    print(f"    {tag} 成本审查: 成本超阈值 {a['threshold_exceeded_pct']:.1f}%")
                elif a['type'] == 'DIVERSIFY_SOURCE':
                    print(f"    [-] 来源多元化: {a['dominant_country']} 占比 {a['current_share_pct']}%, 建议拓展")
                elif a['type'] == 'ESCALATE':
                    print(f"    [!] [升级] {a['issue']} — {a['rationale']}")

    print(f"\n{'─'*90}")
    print(f"  [支撑数据 / Diagnostics]")
    print(f"{'─'*90}")
    print(f"  系统概览: PASS={n_pass}  LIMITED={n_lim}  FAIL={n_fail}  通过率={n_pass/total:.0%}")
    if sys_cost_uplift > 0:
        print(f"  成本影响: LIMITED 惩罚推高系统成本约 +{sys_cost_uplift:.1f}%")
    if total_exposure_with_fail > 0:
        print(f"  总风险敞口: ${total_exposure_with_fail/1e6:.1f}M (LIMITED {lim_exposure/total_exposure_with_fail:.0%} + Reserve {fail_exposure/total_exposure_with_fail:.0%})")
    else:
        print(f"  总风险敞口: $0 (无风险暴露)")
    print()

    # 品类面板
    print(f"  {'品类':20s} {'PASS':6s} {'LIM':5s} {'FAIL':5s} {'覆盖率':8s} {'成本↑':7s} {'风险':8s} {'主要问题'}")
    print(f"  {'-'*20} {'-'*6} {'-'*5} {'-'*5} {'-'*8} {'-'*7} {'-'*8} {'-'*25}")
    for cat in categories:
        ci = diagnostics['categories'][cat]
        flag = '[!]' if ci['shortage_risk'] == 'HIGH' else ('[-]' if ci['shortage_risk'] == 'MEDIUM' else '[OK]')
        cov = f"{ci['coverage_pct']:.0f}%" if ci['coverage_pct'] > 0 else 'N/A'
        cost = f"+{ci['cost_uplift_pct']:.1f}%" if ci['cost_uplift_pct'] > 0 else '—'
        issue = f"{ci['main_risk_type']}({ci['main_risk_impact']})" if ci['main_risk_type'] != '—' else '—'
        print(f"  {flag} {cat:17s} {ci['pass']:6d} {ci['limited']:5d} {ci['fail']:5d} {cov:8s} {cost:7s} {ci['shortage_risk']:8s} {issue}")

    # Top 风险暴露
    print(f"\n  Top 5 风险敞口 / Top Risk Exposure:")
    for _, r in top_risk.head(5).iterrows():
        flag = '[!]' if r['M1_Risk_Exposure'] > 5e6 else ('[-]' if r['M1_Risk_Exposure'] > 0 else '    ')
        print(f"  {flag} {r['supplier_id']:6s} {r['supplier_name']:18s} "
              f"contract=${r['annual_contract_value_usd']/1e6:.1f}M  "
              f"penalty={r['M1_Penalty']:.2f}  "
              f"cost_adj=${r['M1_Penalty_Adjusted_Spend']/1e6:.1f}M  "
              f"risk_exp=${r['M1_Risk_Exposure']/1e6:.1f}M")
    print(f"{'='*90}")

    return {
        'actions': actions,
        'category_actions': category_actions,
        'diagnostics': diagnostics,
    }


# ==========================================
# CLI 入口 — 简洁决策输出
# ==========================================
if __name__ == "__main__":
    df = load_suppliers_data()
    # 默认不带前缀，输出 supplier_reserve_pool.csv（兼容旧调用）
    result = run_m1(df, reserve_prefix='', current_year=None)

    # M1 影响分析（传 reserve_prefix 保持文件名一致）
    _reserve_csv = "supplier_reserve_pool.csv"
    m1_impact_analysis(raw_df=df, active_df=result, reserve_csv=_reserve_csv)

    print(f"\n{'='*90}")
    print(f"  M1 Supplier Qualification Result / M1 供应商资质审核结果（{CURRENT_YEAR} — Strategy: Balanced / 策略: 均衡）")
    print(f"{'='*90}")

    # ── PASS ──
    sub = result[result['M1_Status'] == 'PASS']
    if len(sub) > 0:
        print(f"\n[ACTIVE_POOL] PASS — Full allocation / 可全量分配")
        print(f"  {'ID':6s} {'Region':12s} {'Category':18s} {'Risk_Vector'}")
        print(f"  {'-'*6} {'-'*12} {'-'*18} {'-'*30}")
        for _, r in sub.iterrows():
            region = '中国' if r['country'] == 'China' else ('大马' if r['country'] == 'Malaysia' else r['country'])
            print(f"  {r['supplier_id']:6s} {region:12s} {r['category']:18s} {r['M1_Risk_Vector']}")

    # ── LIMITED ──
    sub = result[result['M1_Status'].isin(['LIMITED_QUALITY_TECH', 'LIMITED_ETHICS'])]
    if len(sub) > 0:
        print(f"\n[CONDITIONAL_POOL] LIMITED — Capped allocation / 受限分配")
        print(f"  {'ID':6s} {'Region':12s} {'Category':18s} {'Primary_Risk':14s} {'Penalty':8s} {'Cap':6s}")
        print(f"  {'-'*6} {'-'*12} {'-'*18} {'-'*14} {'-'*8} {'-'*6}")
        for _, r in sub.iterrows():
            region = '中国' if r['country'] == 'China' else ('大马' if r['country'] == 'Malaysia' else r['country'])
            pen = f"x{r['M1_Penalty']:.2f}"
            cap = f"{r['M1_Capacity_Cap']:.0%}"
            print(f"  {r['supplier_id']:6s} {region:12s} {r['category']:18s} {r['M1_Risk_Type']:14s} {pen:8s} {cap:6s}")

    # ── FAIL → Reserve Pool ──
    try:
        reserve = pd.read_csv(_reserve_csv)
        print(f"\n[RESERVE_POOL] FAIL — Reserve review / 备用池复核")
        print(f"  {'ID':6s} {'Region':12s} {'Category':18s} {'Primary_Risk':14s} {'Risk_Vector':36s} {'Pool'}")
        print(f"  {'-'*6} {'-'*12} {'-'*18} {'-'*14} {'-'*36} {'-'*20}")
        for _, r in reserve.iterrows():
            region = '中国' if r['country'] == 'China' else ('大马' if r['country'] == 'Malaysia' else r['country'])
            print(f"  {r['supplier_id']:6s} {region:12s} {r['category']:18s} {r['M1_Risk_Type']:14s} {r['M1_Risk_Vector']:36s} {r['M1_Pool']}")
        print(f"\n  [!] RESERVE_POOL retained for future scenario analysis / 备胎池保留供未来情景分析使用")
    except FileNotFoundError:
        pass

    # ── 一行摘要 ──
    n_fail = 0
    try:
        n_fail = len(pd.read_csv(_reserve_csv))
    except FileNotFoundError:
        pass
    print(f"\n  Pipeline Summary / 管线摘要: PASS={len(result[result['M1_Status']=='PASS'])}  "
          f"LIMITED={len(result[result['M1_Status'].isin(['LIMITED_QUALITY_TECH','LIMITED_ETHICS'])])}  "
          f"FAIL={n_fail}  → downstream to M2 scoring / 进入 M2 评分")
