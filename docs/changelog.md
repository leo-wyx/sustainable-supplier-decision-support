# 会话复盘记录 — Session 3 (2026-05-02)

## 背景

从 Session 2 commit 之后开始。当前代码状态：M1/M2 管线跑通，dpm-yield 闭环，pcf/ecr 确定化，BLACKLIST 保护已加，但仍有遗留问题（cfg 脱钩、CI NaN 随机性、CATEGORY_CONFIG 死代码）。

---

## 01 — 综合审查 + GPT/Gemini 双源评审

### 触发
你找 GPT 和 Gemini 各自做了一轮代码审查，然后把两边的意见一起发给我，让我分析。

### 我的操作
1. 我自己先读了一遍所有源文件做独立审查，得出 baseline
2. 对照 GPT 和 Gemini 的意见逐条评估
3. 发现 GPT/Gemini 各有遗漏也各有亮点

### 关键发现汇总

| # | 问题 | 谁发现的 | 优先级 | 最终决策 |
|---|---|---|---|---|
| P0-1 | cfg 脱钩：Model1.py:209 赋值后从未使用 | 我（独立 audit） + GPT/Gemini 都提到 | P0 架构级 | 修：所有 penalty/cap 从 config 读取 |
| P0-2 | CI NaN 用 np.random | 我（独立 audit） | P0 数据确定性 | 修：改成 sid_hash 哈希 |
| P0-3 | CATEGORY_CONFIG 死代码 | 我（独立 audit） | P0 代码整洁 | 删 |
| P1-1 | IATF Malaysia PCF=0% | Gemini 指出 | P1 业务真实 | 修：Malaysia 从 China 同组排除 |
| — | Reserve 激活把 FAIL 洗成 LIMITED_QUALITY_TECH | GPT 发现，我和 Gemini 都没发现 | P0 bug | 修：加 RESERVE_ACTIVATED 状态 |
| — | Critical_Raw 109% 产能不足但无备胎 | 我（独立 audit） | P2 认知反转 | 不改，这是黄金亮点（见下文） |
| — | Key_Component ISO 9001 质量合格但被限额 | 我（独立 audit） | P2 认知反转 | 不改，这是正确的采购铁律 |

### 决策博弈：Critical_Raw 109%

**Gemini 建议**：把 gap 填到 90% 需求而不是 100% safety_threshold

**GPT 建议**：用 Risk Budget 替代 gap fill

**我的分析**：当前代码已经用 DEMAND_RATIO=0.50 大幅降低了敏感度。109% 的关键不是缺产能，而是 6 家 FAIL 全部是 RESERVE_BLACKLIST（劳工地雷 + 合规地雷），没有一个可以激活。这意味着系统宁可顶着红线也不向违规低头——这是一个可以展示的设计特征，不是 bug。

**你的决定**：不改。

**GPT 建议进化**：GPT 提出 Risk Budget "替代" gap fill，我发现了其中的数学漏洞——RISK_BUDGET=0.12 是无单位比例，而 `contract × penalty` 是美元，不能直接比较。我设计了**双重闸门**方案并得到你批准。

### 决策博弈：激活状态洗白

**GPT 指出**：当前代码把 FAIL 激活后标记为 LIMITED_QUALITY_TECH，如果原始 FAIL 原因是 Finance（财务风险），就被洗成了"质量/技术问题"。这是语义错误。

**我的判断**：这是真 bug。修。

**你**：直接批。

---

## 02 — 你的审批决策

你看了我整合后的 P0/P1/P2 表，做了明确指示：

> Risk Budget 执行我自己的判断（两个并行）
> 剩下所有改动都可以进行

**范围确认**：当时我有 9 项待改项，我问是否覆盖之前 5 个问题，确认全部包括了你说的每一处。

---

## 03 — 执行阶段

### 7 项改动详情

#### 1. cfg 脱钩（Model1.py + strategy_config.py）

- **现状**：`decide_status_v2()` 硬编码 1.15/0.30/1.40/0.15
- **改动**：
  - StrategyConfig 加 `quality_tech_penalty` 字段
  - 三套策略分别赋值（全部 1.15）
  - `decide_status_v2(r, gate_cols, current_cfg=cfg)` 引用 cfg
  - `_map_gates` 入口 `cfg` 参数，`run_m1` 传入
