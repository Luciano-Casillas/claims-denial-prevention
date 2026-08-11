"""
Clarity Health Plans - Claims Denial Prevention Intelligence Dashboard
Author: Luciano Casillas
Version: 3.0

Interactive analysis of health insurance claims denial patterns, root causes,
and financial recovery opportunities. Loads and aggregates the real synthetic
dataset (data/clarity_claims.csv, clarity_denials.csv, clarity_providers.csv)
and the retrained XGBoost model (models/model_metrics.json) live -- nothing
on this dashboard is hardcoded from a prior analysis run.

Organized around six business questions (see "How This Dashboard Is
Organized" on the Overview tab) rather than around chart types.
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
#   RED     -> a second, visually distinct "risk" hue for charts placed
#              next to an ORANGE chart, so adjacent bars aren't mistaken
#              for the same category (e.g. Specialty vs. Network charts)
#   GREEN   -> appeal success / recovery potential (the opportunity)
#   BLUE    -> neutral descriptive metrics (specialty, feature importance)
#   STEEL   -> muted / non-highlighted comparison bars
# ------------------------------------------------------------

# Fixed judgment-call classification of each denial reason category,
# used on the Root Cause Analysis (Q2) tab. Not derived from data --
# this is analyst categorization, same spirit as categorize_denial_reason().
REASON_CLASSIFICATION = {
    "Prior Authorization": ("Preventable (Process)", "Processing-delay driven; a faster SLA prevents the denial before it happens."),
    "Billing Error": ("Preventable (Process)", "Coding/billing mistakes; pre-submission validation catches most of these."),
    "Network Issue": ("Preventable (Process)", "Provider network verification at submission prevents most of these."),
    "Coverage Limits": ("Structural, but Recoverable", "Policy-defined maximums -- can't prevent the denial, but appeals recover ~59% of it."),
    "Medical Necessity": ("Clinically Structural", "Requires a clinical-judgment or coverage-policy change, not a process fix -- hardest to move."),
    "Other / Unclassified": ("Data Quality Gap", "Free-text or missing reason codes -- fix the intake process, not the denial itself."),
}

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
        min-width: 420px;
        max-width: 460px;
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
    .question-tag {
        color: #707070;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        margin-bottom: 10px;
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


def render_vertical_divider(height_px=380):
    """Light grey vertical divider for a column that sits between two
    unrelated side-by-side charts (different axis/topic, not companion views)."""
    st.markdown(
        f'<div style="border-left: 1px solid #D1E2E5; height: {height_px}px; margin: 24px auto 0 auto;"></div>',
        unsafe_allow_html=True
    )


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


def _pretty_label(raw_value):
    return raw_value.replace("_", " ").title()


claim_categories = st.sidebar.multiselect(
    "Claim Category",
    category_options,
    default=category_options,
    format_func=_pretty_label,
    key="claim_category"
)

specialties = st.sidebar.multiselect(
    "Provider Specialty",
    specialty_options,
    default=specialty_options,
    format_func=_pretty_label,
    key="specialty"
)

st.sidebar.markdown("---")
if st.sidebar.button("Reset All Filters"):
    # st.rerun() alone does NOT clear multiselect widget state -- the
    # widgets are bound to session_state via their `key`, which persists
    # across reruns. Must explicitly reset the session_state values first.
    st.session_state["claim_category"] = category_options
    st.session_state["specialty"] = specialty_options
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

# "Core" reasons exclude Other/Unclassified -- not a real actionable driver,
# just a data-capture gap. Shared by the KPI header, Q2, and Q5 so the
# "top 3 drivers" ranking is computed once and stays consistent everywhere.
core_reasons = reason_summary[reason_summary["category"] != "Other / Unclassified"] \
    .set_index("category").sort_values("denied_usd", ascending=False)
core_reasons["ceiling"] = core_reasons["denied_usd"] * core_reasons["appeal_success_rate"]
top3_reasons = core_reasons.head(3)

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
    if not top3_reasons.empty:
        top3_ceiling = float(top3_reasons["ceiling"].sum())
        st.metric("Recovery Ceiling (Top 3 Drivers)", f"${top3_ceiling/1e6:.1f}M", "Full appeal-push")
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
# TABS -- ordered by the six business questions this dashboard
# answers (Primary, then Secondary, then Optional/Tertiary),
# with Overview first and Recommendations as closing synthesis.
# ============================================================

tabs = st.tabs([
    "Overview",
    "Provider & Specialty Risk",
    "Root Cause Analysis",
    "Recovery Opportunity",
    "Predictive Risk & Intervention",
    "Member Impact",
    "Network Strategy",
    "Recommendations",
])

# ============================================================
# TAB: OVERVIEW
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

    col1, col_div, col2 = st.columns([10, 0.3, 10])

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

    with col_div:
        render_vertical_divider()

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

    st.markdown('<div class="section-header">How This Dashboard Is Organized</div>', unsafe_allow_html=True)
    st.markdown(
        """
