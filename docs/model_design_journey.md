# Model Design Journey

**Supplier Decision Support System for EU-Oriented Manufacturing Sourcing**

This project was not designed as a pure mathematical optimization exercise. The original intention was to build a practical Supplier Decision Support System for a multinational manufacturing company sourcing for the European market. The business setting assumes that a manufacturing firm must evaluate global suppliers while balancing cost, ESG regulation, carbon exposure, geopolitical risk, delivery performance, transportation burden, demand uncertainty, and supply resilience.

## 1. Original Integrated Prototype

Before the current project structure existed, there was an exploratory prototype saved as `old_code.py.txt`. This was a single-script proof-of-concept that bundled M1 through M5 together, using 30 randomly generated suppliers and simplified logic.

The original M1 had only four gates: Quality, Finance, Tech, and Ethics. There was no Compliance gate or Labor gate as in the current version. The original M2 used randomly generated C/R/L/T/E indicators aggregated by simple averaging, which produced scores that were mathematically valid but had weak business-causal explanations. It supported both an AHP baseline and manual weights, but had no sensitivity validation for Cost, ESG, or strategic weights. Notably, the original M3, M4, and M5 ideas were already present in this prototype: order allocation (M3), policy scenario testing and stress testing (M4), and cost-emission Pareto trade-off analysis (M5). These were not later additions to the project scope. The allocation concept, the scenario testing concept, and the trade-off concept all existed from the beginning - they simply needed to be separated from the single-script bundle and given clearer architectural boundaries.

This prototype should not be seen as a failed attempt, nor was it replaced by the later system. The current architecture iterates on this prototype by modularizing the original decision chain and making each layer more business-realistic, explainable, and validated. As an exploratory proof-of-concept, the first version demonstrated the full supplier decision chain from qualification through allocation and trade-off analysis. The later revisions modularized the logic, improved business realism, strengthened data discipline, and added validation mechanisms. The later system was not a replacement of the original prototype, but an iteration of it.

**What the original model could not do.** The early model was functional: it could read supplier data, apply qualification rules, and produce supplier scores. However, it still looked too much like a static academic scorecard. It produced a ranking, but several questions were difficult to defend:

- Why should these indicators be included?
- Why should these weights be used?
- Are all indicators based on obtainable data?
- Does the cost score reflect true sourcing cost, or only contract value?
- Does the ESG layer distinguish CO2 emission, carbon footprint disclosure, and carbon tax exposure?
- Does the ranking remain stable if the company changes its strategic priorities?

The original prototype could output a sorted supplier list, but it could not explain why a supplier should be selected under different corporate strategies, different data reliability assumptions, or different scenario conditions. The ranking was static: it assumed one set of priorities applied universally. In practice, a sourcing decision depends on the company's strategic posture (cost-driven vs. ESG-driven vs. risk-resilient), the reliability of available data, and the assumptions made about future conditions. A static ranking cannot capture these dependencies. The core limitation was that the early model was a ranking-focused prototype. It answered "who scores highest" but not "who should we source from, and under what conditions."

## 2. M1 Business Logic Restructuring: From Pass/Fail to a Qualification Layer

The first major realization when moving from the prototype was that real procurement is not a simple pass/fail decision. A supplier that does not meet certain standards may still be usable under controlled conditions, and a supplier that fails today may become viable later. Deleting failed suppliers from consideration would lose useful information for capacity planning and emergency scenarios.

M1 was therefore restructured from a simple gate filter into a qualification layer. Each supplier is classified into one of three statuses:

| Status | Meaning |
|---|---|
| PASS | Can enter the normal sourcing pool |
| LIMITED | Can be used with restrictions or additional management controls |
| FAIL | Does not enter the normal sourcing pool, but remains in Reserve Pool |

The decision to keep failed suppliers in a Reserve Pool rather than deleting them permanently is closer to real procurement practice. A failed supplier may not be suitable for normal sourcing, but it may still be useful for emergency review, future remediation, or resilience simulation.

Several M1 fields were revised to improve business interpretability. Labor risk explanations were split between confirmed forced labor risk and missing labor assurance. This distinction matters because a confirmed violation and missing audit evidence have different ESG meanings.

M1 also keeps both a primary risk type and a full risk vector. A supplier may fail several gates at the same time, so keeping only one label would hide compound risk.

Finally, M1_Risk_Exposure was corrected. The original logic could make failed suppliers appear to have zero exposure. The revised meaning is:

| Status | M1_Risk_Exposure |
|---|---|
| PASS | 0 |
| LIMITED | contract value x extra penalty |
| FAIL | full contract value |

## 3. Project Scope Convergence: From Network Design to Layered Decision Support

After restructuring M1, I faced a broader question. Should the project be one comprehensive model that handles everything, or should qualification, scoring, allocation, and stress testing be separate?

I initially considered a broader supply chain network planning problem. The original scope included cross-region sourcing, factory location decisions, China-to-Europe flow routing, Malaysia assembly hub evaluation, and EU local procurement comparison - essentially a full greenfield-brownfield network design. However, this ambitious scope required detailed routing data, tariff schedules, warehousing costs, transport mode selection, and bill-of-material granularity that were not reliably available at the supplier data level. Building such a model on estimated data would create a false sense of precision.

Therefore, the project was converged into a layered Supplier Decision Support System with clearly separated modules:

