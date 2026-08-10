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
STEEL_300 = "#D1E2E5"
STEEL_100 = "#F4F9FA"
WHITE = "#FFFFFF"
BLACK = "#2D2D2D"
GRAY_700 = "#707070"
GRAY_300 = "#CCCCCC"
GREEN_700 = "#08CAA9"
GREEN_900 = "#067462"
ORANGE_700 = "#FF8A39"

# Custom CSS
st.markdown("""
<style>
    body { background-color: white; }
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: white; }
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_data():
    """Load and validate claims data."""
    claims = pd.read_csv('data/clarity_claims.csv')
    denials = pd.read_csv('data/clarity_denials.csv')
    providers = pd.read_csv('data/clarity_providers.csv')
    return claims, denials, providers

try:
    claims, denials, providers = load_data()
    data_loaded = True
except Exception as e:
    st.error(f"Error loading data: {e}")
    data_loaded = False

if data_loaded:
    # ============================================================
    # CALCULATE KEY METRICS
    # ============================================================
    
    total_claims = len(claims)
    total_denials = len(denials)
    denial_rate = (total_denials / total_claims) * 100
    total_denied_usd = denials['denied_claim_amount'].sum() if 'denied_claim_amount' in denials.columns else 0
    avg_denied_claim = total_denied_usd / total_denials if total_denials > 0 else 0
    
    # Denial reasons (use denial_reason_code which has actual values)
    denial_reasons = denials['denial_reason_code'].value_counts() if 'denial_reason_code' in denials.columns else {}
    denial_reason_dollars = denials.groupby('denial_reason_code')['denied_claim_amount'].sum() if 'denial_reason_code' in denials.columns else {}
    
    # Appeal analysis
    appealed = len(denials[denials['appeal_submitted'] == True]) if 'appeal_submitted' in denials.columns else 0
    appeal_success = len(denials[(denials['appeal_submitted'] == True) & (denials['appeal_outcome'] == 'approved')]) if 'appeal_outcome' in denials.columns else 0
    appeal_rate = (appealed / total_denials * 100) if total_denials > 0 else 0
    appeal_success_rate = (appeal_success / appealed * 100) if appealed > 0 else 0
    
    # ============================================================
    # SIDEBAR FILTERS
    # ============================================================
    
    st.sidebar.markdown("### Filters")
    
    if 'claim_category' in claims.columns:
        categories = sorted(claims['claim_category'].unique().tolist())
        selected_categories = st.sidebar.multiselect(
            "Claim Category",
            categories,
            default=categories[:3],
            key="cat_filter"
        )
    else:
        selected_categories = []
    
    if 'network_type' in claims.columns:
        networks = sorted(claims['network_type'].unique().tolist())
        selected_networks = st.sidebar.multiselect(
            "Network Type",
            networks,
            default=networks,
            key="net_filter"
        )
    else:
        selected_networks = []
    
    # Reset filters button
    if st.sidebar.button("Reset All Filters", key="reset_btn"):
        st.rerun()
    
    # ============================================================
    # FILTER DATA
    # ============================================================
    
    filtered_claims = claims.copy()
    if selected_categories and 'claim_category' in claims.columns:
        filtered_claims = filtered_claims[filtered_claims['claim_category'].isin(selected_categories)]
    if selected_networks and 'network_type' in claims.columns:
        filtered_claims = filtered_claims[filtered_claims['network_type'].isin(selected_networks)]
    
    # ============================================================
    # TAB STRUCTURE
    # ============================================================
    
    tabs = st.tabs([
        "Overview",
        "Root Cause Analysis",
        "Provider Performance",
        "Risk Analysis",
        "Financial Impact",
        "Recommendations",
        "Cross-Industry"
    ])
    
    # ============================================================
    # TAB 1: OVERVIEW
    # ============================================================
    
    with tabs[0]:
        st.markdown("### Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Claims", f"{total_claims:,}")
        with col2:
            st.metric("Denial Rate", f"{denial_rate:.2f}%")
        with col3:
            st.metric("Total Denied $", f"${total_denied_usd/1e6:.1f}M")
        with col4:
            st.metric("Appeal Success Rate", f"{appeal_success_rate:.1f}%")
        
        st.markdown("---")
        
        st.markdown('<div class="section-header">Denial Status Distribution</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'claim_status' in claims.columns:
                status_counts = claims['claim_status'].value_counts()
                fig = go.Figure(data=[go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    textinfo="percent+label",
                    marker=dict(colors=[BLUE_700, STEEL_700, GREEN_700])
                )])
                fig.update_layout(**dict(
                    height=340,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12, color=BLACK),
                    margin=dict(l=16, r=16, t=44, b=44),
                ))
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'denial_reason_code' in denials.columns:
                top_reasons = denials['denial_reason_code'].value_counts().head(5)
                fig = go.Figure(data=[go.Bar(
                    x=top_reasons.values,
                    y=top_reasons.index,
                    orientation='h',
                    marker=dict(color=BLUE_700)
                )])
                fig.update_layout(**dict(
                    height=340,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12, color=BLACK),
                    margin=dict(l=16, r=16, t=44, b=44),
                ))
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown('<div class="section-header">Project Summary</div>', unsafe_allow_html=True)
        st.markdown(f"""
        **Claims Analyzed:** {total_claims:,}  
        **Denials:** {total_denials:,} ({denial_rate:.2f}%)  
        **Total Denied $:** ${total_denied_usd/1e6:.1f}M  
        **Appeals Submitted:** {appealed:,} ({appeal_rate:.1f}%)  
        **Appeal Success:** {appeal_success:,} ({appeal_success_rate:.1f}%)
        """)
    
    # ============================================================
    # TAB 2: ROOT CAUSE ANALYSIS
    # ============================================================
    
    with tabs[1]:
        st.markdown("### Denial Reasons by Count and Dollar Impact")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'denial_reason_code' in denials.columns:
                reason_counts = denials['denial_reason_code'].value_counts().sort_values(ascending=True).tail(10)
                fig = go.Figure(data=[go.Bar(
                    y=reason_counts.index,
                    x=reason_counts.values,
                    orientation='h',
                    marker=dict(color=BLUE_700)
                )])
                fig.update_layout(**dict(
                    height=400,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12, color=BLACK),
                    margin=dict(l=16, r=16, t=44, b=44),
                    title="Denials by Reason Code"
                ))
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'denial_reason_code' in denials.columns:
                reason_dollars = denials.groupby('denial_reason_code')['denied_claim_amount'].sum().sort_values(ascending=True).tail(10)
                fig = go.Figure(data=[go.Bar(
                    y=reason_dollars.index,
                    x=reason_dollars.values,
                    orientation='h',
                    marker=dict(color=ORANGE_700)
                )])
                fig.update_layout(**dict(
                    height=400,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12, color=BLACK),
                    margin=dict(l=16, r=16, t=44, b=44),
                    title="Denied $ by Reason Code"
                ))
                st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # TAB 3: PROVIDER PERFORMANCE
    # ============================================================
    
    with tabs[2]:
        st.markdown("### Top Providers by Denied Claims")
        
        if 'provider_id' in denials.columns:
            provider_denials = denials['provider_id'].value_counts().head(10)
            fig = go.Figure(data=[go.Bar(
                x=provider_denials.values,
                y=provider_denials.index.astype(str),
                orientation='h',
                marker=dict(color=STEEL_700)
            )])
            fig.update_layout(**dict(
                height=400,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12, color=BLACK),
                margin=dict(l=16, r=16, t=44, b=44),
            ))
            st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # TAB 4: RISK ANALYSIS
    # ============================================================
    
    with tabs[3]:
        st.markdown("### Claim Amount Distribution in Denials")
        
        if 'denied_claim_amount' in denials.columns:
            fig = go.Figure(data=[go.Histogram(
                x=denials['denied_claim_amount'],
                nbinsx=50,
                marker=dict(color=BLUE_700)
            )])
            fig.update_layout(**dict(
                height=400,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12, color=BLACK),
                margin=dict(l=16, r=16, t=44, b=44),
                title="Distribution of Denied Claim Amounts"
            ))
            st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # TAB 5: FINANCIAL IMPACT
    # ============================================================
    
    with tabs[4]:
        st.markdown("### Recovery Scenarios")
        
        save_rate = st.slider("Appeal Save Rate (%)", 0, 100, 50)
        cost_per_appeal = st.number_input("Cost per Appeal ($)", 100, 1000, 300)
        
        recoverable_dollars = total_denied_usd * (save_rate / 100)
        appeal_cost = appealed * cost_per_appeal
        net_recovery = recoverable_dollars - appeal_cost
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Recoverable $", f"${recoverable_dollars/1e6:.1f}M")
        with col2:
            st.metric("Appeal Cost", f"${appeal_cost/1e6:.1f}M")
        with col3:
            st.metric("Net Recovery", f"${net_recovery/1e6:.1f}M")
    
    # ============================================================
    # TAB 6: RECOMMENDATIONS
    # ============================================================
    
    with tabs[5]:
        st.markdown("### Recommendations")
        
        st.markdown('<div class="section-header">Immediate Actions (0-30 Days)</div>', unsafe_allow_html=True)
        st.markdown("""
        1. Audit top 5 denial reasons for process gaps
        2. Launch targeted appeals for high-success-rate categories
        """)
        
        st.markdown('<div class="section-header">Short-Term (30-90 Days)</div>', unsafe_allow_html=True)
        st.markdown("""
        1. Implement submission completeness validation
        2. Build denial prediction scoring
        """)
        
        st.markdown('<div class="section-header">Strategic (90+ Days)</div>', unsafe_allow_html=True)
        st.markdown("""
        1. Deploy denial risk model in adjudication workflow
        2. Member communication program for coverage limits
        """)
    
    # ============================================================
    # TAB 7: CROSS-INDUSTRY
    # ============================================================
    
    with tabs[6]:
        st.markdown("### Healthcare to Other Domains")
        
        st.markdown("""
        **Healthcare Claims Denial → Pharmacy Claims Denial**
        - Prior Auth → PA delays in specialty drugs
        - Coverage Limits → Formulary tier restrictions
        - Billing Errors → Incorrect NDC codes
        
        **Healthcare Claims Denial → Auto Insurance Claims**
        - Prior Auth → Claim verification delays
        - Coverage Limits → Policy limits reached
        - Billing Errors → Documentation gaps
        """)
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #707070; font-size: 12px; margin-top: 32px;">
    <p><strong>Claims Denial Prevention Analytics</strong> | {total_claims:,} claims | {total_denials:,} denials</p>
    <p>Dashboard by Luciano Casillas | <a href="https://github.com/Luciano-Casillas/claims-denial-prevention">GitHub</a></p>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("Unable to load data. Please ensure CSV files are in the data/ folder.")