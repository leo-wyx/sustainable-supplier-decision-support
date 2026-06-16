"""generate_data.py — 50 家供应商按人设（Archetype）生成 (SYNTHETIC DATASET)

⚠️ 重要声明 / Important Disclaimer:
  - suppliers_data.csv 是合成数据集 (synthetic dataset)，并非真实企业供应商数据
  - 所有供应商名称、人员、国家、城市、合同金额等均为虚构
  - 本数据集仅供演示 M1/M2 supplier decision support 工作流，不反映任何实际企业供应链状态
  - Seed=42 + 供应商人设表 (archetype-based) 确保每次生成数据完全可复现

设计要点:
  - 每位供应商有明确的"身份画像"（如龙头/骨干/新进入者/问题户），
    各维度相互绑定而非独立随机抽样，使数据看起来更真实
  - 含 5 种地雷供应商 (landmine suppliers)：故意设计的极端风险场景，
    用于测试 M1 六门禁能否正确捕获对应风险
    财务地雷 S01 | 劳工地雷 S18/S19 | 质量地雷 S26
    合规地雷 S12 | 道德地雷 S50
  - 数据不是真实公司供应商信息，Landmine 的极端值仅用于验证门禁逻辑
"""

import pandas as pd
import numpy as np

np.random.seed(42)

# ==========================================
# 1. 地理数据
# ==========================================
FOREIGN_CITY_MAP = {
    'Chile':        ['圣地亚哥', '安托法加斯塔'],
    'DRC':          ['卢本巴希', '科卢韦齐'],
    'Indonesia':    ['雅加达', '苏拉威西'],
    'South Korea':  ['首尔', '釜山'],
    'Japan':        ['东京', '大阪'],
    'Germany':      ['慕尼黑', '柏林'],
    'Australia':    ['悉尼', '珀斯'],
    'South Africa': ['约翰内斯堡', '开普敦'],
    'USA':          ['底特律', '芝加哥'],
}

CN_CITIES = ['宁德', '深圳', '上海', '广州', '宁波', '长沙', '成都', '青岛',
             '厦门', '天津', '武汉', '南京', '合肥', '常州', '东莞', '佛山',
             '梅州', '温州', '无锡', '赣州', '兰州', '湘潭', '荆门', '杭州',
             '苏州', '南昌', '西安', '郑州', '重庆', '沈阳', '芜湖', '宜春',
             '湖州', '新余', '桐乡', '昆山']

MY_CITIES = ['吉隆坡', '巴生', '槟城', '新山', '马六甲', '古晋', '亚庇',
             '怡保', '芙蓉', '莎阿南', '布城', '居林', '峇六拜', '关丹']

SUB_CATEGORIES = {
    'Critical_Raw':  ['lithium', 'cobalt', 'nickel'],
    'Key_Component': ['separator', 'electrolyte', 'cathode', 'bms'],
    'General_Raw':   ['graphite', 'copper_foil', 'manganese',
                      'recycled_material', 'alumina', 'zinc'],
    'General_Comp':  ['aluminum_shell', 'connector', 'busbar',
                      'fuse', 'thermal_management'],
}

MATERIAL_MAP = {
    'lithium': '碳酸锂', 'cobalt': '硫酸钴', 'nickel': '镍钴锰酸锂',
    'graphite': '人造石墨', 'copper_foil': '锂电铜箔',
    'manganese': '电解二氧化锰', 'recycled_material': '再生钴粉',
    'alumina': '高纯氧化铝', 'zinc': '锌粉添加剂',
    'separator': '湿法隔膜', 'electrolyte': '六氟磷酸锂',
    'cathode': '三元正极材料', 'bms': '电池管理系统',
    'thermal_management': '导热凝胶', 'aluminum_shell': '电池铝壳',
    'connector': '高压连接器', 'busbar': '铜铝复合汇流排',
    'fuse': '高压熔断器',
}