| Module | Name | Role |
|---|---|---|
| M1 | Supplier Qualification & Risk Intelligence | Decide whether a supplier can enter the sourcing pool |
| M2 | Strategic Scoring & ESG Policy Layer | Compare qualified suppliers and assign strategic priority |
| M3 | Cross-border Allocation Optimization | Decide how much demand should be allocated to each supplier |
| M4 | Stress Test & Resilience Simulation | Test whether the sourcing structure remains stable under shocks |

The key boundary is simple: M1 decides whether a supplier can be used; M2 decides which suppliers should be preferred; M3 decides how orders should be allocated; M4 tests whether the supply structure remains resilient under disruption scenarios.

It is important to note that this four-module architecture was not only a top-down design. It emerged from the business logic discovered while refining M1.

When M1 was restructured from a simple pass/fail filter into a qualification layer with PASS, LIMITED, and FAIL statuses plus a Reserve Pool, each status naturally raised a downstream decision question that M1 itself could not answer:

- **LIMITED suppliers triggered an allocation question.** If a supplier is usable but restricted, how much demand should be allocated to it? The answer depends on capacity, cost trade-offs, and alternative supplier coverage. This question belongs in an allocation module, not in a qualification gate.

- **FAIL / Reserve Pool triggered a resilience question.** A failed supplier does not enter normal procurement. But should it be retained as an emergency supply source for disruption scenarios? If so, under what conditions should the reserve be activated? This is a stress-testing question, not a qualification rule.

- **Category capacity shortage triggered a feasibility question.** If the qualified suppliers in a category cannot cover the demand, should the system relax capacity caps, activate reserve suppliers, or flag the scenario as infeasible? The answer requires scenario simulation, not a static check.

- **ESG and carbon exposure triggered a scenario question.** If carbon tax rates change, ESG regulations tighten, logistics costs shift, or regional risks escalate, will the current supply structure remain viable? This is not a property of any single supplier's qualification status. It is a property of the portfolio under changing conditions.

These questions could not be forced back into M1 without overloading it. Attempting to embed allocation logic, stress simulation, and scenario comparison into a qualification layer would have recreated the original problem of bundling everything into one module. The clean response was to let the module boundaries form around the questions themselves:

- M1 handles qualification and risk intelligence
- M2 handles strategic scoring and supplier comparison
- M3 (future) handles allocation optimization
- M4 (future) handles stress testing and resilience simulation

This emergence is important for understanding the project architecture. The modules were not predefined and then populated with logic. The business questions surfaced during M1 refinement, and the boundaries grew around them. This is why the boundaries hold: they are not imposed from theory, but derived from the operational decisions that the system must support.

It should be clarified that M3 and M4 were not afterthoughts. Their initial logic already appeared in the original integrated prototype through order allocation logic (M3), policy scenario testing and stress testing (M4), and cost-emission Pareto trade-off analysis. What changed later was not the existence of these ideas, but their architectural role: instead of being bundled inside one script alongside qualification and scoring, they became planned downstream modules with clearer responsibilities and defined interfaces to M1 and M2.

The convergence was not a compromise. It was a deliberate decision to match model complexity with data reliability. This boundary became the foundation for the later model revisions, and it also prevented the project from putting every possible supply-chain factor into one scoring formula.

## 4. M1 Frozen: Qualification as the Foundation

After these revisions, M1 was frozen as a qualification and risk-intelligence layer. It does not perform allocation, route optimization, or stress testing. Its role is limited to answering one question: can this supplier be used?

M1 uses six gates: Finance, Quality, Tech, Ethics, Compliance, and Labor. All six gates are computed in full (no short-circuit), then a priority decision determines the final status and pool assignment. The gate thresholds, penalty factors, and capacity caps are controlled through configuration rather than hardcoded logic.

Freezing M1 early was intentional. It provided a stable qualification baseline so that M2 development could focus on scoring quality without having to re-validate supplier eligibility on every change.

## 5. M2 First Round: Foundation Repair

With M1 settled, the focus shifted to M2 scoring. The original M2 scoring structure was producing results, but several directional and contextual errors made the scores inconsistent with business logic.

The first round of M2 revision was a foundation repair that addressed these structural errors:

- **C7 (dynamic TCO)** was computed but never entered the Cost Score, making the carbon tax parameter effectively invisible to the ranking. C7 was wired into the Cost Score.
- **C5 (assembly value add)** had its scoring direction reversed - higher value add was treated as worse cost. The direction was corrected.
- **C4** was converted into an EU landed-cost proxy, reflecting the fact that logistics burden depends on origin-to-destination distance, not only on contract value.
- **L2 and L4** were rebuilt as origin-to-EU lane proxies, replacing a China-centric logistics view that was inconsistent with the EU market context.
- **Rankings** were originally done globally across all categories, which does not match how procurement teams manage suppliers. Both global and category-level rankings were added.
- **M1 forward fields** were passed to M2 so that scoring could reference qualification status where relevant.

This stage was about making the M2 scoring foundation business-logic-consistent before addressing the deeper question of which indicators should exist at all.

## 6. External Review Triggers M2 Second Round

After the foundation repair was complete, an external review highlighted several realism gaps in the M2 scoring design. The feedback did not question M1 or the overall architecture. It focused on whether M2 was using the right indicators and whether its weights were defensible.

The key concerns raised were:

- Cost should not be represented by a single proxy. Transportation and landed-cost effects should be reflected.
- CO2 emission, carbon footprint disclosure, and carbon tax exposure should not be mixed into one vague ESG concept. They are related but distinct.
- Unavailable or weakly justified indicators should not be forced into the model. A model can include many factors, but if those factors cannot be measured reliably, they weaken rather than strengthen the decision logic.
- Weights should not be justified only by personal judgement. They should be tested through scenario or sensitivity analysis.

I treated this review as a trigger for model re-audit, not as a directive to implement every suggestion. Instead of directly adding each proposed factor into M2, I re-evaluated the model using four principles:

1. Data availability - can this indicator be reliably measured?
2. Business causality - is the link between indicator and business question defensible?
3. Controlled complexity - does this indicator belong in strategic scoring or in operational optimization?
4. Sensitivity-tested stability - are the weights stable under reasonable scenario changes?

These principles determined which indicators remained in M2, which were removed or downgraded, and which were deferred to M3 or M4.

## 7. Removing Weak Indicators and Rebuilding the 18 Sub-Indicator Model

The M2 indicator set underwent a significant cleanup. The model shifted from "adding more factors" to "selecting reliable factors." The instinct to include more factors is natural - supply chain is complex, and leaving something out feels risky. However, including a poorly measured or weakly connected indicator does not improve the decision. It adds noise.

Each retained sub-indicator had to satisfy three tests: (1) the data is observable or derivable from available fields, (2) the causal link between the indicator and the business question is defensible, and (3) the indicator meaning can be explained without relying on hidden assumptions.

**Indicators removed or downgraded from the main M2 score:**

| Removed or downgraded signal | Reason |
|---|---|
| assembly_value_add | Too many missing values; weak reliability as a main scoring field |
| cooperation_start_date in Cost/ESG | Relationship length does not directly prove lower cost or better ESG |
| city/community ESG proxy | Too subjective and difficult to justify consistently |
| annual_contract_value_usd as ESG | Contract size does not mean stronger ESG performance |
| payment_terms in Lead Time | Payment terms affect working capital, not actual delivery speed |
| duplicated certification indicators | Avoid double-counting the same certification signal |

**Indicators deferred to M3 or M4:**

- real freight mode
- actual loading rate
- true tariff rate
- detailed warehousing cost
- early inventory or stock-building decision
- exact transport route

These are real supply-chain factors, but they require operational data that the M2 scoring layer does not have. Including them would make the scoring model appear more precise than the data supports. They are better handled in M3 allocation optimization or M4 stress testing, where quantities, routes, and scenarios can be modeled explicitly.

This explains why several important factors were deferred instead of forced into M2. Real freight mode, actual loading rate, detailed tariff schedules, and warehousing costs are all genuinely important factors. But they require operational data that M2 does not have. Including them in a strategic scoring layer would make the model look precise on the surface while being fragile underneath. Deferring them to M3 or M4 was not an omission - it was a design decision that respects the difference between strategic scoring and operational optimization.

**Final M2 structure: five dimensions, 18 sub-indicators.**

After the audit, M2 was finalized around fewer but more defensible signals:

| Dimension | Sub-indicators |
|---|---|
| Cost | Base Cost Proxy; Transport/Landed Cost Proxy; Carbon Cost Proxy |
| ESG | Carbon Intensity; PCF Commitment; Certification Compliance; Labor/Governance |
| Risk | Country Risk; Financial Risk; Quality Risk; Single-source Dependency |
| Lead Time | Target-capped Lead Time; EU Logistics Complexity; Customs Complexity |
| Tech | Certification Level; Supplier Rating; Category Technical Complexity; Specialization Scarcity |

**Cost dimension.** Cost was decomposed into three proxy groups: Base Cost Proxy for approximate purchase cost pressure, Transport/Landed Cost Proxy for origin-to-EU logistics and landed-cost burden, and Carbon Cost Proxy for carbon-related cost exposure. This reflects the idea that supplier cost is not only purchase price. For EU-oriented sourcing, distance to market, logistics complexity, and carbon-related exposure also affect economic attractiveness.

**ESG dimension.** ESG was simplified into four explainable components: Carbon Intensity for CO2 emission performance, PCF Commitment for carbon footprint transparency, Certification Compliance for ESG/compliance readiness, and Labor/Governance for labor and governance risk. This structure separates three ideas that were previously easy to mix together: carbon performance, carbon footprint disclosure, and regulatory/governance readiness.

**Risk dimension.** Risk was rebuilt as Country Risk, Financial Risk, Quality Risk, and Single-source Dependency. A supplier can be financially stable but geographically exposed, or technically strong but quality-risky. This structure avoids treating risk as one generic score.

**Lead Time dimension.** Lead Time was revised into Target-capped Actual Lead Time, EU Logistics Complexity, and Customs Complexity. The key design change is target-capping: shorter lead time is better, but once a supplier meets the target lead time, the model should not reward excessive early delivery indefinitely.

**Tech dimension.** Tech was revised into Certification Level, Supplier Rating, Category Technical Complexity, and Specialization Scarcity. This dimension captures strategic capability, not only operational performance.

**Normalization and scoring direction.** All sub-indicators follow a five-level normalization logic: 5 = best, 4 = good, 3 = medium, 2 = weak, 1 = poor. For weighted aggregation, each score is converted to 0-1: `(score - 1) / 4`. Negative indicators such as cost, carbon intensity, lead time, and defect rate are reversed before aggregation so that higher final scores always mean better supplier performance. This unified scoring direction makes the model easier to explain, debug, and compare across dimensions.