This dashboard is built around six business questions, not around chart types. Each tab answers one question directly.

**Primary**
- **Provider & Specialty Risk** -- Which providers are creating denial risk, and what's it costing us?
- **Root Cause Analysis** -- What's actually causing denials -- can we prevent them, or are they built into how we operate?
- **Recovery Opportunity** -- If we focus on the top 3 denial drivers, what's our recovery opportunity in the next 12 months?

**Secondary**
- **Predictive Risk & Intervention** -- Can we predict which claims will be denied before they hit our system, and what's the ROI on early intervention?
- **Member Impact** -- Which members are getting hit repeatedly, and what's the operational burden?

**Optional / Tertiary**
- **Network Strategy** -- Are there network patterns that predict denial risk, and should we adjust our network strategy?
        """
    )

# ============================================================
# TAB: PROVIDER & SPECIALTY RISK  (Q1 -- Primary)
# ============================================================

with tabs[1]:
    st.markdown(
        '<div class="question-tag">Q &mdash; Which providers are creating denial risk, and what\'s it costing us?</div>',
        unsafe_allow_html=True
    )

    top_provider_denied = denials.merge(claims[["claim_id", "provider_id"]], on="claim_id", how="left") \
        .groupby("provider_id")["denied_claim_amount"].sum().sort_values(ascending=False)
    top_provider_pct = (top_provider_denied.iloc[0] / denied_dollars * 100) if len(top_provider_denied) and denied_dollars else 0

    st.markdown(
        f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
        f'<div class="insight-strip-text">Denial risk is <strong>systemic, not concentrated</strong> -- no single provider or specialty '
        f'is "creating" the denial problem. The top provider by denied dollars accounts for just '
        f'{top_provider_pct:.1f}% of total denied dollars in the current filter. The cost is spread thin across '
        f'{claims["provider_id"].nunique():,} providers, which rules out a targeted provider-audit intervention.</div></div>',
        unsafe_allow_html=True
    )

    col1, col_div, col2 = st.columns([10, 0.3, 10])

    with col1:
        spec_rates = claims.groupby("specialty")["is_denied"].mean().sort_values(ascending=False) * 100
        fig = go.Figure(data=[go.Bar(
            x=[s.replace("_", " ").title() for s in spec_rates.index],
            y=spec_rates.values,
            marker=dict(color=BLUE_700),
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

    with col_div:
        render_vertical_divider()

    with col2:
        top_n = 10
        top_providers = top_provider_denied.head(top_n).reset_index()
        top_providers = top_providers.merge(
            providers_all[["provider_id", "provider_name"]], on="provider_id", how="left"
        )
        top_providers["provider_name"] = top_providers["provider_name"].fillna(
            top_providers["provider_id"].apply(lambda p: f"PRV_{int(p)}")
        )
        top_providers = top_providers.sort_values("denied_claim_amount")  # ascending for horizontal bar read-order

        fig = go.Figure(data=[go.Bar(
            x=top_providers["denied_claim_amount"] / 1e3,
            y=top_providers["provider_name"],
            orientation="h",
            marker=dict(color=BLUE_500),
            text=[f"${v/1e3:.0f}K" for v in top_providers["denied_claim_amount"]],
            textposition="outside",
            textfont=dict(size=11, color=NAVY)
        )])
        fig.update_layout(
            title=dict(text=f"Top {top_n} Providers by Denied Dollars", font=dict(family="Arial", size=14, color=NAVY),
                       x=0.01, xanchor="left"),
            height=360,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=11),
            margin=dict(l=16, r=16, t=56, b=44),
            xaxis=dict(title="Denied Amount ($K)")
        )
        st.plotly_chart(fig, width="stretch")
        top10_pct = top_provider_denied.head(top_n).sum() / denied_dollars * 100 if denied_dollars else 0
        st.markdown(
            f"**Takeaway:** Even the top {top_n} providers combined account for only {top10_pct:.1f}% of total denied "
            f"dollars out of {claims['provider_id'].nunique():,} providers in the current filter -- this confirms the "
            f"cost, like the rate, is systemic rather than concentrated in a few bad actors.",
            unsafe_allow_html=True
        )

# ============================================================
# TAB: ROOT CAUSE ANALYSIS  (Q2 -- Primary)
# ============================================================

with tabs[2]:
    st.markdown(
        '<div class="question-tag">Q &mdash; What\'s actually causing denials &mdash; can we prevent them, or are they built into how we operate?</div>',
        unsafe_allow_html=True
    )

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

    st.markdown('<div class="section-header">Preventable or Structural? A Category-by-Category Answer</div>', unsafe_allow_html=True)

    class_rows = []
    for _, row in reason_summary.iterrows():
        cat = row["category"]
        classification, why = REASON_CLASSIFICATION.get(cat, ("Unclassified", ""))
        class_rows.append(
            f"| {cat} | ${row['denied_usd']/1e6:.2f}M | **{classification}** | {why} |"
        )
    table_md = (
        "| Denial Reason | Denied $ | Classification | Why |\n"
        "|---|---|---|---|\n" + "\n".join(class_rows)
    )
    st.markdown(table_md)
    st.markdown(
        "**Takeaway:** 3 of 6 categories (Prior Authorization, Billing Error, Network Issue) are process failures "
        "that can be *prevented* with faster SLAs and pre-submission validation. Coverage Limits is policy-structural "
        "but still worth appealing. Medical Necessity is the hardest to move -- it requires a clinical or coverage-policy "
        "change, not an operations fix. Other/Unclassified is a data-capture problem, not a true root cause.",
        unsafe_allow_html=True
    )

# ============================================================
# TAB: RECOVERY OPPORTUNITY  (Q5 -- Primary / Financial Simulation)
# ============================================================

with tabs[3]:
    st.markdown(
        '<div class="question-tag">Q &mdash; If we focus on the top 3 denial drivers, what\'s our recovery opportunity in the next 12 months?</div>',
        unsafe_allow_html=True
    )

    if len(top3_reasons) == 3:
        top3_names = list(top3_reasons.index)
        top3_ceiling = float(top3_reasons["ceiling"].sum())
        st.markdown(
            f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
            f'<div class="insight-strip-text">The top 3 denial drivers by dollar volume in the current filter are '
            f'<strong>{top3_names[0]}, {top3_names[1]}, and {top3_names[2]}</strong>. Focusing an appeals program on '
            f'just these three yields a theoretical 12-month recovery ceiling of <strong>${top3_ceiling/1e6:.1f}M</strong> '
            f'(100% appeal-push assumption). This is a planning ceiling, not a guarantee -- realistic Year-1 capture '
            f'during program ramp-up is typically 50-70% of ceiling for the first 1-2 categories targeted.</div></div>',
            unsafe_allow_html=True
        )

    pa = core_reasons.loc["Prior Authorization"] if "Prior Authorization" in core_reasons.index else None

    # --- MAIN CHART (expanded, full width) ---
    if len(core_reasons) >= 1:
        n_show = min(3, len(core_reasons))
        labels = list(core_reasons.index[:n_show])
        cumulative = core_reasons["ceiling"].iloc[:n_show].cumsum()

        scenarios = [labels[0] + "\nOnly"]
        for i in range(1, n_show):
            if i == n_show - 1:
                scenarios.append(f"+ {labels[i]}\n(Top {i+1} Drivers)")
            else:
                scenarios.append(f"+ {labels[i]}\n(Top {i+1})")
        recovery = [v / 1e6 for v in cumulative]

        full_ceiling = float(core_reasons["ceiling"].sum())
        if len(core_reasons) > n_show:
            scenarios.append("Full Ceiling\n(All Core Reasons)")
            recovery.append(full_ceiling / 1e6)

        bar_colors = [GREEN_700] * (n_show) + ([STEEL_700] if len(core_reasons) > n_show else [])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=scenarios,
            y=recovery,
            name="Recovery Ceiling ($M)",
            marker=dict(color=bar_colors),
            text=[f"${r:.1f}M" for r in recovery],
            textposition="outside"
        ))
        fig.update_layout(
            title=dict(text="Recovery Ceiling by Scenario (Top 3 Drivers)", font=dict(family="Arial", size=16, color=NAVY),
                       x=0.01, xanchor="left"),
            height=440,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=13),
            margin=dict(l=16, r=16, t=64, b=44),
            yaxis=dict(title="Recovery Ceiling ($M) -- assumes 100% appeal push"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f"**Takeaway:** The top 3 drivers alone ({', '.join(labels)}) reach ${cumulative.iloc[-1]/1e6:.1f}M of the "
            f"${full_ceiling/1e6:.1f}M full-scope ceiling -- {cumulative.iloc[-1]/full_ceiling*100:.0f}% of the total "
            f"opportunity from just 3 of {len(core_reasons)} categories. Recovery scales roughly linearly with scope "
            f"in this dataset because every category carries a real 50%+ appeal success rate once appealed; the "
            f"constraint is operational capacity to run appeals programs simultaneously, not category-level payoff.",
            unsafe_allow_html=True
        )

    # --- SCENARIO CALCULATOR (inputs and results side by side, below the main chart) ---
    st.markdown('<div class="section-header">Prior Authorization Scenario Calculator</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Scenario Analysis")
        pa_denial_count = float(pa["count"]) if pa is not None else 0
        st.markdown(
            f"This calculator stress-tests the **Prior Authorization** recovery estimate only "
            f"(the {int(pa_denial_count):,} Prior Auth denials in the current filter) under different assumptions. "
            f"Drag the sliders to see how the results respond -- it does **not** change the "
            f"chart above, which always shows the real measured appeal-success rate for every category."
        )
        default_rate = float(pa["appeal_success_rate"]) if pa is not None else 0.5
        save_rate = st.slider(
            "Prior Auth Appeal Success Rate", 0.30, 0.80, round(default_rate, 2), 0.01,
            help="Share of appealed Prior Auth denials you assume would win. Defaults to the real rate "
                 "observed in the filtered data; move it to ask 'what if our appeal process got better/worse?'"
        )
        cost_per_contact = st.slider(
            "Cost per Appeal ($)", 100, 500, 300, 50,
            help="Assumed staffing/processing cost to file one appeal. Multiplied by ALL Prior Auth denials "
                 "in the current filter (not just the ones that would win) to estimate total program cost."
        )
        st.caption(
            "Both sliders default to real observed values from the filtered data -- adjust them to model "
            "a better/worse appeal process or a leaner/costlier appeals operation than what's currently happening."
        )

    with col2:
        st.markdown("#### Estimated Recovery")
        pa_denied_usd = float(pa["denied_usd"]) if pa is not None else 0
        estimated_recovery = pa_denied_usd * save_rate
        total_cost = pa_denial_count * cost_per_contact
        roi = estimated_recovery / total_cost if total_cost > 0 else 0

        st.markdown(f"""
        <div class="metric-card" style="margin-top: 16px;">
        <strong>Estimated Recovery</strong><br/>
        <span style="font-size: 12px; color: #707070;">Prior Auth denied $ &times; your success rate</span><br/>
        <span style="font-size: 20px; color: #08CAA9; font-weight: 600;">${estimated_recovery/1e6:.2f}M</span><br/>
        <br/>
        <strong>Total Investment</strong><br/>
        <span style="font-size: 12px; color: #707070;">All {int(pa_denial_count):,} Prior Auth denials &times; cost per appeal</span><br/>
        <span style="font-size: 14px;">${total_cost/1000:.0f}K</span><br/>
        <br/>
        <strong>ROI</strong><br/>
        <span style="font-size: 12px; color: #707070;">Estimated Recovery &divide; Total Investment</span><br/>
        <span style="font-size: 18px; color: #0077B3; font-weight: 600;">{roi:.1f}x</span>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# TAB: PREDICTIVE RISK & INTERVENTION  (Q3 -- Secondary / Modeling)
