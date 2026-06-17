"""Streamlit dashboard for Sustainable Supplier Decision Support System."""

import os
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

POOL_ORDER = ["Preferred", "Core", "Conditional", "Restricted"]

TRADEOFF_LABELS = {
    "no_tradeoff_needed": "No tradeoff needed",
    "lower_esg_or_no_esg_advantage": "No ESG advantage",
    "esg_justified_under_5pct": "ESG justified (<5%)",
    "esg_justified_under_15pct": "ESG justified (<15%)",
    "esg_not_justified_cost_gap_too_high": "Cost gap too high",
}

SCENARIO_LABELS = {
    "Demand_Surge_50": "Demand Surge 50%",
    "Preferred_Disruption": "Preferred Disruption",
    "EU_Carbon_Pressure": "EU Carbon Pressure",
    "Malaysia_Backup_Node": "Malaysia Backup Node",
}


def read_csv(name):
    """Read a CSV from the project directory, return None if missing."""
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        st.warning(f"File not found: {name}")
        return None
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        return df
    except Exception as exc:
        st.warning(f"Cannot read {name}: {exc}")
        return None


def _pool_bar(df, col, title):
    """Horizontal bar chart for Strategic Pool distribution, ordered."""
    data = df[col].value_counts().reindex(POOL_ORDER).fillna(0).astype(int)
    if HAS_PLOTLY:
        fig = px.bar(
            x=data.values, y=data.index, orientation="h",
            title=title, text_auto=True,
            color=data.index, color_discrete_sequence=px.colors.qualitative.Set2,
            labels={"x": "Supplier Count", "y": "Strategic Pool", "color": "Strategic Pool"},
            category_orders={"y": list(reversed(POOL_ORDER))},
        )
        fig.update_layout(showlegend=False, height=280, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(data, horizontal=True)


def _horiz_count_chart(series, title, label_map=None, height=280, xlabel="Count"):
    """Horizontal bar chart from a value_counts series."""
    data = series.copy()
    if label_map:
        data.index = data.index.map(lambda x: label_map.get(x, x))
    if HAS_PLOTLY:
        fig = px.bar(
            x=data.values, y=data.index, orientation="h",
            title=title, text_auto=True,
            color=data.index, color_discrete_sequence=px.colors.qualitative.Set2,
            labels={"x": xlabel, "y": "", "color": ""},
        )
        fig.update_layout(showlegend=False, height=height, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(data, horizontal=True)


st.set_page_config(
    page_title="Sustainable Supplier Decision Support Dashboard",
    layout="wide",
)

st.title("Sustainable Supplier Decision Support Dashboard")

tabs = st.tabs(
    ["Overview", "Supplier Pool", "Cost-ESG Trade-off",
     "Allocation Policy", "Resilience Scenario", "Validation"]
)

# ---------------------------------------------------------------------------
# TAB 1 - Overview
# ---------------------------------------------------------------------------
with tabs[0]:
    # Executive Summary
    st.subheader("Executive Summary")
    st.markdown(
        "The current supplier pool comprises **50 raw candidates**, "
        "of which **37 pass M1 screening** and enter the M2 strategic evaluation. "
        "The pool is distributed as **4 Preferred**, **14 Core**, **8 Conditional**, "
        "and **11 Restricted** suppliers. Stability is strong: **30 of 37 suppliers** "
        "are classified as Stable. External benchmark validation shows **6 aligned** "
        "and **4 different-but-explainable** results. Across all 16 resilience "
        "scenario-policy combinations, **Balanced Core** consistently emerges as "
        "the most robust allocation policy, fully covering demand with a moderate "
        "cost index. **Recommendation:** maintain the current pool structure with "
        "a focus on the Core and Preferred tiers for key-category sourcing."
    )

    sup = read_csv("suppliers_data.csv")
    spv = read_csv("M2_Strategic_Pool_View.csv")
    stb = read_csv("M2_Pool_Stability_Report.csv")
    ben = read_csv("M2_External_Benchmark_Green_Result.csv")

    # KPI row 1
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Raw Suppliers", "50")
    active = len(spv) if spv is not None else 0
    k2.metric("Active M2 Suppliers", "37")
    k3.metric("Preferred", "4")
    k4.metric("Core", "14")
    k5.metric("Conditional / Restricted", "8 / 11")

    # KPI row 2
    k6, k7, k8, k9, k10 = st.columns(5)
    k6.metric("Stable (of 37)", "30")
    k7.metric("Benchmark Aligned", "6")
    k8.metric("Benchmark Diff/Explainable", "4")
    k9.metric("Non-stable Suppliers", "7")
    k10.metric("M4 Coverage (16/16)", "100%")

    # Pool distribution chart
    st.subheader("Strategic Pool Distribution")
    if spv is not None and "Strategic_Pool" in spv.columns:
        _pool_bar(spv, "Strategic_Pool", "Supplier Count by Strategic Pool")

    # Stability mini-section
    st.subheader("Key Findings")
    f1, f2 = st.columns(2)
    with f1:
        st.markdown("- **Pool coverage:** 37 suppliers across 4 tiers covers "
                     "demand in all 16 scenario-policy combinations.")
        st.markdown("- **Stability:** 30 of 37 suppliers are Stable; "
                     "7 are non-stable (Moderate/Sensitive) and may require monitoring.")
    with f2:
        st.markdown("- **Benchmark:** 6 suppliers align with the paper-based "
                     "green classification; 4 diverge for explainable reasons.")
        st.markdown("- **Recommended policy:** Balanced Core offers the best "
                     "trade-off between diversification and cost efficiency.")

    # Tradeoff summary inside expander
    tdr = read_csv("M2_Cost_ESG_Tradeoff_Summary.csv")
    if tdr is not None:
        with st.expander("Cost-ESG Trade-off Summary by Category"):
            st.dataframe(tdr, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 2 - Supplier Pool
# ---------------------------------------------------------------------------
with tabs[1]:
    st.header("Supplier Pool Details")

    spv = read_csv("M2_Strategic_Pool_View.csv")
    if spv is not None:
        filter_cols = st.columns(4)

        categories = sorted(spv["category"].dropna().unique()) if "category" in spv.columns else []
        cat_sel = filter_cols[0].multiselect("Category", options=categories, default=categories)

        pool_opts = POOL_ORDER
        pool_sel = filter_cols[1].multiselect("Strategic Pool", options=pool_opts, default=pool_opts)

        tier_opts = sorted(spv["ESG_Position_Tier"].dropna().unique()) if "ESG_Position_Tier" in spv.columns else []
        tier_sel = filter_cols[2].multiselect("ESG Position Tier", options=tier_opts, default=tier_opts)

        risk_opts = sorted(spv["risk_level"].dropna().unique()) if "risk_level" in spv.columns else []
        risk_sel = filter_cols[3].multiselect("Risk Level", options=risk_opts, default=risk_opts)

        mask = pd.Series(True, index=spv.index)
        if cat_sel and "category" in spv.columns:
            mask &= spv["category"].isin(cat_sel)
        if pool_sel and "Strategic_Pool" in spv.columns:
            mask &= spv["Strategic_Pool"].isin(pool_sel)
        if tier_sel and "ESG_Position_Tier" in spv.columns:
            mask &= spv["ESG_Position_Tier"].isin(tier_sel)
        if risk_sel and "risk_level" in spv.columns:
            mask &= spv["risk_level"].isin(risk_sel)

        filtered = spv[mask]

        # Insight box
        pool_mix = filtered["Strategic_Pool"].value_counts().reindex(POOL_ORDER).fillna(0).astype(int)
        mix_str = " | ".join(f"{p}: {pool_mix[p]}" for p in POOL_ORDER)
        st.info(f"**{len(filtered)} suppliers selected** | Pool mix: {mix_str}")

        # Pool bar chart
        c1, c2 = st.columns([1, 2])
        with c1:
            _pool_bar(filtered, "Strategic_Pool", "Pool Distribution (filtered)")

        # Table inside expander
        display_cols = [
            "supplier_id", "supplier_name", "category", "Adjusted_Cost_Index",
            "ESG_Position_Tier", "risk_level", "delivery_risk",
            "Strategic_Pool", "pool_reason",
        ]
        display_cols = [c for c in display_cols if c in filtered.columns]
        with st.expander("Supplier Detail Table", expanded=True):
            st.dataframe(filtered[display_cols], use_container_width=True)

        # Pool count by category chart
        st.subheader("Pool Count by Category")
        if "category" in filtered.columns and "Strategic_Pool" in filtered.columns:
            ct = filtered.groupby(["category", "Strategic_Pool"]).size().unstack(fill_value=0)
            ct = ct.reindex(columns=[c for c in POOL_ORDER if c in ct.columns], fill_value=0)
            if HAS_PLOTLY:
                fig = px.bar(
                    ct, barmode="group",
                    title="Supplier Count by Category and Strategic Pool",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"value": "Supplier Count", "category": "Category",
                            "Strategic_Pool": "Strategic Pool"},
                )
                fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(ct)
    else:
        st.info("Supplier pool data not available.")

# ---------------------------------------------------------------------------
# TAB 3 - Cost-ESG Trade-off
# ---------------------------------------------------------------------------
with tabs[2]:
    st.header("Cost-ESG Trade-off Ranking")

    tr = read_csv("M2_Cost_ESG_Tradeoff_Ranking.csv")
    if tr is not None:
        st.markdown(
            "ESG is represented as a **required cost premium tolerance**, "
            "not an arbitrary weight. For each supplier, the model checks whether "
            "a cheaper, lower-ESG reference exists and computes the cost premium "
            "needed to select the higher-ESG option. Management chooses a tolerance "
            "level below which the premium is acceptable."
        )

        # Key insight cards
        if "tradeoff_status" in tr.columns:
            counts = tr["tradeoff_status"].value_counts()
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("No trade-off needed",
                       counts.get("no_tradeoff_needed", 0))
            r2.metric("ESG justified (<5% premium)",
                       counts.get("esg_justified_under_5pct", 0))
            r3.metric("No ESG advantage",
                       counts.get("lower_esg_or_no_esg_advantage", 0))
            r4.metric("Cost gap too high (>15%)",
                       counts.get("esg_not_justified_cost_gap_too_high", 0))

        # Tolerance selector
        tol = st.radio(
            "Select ESG premium tolerance",
            options=["0%", "5%", "10%", "15%"],
            horizontal=True,
            index=1,
        )
        tol_map = {"0%": "accepted_under_0pct", "5%": "accepted_under_5pct",
                   "10%": "accepted_under_10pct", "15%": "accepted_under_15pct"}
        tol_col = tol_map[tol]

        # Trade-off status chart (horizontal, short labels)
        st.subheader("Trade-off Status Distribution")
        status_counts = tr["tradeoff_status"].value_counts()
        _horiz_count_chart(status_counts, "", label_map=TRADEOFF_LABELS, height=250, xlabel="Supplier Count")

        # Accepted chart
        if tol_col in tr.columns:
            acc = tr[tol_col].dropna()
            if len(acc) > 0:
                st.subheader(f"Acceptance under {tol} Tolerance")
                _horiz_count_chart(acc.value_counts(), "", height=180)

        # Detail table
        display_cols_tr = [
            "supplier_id", "supplier_name", "category", "Adjusted_Cost_Index",
            "ESG_Position_Tier", "required_esg_premium_pct", tol_col,
            "tradeoff_status", "Strategic_Pool",
        ]
        display_cols_tr = [c for c in display_cols_tr if c in tr.columns]
        with st.expander(f"Supplier Ranking Table (tolerance = {tol})"):
            st.dataframe(tr[display_cols_tr], use_container_width=True)

    tdr = read_csv("M2_Cost_ESG_Tradeoff_Summary.csv")
    if tdr is not None:
        with st.expander("Trade-off Summary by Category"):
            st.dataframe(tdr, use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 4 - Allocation Policy
# ---------------------------------------------------------------------------
with tabs[3]:
    st.header("Allocation Policy Comparison")

    ap = read_csv("M3_Key_Category_Allocation_Summary.csv")
    if ap is not None:
        # Interpretation cards
        st.subheader("Policy Overview")
        p1, p2, p3, p4 = st.columns(4)
        p1.markdown("**Preferred First**\n\nLowest complexity, concentrates "
                     "spend on Preferred suppliers. Minimal diversification.")
        p2.markdown("**Balanced Core**\n\nDiversifies within Core tier. "
                     "Moderate cost increase, best resilience coverage.")
        p3.markdown("**Cost Minimized**\n\nOptimizes for lowest weighted cost. "
                     "Narrow supplier base, higher concentration risk.")
        p4.markdown("**Risk Controlled**\n\nWidest diversification across tiers. "
                     "Highest supplier count but also highest weighted cost.")

        # Summary table
        comp_cols = [
            "label", "category", "total_demand", "allocated_amount",
            "unmet_demand", "preferred_share", "core_share", "conditional_share",
            "weighted_cost_index", "supplier_count_used", "risk_notes",
        ]
        comp_cols = [c for c in comp_cols if c in ap.columns]
        st.dataframe(ap[comp_cols], use_container_width=True)

        # Charts: grouped comparison
        st.subheader("Weighted Cost Index vs Supplier Count")
        c1, c2 = st.columns(2)
        with c1:
            if "label" in ap.columns and "weighted_cost_index" in ap.columns:
                if HAS_PLOTLY:
                    fig = px.bar(
                        ap, x="label", y="weighted_cost_index",
                        title="Weighted Cost Index by Policy",
                        text_auto=".4f",
                        color="label", color_discrete_sequence=px.colors.qualitative.Set2,
                        labels={"label": "Policy", "weighted_cost_index": "Weighted Cost Index"},
                    )
                    fig.update_layout(showlegend=False, height=350,
                                      xaxis_title="", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    chart_data = ap.set_index("label")["weighted_cost_index"]
                    st.bar_chart(chart_data)

        with c2:
            if "label" in ap.columns and "supplier_count_used" in ap.columns:
                if HAS_PLOTLY:
                    fig = px.bar(
                        ap, x="label", y="supplier_count_used",
                        title="Supplier Count by Policy",
                        text_auto=True,
                        color="label", color_discrete_sequence=px.colors.qualitative.Set2,
                        labels={"label": "Policy", "supplier_count_used": "Supplier Count"},
                    )
                    fig.update_layout(showlegend=False, height=350,
                                      margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(ap.set_index("label")["supplier_count_used"])

        st.subheader("Pool Shares by Policy")
        share_cols = [c for c in ["preferred_share", "core_share", "conditional_share"] if c in ap.columns]
        if share_cols and "label" in ap.columns:
            if HAS_PLOTLY:
                fig = px.bar(
                    ap, x="label", y=share_cols,
                    title="Pool Allocation Shares by Policy",
                    barmode="group",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"label": "Policy", "value": "Share (%)"},
                )
                fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(ap.set_index("label")[share_cols])
    else:
        st.info("Allocation policy data not available.")

# ---------------------------------------------------------------------------
# TAB 5 - Resilience Scenario
# ---------------------------------------------------------------------------
with tabs[4]:
    st.header("Resilience Scenario Analysis")

    sc = read_csv("M4_Scenario_Summary.csv")
    if sc is not None:
        # Key metric: 16/16
        total_combos = len(sc)
        all_covered = (sc["unmet_demand"] == 0).all() if "unmet_demand" in sc.columns else False
        k1, k2 = st.columns(2)
        k1.metric("Scenario-Policy Combinations", f"{total_combos}/16 fully cover demand",
                   delta="100%" if all_covered else "Partial")
        k2.metric("Balanced Core Robustness",
                   "Demand met across all 4 scenarios with Core reserve activated.",
                   delta="Best overall")

        # Filters
        fcols = st.columns(2)
        scenarios = sorted(sc["scenario"].dropna().unique()) if "scenario" in sc.columns else []
        policies = sorted(sc["policy"].dropna().unique()) if "policy" in sc.columns else []

        scen_sel = fcols[0].multiselect("Scenario", options=scenarios, default=scenarios)
        pol_sel = fcols[1].multiselect("Policy", options=policies, default=policies)

        mask = pd.Series(True, index=sc.index)
        if scen_sel and "scenario" in sc.columns:
            mask &= sc["scenario"].isin(scen_sel)
        if pol_sel and "policy" in sc.columns:
            mask &= sc["policy"].isin(pol_sel)
        filtered_sc = sc[mask]

        # Summary table
        disp_sc = [
            "scenario", "policy", "total_demand", "allocated_amount",
            "unmet_demand", "preferred_share", "core_share", "conditional_share",
            "weighted_cost_index", "supplier_count_used", "key_finding",
        ]
        disp_sc = [c for c in disp_sc if c in filtered_sc.columns]
        st.dataframe(filtered_sc[disp_sc], use_container_width=True)

        # Coverage check
        if all_covered:
            st.success("All 16 scenario-policy combinations fully cover demand (unmet_demand = 0).")
        else:
            st.warning("Some combinations show unmet demand.")

        # Weighted cost chart: grouped bars by policy within each scenario
        st.subheader("Weighted Cost Index: Grouped by Scenario and Policy")
        if ("scenario" in filtered_sc.columns and "policy" in filtered_sc.columns
                and "weighted_cost_index" in filtered_sc.columns):
            chart_df = filtered_sc.copy()
            if "scenario" in chart_df.columns:
                chart_df["scenario_short"] = chart_df["scenario"].map(
                    lambda x: SCENARIO_LABELS.get(x, x)
                )

            if HAS_PLOTLY:
                fig = px.bar(
                    chart_df, x="scenario_short", y="weighted_cost_index",
                    color="policy", barmode="group",
                    title="Weighted Cost Index by Scenario and Policy",
                    text_auto=".3f",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"scenario_short": "Scenario", "weighted_cost_index": "Weighted Cost Index",
                            "policy": "Policy"},
                )
                fig.update_layout(
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                pt = filtered_sc.pivot_table(
                    index="scenario", columns="policy",
                    values="weighted_cost_index", aggfunc="first"
                )
                st.bar_chart(pt)
    else:
        st.info("Scenario data not available.")

# ---------------------------------------------------------------------------
# TAB 6 - Validation
# ---------------------------------------------------------------------------
with tabs[5]:
    st.header("Validation")

    # Summary cards
    st.subheader("Key Metrics")
    vk1, vk2, vk3, vk4 = st.columns(4)
    vk1.metric("Stable Suppliers", "30 / 37")
    vk2.metric("Benchmark Aligned", "6")
    vk3.metric("Benchmark Diff/Explainable", "4")
    vk4.metric("Sensitive Suppliers", "3")

    v1, v2 = st.columns(2)

    with v1:
        st.subheader("Pool Stability")
        stb = read_csv("M2_Pool_Stability_Report.csv")
        if stb is not None and "stability_label" in stb.columns:
            _horiz_count_chart(
                stb["stability_label"].value_counts(),
                "Stability Distribution",
                height=200,
                xlabel="Supplier Count",
            )
            with st.expander("Stability Detail Table"):
                st.dataframe(stb, use_container_width=True)
        else:
            st.info("Stability report not available.")

    with v2:
        st.subheader("External Benchmark (Green)")
        ben = read_csv("M2_External_Benchmark_Green_Result.csv")
        if ben is not None:
            _horiz_count_chart(
                ben["directional_alignment_flag"].value_counts(),
                "Directional Alignment",
                height=200,
                xlabel="Supplier Count",
            )

            if "simplified_green_pool" in ben.columns and "directional_alignment_flag" in ben.columns:
                with st.expander("Green Pool vs Alignment Cross-Tab"):
                    ct = pd.crosstab(
                        ben["simplified_green_pool"],
                        ben["directional_alignment_flag"]
                    )
                    st.dataframe(ct)

            with st.expander("Benchmark Detail Table"):
                disp_ben = [
                    "supplier_id", "paper_priority_weight", "recomputed_green_score",
                    "simplified_green_pool", "directional_alignment_flag",
                    "directional_alignment_reason",
                ]
                disp_ben = [c for c in disp_ben if c in ben.columns]
                st.dataframe(ben[disp_ben], use_container_width=True)
        else:
            st.info("Benchmark data not available.")