## 8. Weight Justification Through Sensitivity Analysis

A major concern from the review was that weights should not be justified only by intuition. Therefore, three sets of sensitivity analysis were conducted to test whether the baseline weights produce stable rankings under different assumptions.

**Cost internal sensitivity (5 scenarios).** Cost weights were tested under baseline, base-cost-heavy, logistics-heavy, carbon-heavy, and equal-weight scenarios.

| Stability label | Share |
|---|---|
| Stable | 57% |
| Moderate | 38% |
| Sensitive | 5% |

The result shows that the baseline cost structure is stable for most suppliers. The top suppliers are not significantly overturned except under extreme carbon-heavy assumptions.

**ESG internal sensitivity (5 scenarios).** ESG weights were tested under carbon-performance-heavy, disclosure-heavy, compliance/governance-heavy, equal-weight, and baseline scenarios.

| Stability label | Share |
|---|---|
| Stable | 76% |
| Moderate | 24% |
| Sensitive | 0% |

This suggests that the ESG structure is highly stable. Changing internal ESG emphasis does not materially disrupt the supplier ranking.

**Five-dimension strategic sensitivity (5 scenarios).** The final supplier score was tested under Balanced Strategy, Cost Driven, ESG Driven, Risk Resilient, and Tech Driven strategy preferences.

| Stability label | Share |
|---|---|
| Stable | 30% |
| Moderate | 49% |
| Sensitive | 22% |

Across strategic scenarios, Top 10 overlap with the balanced baseline remains 9/10 or 10/10. In total, 29 out of 37 suppliers are Stable or Moderate.

This result is important because it shows two things at the same time. First, the model is sensitive enough to reflect different strategic preferences. Second, it is not so unstable that rankings become random. This sensitivity analysis provides the main evidence for why the baseline weights are acceptable. The weights are not purely subjective; they are validated against the range of plausible business priorities.

## 9. Decision: Separating Weighting Views from Procurement Decisions

Once AHP baseline weights, manual preference adjustment, and sensitivity analysis were established, an important structural question emerged: are the global Top 5 rankings from AHP and Manual weighting meant to be final procurement decisions?

The answer is no. A global ranking across four categories implies that a supplier in Key_Component and a supplier in General_Raw are directly substitutable, which is not how procurement works. A cross-category ranking provides a portfolio-level perspective, but the actual sourcing decision must respect category boundaries, supplier tier classification, and dimensional trade-offs visible at the category level.

The system was therefore structured into three levels:

### Level 1: Portfolio-Level Views

- **AHP weighting** is retained as an **Analytical Baseline** — a mathematically derived, portfolio-level view of relative importance across the five dimensions. It reflects balanced priorities from a multi-criteria decision analysis perspective.
- **Manual weighting** is retained as a **Management Preference View** — a what-if simulation of business priority adjustment. It allows the user to test how the ranking would shift if, for example, Cost were emphasized more heavily or Risk were deprioritized.

Both AHP and Manual global Top 5 outputs are useful for strategic discussion, but they are not procurement decisions. They answer "what does the portfolio look like under these weights?" not "which supplier should we source from?"

### Level 2: Robustness Validation

- **Sensitivity analysis** is the **Robustness Validation** layer. Its role is to test whether the baseline (AHP) weight structure produces stable rankings under different strategic assumptions. The Cost, ESG, and Strategic sensitivity analyses (15 scenarios total) provide the main evidence for baseline weight stability.
- Sensitivity does not select suppliers. It confirms that the ranking is not an artifact of a specific weight choice.

### Level 3: Procurement Action Views

Final sourcing decisions rely on three outputs that respect category boundaries and operational reality:

1. **Strategic Tier** — assigns suppliers into five actionable categories (Strategic Preferred, Core, Watchlist, Backup, Restricted), incorporating M1 gate discipline and multi-scenario stability.
2. **Category Ranking** — ranks suppliers within their own category, so procurement compares substitutable suppliers.
3. **Category Radar** — visualizes the five-dimension profile per category, enabling qualitative assessment of each supplier's strengths and weaknesses.

This three-level structure ensures that weighting views inform strategic discussion without being mistaken for final procurement decisions.

| Level | Purpose | Output |
|---|---|---|
| Portfolio-Level Views | Strategic discussion and what-if comparison | AHP and Manual global Top 5 |
| Robustness Validation | Evidence for weight stability | Cost / ESG / Strategic sensitivity |
| Procurement Action Views | Actual sourcing decisions | Strategic Tier + Category Ranking + Radar |

## 10. Strategic Supplier Tier as the Final M2 Decision Layer

The final M2 output is not only a ranking. A pure ranking is not enough for real supplier management because procurement teams need portfolio actions.

Therefore, suppliers are assigned into five strategic tiers:

| Tier | Meaning |
|---|---|
| Strategic Preferred | Stable, high-performing suppliers suitable for strategic partnership |
| Core Supplier | Reliable suppliers suitable for normal sourcing |
| Capability Watchlist | Suppliers with useful capability but visible weaknesses |
| Backup Supplier | Usable but lower-priority suppliers |
| Restricted Supplier | Suppliers restricted by M1 gate discipline or weak performance |

The current tier distribution is:

| Tier | Count |
|---|---|
| Strategic Preferred | 2 |
| Core Supplier | 8 |
| Capability Watchlist | 2 |
| Backup Supplier | 13 |
| Restricted Supplier | 12 |

