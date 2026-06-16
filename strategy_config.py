"""strategy_config.py - Master configuration for M1-M2 supply chain decision system.

All business rules centralized here. Config can be modified for what-if scenario testing.
No hardcoded thresholds in Model1.py or Model2.py.

Section structure:
  1. M1 active gate thresholds    - Qualification gates, triggers, capacity params
  2. M2 active scoring config     - Dimension scores, sub-indicator maps, normalization bins
  3. M2 sub-indicator weights     - SUB_WEIGHTS for 18 sub-indicators (5 dimensions)
  4. Legacy retained for compat   - Deprecated maps kept for reference, not used in M2 scoring
  5. Roadmap extension parameters - Strategy configs for future allocation/resilience scenarios
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set


# ==========================================
# Section 1: M1 active gate thresholds
# Referenced by Model1.py for Six-Gate Qualification.
# ==========================================

THRESHOLDS = {
    'FINANCE': {
        'min_z_score': 1.8,
        'status_required': 'active',
    },
    'QUALITY': {
        'min_yield_key_component': 0.98,
        'min_yield_general': 0.95,
        'key_component_cert': 'IATF',
        'general_cert_keywords': ['ISO 9001', 'IATF'],
    },
    'TECH': {
        'min_rating': {
            'Key_Component': 4.5,
            'Critical_Raw': 3.8,
            'General_Comp': 3.6,
            'General_Raw': 3.5,
        },
    },
    'ETHICS': {
        'cpi_threshold': 0.85,
        'cmrt_bonus': 0.10,
        'country_cpi': {
            'Germany': 0.98,
            'Japan': 0.95,
            'South Korea': 0.95,
            'Australia': 0.95,
            'China': 0.90,
            'Malaysia': 0.90,
            'Chile': 0.85,
            'Indonesia': 0.80,
            'South Africa': 0.75,
            'DRC': 0.60,
        },
    },
    'COMPLIANCE': {
        'cmrt_required_categories': ['Critical_Raw', 'Key_Component'],
    },
    'LABOR': {
        'iatf_bypass': True,
        'rba_alternative': True,
    },
}

# M1 trigger thresholds -- drives decision recommendations (not gate logic)
TRIGGER_THRESHOLDS = {
    # Category-level triggers
    'coverage_low_pct': 85,           # Coverage < 85% triggers action
    'fail_high_pct': 30,              # FAIL rate > 30% triggers action
    'fail_critical_pct': 50,          # FAIL rate > 50% escalates decision
    'concentration_high_pct': 60,     # Country concentration > 60% triggers action
    'cost_high_pct': 5.0,             # Cost increase > 5% triggers action
    # System-level triggers
    'high_risk_category_count': 2,    # >= 2 categories HIGH risk -> escalate
    'sys_cost_acceptable_pct': 5.0,   # System cost increase < 5% acceptable
}

# Demand ratio (50% of contract total treated as demand, for capacity health check)
DEMAND_RATIO = 0.50

# Capacity safety redundancy factor
CAPACITY_SAFETY_FACTOR = 1.15

# Penalty applied if reserve pool suppliers were activated in future scenario analysis
RESERVE_ACTIVATION_PENALTY = 2.00

# Risk budget for future scenario analysis (not enforced by current M1/M2):
# sum(activated_contract x penalty) / total_demand <= RISK_BUDGET
RISK_BUDGET = 0.12


# ==========================================
# Section 2: M2 active scoring config
# Referenced by Model2.py for 5-dimension scoring (18 sub-indicators).
# Legacy entries are marked and kept in Section 4.
# ==========================================

M2_CONFIG = {
    # --- Carbon tax and volume assumptions ---
    'CARBON_TAX_PER_TON': 80.0,              # USD/ton CO2
    'UNIT_PRICE_VOLUME_ASSMPTION': 200000,    # Annual contract / this ~ unit price proxy

    # --- Geographic penalty (region grouping, threshold, amount) ---
    'REGION_GROUPS': {
        'CN':       ['China'],
        'MY':       ['Malaysia'],
        'JP_KR':    ['Japan', 'South Korea'],
        'EU_OC':    ['Germany', 'Australia', 'Chile'],
        'NA':       ['USA'],
        'SEA_AF':   ['Indonesia', 'South Africa', 'DRC'],
    },
    'GEO_PENALTY_DOMINANT_THRESHOLD': 0.60,
    'GEO_PENALTY_AMOUNT': 0.20,

    # --- ESG city tier classification ---
    'TIER1_CITIES': {
        'Shanghai', 'Guangzhou', 'Shenzhen', 'Ningbo', 'Chengdu', 'Tianjin', 'Hangzhou',
        'Xiamen', 'Ningde',
        'Wuhan', 'Nanjing', 'Hefei', 'Changzhou',
    },

    # --- Financial risk (Altman Z-score bins) ---
    'Z_SCORE_BINS': [0, 1.8, 2.5, 3.5, float('inf')],
    'Z_SCORE_LABELS': [5, 4, 2, 1],

    # --- Single-source dependency bins (R4) ---
    'SINGLE_SOURCE_BINS': [0, 2, 4, 6, 100],
    'SINGLE_SOURCE_LABELS': [5, 4, 2, 1],

    # --- Rating bins (R3 quality risk / T2 supplier rating) ---
    'RATING_BINS': [0, 3.5, 4.0, 4.5, 5.1],
    'RATING_LABELS': [5, 4, 2, 1],

    # --- C4: EU Landed-Cost Proxy ---
    # Approximate landed cost (not exact). 1=lowest cost, 5=highest cost.
    # Germany=lowest EU local, CN/MY->EU sea medium-high, DRC highest.
    # (Future roadmap: compute precise transport/carbon/customs costs.)
    'REGION_COST_MAP': {
        'Germany': 1,
        'Japan': 2, 'South Korea': 2,
        'Australia': 3, 'Malaysia': 3,
        'Chile': 4, 'China': 4, 'Indonesia': 4, 'South Africa': 4,
        'DRC': 5,
    },

    # --- EU Lane Proxy (origin-to-EU logistics approximation) ---
    # M2 uses lane group first-order score correction, not exact route planning.
    # (Future roadmap: handle precise transport cost, carbon, customs.)
    # Default: unknown country -> OVERSEAS_STABLE (score=2, conservative neutral)
    'EU_LANE_GROUPS': {
        'EU_NEARSHORE':    ['Germany'],
        'OVERSEAS_STABLE': ['Japan', 'South Korea', 'Australia'],
        'ASEAN_MED':       ['Malaysia', 'Indonesia'],
        'CHINA_LONG':      ['China'],
        'REMOTE_RAW':      ['DRC', 'South Africa', 'Chile'],
    },
    'EU_LANE_DEFAULT': 'OVERSEAS_STABLE',

    # --- L2: Logistics complexity score (EU perspective, 1=simplest, 5=most complex) ---
    'EU_LANE_L2_MAP': {
        'EU_NEARSHORE':    1,
        'OVERSEAS_STABLE': 2,
        'ASEAN_MED':       3,
        'CHINA_LONG':      3,
        'REMOTE_RAW':      4,
    },
    'EU_LANE_L2_DEFAULT': 3,

    # --- L4 (L3 in current model): Customs complexity score (EU perspective) ---
    'EU_LANE_L4_MAP': {
        'EU_NEARSHORE':    1,
        'OVERSEAS_STABLE': 2,
        'ASEAN_MED':       3,
        'CHINA_LONG':      3,
        'REMOTE_RAW':      4,
    },
    'EU_LANE_L4_DEFAULT': 3,

    # --- T1/E5/E12: Certification level map ---
    # IATF=5, ISO14001=4, ISO9001=3, other=1
    'CERT_LEVEL_MAP': {'IATF': 5, '14001': 4, '9001': 3},
    'CERT_LEVEL_DEFAULT': 1,

    # --- T3: Category technical complexity ---
    'CAT_TECH_COMPLEXITY_MAP': {
        'Critical_Raw': 3, 'General_Raw': 3,
        'Key_Component': 4, 'General_Comp': 4,
    },
    'CAT_TECH_COMPLEXITY_DEFAULT': 3,

    # --- E4: Labor Governance map (merged from legacy E4 labor + E8 anti-corruption) ---
    'LABOR_GOV_MAP': {
        'Germany': 5, 'Japan': 5, 'Australia': 5, 'South Korea': 4,
        'Chile': 4, 'China': 3, 'Malaysia': 3,
        'Indonesia': 2, 'South Africa': 2,
        'DRC': 1,
    },
    'LABOR_GOV_DEFAULT': 3,

    # --- E8: Anti-corruption index (independent score, referenced by M2 E4) ---
    'ANTI_CORRUPTION_MAP': {
        'Germany': 5, 'Japan': 5, 'Australia': 5, 'South Korea': 4,
        'Chile': 4, 'China': 3, 'Malaysia': 3, 'South Africa': 2,
        'Indonesia': 2, 'DRC': 1,
    },
    'ANTI_CORRUPTION_DEFAULT': 3,

    # --- R1 Country Risk map (merged from legacy supply disruption + geopolitical) ---
    # Average of two legacy maps. Range 1-5, 5=highest risk.
    'COUNTRY_RISK_MAP': {
        'Germany': 1, 'Japan': 1, 'Australia': 1, 'South Korea': 1,
        'Malaysia': 2, 'Chile': 2,
        'China': 3, 'Indonesia': 3, 'South Africa': 3,
        'DRC': 5,
    },
    'COUNTRY_RISK_DEFAULT': 3,

    # --- Category target lead time (days, for L1 target-capped scoring) ---
    'LT_TARGET_DAYS': {
        'Key_Component': 14,
        'Critical_Raw': 21,
        'General_Comp': 30,
        'General_Raw': 45,
    },

    # --- T4: Specialization scarcity bins ---
    # Fewer suppliers in sub_category = higher scarcity score
    'T4_SINGLE_SOURCE_BINS': [0, 1, 3, 6, 100],
    'T4_SINGLE_SOURCE_LABELS': [5, 4, 2, 1],

    # --- Percentile rank bins (for C3 category-internal ranking) ---
    'RANK_PCT_BINS': [-0.001, 0.2, 0.4, 0.6, 0.8, 1.001],
    'RANK_PCT_LABELS': [1, 2, 3, 4, 5],

    # --- AHP dual-mode scoring (for Model2.py AHP path) ---
    # Matrix order: [Cost, ESG, Risk, LT, Tech]
    # pairwise comparison -- value > 1 means row more important than column
    'AHP_MATRIX': [
        [1,   1/3, 1,   1,   1/3],
        [3,   1,   3,   3,   1],
        [1,   1/3, 1,   1,   1/3],
        [1,   1/3, 1,   1,   1/3],
        [3,   1,   3,   3,   1],
    ],
    'MANUAL_WEIGHTS_RAW': [20, 40, 10, 10, 20],  # Manual override weights (pre-normalization)

    # --- Adjusted Cost Index weights (MVP) ---
    # Global defaults for cost component weights within each category.
    # Category-specific overrides in ADJ_COST_CATEGORY_WEIGHTS_MAP take precedence.
    'ADJ_COST_BASE_WEIGHT': 0.60,
    'ADJ_COST_LOGISTICS_WEIGHT': 0.25,
    'ADJ_COST_CARBON_WEIGHT': 0.15,
    # Category-specific overrides: only Critical_Raw gets logistics-heavy split per design doc
    'ADJ_COST_CATEGORY_WEIGHTS_MAP': {
        'Critical_Raw': {'base': 0.50, 'logistics': 0.35, 'carbon': 0.15},
    },
}


# ==========================================
# Section 3: M2 sub-indicator weights
# Used by Model2.py for weighted aggregation within each dimension.
# Sensitivity analysis reloads these dictionaries for scenario scanning.
# ==========================================

SUB_WEIGHTS = {
    'Cost': {
        'C1_Base_Cost_Proxy': 0.60,
        'C2_Transport_Landed_Proxy': 0.25,
        'C3_Carbon_Cost_Proxy': 0.15,
    },
    'ESG': {
        'E1_Carbon_Intensity': 0.35,
        'E2_PCF_Commitment': 0.25,
        'E3_Certification_Compliance': 0.20,
        'E4_Labor_Governance': 0.20,
    },
    'Risk': {
        'R1_Country_Risk': 0.30,
        'R2_Financial_Risk': 0.25,
        'R3_Quality_Risk': 0.25,
        'R4_Single_Source_Dependency': 0.20,
    },
    'LeadTime': {
        'L1_Target_Capped': 0.50,
        'L2_Logistics_Complexity': 0.30,
        'L3_Customs_Complexity': 0.20,
    },
    'Tech': {
        'T1_Certification_Level': 0.30,
        'T2_Supplier_Rating': 0.30,
        'T3_Category_Complexity': 0.20,
        'T4_Specialization_Scarcity': 0.20,
    },
}


# ==========================================
# Section 4: Legacy configs retained for compatibility
# These are no longer used in M2 active scoring but kept for:
#   - M1 code paths (payment terms)
#   - Reference / data provenance
#   - Future roadmap integration
# ==========================================

# [LEGACY] Payment terms map -- no longer used in M2 Cost/LeadTime scoring.
# Retained for reference and future extension.
M2_CONFIG['PAYMENT_TERMS_MAP'] = {'Net 30': 1, 'Net 45': 3, 'Net 60': 5}

# [LEGACY] Cooperation years bins (Cost dimension) -- no longer in M2 main scoring.
M2_CONFIG['COOP_YEARS_BINS'] = [0, 3, 5, 100]
M2_CONFIG['COOP_YEARS_LABELS'] = [5, 3, 1]

# [LEGACY] Supply disruption risk map (R1) -- superseded by COUNTRY_RISK_MAP.
M2_CONFIG['SUPPLY_DISRUPTION_RISK'] = {
    1: ['Germany', 'Japan'],
    2: ['South Korea', 'Australia'],
    3: ['China', 'Malaysia', 'Chile'],
    4: ['Indonesia', 'South Africa'],
    5: ['DRC'],
}

# [LEGACY] Geopolitical risk map (R2) -- superseded by COUNTRY_RISK_MAP.
M2_CONFIG['GEOPOLITICAL_RISK'] = {
    1: ['Germany', 'Australia'],
    2: ['Japan', 'South Korea', 'Chile'],
    3: ['China', 'Malaysia'],
    4: ['Indonesia', 'South Africa'],
    5: ['DRC'],
}

# [LEGACY] E2 carbon management commitment scores -- replaced by pcf_commitment direct scoring.
M2_CONFIG['E2_IATF_SCORE'] = 4
M2_CONFIG['E2_PCF_SCORE'] = 3
M2_CONFIG['E2_NONE_SCORE'] = 2

# [LEGACY] E3 category environmental risk map -- no longer in M2 ESG main scoring.
M2_CONFIG['CAT_ENV_RISK_MAP'] = {
    'Critical_Raw': 2, 'General_Raw': 2,
    'Key_Component': 4, 'General_Comp': 4,
}
M2_CONFIG['CAT_ENV_RISK_DEFAULT'] = 3

# [LEGACY] E4/E8 labor score map -- superseded by LABOR_GOV_MAP.
M2_CONFIG['LABOR_SCORE_MAP'] = {
    'Germany': 5, 'Japan': 5, 'Australia': 5,
    'South Korea': 4,
    'China': 3, 'Malaysia': 3, 'Chile': 3,
    'Indonesia': 2, 'South Africa': 2,
    'DRC': 1,
}
M2_CONFIG['LABOR_SCORE_DEFAULT'] = 3

# [LEGACY] E5/E9 certification binary scores -- superseded by E3 Certification Compliance.
M2_CONFIG['E5_IATF_SCORE'] = 5
M2_CONFIG['E5_DEFAULT_SCORE'] = 3
M2_CONFIG['E9_IATF_SCORE'] = 4
M2_CONFIG['E9_DEFAULT_SCORE'] = 2

# [LEGACY] E7 cooperation years bins (ESG) -- no longer in M2 main scoring.
M2_CONFIG['ESG_YEARS_BINS'] = [0, 3, 5, 8, 100]
M2_CONFIG['ESG_YEARS_LABELS'] = [1, 2, 4, 5]


# ==========================================
# Section 5: Roadmap extension parameters
# Strategy configs for future roadmap development (allocation, resilience scenarios).
# Not actively used by current M1/M2 workflow. Parameters retained as reference.
# ==========================================

@dataclass
class StrategyConfig:
    name: str
    quality_tech_penalty: float   # LIMITED_QUALITY_TECH cost penalty coefficient
    quality_tech_cap: float       # LIMITED_QUALITY_TECH max allocation ratio
    ethics_penalty: float         # LIMITED_ETHICS cost penalty coefficient
    ethics_cap: float             # LIMITED_ETHICS max allocation ratio
    reserve_review_policy: str    # RESERVE_POOL rule for future scenario analysis (not executed by M1/M2)
    capacity_safety_factor: float = 1.2  # Safety redundancy coefficient


# Three predefined strategies for future roadmap use (not implemented in current M1/M2).
# Cost_Focused: prioritizes lowest-cost allocation.
# Balanced: equal consideration of cost, risk, and ESG.
# Risk_Resilient: favors multi-region diversification.
STRATEGIES: Dict[str, StrategyConfig] = {
    'Cost_Focused': StrategyConfig(
        name='Cost_Focused',
        quality_tech_penalty=1.15,
        quality_tech_cap=0.40,
        ethics_penalty=1.30,
        ethics_cap=0.20,
        reserve_review_policy='allowed',
    ),
    'Balanced': StrategyConfig(
        name='Balanced',
        quality_tech_penalty=1.15,
        quality_tech_cap=0.30,
        ethics_penalty=1.40,
        ethics_cap=0.15,
        reserve_review_policy='infeasible_only',
    ),
    'Risk_Resilient': StrategyConfig(
        name='Risk_Resilient',
        quality_tech_penalty=1.15,
        quality_tech_cap=0.20,
        ethics_penalty=1.50,
        ethics_cap=0.10,
        reserve_review_policy='infeasible_only',
    ),
}


def get_strategy(name='Balanced'):
    return STRATEGIES.get(name, STRATEGIES['Balanced'])


def list_strategies():
    return list(STRATEGIES.keys())