- **问题**：`_map_gates` 被外部直接调用时 cfg=None → 加 fallback
- **验证**：S10 penalty=x1.15, S50 penalty=x1.40，来自 config 而非硬编码

#### 2. CI NaN 确定性（generate_data.py:250）

- **改动**：`np.random.random() >= 0.10` → `sid_hash % 100 >= 10`
- **验证**：6 家固定 NaN(S06/S17/S42/S43/S47/S50)，rerun 确认一致

#### 3. CATEGORY_CONFIG 删除

- **删除 6 行**，无人引用

#### 4. IATF Malaysia PCF（generate_data.py:229）

- **改动**：`country not in ('China', 'Malaysia')` → `country not in ('China',)`
- **验证**：S08+S11 全部 PCF=True(2/2)

#### 5. 激活状态不乱标（Model1.py:308）

- **改动**：M1_Status='LIMITED_QUALITY_TECH' → 'RESERVE_ACTIVATED'
- **同时**：更新 CLI 输出（LIMITED 区段也显示 RESERVE_ACTIVATED）
- ⚠️ 审计发现 M2 valid list 没包含 RESERVE_ACTIVATED → 补修

#### 6. 双重闸门激活（Model1.py 激活段）

- **改动**：单闸(gap fill) → 双闸(gap fill + risk budget)，谁先到停谁
- **需要你注意**：当前无品类触发激活，新逻辑未在运行状态验证。要验证需要手动改 DEMAND_RATIO 制造场景

#### 7. 约束松弛注释（Model1.py）

- **加 4 行**：diversification → cap → reserve activation

#### 8. M2 潜 bug（审计发现）

- **情况**：当前无激活所以没触发，但一旦有激活 M2 会跳过评分
- **改动**：valid list 加 RESERVE_ACTIVATED

#### 9. GBK 编码（审计顺手）

- ⚠️ → [R], 激活标记 → [A]

---

## 04 — 最终结果验证

### 管线运行
- generate_data.py: 50 家供应商，4 品类 ✓
- Model1.py: PASS=33, LIMITED=4(含 2x Q/T+2x Ethics), FAIL=13 ✓
- Model2.py: 37 家评分，无错误 ✓

### 数据确定性
- dpm-yield 0 mismatch/50 ✓
- pcf/ecr/rba/CI NaN 全部确定性 ✓
- rerun 后 7 个核心字段 0 不一致 ✓

### 业务逻辑
- China forced_labor_risk = 0/24 ✓
- IATF yield > ISO yield 全部品类 ✓
- Key_Component IATF = 10/12(83%) ✓
- Key_Component cmrt = 11/12(92%) ✓
- IATF Malaysia PCF = 2/2 ✓

---

## 05 — 存储完成

- `docs/architecture.md` — 架构文档
- `docs/changelog.md` — 本文件
- `.openclaude/memory/design_decisions.md` — 关键决策记忆

---

## Session 3.5 — GPT/Gemini Model1.py 建议评估（会话续接）

### 背景
你找了 GPT 和 Gemini 做第二轮审查（这次专注 Model1.py），把 7 条建议发给我评估。

### 我的评估结论

| 建议 | 来源 | 我的判断 | 理由 |
|-----|------|---------|------|
| M1_Decision_Reason 字段 | GPT | ✅ 做 | 把系统从打分卡变成决策引擎 |
| Business Impact 映射 | GPT | ✅ 做 | 方便管理层理解每个 LIMIT/FAIL 的业务含义 |
| Category Risk Dashboard | GPT | ✅ 做 | 品类级风险面板一目了然 |
| Decision Summary | GPT | ✅ 做 | 整合产能+激活+风险建议 |
| 消除 disk I/O | Gemini | ✅ 做 | to_csv→read_csv 同函数循环，简单修 |
| apply 向量化 | Gemini | ❌ 跳过 | 50 行数据不需要 |
| import 标准化 | Gemini | ❌ 跳过 | 局部 import 是故意设计，防循环依赖 |