All LIMITED suppliers are assigned to Restricted Supplier. This is intentional. A supplier should not become strategically preferred if M1 has already identified gate-level restrictions. This preserves the discipline between M1 qualification and M2 scoring: M1 gate status overrides M2 scoring preference. Restricted Supplier is not a deletion - it represents capped allocation with a defined remediation path.

## 11. Category-Level Ranking and Radar for Procurement Action

Once the Strategic Tier was established, a practical question emerged: what does a procurement team actually do with a global ranking of 37 suppliers across four categories? A single rank across all suppliers says little about who the best option is within Key_Component or General_Raw. Each category has different requirements, different suppliers, and different decision contexts.

### Ranking Tables by Category

The solution was simple: produce separate ranking tables per category so that procurement can compare suppliers within the same competitive set. The display rules are:

- **Key_Component, Critical_Raw**: show Top 5 per category (tier-1 supplier visibility)
- **General_Comp, General_Raw**: show Top 10 per category (broader pool for commodity-like items)

The ranking uses the same Final_Score computed for strategic tiering. No re-scoring. Global_Rank and Category_Rank are derived from the same weighted dimension scores. Each ranking CSV includes the five dimension scores, Final_Score, Global_Rank, and Category_Rank, giving procurement immediate visibility into why a supplier ranks where it does.

### Radar Charts by Category and Overall

Ranking tables answer the question "who is top in this category?" but they do not answer "why is this supplier strong?" The radar chart fills this gap by visualizing the five-dimension profile (Cost, ESG, Risk, LeadTime, Tech) in a single view.

The radar chart generation covers:

- **Per-category Top 3**: the best-performing suppliers in each category, plotted together so their dimensional strengths and weaknesses can be compared visually. This helps procurement see at a glance whether the top-ranked supplier leads across all dimensions or only on cost.
- **Overall Top 5**: the five highest Final_Score suppliers across the entire pool, regardless of category. This provides a consolidated benchmark of the strongest suppliers in the portfolio.

### Design Constraints

- No re-scoring: all visualizations derive from M2 scoring outputs; the ranking and radar layers are purely presentational.
- No gate override: M1 gate status is unchanged; category rankings may include LIMITED suppliers (their M1 penalty is already reflected in the Cost_Score).
- No weight distortion: the radar and ranking share the Balanced strategy dimension weights (0.25/0.25/0.20/0.15/0.15), the same weights used for Strategic Tier.

The ranking and radar outputs serve different roles in the procurement workflow: tables support quantitative comparison and supplier selection, radars support qualitative profile assessment and negotiation preparation.

*Output files: M2_Category_Ranking_Key_Component.csv, M2_Category_Ranking_Critical_Raw.csv, M2_Category_Ranking_General_Comp.csv, M2_Category_Ranking_General_Raw.csv, radar_m2_category_*.png, radar_m2_overall_top5.png*

## 12. Final Reflection: From Static Prototype to Decision Support System

The project evolved through several stages, each addressing a different layer of the problem:

- **Original integrated prototype**: full-chain demonstration, but bundled and simplified
- **M1 restructuring**: from pass/fail to business-realistic qualification with PASS/LIMITED/FAIL statuses
- **Scope convergence**: from broad network design to layered M1-M4 decision support
- **M2 foundation repair**: from broken scoring logic to business-consistent structure
- **External review**: from intuition-driven to evidence-validated indicator selection
- **M2 simplification**: from many weak indicators to 18 reliable sub-indicators
- **Sensitivity validation**: from subjective weights to scenario-tested stability
- **Strategic tiering**: from ranking to portfolio action with M1 gate discipline

The final system logic:

| Module | Question answered |
|---|---|
| M1 | Can this supplier be used? |
| M2 | How strategically attractive is this supplier? |
| M3 | How much demand should be allocated? |
| M4 | How resilient is the supplier structure under shocks? |

The project therefore follows a layered decision process:

Qualification -> Strategic Scoring -> Allocation Optimization -> Resilience Simulation

**Engineering reliability as a foundation.** Several cross-cutting improvements supported every stage of the revision. Configuration hardcoding was reduced so that penalties and caps are controlled from configuration rather than scattered across the model. Data generation was made deterministic, which helps avoid random changes in CI or repeated runs. M1 and M2 responsibilities were cleaned so that qualification, scoring, allocation, and stress testing remain separate.

These engineering fixes support the credibility of the model. A decision support system should not only produce reasonable results; it should also produce them consistently.

What may look like purely technical improvements - config decoupling, deterministic data generation, and responsibility cleanup - had a broader purpose. Config decoupling ensured that sensitivity analysis could vary weights without silently polluting global state; without this, the 15-scenario sensitivity run would have produced unreliable results. Deterministic data generation meant that every output could be reproduced identically across runs, which is essential for auditability and for comparing scenario outcomes. Responsibility cleanup - defining M1 as a qualification layer, M2 as a scoring layer, and deferring allocation to M3 - prevented the common trap of making one module try to do everything. These changes did not add new features, but they made every other feature more trustworthy.

Most importantly, the project moved from a static supplier scoring script to a more realistic Supplier Decision Support System prototype for EU-oriented manufacturing sourcing.

## 13. Traceability Matrix