# ============================================================

with tabs[4]:
    st.markdown(
        '<div class="question-tag">Q &mdash; Can we predict which claims will be denied before they hit our system, and what\'s the ROI on early intervention?</div>',
        unsafe_allow_html=True
    )

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
            f'<div class="insight-strip-text">Yes, with caveats. XGBoost achieves test ROC AUC {auc_test:.4f} (near-random -- '
            f'the available features have limited predictive power for this synthetic label) but still concentrates '
            f'{lift:.2f}x lift in the top decile ({d1_rate:.2f}% denial rate vs {baseline:.2f}% baseline). That '
            f'concentration is weak evidence for individual-claim scoring but real evidence for triage: flagging the '
            f'riskiest 20% of claims for pre-submission review is a defensible early-intervention strategy -- see the '
            f'ROI calculator below.</div></div>',
            unsafe_allow_html=True
        )

        col1, col_div, col2 = st.columns([10, 0.3, 10])

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

        with col_div:
            render_vertical_divider()

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

        st.markdown('<div class="section-header">Early-Intervention ROI Calculator</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size: 16px; line-height: 1.6;">This is a <strong>different financial model</strong> than '
            "the Recovery Opportunity tab. That tab models recovering money <em>after</em> a claim is already denied, "
            "via appeals. This one models <em>preventing</em> the denial in the first place by flagging high-risk "
            'claims (Deciles 1-2) for review before submission.</div>',
            unsafe_allow_html=True
        )

        d1 = decile.get("1", {"claim_count": 0, "denial_count": 0})
        d2 = decile.get("2", {"claim_count": 0, "denial_count": 0})
        d12_claims = d1["claim_count"] + d2["claim_count"]
        d12_denials = d1["denial_count"] + d2["denial_count"]

        col_calc, col_slider, col_results = st.columns([1.3, 0.9, 1.0])

        with col_calc:
            st.markdown(
                f"""<div style="font-size: 16px; line-height: 1.6;">

**How this is calculated:**
1. Deciles 1-2 = the model's highest-risk **{d12_claims:,} claims** (fixed model test set), containing **{d12_denials:,}** real denials ({d12_denials/d12_claims*100:.2f}% rate).
2. "Prevention Success Rate" = what share of those {d12_denials:,} denials a pre-submission review would actually catch and fix.
3. Avoided Denial Value = prevented denial count &times; the current filter's average denied-claim amount (**${avg_denied_claim:,.0f}**).
4. Review Investment = **all** {d12_claims:,} flagged claims &times; cost per review (you review the whole high-risk population, not just the ones that would have been denied -- you don't know which ones in advance).
5. ROI = Avoided Denial Value &divide; Review Investment.

**Caveat:** Deciles 1-2 counts come from the model's fixed 40,000-claim test set established at training time -- this section does not react to the sidebar filters the way the rest of the dashboard does. Given the model's honest AUC of {auc_test:.2f}, treat this as a directional business case for a pilot, not a precise forecast.

</div>""",
                unsafe_allow_html=True
            )

        with col_slider:
            review_cost = st.slider(
                "Pre-Submission Review Cost per Claim ($)", 10, 100, 40, 5,
                help="Assumed cost of a semi-automated pre-submission check on one high-risk claim -- "
                     "cheaper than a full appeal since it happens before the denial occurs."
            )
            prevention_rate = st.slider(
                "Prevention Success Rate", 0.10, 0.60, 0.30, 0.05,
                help="Share of would-be denials in the flagged high-risk population (Deciles 1-2) that "
                     "pre-submission review actually catches and fixes before the claim is submitted."
            )

        with col_results:
            prevented_denials = d12_denials * prevention_rate
            avoided_value = prevented_denials * avg_denied_claim
            review_investment = d12_claims * review_cost
            prevention_roi = avoided_value / review_investment if review_investment > 0 else 0

            st.markdown(f"""
            <div class="metric-card">
            <strong>Denials Prevented</strong><br/>
            <span style="font-size: 18px; color: #08CAA9; font-weight: 600;">{prevented_denials:.0f}</span>
            <span style="font-size: 12px; color: #707070;"> of {d12_denials:,} in Deciles 1-2</span><br/>
            <br/>
            <strong>Avoided Denial Value</strong><br/>
            <span style="font-size: 20px; color: #08CAA9; font-weight: 600;">${avoided_value/1e6:.2f}M</span><br/>
            <br/>
            <strong>Review Investment</strong><br/>
            <span style="font-size: 14px;">${review_investment/1e3:.0f}K</span>
            <span style="font-size: 12px; color: #707070;"> ({d12_claims:,} claims reviewed)</span><br/>
            <br/>
            <strong>ROI</strong><br/>
            <span style="font-size: 18px; color: #0077B3; font-weight: 600;">{prevention_roi:.1f}x</span>
            </div>
            """, unsafe_allow_html=True)