# MY 组装附加值范围（按 sub_category）
AVA_RANGES = {
    'cathode': (0.40, 0.50), 'electrolyte': (0.35, 0.50),
    'bms': (0.35, 0.50), 'separator': (0.30, 0.45),
    'thermal_management': (0.25, 0.40),
    'aluminum_shell': (0.20, 0.35), 'connector': (0.25, 0.40),
    'busbar': (0.20, 0.35), 'fuse': (0.20, 0.35),
    'graphite': (0.15, 0.30), 'copper_foil': (0.15, 0.30),
    'manganese': (0.10, 0.25), 'recycled_material': (0.12, 0.28),
    'alumina': (0.10, 0.25), 'zinc': (0.10, 0.20),
    'lithium': (0.10, 0.25), 'cobalt': (0.10, 0.20),
    'nickel': (0.10, 0.20),
}

# ==========================================
# 2. 供应商人设表 / Supplier Archetypes
# ==========================================
# 每位供应商占一行，字段明确赋值 ± 小范围 jitter（用 ~ 标注）
# Jitter 在 make_supplier 内部用 uniform 实现
#
# 5 种地雷标记 ★:
#   ★Finance  S01  Key_Component  CN  Z=1.50
#   ★Labor    S18  Critical_Raw   DRC forced_labor=True
#   ★Comply   S12  Key_Component  CN  cmrt=False
#   ★Quality  S26  General_Comp   CN  cert_expiry=2025 yield<0.95
#   ★Ethics   S50  General_Raw    ZA  cmrt=False