| Decision | Source / Trigger | Final Design Response | Validation Evidence |
|---|---|---|---|
| Modularize the integrated prototype into a commercial DSS architecture | old_code.py.txt already demonstrated the full supplier decision chain, but in a bundled and simplified form | Reorganize the original M1-M5 logic into clearer modules: M1 qualification, M2 scoring/tiering, M3 allocation, and M4 resilience | Current architecture, M1 frozen status, revised 18-sub-indicator M2, sensitivity outputs |
| Keep PASS/LIMITED/FAIL instead of simple pass/fail | Real procurement logic and M1 audit | Suppliers enter Active, Conditional, or Reserve pools | M1 final result: PASS 32, LIMITED 5, FAIL 13 |
| Split labor risk explanations | M1 risk explanation audit | Separate confirmed forced labor from missing labor assurance | Decision reasons became more audit-readable |
| Correct M1_Risk_Exposure | Semantic inconsistency in exposure calculation | PASS=0, LIMITED=extra exposure, FAIL=full contract value | Risk exposure now reflects business impact |
| Define M1/M2/M3/M4 boundaries | Project scope convergence and data availability assessment | Separate qualification, scoring, allocation, and resilience roles | Current architecture documents M1/M2 and leaves M3/M4 planned |
| Remove weak M2 indicators | External review and indicator audit | Remove or downgrade weak-causal/unavailable indicators | Revised M2 uses 18 reliable sub-indicators |
| Use Cost = Base + Transport/Landed + Carbon | Cost realism gap | Build lightweight TCO proxy without full routing data | Cost internal sensitivity completed |
| Separate CO2, PCF, and ESG governance | ESG concept ambiguity | ESG includes carbon intensity, PCF, certification, labor/governance | ESG sensitivity shows 0% Sensitive |
| Defer real freight/loading/tariff/warehouse data | Data availability and complexity concerns | Leave detailed operational modeling to M3/M4 | Architecture states M3/M4 future scope |
| Validate weights through sensitivity analysis | Need to justify baseline weights | Run Cost, ESG, and strategic sensitivity scenarios | Cost/ESG/Strategic reports generated |
| Convert ranking to Strategic Tier | Ranking alone is not actionable | Output five supplier portfolio tiers | M2_Strategic_Tier.csv generated |

## 14. Advisor Feedback and Final Scope Convergence: From Scoring Model to Decision Support Prototype

After completing the revised M1 and M2 structure, I discussed the project direction with my supply chain advisor. This discussion became an important turning point because it clarified that the project should not continue expanding into an overly complex enterprise optimization model. Instead, the model should become more realistic, better bounded, and easier to defend with available data.

The main feedback was that supplier selection should not be treated as a simple weighted-score problem. In real procurement, some criteria work as qualification gates, some become cost penalties, some remain diagnostic indicators, and some represent strategic management preferences. Therefore, forcing every factor into one final score could create a false sense of precision.

### 14.1 Key Learning from Advisor Discussion

The advisor feedback helped clarify several important points:

- Lead time should not necessarily be rewarded as an independent score. If a supplier delivers within the promised cycle, that is normal fulfilment. If the supplier is late, the business impact should be reflected through delay cost, contract penalty, expedited logistics cost, or delivery-risk diagnostics.
- Risk should not be treated as a vague score without a measurable basis. If risk can be monetized, it should become a risk premium or penalty. If it cannot be reliably monetized, it should remain as a diagnostic signal.
- Technical capability is difficult to compare fairly as a generic weighted score. If a supplier lacks the required technology, it should normally be treated as an eligibility or qualification issue. If multiple suppliers are technically eligible, sourcing comparison should focus more on adjusted cost, ESG performance, delivery reliability, and risk exposure.
- Quality can appear in two layers. M1 checks whether a supplier meets minimum quality requirements. M2 may still consider over-the-threshold quality performance, defect risk, or quality-cost impact if the data is available.
- ESG should remain visible as a separate strategic dimension, especially for EU-oriented sourcing. Some ESG elements, such as carbon cost, can be partially monetized, while others, such as PCF readiness, certification, and labor governance, remain policy or governance indicators.
- The project should set a stopping point. A portfolio project should demonstrate clear thinking, realistic assumptions, and a working decision pipeline rather than trying to replicate a full enterprise procurement system.

### 14.2 Revised Interpretation of M2

This discussion changed the interpretation of M2. The earlier version treated Cost, ESG, Risk, Lead Time, and Tech as five weighted dimensions leading to a single Final_Score. That structure was useful as a first-stage strategic scoring prototype, but it was not the most realistic final interpretation of supplier decision-making.

The revised M2 should be understood as a two-layer or three-layer decision support module:

| Layer | Role | Decision Meaning |
|---|---|---|
| Scenario-based Adjusted TCO | Convert measurable cost-related supplier issues into an adjusted cost view | Supports supplier comparison and M3 allocation input |
| ESG Evaluation | Keep carbon, PCF readiness, certification, and labor governance visible | Supports EU-market sustainability and policy alignment |
| Risk & Performance Diagnostic | Retain TQRDC-style logic to explain supplier weaknesses and risk sources | Supports tiering, constraints, caps, and management interpretation |

This means the five-dimension or TQRDC-style logic is not deleted. It is repositioned. It becomes a supplier risk and performance diagnostic layer rather than the only final sourcing decision rule.

### 14.3 Why Penalty Coefficients Cannot Be Treated as Real Company Costs

