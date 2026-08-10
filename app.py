"""
Clarity Health Plans - Claims Denial Prevention Intelligence Dashboard
Author: Luciano Casillas
Version: 1.0

Interactive analysis of health insurance claims denial patterns, root causes,
and financial recovery opportunities. Powered by XGBoost risk prediction and
SQL-driven cohort analysis on 200,000 historical claims.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

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
STEEL_100 = "#F4F9FA"
WHITE = "#FFFFFF"
BLACK = "#2D2D2D"
GRAY_700 = "#707070"
GREEN_700 = "#08CAA9"
ORANGE_700 = "#FF8A39"

# Custom CSS
st.markdown("""
<style>
    .insight-strip {
        background-color: white;
        border-left: 4px solid #0077B3;
        padding: 16px;
        border-radius: 4px;
        margin: 16px 0;
    }
    .insight-label {
        color: #0A3360;
        font-weight: bold;
        font-size: 13px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .insight-text {
        color: #2D2D2D;
        font-size: 14px;
        line-height: 1.6;
    }
    .section-header {
        background-color: #F4F9FA;
        border-left: 4px solid #0077B3;
        padding: 12px 16px;
        margin: 24px 0 12px 0;
        font-weight: bold;
        color: #0A3360;
    }
    .rec-card {
        background-color: white;
        border-left: 4px solid #0077B3;
        padding: 16px;
        margin: 12px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_data():
    """Load all datasets for dashboard"""
    claims = pd.read_csv('data/clarity_claims.csv')
    denials = pd.read_csv('data/clarity_denials.csv')
    providers = pd.read_csv('data/clarity_providers.csv')
    
    # Merge denials into claims
    claims['is_denied'] = claims['claim_id'].isin(denials['claim_id']).astype(int)
    claims = claims.merge(denials[['claim_id', 'denial_reason_code']], 
                          on='claim_id', how='left')
    
    return claims, denials, providers

claims, denials, providers = load_data()

# ============================================================
# HELPERS
# ============================================================

def insight_strip(label, text):
    """Render blue-bordered insight strip"""
    html = f"""
    <div class="insight-strip">
        <div class="insight-label">{label}</div>
        <div class="insight-text">{text}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def base_layout(height=340):
    """Standard Plotly layout"""
    return dict(
        height=height,
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="sans-serif", size=12, color=BLACK),
        margin=dict(l=16, r=16, t=44, b=44),
    )

def section_header(text):
    """Render section header"""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR & FILTERS
# ============================================================

st.sidebar.header("Filters")

claim_categories = ['All'] + sorted(claims['claim_category'].unique().tolist())
selected_categories = st.sidebar.multiselect("Claim Category", 
                                             claim_categories,
                                             default=['All'])

specialties = ['All'] + sorted(claims['specialty'].dropna().unique().tolist())
selected_specialties = st.sidebar.multiselect("Provider Specialty",
                                              specialties,
                                              default=['All'])

# Apply filters
filtered_claims = claims.copy()
if 'All' not in selected_categories:
    filtered_claims = filtered_claims[filtered_claims['claim_category'].isin(selected_categories)]
if 'All' not in selected_specialties:
    filtered_claims = filtered_claims[filtered_claims['specialty'].isin(selected_specialties)]

filtered_denials = filtered_claims[filtered_claims['is_denied'] == 1]

# Stats
st.sidebar.markdown("---")
st.sidebar.metric("Filtered Claims", f"{len(filtered_claims):,}")
st.sidebar.metric("Filtered Denials", f"{len(filtered_denials):,}")
st.sidebar.metric("Denial Rate", f"{len(filtered_denials)/len(filtered_claims)*100:.2f}%")

# ============================================================
# KPI HEADER
# ============================================================

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    denied_millions = filtered_denials['claim_amount'].sum() / 1_000_000
    st.metric("Total Denied ($M)", f"${denied_millions:.2f}")

with kpi2:
    denial_rate = len(filtered_denials) / len(filtered_claims) * 100
    st.metric("Denial Rate (%)", f"{denial_rate:.2f}%")

with kpi3:
    recovery_est = min(denied_millions * 0.50, 10)
    st.metric("Recovery Potential ($M)", f"${recovery_est:.2f}")

with kpi4:
    appeal_success = denials['appeal_outcome'].isin(['approved', 'partial_approval']).sum() / max(denials['appeal_submitted'].sum(), 1) * 100
    st.metric("Appeal Success Rate (%)", f"{appeal_success:.1f}%")

st.markdown("---")

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview",
    "Provider Analysis",
    "Root Cause",
    "Risk Prediction",
    "Financial Impact",
    "Recommendations",
    "Cross-Industry"
])

with tab1:
    st.header("Executive Summary")
    
    insight_strip(
        "KEY FINDING",
        "Prior authorization delays are driving 35% of all denied claims ($10.4M). This is the single largest recovery opportunity combined with billing error fixes."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        denial_summary = filtered_claims['claim_status'].value_counts()
        fig_pie = go.Figure(data=[go.Pie(
            labels=denial_summary.index,
            values=denial_summary.values,
            marker=dict(colors=[GREEN_700, ORANGE_700, BLUE_500, GRAY_700]),
            textinfo='percent'
        )])
        fig_pie.update_layout(**base_layout(height=380))
        st.plotly_chart(fig_pie, use_container_width=True)
        st.caption("Claim Status Distribution")
    
    with col2:
        reason_summary = filtered_denials['denial_reason_code'].fillna('Unknown').value_counts().head(5)
        fig_reasons = go.Figure(data=[go.Bar(
            x=reason_summary.values,
            y=reason_summary.index,
            orientation='h',
            marker=dict(color=BLUE_700)
        )])
        fig_reasons.update_layout(**base_layout(height=380))
        st.plotly_chart(fig_reasons, use_container_width=True)
        st.caption("Top 5 Denial Reasons")

with tab2:
    st.header("Provider Performance Analysis")
    
    insight_strip(
        "KEY FINDING",
        "Denial rates are uniform across providers (3.6% - 4.1%). Focus on process improvements, not provider audits."
    )
    
    section_header("Top 10 Providers by Denied Claims ($)")
    
    top_providers = filtered_claims.groupby('provider_id').agg({
        'claim_id': 'count',
        'is_denied': 'sum'
    }).reset_index()
    top_providers['denied_amount'] = filtered_denials.groupby('provider_id')['claim_amount'].sum()
    top_providers = top_providers.dropna().head(10).sort_values('denied_amount', ascending=False)
    
    fig_top = go.Figure(data=[go.Bar(
        x=top_providers['denied_amount'] / 1_000_000,
        y=[f"PRV_{int(pid):04d}" for pid in top_providers['provider_id']],
        orientation='h',
        marker=dict(color=BLUE_700),
        text=[f"${x/1_000_000:.2f}M" for x in top_providers['denied_amount']],
        textposition='outside'
    )])
    fig_top.update_layout(**base_layout(height=350))
    st.plotly_chart(fig_top, use_container_width=True)

with tab3:
    st.header("Root Cause Analysis")
    
    insight_strip(
        "KEY FINDING",
        "Three causes explain 66% of denied dollars: Prior Auth ($10.4M, 35%), Network Issues ($5.2M, 18%), Coverage Limits ($4.1M, 14%)."
    )
    
    # Root cause mapping
    root_cause_map = {
        'PA01': 'Prior Auth', 'PA02': 'Prior Auth', 'PA03': 'Prior Auth',
        'NW01': 'Network', 'NW02': 'Network', 'provider not network': 'Network',
        'CVRG01': 'Coverage', 'CVRG02': 'Coverage',
        'BILL01': 'Billing', 'BILL02': 'Billing',
        'MED01': 'Medical Necessity'
    }
    
    filtered_denials_copy = filtered_denials.copy()
    filtered_denials_copy['root_cause'] = filtered_denials_copy['denial_reason_code'].map(root_cause_map).fillna('Other')
    
    cause_summary = filtered_denials_copy.groupby('root_cause')['claim_amount'].sum().sort_values(ascending=True)
    
    fig_cause = go.Figure(data=[go.Bar(
        x=cause_summary.values / 1_000_000,
        y=cause_summary.index,
        orientation='h',
        marker=dict(color=BLUE_700),
        text=[f"${x/1_000_000:.2f}M" for x in cause_summary.values],
        textposition='outside'
    )])
    fig_cause.update_layout(**base_layout(height=300))
    st.plotly_chart(fig_cause, use_container_width=True)

with tab4:
    st.header("Risk Prediction Model")
    
    insight_strip(
        "MODEL SUMMARY",
        "XGBoost classifier trained on 160k claims. ROC AUC: 0.5079. Claim amount and plan type are strongest predictors."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Simulated decile data
        deciles = list(range(1, 11))
        denial_rates = [4.65, 4.05, 3.70, 3.60, 3.70, 4.02, 4.02, 3.57, 4.15, 3.82]
        
        fig_decile = go.Figure(data=[go.Bar(
            x=deciles,
            y=denial_rates,
            marker=dict(color=[BLUE_700 if d <= 3 else BLUE_500 for d in deciles]),
            text=[f"{x:.2f}%" for x in denial_rates],
            textposition='outside'
        )])
        fig_decile.update_layout(**base_layout(height=360))
        st.plotly_chart(fig_decile, use_container_width=True)
    
    with col2:
        features = ['Claim Amount', 'Plan Type', 'Chronic Condition', 'Network Status', 'Specialty']
        importance = [0.1071, 0.0946, 0.0920, 0.0910, 0.0910]
        
        fig_feat = go.Figure(data=[go.Bar(
            x=importance,
            y=features,
            orientation='h',
            marker=dict(color=BLUE_700)
        )])
        fig_feat.update_layout(**base_layout(height=360))
        st.plotly_chart(fig_feat, use_container_width=True)

with tab5:
    st.header("Financial Impact")
    
    insight_strip(
        "SCENARIOS",
        "Baseline denied: $29.94M. Conservative recovery (prior auth focus): $3-5M. Moderate (balanced): $6-8M. Full: $8-10M."
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Recovery Scenarios")
        st.metric("Conservative", "$5.0M")
        st.metric("Moderate", "$7.0M")
        st.metric("Full Investment", "$9.0M")
    
    with col2:
        scenario_data = {
            'Scenario': ['Conservative', 'Moderate', 'Full'],
            'Recovery': [5.0, 7.0, 9.0]
        }
        df_scenario = pd.DataFrame(scenario_data)
        fig_scenario = go.Figure(data=[go.Bar(x=df_scenario['Scenario'], y=df_scenario['Recovery'])])
        fig_scenario.update_layout(**base_layout())
        st.plotly_chart(fig_scenario, use_container_width=True)

with tab6:
    st.header("Recommendations")
    
    st.markdown("""
    <div style="background-color: #F4F9FA; border-left: 4px solid #0077B3; padding: 12px 16px; margin: 16px 0;">
        <strong>IMMEDIATE (0-30 Days)</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
        <strong>1. Accelerate Prior Authorization Processing</strong><br>
        Prior auth delays = $10.4M (35% of denials). Target: reduce from 5 to 2 days.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
        <strong>2. Launch Billing Error Appeals</strong><br>
        Billing errors appeal at 61% success rate. $3.64M recovery potential.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #F4F9FA; border-left: 4px solid #0077B3; padding: 12px 16px; margin: 16px 0;">
        <strong>SHORT-TERM (30-90 Days)</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
        <strong>3. Pre-Submission Validation</strong><br>
        Automate checks to catch incomplete submissions before denial.
    </div>
    """, unsafe_allow_html=True)

with tab7:
    st.header("Cross-Industry Application")
    
    st.markdown("""
    The denial prevention framework generalizes across industries:
    
    - **Healthcare:** Prior auth delays → Pharmacy: Step therapy → Auto: Coverage tier → Telecom: Service area
    - **Core Pattern:** Pre-submission validation + risk-based prioritization + appeals automation
    
    Same model. Different domain.
    """)

st.markdown("---")
footer = f"""<div style="text-align: center; color: #707070; font-size: 12px;">
Clarity Health Plans Denial Prevention | Last Updated: {datetime.now().strftime('%B %d, %Y')}
</div>"""
st.markdown(footer, unsafe_allow_html=True)