### 改动详情

#### 1. Decision_Reason + Business_Impact + Risk_Level
- **文件**: Model1.py
- **做法**: `decide_status_v2` 返回值从 6 元组扩展到 9 元组（+Decision_Reason, +Business_Impact, +Risk_Level）
- **PASS**: "全部门禁通过 → 全量分配"
- **LIMITED**: 含具体原因如 `质量门禁未通过 (yield=0.98, cert=ISO 9001) → 限容分配`
- **FAIL**: 含具体数值如 `财务风险 (Altman Z=1.23) → 保留备胎池`
- **RESERVE_ACTIVATED**: `产能熔断激活: {风险类型}供应商从备胎池紧急激活 (penalty x2)`
- 同时新增 `RISK_BUSINESS_IMPACT` 模块级映射字典（6 种风险→业务影响）

#### 2. Category Risk Dashboard（CLI 输出）
- 每个品类的 PASS/LIMITED/FAIL 统计 + 风险等级（LOW/MED/HIGH）+ 主要风险类型
- Critical_Raw 显示 60% 淘汰率 = HIGH ✓

#### 3. Decision Summary（CLI 输出末尾）
- 系统可行性、分布统计、高风险品类、M2 建议

#### 4. 消除 disk I/O（Model1.py run_m1）
- reserve_df 从内存传递给 `reserve_fallback`，不再 to_csv→read_csv

### 验证
- Model1.py 独立运行：PASS=32, LIMITED=5, FAIL=13 ✓
- Category Risk Dashboard: Critical_Raw HIGH ✓
- Decision Reason 字段输出完整 ✓
- Model2.py 管线全通：37 家评分 ✓
- GeoPenalty General_Comp CN 70% → -0.2 ✓

### 未纳入
- Gemini 的 apply 向量化（50 行没必要）
- Gemini 的 import 标准化（与架构冲突）

---

## Session 4 — Model1.py 架构修正（2026-05-03）

### 触发
你审查完 Session 3.5 的改动后指出了两个问题：
1. M1 包含 capacity check + reserve activation，侵占了 M3 的职责
2. CLI 输出信息过载（Dashboard + Decision_Reason + Business_Impact + Summary 一起输出）

### 我的判断
你说得对。M1 做 activation 是 Session 3 的历史遗留（我当时提议的，你批准的），但放到整体架构看不合理。GPT 的 4 条我采纳太多了——每条单独看合理，合起来就是噪音。

### 改动详情

#### 1. 职责剥离：M1 不再做备胎激活
- **删 150+ 行**：capacity health check、dual-gate activation、reserve_activated 拼接
- M1 现在只做：门禁计算 → 三态决策 → 写入 reserve pool CSV → 返回 PASS+LIMITED
- M3 按需读 `supplier_reserve_pool.csv` 自己做激活决策
- `RESERVE_ACTIVATED` 状态保留（M3 会用），M1 不再产生
- 删除 M1 对 `DEMAND_RATIO`、`CAPACITY_SAFETY_FACTOR`、`RISK_BUDGET`、`RESERVE_ACTIVATION_PENALTY` 的引用

#### 2. M1_Risk_Exposure 字段
- 新增 `M1_Risk_Exposure = M1_Penalty × annual_contract_value_usd`
- 统一的货币化风险度量，PASS=1.0×合同额，LIMITED_QT=1.15×合同额，LIMITED_ETH=1.40×合同额
- Reserve CSV 也包含该字段，供 M3 直接使用

#### 3. CLI 输出精简
- 删除 Category Risk Dashboard（移给 M4 管理面板）
- 删除 Decision Summary
- 恢复简洁输出：Status、Risk_Type 三列 + 一行摘要
- `Decision_Reason`、`Business_Impact`、`Risk_Level` 保留为数据字段不展示

#### 4. M2 清理
- 从 valid 列表删除 `RESERVE_ACTIVATED`（M1 不再产生，M3 用不同路径）