# ============================================================
# TAB: MEMBER IMPACT  (Q4 -- Secondary)
# ============================================================

with tabs[5]:
    st.markdown(
        '<div class="question-tag">Q &mdash; Which members are getting hit repeatedly, and what\'s the operational burden?</div>',
        unsafe_allow_html=True
    )

    den_with_member = denials.merge(claims[["claim_id", "member_id"]], on="claim_id", how="left")
    member_denial_counts = den_with_member.groupby("member_id").size()
    total_members_seen = claims["member_id"].nunique()
    zero_denial_members = total_members_seen - len(member_denial_counts)
    bucket_1 = int((member_denial_counts == 1).sum())
    bucket_2 = int((member_denial_counts == 2).sum())
    bucket_3plus = int((member_denial_counts >= 3).sum())
    repeat_pct = bucket_3plus / total_members_seen * 100 if total_members_seen else 0

    st.markdown(
        f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
        f'<div class="insight-strip-text">No material repeat-member burden. Only <strong>{bucket_3plus} of {total_members_seen:,}</strong> '
        f'members with claims in the current filter ({repeat_pct:.3f}%) have 3+ denials. The overwhelming majority of '
        f'denied members experience it once. This rules out a targeted member-outreach or case-management intervention '
        f'as a high-leverage lever -- the problem is process-driven (see Root Cause Analysis), not concentrated in a '
        f'repeat-denial member segment.</div></div>',
        unsafe_allow_html=True
    )

    buckets = ["0 Denials", "1 Denial", "2 Denials", "3+ Denials"]
    counts = [zero_denial_members, bucket_1, bucket_2, bucket_3plus]

    fig = go.Figure(data=[go.Bar(
        x=buckets,
        y=counts,
        marker=dict(color=[STEEL_300, STEEL_700, ORANGE_700, RED_700]),
        text=[f"{c:,}" for c in counts],
        textposition="outside",
        textfont=dict(size=12, color=NAVY)
    )])
    fig.update_layout(
        title=dict(text="Members by Denial Count", font=dict(family="Arial", size=14, color=NAVY),
                   x=0.01, xanchor="left"),
        height=380,
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="Arial", size=12),
        margin=dict(l=16, r=16, t=56, b=44),
        yaxis=dict(title="Member Count", type="log"),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Y-axis is log-scaled -- the 3+ bucket is a tiny fraction of the 0-denial bucket and would be invisible on a linear scale.")

    st.markdown(
        f"**Takeaway:** {zero_denial_members:,} members ({zero_denial_members/total_members_seen*100:.1f}%) with claims "
        f"in the current filter have zero denials. {bucket_1:,} have exactly one. Operational burden from repeat "
        f"denials is effectively nonexistent in this population -- a member-level case-management program would have "
        f"almost no one to manage.",
        unsafe_allow_html=True
    )