The literature supports adding delay penalty, quality penalty, risk premium, and carbon cost into supplier selection and order allocation models. However, the actual coefficients are usually company-specific. In real implementation, these coefficients should come from:

- contract late-delivery penalty clauses;
- ERP delivery records and delay history;
- line-stoppage loss or expedited logistics cost;
- quality loss records such as scrap, rework, return, warranty, or defect cost;
- supplier disruption history or risk-premium estimation;
- internal carbon price, EU ETS, CBAM-related assumptions, or company ESG policy.

Because the current project does not have access to real contract clauses, ERP records, quality-cost records, or historical disruption-cost data, M2 should not claim to calculate a true enterprise-level adjusted TCO. Instead, it should be described as a calibratable, scenario-based adjusted TCO framework.

The correct interpretation is:

> The model structure is evidence-based, while the penalty coefficients are scenario parameters. In real enterprise deployment, these parameters should be replaced by company-specific contract, ERP, quality, finance, and ESG data.

This distinction prevents the model from pretending to have false precision while still keeping the decision logic useful.

### 14.4 Revised M2 Design Decision

The final M2 design direction is:

| Previous Interpretation | Revised Interpretation |
|---|---|
| Five weighted dimensions produce the final supplier score | Five/TQRDC-style evaluation supports diagnostic explanation |
| Lead time is a standalone positive dimension | Late delivery creates delay penalty or delivery-risk diagnostic |
| Risk is a normal weighted score | Risk becomes risk premium if monetizable, otherwise diagnostic |
| Tech is a normal weighted score | Tech is mainly eligibility, capability, or scarcity diagnostic |
| M2 ranking directly drives sourcing | Adjusted TCO + ESG + constraints support sourcing and allocation |

The revised M2 outputs should therefore include:

- Scenario-based Adjusted TCO or Adjusted Cost Index;
- ESG Score or ESG Evaluation;
- Supplier Risk & Performance Diagnostic;
- Strategic Tier;
- Category-level ranking and management view.

### 14.5 Revised M3 Scope Decision

The advisor discussion also clarified the M3 scope. Without real demand, supplier capacity, contract volumes, and production planning data, a complex MILP model would create mathematical precision that the input data cannot support.

Therefore, M3 should be designed as a lightweight, constraint-aware allocation prototype rather than a full enterprise optimization engine.

M3 should answer:

> Under normal operating conditions, how should category demand be allocated among eligible suppliers?

M3 should use:

- external or scenario-based category demand;
- supplier capacity proxy or scenario capacity;
- M1 status and capacity caps;
- M2 adjusted TCO;
- ESG performance;
- risk diagnostics;
- diversification rules.

M3 should output:

- allocation amount by supplier;
- allocation share;
- weighted adjusted TCO;
- weighted ESG score;
- unmet demand;
- concentration warning;
- use of LIMITED suppliers.

This makes M3 explainable and consistent with the available data.

### 14.6 Revised M4 Scope Decision

M4 should become the layer that shows how supplier choice and allocation respond to external changes. The purpose is not to simulate full legal compliance, tariffs, warehousing, routing, or production planning. Instead, M4 translates EU policy pressure and supply-chain disruptions into operational stress-test scenarios.

Recommended M4 scenarios:

| Scenario | Business Interpretation |
|---|---|
| Carbon price shock | High-carbon suppliers become more expensive under EU carbon pressure |
| Geopolitical disruption | Suppliers in selected countries or regions face reduced available capacity |
| Logistics delay shock | Long-distance or complex logistics suppliers receive higher delay-cost impact |
| Demand surge | Category demand increases and tests supplier coverage |
| Forced-labor exclusion | Suppliers with critical labor risk are excluded from normal sourcing |

M4 should compare before-and-after allocation results and show cost increase, ESG change, unmet demand, supplier concentration, and management recommendations.

### 14.7 Final Stopping Criteria

This feedback led to a clearer stopping point for the portfolio version of the project.

The project should not continue expanding into a full enterprise supply chain planning platform. The final portfolio version should stop when the following conditions are met:

| Module | Stopping Criterion |
|---|---|
| M1 | Qualification gates are stable and documented with data-foundation evidence |
| M2 | Revised as Adjusted TCO + ESG + Risk Diagnostic, with scenario parameters clearly documented |
| M3 | Normal-case allocation prototype works with demand, capacity, cap, ESG, and diversification assumptions |
| M4 | Stress-test scenarios show how supplier choice changes under carbon, geopolitical, logistics, labor, and demand shocks |
| Dashboard | Decision cockpit visualizes the end-to-end pipeline and management recommendations |

The project is therefore not positioned as a fully deployable procurement system. It is a portfolio-oriented decision support prototype that demonstrates how supplier decision logic can move from subjective scoring toward a more structured, evidence-aware, and scenario-tested sourcing framework.

### 14.8 Final Project Logic After Convergence

The final logic can be summarized as:

| Module | Core Question | Final Role |
|---|---|---|
| M1 | Can this supplier be used? | Qualification gate |
| M2 | Why is this supplier economically, strategically, or ESG-attractive? | Adjusted TCO + ESG + diagnostic evaluation |
| M3 | How much normal demand should be allocated? | Constraint-aware allocation prototype |
| M4 | How does the decision change under shocks? | Stress test and resilience simulation |
| Dashboard | What should management do? | Decision cockpit |

The final model philosophy is:

> Qualification before scoring. Adjusted TCO and ESG before ranking. Allocation after evaluation. Stress testing before recommendation.

This final convergence is important for the portfolio narrative. It shows that the model did not simply become more complicated over time. Instead, the design became more disciplined: every indicator needs a business meaning, every parameter needs an assumption source, and every module needs a clear decision role.

## 15. Parameter Register and MVP Implementation Direction

After the M2/M3 scope convergence, a new issue became clear: some future allocation and stress-test parameters cannot be defended as fixed real-world values without company-specific data. Examples include maximum supplier share, LIMITED supplier allocation cap, delay penalty rate, carbon price, risk premium, and quarterly demand. These values may be valid as scenario assumptions, but they should not be hidden inside the code or presented as universal procurement rules.

To address this, the project introduced a parameter register as a design-control layer. The purpose of the register is not to make the model more complex. Its purpose is to make the assumptions visible, traceable, and replaceable.

The new parameter register records:

- parameter name;
- related module;
- current value;
- unit;
- decision role;
- current source;
- real company replacement data;
- status;
- notes.

This creates a cleaner boundary between three types of data:

| Data Type | Meaning | Example |
|---|---|---|
| Real project data | Data already available in the current dataset | supplier category, country, annual contract value, M1 status |
| Scenario assumption | Temporary value used to run the MVP | supplier cap, LIMITED cap, quarterly demand placeholder |
| Enterprise replacement data | Data required for real deployment | procurement plan, supplier committed capacity, contract penalty clause, sourcing policy |

The key design decision is:

> The model structure can be evidence-based even when some parameters remain scenario-based. The condition is that all scenario parameters must be explicitly registered and explained.

This avoids false precision. Instead of saying "the model knows the true demand" or "the model knows the true penalty rate", the project now says:

> These parameters are currently scenario assumptions. In a company setting, they should be replaced by procurement plans, contract terms, supplier capacity data, sourcing policies, and ESG/carbon policy data.

### 15.1 M3 Demand Interpretation

The M3 demand issue was especially important. Historical annual contract value should not be mechanically converted into order demand using a fixed ratio such as `DEMAND_RATIO = 0.50`. Historical spend may be useful as a reference for supplier scale or sourcing exposure, but it is not the same as future demand.

Therefore, M3 demand is now treated as an external or scenario input.

The correct interpretation is:

| Incorrect Interpretation | Revised Interpretation |
|---|---|
| M3 demand is generated from historical contract value using a fixed ratio | M3 demand is provided as a planning or scenario input |
| Annual contract value directly determines quarterly order amount | Annual contract value may support supplier capacity proxy or exposure analysis |
| Demand assumptions are hardcoded | Demand assumptions are registered and marked as pending/provisional |

This decision keeps M3 closer to real procurement practice. In a company environment, category demand would normally come from a procurement plan, production plan, sales forecast, MRP/ERP system, or category manager input.

### 15.2 M3 MVP Scope

The M3 MVP should remain lightweight and explainable. It should not start with a complex MILP model because the current project does not yet have real quarterly demand, supplier committed capacity, contract penalty terms, or production planning data.

The first M3 implementation should therefore focus on a single-category allocation case. Other categories can later be tested by changing category-level parameters, qualification thresholds, and preference settings.

The M3 MVP should:

- select eligible suppliers from M1/M2 outputs;
- use external or scenario-based category demand;
- apply supplier capacity proxy or registered capacity assumption;
- limit concentration through a maximum single-supplier share;
- restrict LIMITED suppliers through a separate cap;
- allocate demand using a simple, transparent preference score;
- flag unmet demand or insufficient supplier coverage;
- produce allocation amount, allocation share, and warning indicators.

This single-category logic is not a weakness. It is a deliberate MVP boundary. In real sourcing decisions, suppliers must be comparable before they can be allocated against the same demand. If different suppliers provide completely different products, direct allocation comparison becomes a multi-product sourcing problem and requires additional data structures.

### 15.3 Role of Benchmarking

Benchmarking remains useful, but it should not delay the MVP. The purpose of benchmarking is not to force this project to copy another paper or company model. The purpose is to test whether a simpler, more accessible decision framework can produce similar or explainable results when applied to public case data.

The benchmark should answer:

- What data does the public case provide?
- Which of the project's required indicators are available?
- Which indicators are missing?
- Does the model produce a similar supplier ranking or selection result?
- If the result differs, which indicators explain the difference?
- Can the project reach a useful decision with fewer or more obtainable inputs?

This means the benchmark is a validation and comparison layer, not the core model itself.

### 15.4 Updated Portfolio MVP Boundary

For the portfolio version, the project should now converge to the following MVP:

| Component | MVP Role |
|---|---|
| M1 | Supplier qualification and reserve-pool logic |
| M2 | Cost-ESG shortlist plus supplier diagnostic view |
| Parameter Register | Transparent management of scenario assumptions |
| M3 | Single-category normal allocation prototype |
| M4 | Stress-test scenarios showing decision changes |
| Dashboard | Management-facing decision cockpit |
| Mini Benchmark | One public case comparison after the MVP is functional |

The revised project narrative is therefore:

> Build the MVP first, make assumptions visible, then validate selectively.

This is more suitable for a portfolio project than trying to build a fully optimized enterprise procurement platform. It keeps the project practical enough to finish, but still shows mature supply-chain thinking: data availability, parameter traceability, decision boundaries, and business explainability.