### 验证（全自动化审计）
- M1 preserves data fields: OK (4 fields × 37 suppliers)
- M1_Risk_Exposure 计算: PASS=x1.0, LIMITED=x1.15 ✓
- Reserve pool has Risk_Exposure: 13 suppliers ✓
- No RESERVE_ACTIVATED in active pool ✓
- M2 scored 37 suppliers ✓
- M1 no longer imports activation constants (6 assertions passed) ✓

---

## Session 4 — 收尾: m1_impact_analysis() 上线（2026-05-03）

### 背景
Session 4 主体改动（M1 职责剥离、CLI 精简、Risk_Exposure 字段）完成后，你审批了三件事：恢复 Dashboard（精简版）、激活 Risk_Exposure、添加 `m1_impact_analysis()`。

### 改动

#### 1. m1_impact_analysis() 函数
- 新增在 `run_m1()` 之后，纯分析/报告层 — 不改任何决策逻辑
- **品类级面板**：PASS/LIMITED/FAIL 统计 + 短缺风险 (HIGH/MEDIUM/LOW, 阈值 40%/20%) + 成本增幅 + 国家集中度 + 中文业务叙事
- **成本影响**：系统级 LIMITED 惩罚 → 成本增幅估算
- **风险敞口**：Total $894.0M，PASS 88% + LIMITED 12%，Top 5 排序
- **Key Findings**：中文业务叙事 — Critical_Raw HIGH 短缺风险、品类集中度、成本影响

#### 2. CLI 集成
- `m1_impact_analysis()` 在 PASS/LIMITED/FAIL 表格之前输出
- 覆盖 Scenario 2 的 dashboard 功能，但更聚焦业务影响而非统计数据

### 验证
- M1: PASS=32, LIMITED_QT=4, LIMITED_ETH=1, FAIL=13 ✓
- Impact Analysis: Critical_Raw HIGH risk, $894.0M total exposure ✓
- M2: 37 suppliers scored, GeoPenalty applied ✓
- 无回归问题

---

## Session 4 — 再收尾: M1 决策建议层上线（2026-05-03）

### 背景
Session 4 主体改动后，GPT 提出了 4 步优化方案。用户审批通过其中 3 步：重构输出结构（actions 为主）、结构化 action type、标准化 TRIGGERS。第 4 步 expected_impact 因缺乏历史数据支撑被跳过。

### 改动

#### 1. TRIGGER_THRESHOLDS 迁入 strategy_config.py
- 新增 `TRIGGER_THRESHOLDS` dict：6 个品类级阈值 + 3 个系统级阈值
- 覆盖：coverage_low(85%)、fail_high(30%)、fail_critical(50%)、concentration_high(60%)、cost_high(5%)、高风品类计数(2)
- 所有触发条件从 Model1.py 的 if 散落代码收敛到 config 统一管理

#### 2. m1_impact_analysis() 重构：以 actions 为核心
- 返回结构改为 `{actions, category_actions, diagnostics}`
- `diagnostics` 包含原来全部的 overview/categories/cost_impact/exposure 数据
- `actions` 为系统级建议（ACCEPT_COST、INFO、ESCALATE）
- `category_actions` 为品类级建议（品类下无建议则不出现）

#### 3. 标准化触发机制
- `_make_triggers()`: 从 config 读取阈值构造 callable dict
- `_category_actions(cat_name, cat_data)`: 品类级 5 种触发（ONBOARD_SUPPLIER、ESCALATE、ALLOW_RESERVE_ACTIVATION、REVIEW_COST、DIVERSIFY_SOURCE）
- `_system_actions(diagnostics)`: 系统级 3 种触发（ESCALATE、ACCEPT_COST、INFO）
- 触发逻辑通过 `_make_triggers()` 统一评估，不再散落 if 判断

#### 4. CLI 输出倒置
- **先打** Decision Recommendations（actions 区段）
- **再打** Diagnostics（详细数据面板）
- Critical_Raw 触发 ESCALATE（60% FAIL > 50% 阈值），其余品类正常

### 边界
- 本次改动的输出不被任何下游模块直接消费（M2 只读 scored_df），可安全调整
- M3 建立时可以读取 actions 作为输入约束
- Step 4（expected_impact）跳过 — 无历史数据支撑，避免虚假精度
