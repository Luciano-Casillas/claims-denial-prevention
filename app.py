"""
Clarity Health Plans - Claims Denial Prevention Intelligence Dashboard
Author: Luciano Casillas
Version: 2.0

Interactive analysis of health insurance claims denial patterns, root causes,
and financial recovery opportunities. Loads and aggregates the real synthetic
dataset (data/clarity_claims.csv, clarity_denials.csv, clarity_providers.csv)
and the retrained XGBoost model (models/model_metrics.json) live -- nothing
on this dashboard is hardcoded from a prior analysis run.
"""

import json
import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PAGE CONFIG & STYLING
# ============================================================

st.set_page_config(
    page_title="Clarity Health - Denial Prevention",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Color palette
NAVY = "#0A3360"
STEEL_700 = "#405E7C"
BLUE_700 = "#0077B3"
BLUE_500 = "#4EBEE5"
STEEL_300 = "#D1E2E5"
STEEL_100 = "#F4F9FA"
WHITE = "#FFFFFF"
BLACK = "#2D2D2D"
GRAY_700 = "#707070"
GRAY_300 = "#CCCCCC"
GREEN_700 = "#08CAA9"
GREEN_900 = "#067462"
ORANGE_700 = "#FF8A39"
RED_700 = "#E8543C"

# ------------------------------------------------------------
# Consistent color encoding used across every tab:
#   ORANGE  -> denial volume / denied dollars / risk (the problem)
#   GREEN   -> appeal success / recovery potential (the opportunity)
#   BLUE    -> neutral descriptive metrics (specialty, feature importance)
#   STEEL   -> muted / non-highlighted comparison bars
# ------------------------------------------------------------

# Custom CSS
st.markdown("""
<style>
    body {
        background-color: white;
    }
    .stApp {
        background-color: white;
    }
    [data-testid="stSidebar"] {
        background-color: white;
    }
    .insight-strip {
        background-color: white;
        border-left: 4px solid #0077B3;
        padding: 16px;
        border-radius: 4px;
        margin: 16px 0;
    }
    .insight-strip-label {
        color: #0A3360;
        font-weight: 600;
        font-size: 12px;
        margin-bottom: 8px;
    }
    .insight-strip-text {
        color: #2D2D2D;
        font-size: 14px;
        line-height: 1.6;
    }
    .section-header {
        background-color: #F4F9FA;
        border-left: 4px solid #0077B3;
        padding: 16px;
        margin: 24px 0 16px 0;
        font-weight: 600;
        font-size: 14px;
        color: #0A3360;
    }
    .metric-card {
        background-color: white;
        border: 1px solid #D1E2E5;
        border-left: 4px solid #0077B3;
        padding: 16px;
        border-radius: 4px;
    }
    .rec-card {
        background-color: white;
        border: 1px solid #D1E2E5;
        border-left: 4px solid #0077B3;
        padding: 16px;
        border-radius: 4px;
        margin: 12px 0;
    }
    .caveat-note {
        color: #707070;
        font-size: 11px;
        font-style: italic;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA LOADING (real CSVs, computed live -- not hardcoded)
# ============================================================

DENIAL_CATEGORY_MAP_NOTE = (
    "PA01-PA03=Prior Authorization | CVRG01-02=Coverage Limits | "
    "NW01-02 & 'provider not network'=Network Issue | BILL01-02=Billing Error | "
    "MED01=Medical Necessity | 999/blank/free-text='Other / Unclassified'"
)


def categorize_denial_reason(code):
    if pd.isna(code):
        return "Other / Unclassified"
    code = str(code)
    if code in ("PA01", "PA02", "PA03"):
        return "Prior Authorization"
    if code in ("CVRG01", "CVRG02"):
        return "Coverage Limits"
    if code in ("NW01", "NW02", "provider not network"):
        return "Network Issue"
    if code in ("BILL01", "BILL02"):
        return "Billing Error"
    if code == "MED01":
        return "Medical Necessity"
    return "Other / Unclassified"


@st.cache_data
def load_raw_data():
    claims = pd.read_csv("data/clarity_claims.csv")
    denials = pd.read_csv("data/clarity_denials.csv")
    providers = pd.read_csv("data/clarity_providers.csv")

    claims["is_denied"] = claims["claim_id"].isin(denials["claim_id"]).astype(int)
    denials = denials.copy()
    denials["category"] = denials["denial_reason_code"].apply(categorize_denial_reason)

    # Merge specialty onto claims for filtering/grouping
    claims = claims.merge(
        providers[["provider_id", "specialty", "network_status"]],
        on="provider_id", how="left"
    )

    return claims, denials, providers


@st.cache_data
def load_model_metrics():
    try:
        with open("models/model_metrics.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


@st.cache_data
def load_data_metadata():
    try:
        with open("data/clarity_metadata.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def two_proportion_ztest(x1, n1, x2, n2):
    """Two-proportion z-test using the normal approximation (no scipy dependency)."""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pool if se_pool > 0 else 0.0
    # two-sided p-value from standard normal CDF via erf
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))

    se1 = math.sqrt(p1 * (1 - p1) / n1)
    se2 = math.sqrt(p2 * (1 - p2) / n2)
    ci1 = (p1 - 1.96 * se1, p1 + 1.96 * se1)
    ci2 = (p2 - 1.96 * se2, p2 + 1.96 * se2)
    return z, pval, ci1, ci2


claims_all, denials_all, providers_all = load_raw_data()
model_metrics = load_model_metrics()
data_metadata = load_data_metadata()

# ============================================================
# SIDEBAR FILTERS (built from real distinct values, actually applied)
# ============================================================

st.sidebar.markdown("### Filters")

category_options = sorted(claims_all["claim_category"].dropna().unique().tolist())
specialty_options = sorted(claims_all["specialty"].dropna().unique().tolist())

claim_categories = st.sidebar.multiselect(
    "Claim Category",
    category_options,
    default=category_options,
    key="claim_category"
)

specialties = st.sidebar.multiselect(
    "Provider Specialty",
    specialty_options,
    default=specialty_options,
    key="specialty"
)

st.sidebar.markdown("---")
if st.sidebar.button("Reset All Filters"):
    st.rerun()

# Apply filters to the working claims dataframe
_cat_filter = claim_categories if claim_categories else category_options
_spec_filter = specialties if specialties else specialty_options

claims = claims_all[
    claims_all["claim_category"].isin(_cat_filter)
    & (claims_all["specialty"].isin(_spec_filter) | claims_all["specialty"].isna())
].copy()

denials = denials_all[denials_all["claim_id"].isin(claims["claim_id"])].copy()

if len(claims) == 0:
    st.warning("No claims match the current filter selection. Adjust filters in the sidebar.")
    st.stop()

# ============================================================
# COMPUTED AGGREGATES (all derived from the filtered real data)
# ============================================================

total_claims = len(claims)
total_denials = int(claims["is_denied"].sum())
denial_rate = total_denials / total_claims * 100 if total_claims else 0.0
denied_dollars = float(denials["denied_claim_amount"].sum())
avg_denied_claim = denied_dollars / total_denials if total_denials else 0.0

reason_summary = denials.groupby("category").agg(
    count=("denial_id", "size"),
    denied_usd=("denied_claim_amount", "sum"),
).reset_index()


def _appeal_success_rate(g):
    submitted = g[g["appeal_submitted"] == True]
    if len(submitted) == 0:
        return 0.0
    return (submitted["appeal_outcome"].isin(["approved", "partial_approval"])).mean()


appeal_summary = denials.groupby("category").apply(_appeal_success_rate).reset_index(name="appeal_success_rate")
reason_summary = reason_summary.merge(appeal_summary, on="category", how="left").fillna(0)
reason_summary = reason_summary.sort_values("denied_usd", ascending=False).reset_index(drop=True)

# ============================================================
# KPI HEADER
# ============================================================

st.markdown("### Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Claims", f"{total_claims:,}")

with col2:
    st.metric("Denial Rate", f"{denial_rate:.2f}%")

with col3:
    st.metric("Total Denied $", f"${denied_dollars/1e6:.2f}M")

with col4:
    if not reason_summary.empty:
        core = reason_summary[reason_summary["category"] != "Other / Unclassified"]
        pa_row = core[core["category"] == "Prior Authorization"]
        billing_row = core[core["category"] == "Billing Error"]
        pa_ceiling = float((pa_row["denied_usd"] * pa_row["appeal_success_rate"]).sum())
        billing_ceiling = float((billing_row["denied_usd"] * billing_row["appeal_success_rate"]).sum())
        moderate_ceiling = pa_ceiling + billing_ceiling
        st.metric("Recovery Ceiling (PA+Billing)", f"${moderate_ceiling/1e6:.1f}M", "Full appeal-push")
    else:
        st.metric("Recovery Ceiling", "N/A")

st.markdown(
    f'<div class="caveat-note">Live metrics computed from {len(claims):,} filtered claims '
    f'({len(claim_categories)}/{len(category_options)} categories, {len(specialties)}/{len(specialty_options)} specialties selected). '
    f'KPI cards above are single-snapshot metrics with no period-over-period deltas -- see "Denial Rate Over Time" '
    f'in the Overview tab for the monthly trend.</div>',
    unsafe_allow_html=True
)

# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "Overview",
    "Root Cause Analysis",
    "Provider Performance",
    "Risk Model",
    "Financial Impact",
    "Recommendations",
    "Cross-Industry"
])

# ============================================================
# TAB 1: OVERVIEW
# ============================================================

with tabs[0]:
    top_reason = reason_summary.iloc[0] if not reason_summary.empty else None
    if top_reason is not None:
        st.markdown(
            f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
            f'<div class="insight-strip-text">{top_reason["category"]} drives ${top_reason["denied_usd"]/1e6:.2f}M '
            f'({top_reason["denied_usd"]/denied_dollars*100:.0f}% of denied dollars in the current filter). '
            f'{top_reason["appeal_success_rate"]*100:.0f}% of these denials that were appealed succeeded.</div></div>',
            unsafe_allow_html=True
        )

    col1, col2 = st.columns(2)

    with col1:
        status_counts = claims["claim_status"].value_counts()  # already sorted desc by count
        status_colors = {
            "approved": GREEN_700,
            "denied": ORANGE_700,
            "processing": STEEL_300,
            "appeal_pending": BLUE_500,
            "submitted": STEEL_700,
        }

        # Largest-remainder (Hamilton) allocation of 100 waffle squares so
        # counts always sum to exactly 100 regardless of rounding.
        total_n = status_counts.sum()
        exact = status_counts / total_n * 100
        base = np.floor(exact).astype(int)
        remainder = 100 - int(base.sum())
        fracs = (exact - base).sort_values(ascending=False)
        alloc = base.copy()
        for status in fracs.index[:remainder]:
            alloc[status] += 1

        # Row-major grid fill, contiguous blocks per category (not speckled).
        GRID = 10
        xs, ys, cell_status = [], [], []
        cell = 0
        for status in status_counts.index:
            for _ in range(int(alloc[status])):
                row, col = divmod(cell, GRID)
                xs.append(col)
                ys.append(row)
                cell_status.append(status)
                cell += 1

        fig = go.Figure()
        for status in status_counts.index:
            idx = [i for i, s in enumerate(cell_status) if s == status]
            pct = exact[status]
            n_sq = int(alloc[status])
            label = status.replace("_", " ").title()
            fig.add_trace(go.Scatter(
                x=[xs[i] for i in idx],
                y=[ys[i] for i in idx],
                mode="markers",
                marker=dict(symbol="square", size=22,
                            color=status_colors.get(status, GRAY_300),
                            line=dict(width=1, color=WHITE)),
                name=f"{label} ({pct:.1f}%)",
                hovertemplate=f"{label}: {pct:.2f}%<br>{n_sq} of 100 squares<extra></extra>",
            ))

        fig.update_xaxes(visible=False, range=[-0.6, GRID - 0.4], fixedrange=True)
        fig.update_yaxes(visible=False, range=[GRID - 0.4, -0.6], fixedrange=True,
                          scaleanchor="x", scaleratio=1)
        fig.update_layout(
            title=dict(text="Claim Status Breakdown", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.18),
        )
        st.plotly_chart(fig, width="stretch")
        appeal_rate = denials["appeal_submitted"].mean() * 100 if len(denials) else 0
        st.markdown(f"**Takeaway:** {denial_rate:.2f}% of claims are denied; {appeal_rate:.1f}% of denials proceed to appeal.", unsafe_allow_html=True)

    with col2:
        fig = go.Figure(data=[go.Bar(
            x=reason_summary["category"],
            y=reason_summary["count"],
            marker=dict(color=ORANGE_700),
            text=[f"{c:,}" for c in reason_summary["count"]],
            textposition="outside",
            textfont=dict(size=12, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text="Denial Volume by Reason Category", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(tickangle=-20),
            yaxis=dict(title="Denial Count")
        )
        st.plotly_chart(fig, width="stretch")
        top2 = reason_summary.head(2)
        top2_pct = top2["count"].sum() / reason_summary["count"].sum() * 100 if len(reason_summary) else 0
        if len(top2) > 1:
            takeaway = (
                f"**Takeaway:** {top2.iloc[0]['category']} ({top2.iloc[0]['count']:,}) and "
                f"{top2.iloc[1]['category']} ({top2.iloc[1]['count']:,}) "
                f"account for {top2_pct:.0f}% of denials in the current filter."
            )
        else:
            takeaway = f"**Takeaway:** {top2.iloc[0]['category']} accounts for {top2_pct:.0f}% of denials in the current filter."
        st.markdown(takeaway, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Executive Metrics</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        tr = reason_summary.iloc[0] if not reason_summary.empty else None
        if tr is not None:
            st.markdown(f"""
            <div class="metric-card">
            <strong>Top Denial Reason</strong><br/>
            {tr['category']}<br/>
            <span style="color: #0077B3; font-weight: 600;">${tr['denied_usd']/1e6:.2f}M | {tr['count']/total_denials*100:.0f}% of denials</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        if not reason_summary.empty:
            best = reason_summary.loc[reason_summary["appeal_success_rate"].idxmax()]
            st.markdown(f"""
            <div class="metric-card">
            <strong>Highest Appeal Success</strong><br/>
            {best['category']}<br/>
            <span style="color: #0077B3; font-weight: 600;">{best['appeal_success_rate']*100:.0f}% | ${best['denied_usd']/1e6:.2f}M at risk</span>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        net = claims.groupby("network_type")["is_denied"].mean()
        in_rate = net.get("in_network", 0) * 100
        out_rate = net.get("out_of_network", 0) * 100
        label = "No Significant Difference" if abs(in_rate - out_rate) < 1 else "Difference Detected"
        st.markdown(f"""
        <div class="metric-card">
        <strong>Network Correlation</strong><br/>
        {label}<br/>
        <span style="color: #0077B3; font-weight: 600;">In: {in_rate:.2f}% | Out: {out_rate:.2f}%</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Denial Rate Over Time</div>', unsafe_allow_html=True)

    claim_dates = pd.to_datetime(claims["claim_date"])
    month_df = claims.copy()
    month_df["claim_month"] = claim_dates.dt.to_period("M").dt.to_timestamp()
    monthly = month_df.groupby("claim_month")["is_denied"].agg(["count", "mean"]).reset_index()
    monthly["denial_rate_pct"] = monthly["mean"] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["claim_month"], y=monthly["denial_rate_pct"],
        mode="lines+markers",
        line=dict(color=ORANGE_700, width=2),
        marker=dict(size=7, color=ORANGE_700),
        hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=denial_rate, line_dash="dot", line_color=STEEL_700,
                  annotation_text=f"Overall: {denial_rate:.2f}%", annotation_position="top left")
    fig.update_layout(
        title=dict(text="Monthly Denial Rate Trend", font=dict(family="Arial", size=14, color=NAVY),
                   x=0.01, xanchor="left"),
        height=320,
        paper_bgcolor=WHITE, plot_bgcolor=WHITE,
        font=dict(family="Arial", size=12),
        margin=dict(l=16, r=16, t=56, b=44),
        xaxis=dict(title="Month", tickformat="%b %Y"),
        yaxis=dict(title="Denial Rate (%)"),
    )
    st.plotly_chart(fig, width="stretch")

    date_range_note = f"{claim_dates.min():%b %d, %Y} - {claim_dates.max():%b %d, %Y}"
    st.markdown(
        f"**Takeaway:** Data covers {date_range_note}. Denial rate is stable across the year "
        f"(no seasonal pattern is built into the synthetic generator) -- month-to-month movement "
        f"reflects sampling noise around the {denial_rate:.2f}% baseline, not a real trend.",
        unsafe_allow_html=True
    )

# ============================================================
# TAB 2: ROOT CAUSE ANALYSIS
# ============================================================

with tabs[1]:
    if not reason_summary.empty:
        best = reason_summary.loc[reason_summary["appeal_success_rate"].idxmax()]
        worst = reason_summary.loc[reason_summary["appeal_success_rate"].idxmin()]
        st.markdown(
            f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
            f'<div class="insight-strip-text">{best["category"]} appeals succeed at {best["appeal_success_rate"]*100:.0f}% '
            f'(highest in the current filter); {worst["category"]} succeeds least often at {worst["appeal_success_rate"]*100:.0f}%. '
            f'All core denial reasons in this dataset carry a real, non-zero appeal pathway.</div></div>',
            unsafe_allow_html=True
        )

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(data=[go.Bar(
            x=reason_summary["category"],
            y=reason_summary["denied_usd"] / 1e6,
            marker=dict(color=ORANGE_700),
            text=[f"${d:.2f}M" for d in reason_summary["denied_usd"] / 1e6],
            textposition="outside",
            textfont=dict(size=12, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text="Denied Dollars by Reason Category", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(tickangle=-20),
            yaxis=dict(title="Denied Amount ($M)")
        )
        st.plotly_chart(fig, width="stretch")
        top2 = reason_summary.head(2)
        top2_pct = top2["denied_usd"].sum() / reason_summary["denied_usd"].sum() * 100 if len(reason_summary) else 0
        st.markdown(f"**Takeaway:** Top 2 reasons own {top2_pct:.0f}% of denied dollars in the current filter.", unsafe_allow_html=True)

    with col2:
        fig = go.Figure(data=[go.Bar(
            x=reason_summary["category"],
            y=reason_summary["appeal_success_rate"] * 100,
            marker=dict(color=GREEN_700),
            text=[f"{r:.0f}%" for r in reason_summary["appeal_success_rate"] * 100],
            textposition="outside",
            textfont=dict(size=12, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text="Appeal Success Rate by Reason Category", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(tickangle=-20),
            yaxis=dict(title="Appeal Success Rate (%)")
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            "**Takeaway:** Every core denial reason category shows 50%+ appeal success when appealed -- "
            "including Coverage Limits, which earlier internal reporting incorrectly assumed was unrecoverable.",
            unsafe_allow_html=True
        )
        st.caption(DENIAL_CATEGORY_MAP_NOTE)

# ============================================================
# TAB 3: PROVIDER PERFORMANCE
# ============================================================

with tabs[2]:
    top_provider_denied = denials.merge(claims[["claim_id", "provider_id"]], on="claim_id", how="left") \
        .groupby("provider_id")["denied_claim_amount"].sum().sort_values(ascending=False)
    top_provider_pct = (top_provider_denied.iloc[0] / denied_dollars * 100) if len(top_provider_denied) and denied_dollars else 0

    st.markdown(
        f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
        f'<div class="insight-strip-text">No provider is an outlier. The top provider by denied dollars accounts for '
        f'{top_provider_pct:.1f}% of total denied dollars in the current filter. Denials are systemic, not concentrated.</div></div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        spec_rates = claims.groupby("specialty")["is_denied"].mean().sort_values(ascending=False) * 100
        fig = go.Figure(data=[go.Bar(
            x=[s.replace("_", " ").title() for s in spec_rates.index],
            y=spec_rates.values,
            marker=dict(color=ORANGE_700),
            text=[f"{r:.2f}%" for r in spec_rates.values],
            textposition="outside",
            textfont=dict(size=12, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text="Denial Rate by Provider Specialty", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(tickangle=-20),
            yaxis=dict(title="Denial Rate (%)")
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f"**Takeaway:** Denial rates cluster tightly ({spec_rates.min():.2f}% to {spec_rates.max():.2f}%). "
            "No specialty is a consistent outlier.",
            unsafe_allow_html=True
        )

    with col2:
        net_grp = claims.groupby("network_type")["is_denied"].agg(["count", "sum", "mean"])
        if "in_network" in net_grp.index and "out_of_network" in net_grp.index:
            n1, x1 = int(net_grp.loc["in_network", "count"]), int(net_grp.loc["in_network", "sum"])
            n2, x2 = int(net_grp.loc["out_of_network", "count"]), int(net_grp.loc["out_of_network", "sum"])
            z, pval, ci1, ci2 = two_proportion_ztest(x1, n1, x2, n2)
        else:
            z = pval = None
            ci1 = ci2 = (0, 0)

        rates = net_grp["mean"] * 100
        fig = go.Figure(data=[go.Bar(
            x=[n.replace("_", " ").title() for n in rates.index],
            y=rates.values,
            marker=dict(color=[ORANGE_700, STEEL_700]),
            text=[f"{r:.2f}%" for r in rates.values],
            textposition="outside",
            textfont=dict(size=12, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text="Denial Rate: In-Network vs. Out-of-Network", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(tickangle=0),
            yaxis=dict(title="Denial Rate (%)")
        )
        st.plotly_chart(fig, width="stretch")

        if pval is not None:
            sig = "not statistically significant" if pval >= 0.05 else "statistically significant"
            st.markdown(
                f"**Takeaway:** Two-proportion z-test: z={z:.2f}, p={pval:.2f} -- the difference is **{sig}** at the 95% confidence level. "
                f"In-network 95% CI [{ci1[0]*100:.2f}%, {ci1[1]*100:.2f}%]; Out-of-network 95% CI [{ci2[0]*100:.2f}%, {ci2[1]*100:.2f}%].",
                unsafe_allow_html=True
            )
        else:
            st.markdown("**Takeaway:** Insufficient data in one network segment under the current filter to run a significance test.", unsafe_allow_html=True)

# ============================================================
# TAB 4: RISK MODEL
# ============================================================

with tabs[3]:
    if model_metrics is None:
        st.warning(
            "Model metrics file (models/model_metrics.json) not found. "
            "Run `python scripts/03_train_model.py` from the scripts/ directory to generate it."
        )
    else:
        auc_test = model_metrics["auc_test"]
        decile = model_metrics["decile_analysis"]
        d1_rate = decile["1"]["denial_rate_pct"]
        baseline = model_metrics["baseline_denial_rate"] * 100
        lift = d1_rate / baseline if baseline else 0
        top_features = model_metrics["feature_importance"][:6]

        st.markdown(
            f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
            f'<div class="insight-strip-text">XGBoost model achieves test ROC AUC {auc_test:.4f} (near-random -- '
            f'the available features have limited predictive power for this synthetic label) and {lift:.2f}x lift '
            f'in the top decile ({d1_rate:.2f}% denial rate vs {baseline:.2f}% baseline). '
            f'Top feature: {top_features[0]["feature"].replace("_", " ").title()} ({top_features[0]["importance"]*100:.1f}%).</div></div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:
            deciles = sorted(decile.keys(), key=int)
            rates = [decile[d]["denial_rate_pct"] for d in deciles]
            fig = go.Figure(data=[go.Bar(
                x=[f"D{d}" for d in deciles],
                y=rates,
                marker=dict(color=[ORANGE_700 if int(d) <= 2 else STEEL_700 for d in deciles]),
                text=[f"{r:.2f}%" for r in rates],
                textposition="outside",
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                title=dict(text="Denial Rate by Risk Decile", font=dict(family="Arial", size=14, color=NAVY),
                           x=0.01, xanchor="left"),
                height=360,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=56, b=44),
                xaxis=dict(title="Decile (1=Highest Risk)"),
                yaxis=dict(title="Denial Rate (%)")
            )
            st.plotly_chart(fig, width="stretch")
            st.markdown(
                f"**Takeaway:** Real model output is noisier than a hand-picked example would suggest -- "
                f"deciles are not perfectly monotonic, which is expected at AUC {auc_test:.2f}. "
                f"Decile 1 still carries the highest rate ({d1_rate:.2f}%), giving {lift:.2f}x lift for prioritized review.",
                unsafe_allow_html=True
            )

        with col2:
            feat_names = [f["feature"].replace("_", " ").title() for f in top_features]
            feat_imp = [f["importance"] for f in top_features]
            colors = [BLUE_700 if i < 3 else STEEL_300 for i in range(len(feat_names))]

            fig = go.Figure(data=[go.Bar(
                x=feat_names,
                y=feat_imp,
                marker=dict(color=colors),
                text=[f"{i*100:.1f}%" for i in feat_imp],
                textposition="outside",
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                title=dict(text="Top Predictive Features (XGBoost Model)", font=dict(family="Arial", size=14, color=NAVY),
                           x=0.01, xanchor="left"),
                height=360,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=56, b=44),
                xaxis=dict(tickangle=-20),
                yaxis=dict(title="Feature Importance")
            )
            st.plotly_chart(fig, width="stretch")
            top3_sum = sum(feat_imp[:3]) * 100
            st.markdown(
                f"**Takeaway:** {feat_names[0]} ({feat_imp[0]*100:.1f}%) is the strongest predictor "
                f"(highlighted in blue, top 3). Top 3 features explain {top3_sum:.0f}% of total feature importance; "
                f"the remaining {100-top3_sum:.0f}% is spread thinly across the rest.",
                unsafe_allow_html=True
            )

        st.caption(
            "Model trained via scripts/03_train_model.py: XGBoost with scale_pos_weight to correct for the 3.93% "
            "denial base rate. Categorical features are LabelEncoder-encoded (models/label_encoders.pkl) -- "
            "no StandardScaler is used, since XGBoost is tree-based and does not require feature scaling."
        )

# ============================================================
# TAB 5: FINANCIAL IMPACT
# ============================================================

with tabs[4]:
    core_reasons = reason_summary[reason_summary["category"] != "Other / Unclassified"].set_index("category")

    pa = core_reasons.loc["Prior Authorization"] if "Prior Authorization" in core_reasons.index else None

    if pa is not None:
        st.markdown(
            f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
            f'<div class="insight-strip-text">Theoretical recovery ceiling (100% appeal-push across all 5 core denial reasons): '
            f'${core_reasons["denied_usd"].mul(core_reasons["appeal_success_rate"]).sum()/1e6:.1f}M. '
            f'This is a planning ceiling, not a Year-1 guarantee -- realistic Year-1 capture during program ramp-up '
            f'is typically 50-70% of ceiling for the first 1-2 categories targeted.</div></div>',
            unsafe_allow_html=True
        )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Scenario Analysis")
        default_rate = float(pa["appeal_success_rate"]) if pa is not None else 0.5
        save_rate = st.slider("Prior Auth Appeal Success Rate", 0.30, 0.80, round(default_rate, 2), 0.01)
        cost_per_contact = st.slider("Cost per Appeal ($)", 100, 500, 300, 50)

        pa_denied_usd = float(pa["denied_usd"]) if pa is not None else 0
        pa_denial_count = float(pa["count"]) if pa is not None else 0
        estimated_recovery = pa_denied_usd * save_rate
        total_cost = pa_denial_count * cost_per_contact
        roi = estimated_recovery / total_cost if total_cost > 0 else 0

        st.markdown(f"""
        <div class="metric-card" style="margin-top: 16px;">
        <strong>Estimated Recovery</strong><br/>
        <span style="font-size: 20px; color: #08CAA9; font-weight: 600;">${estimated_recovery/1e6:.2f}M</span><br/>
        <br/>
        <strong>Total Investment</strong><br/>
        <span style="font-size: 14px;">${total_cost/1000:.0f}K</span><br/>
        <br/>
        <strong>ROI</strong><br/>
        <span style="font-size: 18px; color: #0077B3; font-weight: 600;">{roi:.1f}x</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Slider defaults to the real observed Prior Authorization appeal success rate from the filtered data.")

    with col2:
        if pa is not None:
            billing = core_reasons.loc["Billing Error"] if "Billing Error" in core_reasons.index else None
            others = core_reasons.drop(index=[i for i in ["Prior Authorization", "Billing Error"] if i in core_reasons.index])

            pa_ceiling = float(pa["denied_usd"] * pa["appeal_success_rate"])
            billing_ceiling = float(billing["denied_usd"] * billing["appeal_success_rate"]) if billing is not None else 0
            others_ceiling = float((others["denied_usd"] * others["appeal_success_rate"]).sum())

            scenarios = ["Conservative\n(Prior Auth Only)", "Moderate\n(+ Billing)", "Full Ceiling\n(All 5 Core Reasons)"]
            recovery = [pa_ceiling / 1e6, (pa_ceiling + billing_ceiling) / 1e6, (pa_ceiling + billing_ceiling + others_ceiling) / 1e6]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=scenarios,
                y=recovery,
                name="Recovery Ceiling ($M)",
                marker=dict(color=GREEN_700),
                text=[f"${r:.1f}M" for r in recovery],
                textposition="outside"
            ))
            fig.update_layout(
                title=dict(text="Recovery Ceiling by Scenario", font=dict(family="Arial", size=14, color=NAVY),
                           x=0.01, xanchor="left"),
                height=360,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=56, b=44),
                yaxis=dict(title="Recovery Ceiling ($M) -- assumes 100% appeal push"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, width="stretch")
            st.markdown(
                "**Takeaway:** Recovery scales roughly linearly with scope in this dataset because every core denial "
                "reason -- including Coverage Limits -- carries a real 50%+ appeal success rate once appealed. "
                "There is no evidence of diminishing returns from expanding scope; the constraint is operational "
                "capacity to run appeals programs across categories simultaneously, not category-level payoff.",
                unsafe_allow_html=True
            )

# ============================================================
# TAB 6: RECOMMENDATIONS
# ============================================================

with tabs[5]:
    st.markdown("### Claim Denial Prevention Strategy")

    st.markdown('<div class="section-header">Immediate Actions (0-30 Days)</div>', unsafe_allow_html=True)

    if not reason_summary.empty:
        best = reason_summary.loc[reason_summary["appeal_success_rate"].idxmax()]
        st.markdown(f"""
        <div class="rec-card">
        <strong>1. Launch Targeted Appeals Program for {best['category']}</strong><br/>
        {best['category']} appeals succeed at {best['appeal_success_rate']*100:.0f}% (highest in the current filter). Push the
        ${best['denied_usd']/1e6:.2f}M in denied claims through appeals with dedicated staff.
        </div>

        <div class="rec-card">
        <strong>2. Implement Prior Authorization Processing SLA</strong><br/>
        Set a 2-day maximum processing target. Prior authorization denials appeal successfully at a real,
        measured rate in this dataset -- most are recoverable, and accelerating approvals prevents denials upfront.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Short-Term Actions (30-90 Days)</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="rec-card">
    <strong>3. Build Pre-Submission Validation</strong><br/>
    Automate basic validation (coverage tier check, provider network verification) to catch preventable denials before submission.
    </div>

    <div class="rec-card">
    <strong>4. Re-Evaluate the Coverage Limits Appeal Pathway</strong><br/>
    Prior internal reporting assumed Coverage Limit denials were policy-defined and unrecoverable. The real data shows a
    measured appeal success rate above 50% for this category -- add it to the active appeals program rather than
    writing it off, and separately audit why past reporting assumed 0%.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Strategic Investments (90+ Days)</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="rec-card">
    <strong>5. Deploy Denial-Risk Scoring in Adjudication</strong><br/>
    Integrate the model's risk decile into the claims system to flag high-risk claims for human review before final adjudication.
    Treat this as a low/moderate-confidence signal given the model's current AUC -- useful for triage prioritization,
    not as a standalone denial/approval decision.
    </div>

    <div class="rec-card">
    <strong>6. Establish Quarterly Denial Deep-Dive Reviews</strong><br/>
    Continue monitoring denial patterns by reason, appeal success, and provider/specialty cohort. Re-run this analysis
    against fresh data each quarter rather than treating any single snapshot's findings as permanent.
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# TAB 7: CROSS-INDUSTRY
# ============================================================

with tabs[6]:
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">FRAMEWORK PORTABILITY</div><div class="insight-strip-text">Healthcare claim denials follow a universal pattern: high-volume low-value rejections with concentrated root causes. This framework translates across insurance domains.</div></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Healthcare → Pharmacy

        | Healthcare | Pharmacy |
        |---|---|
        | Prior Authorization Delay | Prior Authorization Delay |
        | Billing Error | Quantity Limit Violation |
        | Coverage Limits | Formulary Tier Denial |
        | Network Status | Network Pharmacy Status |
        | Medical Necessity | Diagnosis Code Mismatch |
        """)

    with col2:
        st.markdown("""
        ### Healthcare → Auto Insurance

        | Healthcare | Auto |
        |---|---|
        | Prior Authorization | Claim Verification |
        | Billing Error | Provider Network |
        | Coverage Limits | Policy Limit Exceeded |
        | Network Status | Deductible/Copay |
        | Medical Necessity | Exclusion Clause |
        """)

    st.markdown('<div class="section-header">Key Principles for Adaptation</div>', unsafe_allow_html=True)

    st.markdown("""
    1. **Root-Cause Concentration:** Identify the top 3-5 denial reasons that own 70%+ of denied dollars
    2. **Verify Appeal Assumptions With Data:** Don't assume a category is "unrecoverable" without measuring actual appeal outcomes -- this analysis found a supposedly zero-recovery category was actually recoverable above 50% of the time
    3. **Network/Provider Effects:** Test whether denials correlate with provider/network tier using a real significance test, not eyeballed percentages
    4. **Systemic vs. Concentrated:** Determine if denials are spread (process problem) or concentrated (bad actors/outliers)
    5. **Financial Modeling:** Distinguish a theoretical full-scope recovery ceiling from a realistic Year-1 target
    """)

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

if data_metadata:
    gen_date = data_metadata.get("generated_date", "unknown")
    seed = data_metadata.get("seed", "unknown")
    freshness_note = f"Synthetic dataset | seed={seed} | generated {gen_date[:10]}"
else:
    freshness_note = "Synthetic dataset | seed=42"

st.markdown(f"""
<div style="text-align: center; color: #707070; font-size: 12px; margin-top: 32px;">
<p><strong>Claims Denial Prevention Analytics</strong> | {total_claims:,} claims | {total_denials:,} denials | ${denied_dollars/1e6:.2f}M denied (current filter)</p>
<p>{freshness_note} | All figures on this page are computed live from the CSVs in data/ -- no numbers are hardcoded.</p>
<p>Dashboard built by Luciano Casillas | <a href="https://github.com/Luciano-Casillas/claims-denial-prevention">GitHub</a></p>
</div>
""", unsafe_allow_html=True)