SUPPLIER_DEFS = [
    # ===== Key_Component (12 家) =====
    # ID  Country   City     Sub_cat  Cert     Rating Z      CMRT RBA  Yield   Expiry  Contract   Start  CI      FL  Pay  Landmine
    # --- 龙头 / 全球级 ---
    ('S01','China',  '宁德',   'cathode',   'IATF 16949', 5.00, 1.50, True, True,  0.993,  2027, 15_000_000, '2017-03-15', 0.680, False,'Net 45', '★Finance'),
    ('S02','Japan',  '东京',   'separator', 'IATF 16949', 4.90, 3.80, True, True,  0.997,  2028, 48_000_000, '2015-06-01', 0.280, False,'Net 60', ''),
    ('S05','South Korea','首尔','electrolyte','IATF 16949',4.85, 3.50, True, True,  0.995,  2028, 35_000_000, '2016-09-20', 0.320, False,'Net 45', ''),
    ('S09','Germany','慕尼黑', 'bms',       'IATF 16949', 4.95, 4.00, True, True,  0.998,  2028, 55_000_000, '2015-04-10', 0.150, False,'Net 60', ''),
    ('S10','South Korea','釜山','separator', 'ISO 9001',   4.60, 3.20, True, True,  0.978,  2027, 28_000_000, '2018-11-05', 0.350, False,'Net 45', ''),
    # --- 骨干 / 区域优质 ---
    ('S03','China',  '深圳',   'cathode',   'IATF 16949', 4.60, 3.00, True, True,  0.990,  2027, 22_000_000, '2017-08-12', 0.620, False,'Net 30', ''),
    ('S04','China',  '上海',   'electrolyte','IATF 16949',4.50, 2.80, True, True,  0.988,  2027, 20_000_000, '2018-02-20', 0.580, False,'Net 30', ''),
    ('S07','China',  '长沙',   'bms',       'IATF 16949', 4.40, 2.50, True, True,  0.985,  2026, 18_000_000, '2018-07-01', 0.550, False,'Net 30', ''),
    ('S08','Malaysia','槟城',  'cathode',   'IATF 16949', 4.50, 2.80, True, True,  0.987,  2027, 25_000_000, '2018-05-15', 0.420, False,'Net 45', ''),
    ('S11','Malaysia','吉隆坡','electrolyte','IATF 16949',4.30, 2.50, True, True,  0.983,  2026, 20_000_000, '2019-03-01', 0.450, False,'Net 45', ''),
    # --- 问题户 ---
    ('S06','China',  '广州',   'separator', 'ISO 9001',   3.80, 2.20, True, False, 0.965,  2025, 10_000_000, '2022-09-10', 0.640, False,'Net 30', '新进入者: RBA缺失→Labor FAIL(掩蔽Quality+Tech)'),
    ('S12','China',  '宁波',   'bms',    'IATF 16949', 4.50, 3.00, False, True, 0.992,  2027, 18_000_000, '2017-11-20', 0.570, False,'Net 30', '★Comply'),

    # ===== Critical_Raw (10 家) =====
    # ID  Country   City       Sub_cat   Cert     Rating Z     CMRT RBA   Yield  Expiry  Contract   Start      CI     FL       Pay     Landmine
    ('S13','China',  '成都',   'lithium',  'IATF 16949', 4.40, 2.60, True, True,  0.995,  2027, 25_000_000, '2018-04-01', 0.650, False,'Net 30', ''),
    ('S14','China',  '天津',   'cobalt',   'ISO 9001',   4.20, 2.30, True, True,  0.975,  2026, 20_000_000, '2019-06-15', 0.590, False,'Net 30', ''),
    ('S15','Chile',  '圣地亚哥','lithium',  'ISO 9001',   4.40, 2.50, True, True,  0.980,  2027, 35_000_000, '2019-08-20', 0.280, False,'Net 45', ''),
    ('S16','South Africa','约翰内斯堡','cobalt','ISO 9001',4.20, 2.20, True, True,  0.970,  2026, 30_000_000, '2020-03-10', 0.550, False,'Net 45', ''),
    ('S17','China',  '武汉',   'nickel',   'ISO 9001',   4.00, 2.00, True, False, 0.960,  2026, 18_000_000, '2020-07-01', 0.610, False,'Net 30', '无RBA→Labor FAIL'),
    # --- 地雷相关 ---
    ('S18','DRC',    '卢本巴希','cobalt',   'ISO 9001',   4.10, 2.20, True, False, 0.960,  2026, 15_000_000, '2019-01-15', 0.180, True, 'Net 60', '★Labor'),
    ('S19','Indonesia','雅加达','nickel',   'ISO 9001',   4.00, 2.00, True, False, 0.955,  2025, 12_000_000, '2021-05-01', 0.520, True, 'Net 60', '★Labor(forced_labor)'),
    # --- 合规问题 ---
    ('S20','China',  '西安',   'lithium',  'ISO 9001',   3.80, 2.10, False, True, 0.970,  2026, 14_000_000, '2021-11-01', 0.600, False,'Net 30', '无cmrt→Compliance FAIL'),
    ('S21','China',  '合肥',   'cobalt',   'ISO 9001',   3.70, 1.90, False, False, 0.958,  2025, 12_000_000, '2022-06-01', 0.580, False,'Net 30', '无cmrt+无RBA→FAIL'),
    ('S22','Malaysia','居林',  'lithium',  'ISO 9001',   3.90, 2.00, True, False, 0.965,  2026, 18_000_000, '2020-09-01', 0.480, False,'Net 45', '无RBA→Labor FAIL'),

    # ===== General_Comp (15 家) =====
    # ID  Country   City     Sub_cat          Cert     Rating Z     CMRT RBA   Yield  Expiry  Contract   Start      CI     FL  Pay     Landmine
    ('S23','China',  '厦门',   'thermal_management','IATF 16949',4.50, 3.20, True, True,  0.995,  2028, 22_000_000, '2018-02-01', 0.600, False,'Net 30', ''),
    ('S24','China',  '青岛',   'busbar',     'IATF 16949', 4.30, 2.80, True, True,  0.992,  2027, 18_000_000, '2019-05-15', 0.580, False,'Net 30', ''),
    ('S25','Japan',  '大阪',   'connector',  'IATF 16949', 4.80, 3.50, True, True,  0.996,  2028, 42_000_000, '2016-11-01', 0.250, False,'Net 60', ''),
    ('S26','China',  '东莞',   'aluminum_shell','ISO 9001', 4.00, 2.30, True, True,  0.930,  2025, 12_000_000, '2021-08-01', 0.620, False,'Net 30', '★Quality(yield<0.95+过期)'),
    ('S27','China',  '佛山',   'fuse',       'ISO 9001',   4.20, 2.50, True, True,  0.975,  2027, 15_000_000, '2019-10-20', 0.550, False,'Net 30', ''),
    ('S28','China',  '杭州',   'connector',  'ISO 9001',   4.10, 2.40, True, True,  0.970,  2026, 14_000_000, '2020-03-01', 0.590, False,'Net 30', ''),
    ('S29','China',  '苏州',   'thermal_management','ISO 9001',4.30, 2.60, True, True,  0.974,  2027, 16_000_000, '2019-06-01', 0.570, False,'Net 30', ''),
    ('S30','Malaysia','新山',  'busbar',     'ISO 9001',   4.20, 2.60, True, True,  0.972,  2026, 18_000_000, '2020-01-15', 0.460, False,'Net 45', ''),
    ('S31','Malaysia','巴生',  'connector',  'ISO 9001',   4.10, 2.40, True, True,  0.970,  2027, 16_000_000, '2020-04-01', 0.480, False,'Net 45', ''),
    ('S32','Malaysia','马六甲','fuse',       'ISO 9001',   4.00, 2.30, True, True,  0.968,  2026, 14_000_000, '2020-07-01', 0.440, False,'Net 30', ''),
    ('S33','South Korea','釜山','thermal_management','ISO 9001',4.50, 3.00, True, True,  0.982,  2027, 30_000_000, '2018-09-01', 0.340, False,'Net 45', ''),
    ('S34','USA',   '底特律', 'connector',  'ISO 9001',   4.60, 3.50, True, True,  0.985,  2028, 38_000_000, '2017-12-01', 0.300, False,'Net 60', ''),
    ('S35','Indonesia','苏拉威西','aluminum_shell','ISO 9001',3.80, 1.90, True, False, 0.955,  2025, 10_000_000, '2022-05-01', 0.480, False,'Net 60', '无RBA→Labor FAIL'),
    ('S36','China',  '南京',   'aluminum_shell','ISO 9001',4.10, 2.30, True, True,  0.960,  2026, 13_000_000, '2020-11-01', 0.610, False,'Net 30', ''),
    ('S37','Malaysia','莎阿南','aluminum_shell','ISO 9001',4.00, 2.20, True, True,  0.962,  2027, 15_000_000, '2020-08-01', 0.450, False,'Net 45', ''),

    # ===== General_Raw (13 家) =====
    # ID  Country   City     Sub_cat          Cert     Rating Z     CMRT RBA   Yield  Expiry  Contract   Start      CI     FL  Pay     Landmine
    ('S38','China',  '南昌',   'graphite',    'IATF 16949', 4.30, 2.50, True, True,  0.990,  2027, 22_000_000, '2019-03-01', 0.630, False,'Net 30', ''),
    ('S39','China',  '郑州',   'copper_foil', 'ISO 9001',   4.10, 2.20, True, True,  0.975,  2026, 18_000_000, '2020-02-15', 0.580, False,'Net 30', ''),
    ('S40','China',  '重庆',   'manganese',   'ISO 9001',   3.90, 2.00, True, True,  0.970,  2026, 16_000_000, '2020-06-01', 0.600, False,'Net 30', ''),
    ('S41','China',  '沈阳',   'recycled_material','ISO 9001',3.80, 1.90, True, True,  0.965,  2025, 14_000_000, '2021-08-01', 0.550, False,'Net 30', ''),
    ('S42','China',  '芜湖',   'alumina',     'ISO 9001',   3.70, 1.68, True, True,  0.960,  2026, 12_000_000, '2021-11-01', 0.640, False,'Net 30', 'Z<1.8→Finance FAIL'),
    ('S43','China',  '宜春',   'zinc',        'ISO 9001',   3.60, 1.70, True, True,  0.955,  2025, 10_000_000, '2022-04-01', 0.590, False,'Net 30', 'Z<1.8→Finance FAIL'),
    ('S44','Malaysia','古晋', 'graphite',    'ISO 9001',   4.10, 2.30, True, True,  0.974,  2027, 22_000_000, '2020-05-01', 0.480, False,'Net 45', ''),
    ('S45','Malaysia','亚庇', 'copper_foil', 'ISO 9001',   3.90, 2.10, True, True,  0.968,  2026, 18_000_000, '2020-10-01', 0.500, False,'Net 45', ''),
    ('S46','Malaysia','怡保', 'manganese',   'ISO 9001',   3.80, 2.00, True, True,  0.965,  2026, 16_000_000, '2021-03-01', 0.460, False,'Net 30', ''),
    ('S47','Malaysia','芙蓉', 'recycled_material','ISO 9001',3.70, 1.90, True, False, 0.960,  2025, 14_000_000, '2021-07-01', 0.520, False,'Net 45', '无RBA→Labor FAIL'),
    ('S48','Australia','悉尼','graphite',    'ISO 9001',   4.50, 3.20, True, True,  0.985,  2027, 40_000_000, '2018-08-01', 0.420, False,'Net 45', ''),
    ('S49','South Africa','开普敦','manganese','ISO 9001', 4.00, 2.10, True, True,  0.970,  2026, 28_000_000, '2020-12-01', 0.550, False,'Net 45', ''),
    # --- ★Ethics 地雷: South Africa, General_Raw, cmrt=False ---
    ('S50','South Africa','开普敦','alumina','ISO 9001',  3.90, 2.00, False, True, 0.965,  2026, 22_000_000, '2021-06-01', 0.580, False,'Net 45', '★Ethics(cmrt=False, CPI=0.75)'),
]