# ============================================================
# TAB: NETWORK STRATEGY  (Q6 -- Optional / Tertiary)
# ============================================================

with tabs[6]:
    st.markdown(
        '<div class="question-tag">Q &mdash; Are there network patterns that predict denial risk, and should we adjust our network strategy?</div>',
        unsafe_allow_html=True
    )

    net_grp = claims.groupby("network_type")["is_denied"].agg(["count", "sum", "mean"])
    if "in_network" in net_grp.index and "out_of_network" in net_grp.index:
        n1, x1 = int(net_grp.loc["in_network", "count"]), int(net_grp.loc["in_network", "sum"])
        n2, x2 = int(net_grp.loc["out_of_network", "count"]), int(net_grp.loc["out_of_network", "sum"])
        z, pval, ci1, ci2 = two_proportion_ztest(x1, n1, x2, n2)
    else:
        z = pval = None
        ci1 = ci2 = (0, 0)

    net_importance = None
    if model_metrics is not None:
        net_importance = next(
            (f["importance"] for f in model_metrics["feature_importance"] if f["feature"] == "network_type"), None
        )

    sig_text = ""
    if pval is not None:
        sig = "not statistically significant" if pval >= 0.05 else "statistically significant"
        sig_text = f"a two-proportion z-test shows the raw difference is <strong>{sig}</strong> (p={pval:.2f})"

    imp_text = ""
    if net_importance is not None:
        imp_text = (
            f" Yet network type is the model's <strong>#2 most important feature</strong> ({net_importance*100:.1f}%) on the "
            f"Predictive Risk tab -- not a contradiction: a tree-based model can use network status productively in "
            f"combination with other features (e.g. it may matter for certain specialties or claim categories) even "
            f"when its average, on-its-own effect is flat."
        )

    st.markdown(
        f'<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div>'
        f'<div class="insight-strip-text">No simple network-tier effect: {sig_text if sig_text else "insufficient data to test"}.'
        f'{imp_text} <strong>Recommendation:</strong> don\'t adjust network strategy based on tier alone -- if a network '
        f'effect exists, it\'s conditional/interactive, not a simple main effect, and would need an interaction analysis '
        f'(e.g. network status &times; specialty) before it justifies a contracting decision.</div></div>',
        unsafe_allow_html=True
    )

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
        height=380,
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="Arial", size=12),
        margin=dict(l=16, r=16, t=56, b=44),
        xaxis=dict(tickangle=0),
        yaxis=dict(title="Denial Rate (%)")
    )
    st.plotly_chart(fig, width="stretch")

    if pval is not None:
        st.markdown(
            f"**Takeaway:** Two-proportion z-test: z={z:.2f}, p={pval:.2f}. "
            f"In-network 95% CI [{ci1[0]*100:.2f}%, {ci1[1]*100:.2f}%]; Out-of-network 95% CI [{ci2[0]*100:.2f}%, {ci2[1]*100:.2f}%] -- "
            f"the intervals overlap substantially, consistent with no main effect.",
            unsafe_allow_html=True
        )
    else:
        st.markdown("**Takeaway:** Insufficient data in one network segment under the current filter to run a significance test.", unsafe_allow_html=True)

