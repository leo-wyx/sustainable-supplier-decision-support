# Portfolio Project Brief

## Project Title

Cost-led ESG Supplier Decision Support System

## Short Description

Built a modular supplier decision-support system for EV battery supply-chain
sourcing. The project combines supplier qualification gates, adjusted cost
indexing, ESG premium tolerance, TQRDC diagnostic risk profiling, strategic
supplier pooling, lightweight allocation simulation, resilience scenarios, and
external benchmark validation.

## Resume Bullets

### English Version

- Built an end-to-end supplier decision-support pipeline for EV battery supply
  chain sourcing, covering qualification gates, adjusted cost indexing, ESG
  trade-off ranking, diagnostic risk profiling, strategic supplier pooling, and
  scenario validation.
- Replaced arbitrary Cost/ESG weighted scoring with a cost-led ESG premium
  tolerance method, quantifying how much adjusted-cost premium is required to
  justify selecting a higher-ESG supplier.
- Designed M3/M4 extension modules to compare allocation policies and stress
  test supplier pool resilience under demand surge, preferred supplier
  disruption, EU carbon pressure, and Malaysia backup-node scenarios.
- Validated supplier-pool logic through internal stability analysis and an
  external green supplier-selection benchmark, achieving 100% top/bottom tier
  alignment on the published green supplier case.

## STAR Interview Story

### Situation

Supplier selection for EV battery supply chains must balance cost pressure,
ESG requirements, qualification risk, delivery exposure, and resilience. A
simple weighted supplier score is difficult to defend because cost, ESG, risk,
and quality do not behave like fully interchangeable factors.

### Task

Build an explainable sourcing decision-support model that can identify
qualified suppliers, quantify cost-ESG trade-offs, classify suppliers into
management-ready pools, and demonstrate downstream allocation and scenario use.

### Action

1. Built M1 qualification gates for Quality, Finance, Technology, Labor,
   Compliance, and Ethics.
2. Built M2 Adjusted Cost Index using base, logistics, and carbon cost
   components.
3. Reframed ESG from a weighted score into a required cost-premium tolerance
   question.
4. Kept TQRDC as a diagnostic layer instead of forcing unsupported monetary
   penalties.
5. Built Strategic Pool labels for sourcing actions.
6. Added M3 allocation policy comparison and M4 resilience scenarios.
7. Added stability analysis and external green supplier benchmark validation.

### Result

- M2 processed 37 active suppliers and classified them into 4 Preferred,
  14 Core, 8 Conditional, and 11 Restricted suppliers.
- 7 suppliers showed ESG-justified premiums under 5% or 15% tolerance bands.
- 30/37 suppliers were stable under M2 pool stability analysis.
- M4 tested 16 scenario-policy combinations and achieved full demand coverage
  under current illustrative assumptions.
- External green benchmark achieved 6/6 top/bottom tier alignment.

## Core Technical Talking Points

### Why not use Cost 70% + ESG 30%?

A weighted score hides the actual cost paid for ESG and may double-count carbon
because carbon is already included in Adjusted Cost Index. The project instead
uses required ESG premium tolerance, which is easier to explain to procurement
and management.

### Why is TQRDC not converted into penalty cost?

Risk, delivery, and quality penalties require contract-level delay penalties,
ERP late-delivery loss, quality scrap/rework cost, warranty cost, or disruption
loss data. Without those data sources, monetizing TQRDC would create false
precision. The current model keeps TQRDC as diagnostic risk and pool context.

### Why keep M3 and M4 lightweight?

Real allocation optimization requires actual demand, committed supplier
capacity, minimum order quantity, contract price, and policy constraints. The
current M3/M4 modules demonstrate how M2 outputs can be used downstream without
pretending to be a full enterprise optimization engine.

## Interview Questions to Prepare

1. What is the difference between Adjusted Cost Index and true TCO?
2. Why is ESG handled as cost premium tolerance rather than a fixed weight?
3. How does Strategic Pool differ from final order allocation?
4. What data would be needed to convert TQRDC diagnostics into monetary
   penalties?
5. Why does the external benchmark validate direction rather than exact
   operational accuracy?
6. What would you improve if real company procurement data were available?

## One-Sentence Pitch

I built an explainable supplier decision-support system that links cost,
carbon, ESG readiness, supplier risk, sourcing pool classification, allocation
policy comparison, and resilience scenarios into one reproducible analytics
pipeline.