# ==========================================
# 3. 供应商工厂 / make_supplier
# ==========================================
def make_supplier_from_archetype(def_tuple):
    """从人设元组生成供应商行（加入 ±5% 微调 jitter）"""
    (sid, country, city, sub_cat, cert_type, rating_base, z_base,
     cmrt, rba, yield_base, cey, contract_base, start_date,
     ci_base, fl_risk, pay_terms, _landmine_label) = def_tuple

    category = None
    for cat, subs in SUB_CATEGORIES.items():
        if sub_cat in subs:
            category = cat
            break
    if category is None:
        raise ValueError(f"Unknown sub_category: {sub_cat}")

    material = MATERIAL_MAP.get(sub_cat, sub_cat)

    # === 微调 / Jitter (±2% 相对波动) ===
    jitter = lambda base, pct=0.02: base * (1 + np.random.uniform(-pct, pct))

    # 合同额 ≈ 保留三位有效数字
    contract = int(round(jitter(contract_base, 0.05), -3))

    # 评分 ±0.1，上限 5.0
    rating = round(min(5.0, rating_base + np.random.uniform(-0.1, 0.1)), 1)

    # 良率 ±0.003
    yr = round(min(0.999, yield_base + np.random.uniform(-0.003, 0.003)), 3)

    # Z-Score ±0.1
    azs = round(z_base + np.random.uniform(-0.1, 0.1), 2)

    # 碳强度 ±5%
    ci = round(jitter(ci_base, 0.05), 3)

    # 确定性哈希（用于 pcf/ecr，不再依赖 np.random），范围 0-99 均匀分布
    sid_hash = (int(sid[1:]) * 7 + 83) % 100

    # 缺陷率 = 严格由 yield 反推（低 yield = 高 PPM），数学闭环
    dpm = int(round((1.0 - yr) * 1_000_000))

    # 交期 = 品类基准 × 地区 modifier
    lead_modifier = {
        'China': 0.70, 'Malaysia': 0.85, 'Japan': 0.90,
        'South Korea': 0.90, 'Germany': 1.00, 'USA': 1.00,
        'Australia': 1.10, 'Chile': 1.20, 'Indonesia': 1.20,
        'South Africa': 1.15, 'DRC': 1.40,
    }
    lead_ranges = {
        'Key_Component': (5, 25), 'Critical_Raw': (15, 45),
        'General_Comp': (5, 25), 'General_Raw': (15, 45),
    }
    lo_l, hi_l = lead_ranges[category]
    lead = int(round(np.random.uniform(lo_l, hi_l) * lead_modifier.get(country, 1.0)))

    # 改善潜力 — IATF 更高
    if cert_type == 'IATF 16949':
        kz = round(np.random.uniform(0.02, 0.06), 3)
    else:
        kz = round(np.random.uniform(0.0, 0.04), 3)

    # 碳减排承诺 — 确定性哈希（非随机），确保每次运行一致
    if cert_type == 'IATF 16949' and country not in ('China',):
        pcf = True
    else:
        pcf = (sid_hash % 100) < 35  # 35% 概率，但完全确定性

    # 出口管制 — Key_Component/General_Comp Foreign 有一定概率（确定性哈希）
    if country == 'China':
        ecr = False
    elif category in ('Key_Component', 'General_Comp'):
        ecr = (sid_hash % 5) == 0  # 20%
    else:
        ecr = (sid_hash % 20) == 0  # 5%

    # MY 组装附加值
    if country == 'Malaysia':
        lo_a, hi_a = AVA_RANGES.get(sub_cat, (0.10, 0.35))
        ava = round(np.random.uniform(lo_a, hi_a), 3)
    else:
        ava = np.nan

    # 碳强度 10% NaN（确定性哈希，非随机）
    ci_final = ci if sid_hash % 100 >= 10 else np.nan

    row = dict(
        supplier_id=sid,
        supplier_name=f'Supplier_{sid}',
        category=category,
        sub_category=sub_cat,
        country=country,
        city=city,
        material_service=material,
        annual_contract_value_usd=contract,
        cooperation_start_date=start_date,
        rating=rating,
        status='active',
        payment_terms=pay_terms,
        lead_time_days=lead,
        cert_type=cert_type,
        cert_expiry_year=cey,
        yield_rate=yr,
        defect_rate_ppm=dpm,
        altman_z_score=azs,
        cmrt_audit=cmrt,
        pcf_commitment=pcf,
        carbon_intensity=ci_final,
        assembly_value_add=ava,
        kaizen_factor=kz,
        rba_audit_pass=rba,
        forced_labor_risk=fl_risk,
        export_control_restricted=ecr,
    )
    return row