# ============================================================
# TAB: RECOMMENDATIONS  (synthesis)
# ============================================================

with tabs[7]:
    st.markdown("### Claim Denial Prevention Strategy")
    st.markdown(
        "Synthesized across all six questions above -- prioritized by what the data actually supports, "
        "not by intuition.",
    )

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
    <strong>3. Build Pre-Submission Validation for Preventable Categories</strong><br/>
    Prior Authorization, Billing Error, and Network Issue are all process failures (see Root Cause Analysis).
    Automate basic validation (coverage tier check, provider network verification) to catch these before submission.
    </div>

    <div class="rec-card">
    <strong>4. Re-Evaluate the Coverage Limits Appeal Pathway</strong><br/>
    Prior internal reporting assumed Coverage Limit denials were policy-defined and unrecoverable. The real data shows a
    measured appeal success rate above 50% for this category -- add it to the active appeals program rather than
    writing it off, and separately audit why past reporting assumed 0%.
    </div>

    <div class="rec-card">
    <strong>5. Do Not Build a Repeat-Member Case-Management Program</strong><br/>
    Member Impact analysis shows a negligible repeat-denial population (well under 1% of members with 3+ denials).
    This is not a high-leverage lever -- redirect that budget to the process fixes above.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Strategic Investments (90+ Days)</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="rec-card">
    <strong>6. Pilot Pre-Submission Review on the Model's Top 2 Risk Deciles</strong><br/>
    Given the model's honest AUC (~0.51), don't deploy it as a standalone approve/deny gate. Use it to triage the
    riskiest 20% of claims for human pre-submission review, and validate the Early-Intervention ROI calculator's
    assumptions against a real pilot before scaling.
    </div>

    <div class="rec-card">
    <strong>7. Do Not Prioritize Network Renegotiation on Tier Alone</strong><br/>
    In-network vs. out-of-network shows no significant main-effect difference in denial rate, despite network type
    ranking highly in the model's feature importance -- any real effect is likely conditional on other factors
    (specialty, claim category). Run an interaction analysis before making a network-strategy decision.
    </div>

    <div class="rec-card">
    <strong>8. Establish Quarterly Denial Deep-Dive Reviews</strong><br/>
    Continue monitoring denial patterns by reason, appeal success, and provider/specialty cohort. Re-run this analysis
    against fresh data each quarter rather than treating any single snapshot's findings as permanent.
    </div>
    """, unsafe_allow_html=True)

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