# ==========================================
# 4. 生成 50 家供应商
# ==========================================
all_rows = [make_supplier_from_archetype(d) for d in SUPPLIER_DEFS]

columns = [
    'supplier_id', 'supplier_name', 'category', 'sub_category',
    'country', 'city', 'material_service',
    'annual_contract_value_usd', 'cooperation_start_date',
    'rating', 'status', 'payment_terms', 'lead_time_days',
    'cert_type', 'cert_expiry_year',
    'yield_rate', 'defect_rate_ppm',
    'altman_z_score', 'cmrt_audit', 'pcf_commitment',
    'carbon_intensity', 'assembly_value_add', 'kaizen_factor',
    'rba_audit_pass', 'forced_labor_risk', 'export_control_restricted',
]

df = pd.DataFrame(all_rows, columns=columns)

# 地雷标注输出
print('  [Landmines]')
landmine_rows = [d for d in SUPPLIER_DEFS if d[-1]]
for d in landmine_rows:
    sid = d[0]
    label = d[-1]
    print(f'    {sid}: {label}')

df.to_csv('suppliers_data.csv', index=False, encoding='utf-8-sig')

# ==========================================
# 5. 摘要输出
# ==========================================
print(f'\n[OK] 已生成 {len(df)} 家供应商数据 -> suppliers_data.csv\n')

print('=' * 72)
print('  前 10 家供应商数据摘要')
print('=' * 72)
for _, r in df.head(10).iterrows():
    cmrt = '[A]' if r['cmrt_audit'] else '   '
    print(f'  {r["supplier_id"]} {cmrt} {r["category"]:14s} | '
          f'{r["country"]:12s} | '
          f'评分={r["rating"]:.1f} | cert={r["cert_type"]} | '
          f'yield={r["yield_rate"]:.3f} | dpm={int(r["defect_rate_ppm"]):4d} | '
          f'z={r["altman_z_score"]:.2f} | CI={r["carbon_intensity"]:.3f}')

print(f'\n{"=" * 72}')
print('  品类分布:')
print('=' * 72)
for cat, cnt in df['category'].value_counts().sort_index().items():
    sub = df[df.category == cat]
    c_f = sub[~sub.country.isin(['China', 'Malaysia'])].shape[0]
    c_my = (sub.country == 'Malaysia').sum()
    c_cn = (sub.country == 'China').sum()
    print(f'  {cat:16s} {cnt:2d} 家  -> Foreign {c_f} / MY {c_my} / CN {c_cn}')

print(f'\n{"=" * 72}')
print('  国家分布:')
print('=' * 72)
for c, cnt in df['country'].value_counts().sort_index().items():
    hi = df[(df.country == c) & df.cmrt_audit].shape[0]
    print(f'  {c:15s} {cnt:2d} 家  (cmrt_audit=True: {hi})')

print(f'\n{"=" * 72}')
print('  核心审计字段统计:')
print('=' * 72)
print(f'  yield_rate:        {df["yield_rate"].min():.3f} ~ {df["yield_rate"].max():.3f} '
      f'(均值: {df["yield_rate"].mean():.4f})')
print(f'  defect_rate_ppm:   {int(df.defect_rate_ppm.min()):d} ~ {int(df.defect_rate_ppm.max()):d}')
print(f'  altman_z_score:    {df["altman_z_score"].min():.2f} ~ {df["altman_z_score"].max():.2f}')
print(f'  kaizen_factor:     {df["kaizen_factor"].min():.3f} ~ {df["kaizen_factor"].max():.3f}')
print(f'  carbon_intensity:  '
      f'{df["carbon_intensity"].min():.3f} ~ {df["carbon_intensity"].max():.3f} kgCO2/kWh')
print(f'  carbon_intensity NaN: {df.carbon_intensity.isna().sum()} 家')
print(f'  cmrt_audit=True:   {df["cmrt_audit"].sum()} 家')
print(f'  pcf_commitment=True: {df["pcf_commitment"].sum()} 家')
ava_ct = df.assembly_value_add.notna().sum()
print(f'  assembly_value_add (MY): {ava_ct} 家, '
      f'{df.assembly_value_add.min():.3f} ~ {df.assembly_value_add.max():.3f}')

print(f'\n{"=" * 72}')
print('  认证分布 (品类 x 认证类型):')
print('=' * 72)
ct_cross = df.groupby(['category', 'cert_type']).size().unstack(fill_value=0)
print(ct_cross.to_string())

# 品类内 IATF vs ISO yield 均值对比
print(f'\n{"=" * 72}')
print('  IATF vs ISO yield 均值对比 (品类内):')
print('=' * 72)
for cat in df['category'].unique():
    sub = df[df.category == cat]
    iatf_y = sub[sub.cert_type == 'IATF 16949']['yield_rate'].mean()
    iso_y = sub[sub.cert_type == 'ISO 9001']['yield_rate'].mean()
    ok_mark = '[OK]' if iatf_y > iso_y else '[NO]'
    print(f'  {cat:16s}  IATF={iatf_y:.4f}  ISO={iso_y:.4f}  {ok_mark}')

print(f'\n{"=" * 72}')
print('  地雷供应商 / Landmines:')
print('=' * 72)
for d in landmine_rows:
    sid = d[0]
    row = df[df.supplier_id == sid].iloc[0]
    print(f'  {sid}: {d[-1]}')
    print(f'       {row.category:16s} {row.country:12s} '
          f'rating={row.rating:.1f} z={row.altman_z_score:.2f} '
          f'cmrt={row.cmrt_audit} rba={row.rba_audit_pass}')
