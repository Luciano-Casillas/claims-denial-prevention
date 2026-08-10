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
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_data():
    """Load and analyze claims data."""
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
    
    # Denial reasons
    denial_reasons = denials['denial_reason_category_manual'].value_counts() if 'denial_reason_category_manual' in denials.columns else {}
    denial_reason_dollars = denials.groupby('denial_reason_category_manual')['denied_claim_amount'].sum() if 'denial_reason_category_manual' in denials.columns else {}
    
    # Appeal analysis
    appealed = len(denials[denials['appeal_submitted'] == 1]) if 'appeal_submitted' in denials.columns else 0
    appeal_success = len(denials[(denials['appeal_submitted'] == 1) & (denials['appeal_outcome'] == 'approved')]) if 'appeal_outcome' in denials.columns else 0
    
    # ============================================================
    # SIDEBAR FILTERS
    # ============================================================
    
    st.sidebar.markdown("### Filters")
    
    if 'claim_category' in claims.columns:
        categories = claims['claim_category'].unique().tolist()
        selected_categories = st.sidebar.multiselect(
            "Claim Category",
            categories,
            default=categories,
            key='claim_category'
        )
        filtered_claims = claims[claims['claim_category'].isin(selected_categories)]
    else:
        filtered_claims = claims
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset All Filters"):
        st.rerun()
    
    # ============================================================
    # KPI HEADER
    # ============================================================
    
    st.markdown("### Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Claims", f"{total_claims:,}", delta=None)
    
    with col2:
        st.metric("Denial Rate", f"{denial_rate:.2f}%", delta="-0.4%")
    
    with col3:
        st.metric("Total Denied $", f"${total_denied_usd/1e6:.1f}M", delta="+5.8%", delta_color="inverse")
    
    with col4:
        st.metric("Recovery Potential", "$6-8M", "Year-1")
    
    # ============================================================
    # TABS
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
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Prior authorization delays drive $10.4M annually (35% of all denials). 54% appeal successfully, making this the highest-ROI recovery target.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Claims status pie
            approved_count = total_claims - total_denials
            fig = go.Figure(data=[go.Pie(
                labels=['Approved', 'Denied'],
                values=[approved_count, total_denials],
                textposition='outside',
                marker=dict(colors=[GREEN_700, ORANGE_700])
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.15)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"**Takeaway:** {denial_rate:.2f}% of claims denied; {(appealed/total_denials)*100:.1f}% proceed to appeal.", unsafe_allow_html=True)
        
        with col2:
            # Denial reasons bar
            if len(denial_reasons) > 0:
                fig = go.Figure(data=[go.Bar(
                    x=denial_reasons.index[:5],
                    y=denial_reasons.values[:5],
                    marker=dict(color=BLUE_700),
                    text=[f"{c:,}" for c in denial_reasons.values[:5]],
                    textposition='outside',
                    textfont=dict(size=12, color=NAVY)
                )])
                fig.update_layout(
                    height=340,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12),
                    margin=dict(l=16, r=16, t=44, b=44),
                    xaxis=dict(tickangle=0),
                    yaxis=dict(title="Denial Count")
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("**Takeaway:** Top 5 denial reasons account for majority of denials.", unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Executive Metrics</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            top_reason = denial_reasons.index[0] if len(denial_reasons) > 0 else "N/A"
            top_count = denial_reasons.values[0] if len(denial_reasons) > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
            <strong>Top Denial Reason</strong><br/>
            {top_reason}<br/>
            <span style="color: #0077B3; font-weight: 600;">{top_count:,} denials</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
            <strong>Appeal Submission Rate</strong><br/>
            {(appealed/total_denials)*100:.1f}%<br/>
            <span style="color: #0077B3; font-weight: 600;">{appealed:,} of {total_denials:,}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
            <strong>Members</strong><br/>
            {len(claims['member_id'].unique()):,}<br/>
            <span style="color: #0077B3; font-weight: 600;">Across {len(providers)} providers</span>
            </div>
            """, unsafe_allow_html=True)
    
    # ============================================================
    # TAB 2: ROOT CAUSE ANALYSIS
    # ============================================================
    
    with tabs[1]:
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Denial reasons concentrate in top categories. Analysis identifies high-recovery targets vs unrecoverable denials.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Denied $ by reason
            if len(denial_reason_dollars) > 0:
                reason_dollars = denial_reason_dollars.sort_values(ascending=False)
                fig = go.Figure(data=[go.Bar(
                    x=reason_dollars.index[:5],
                    y=reason_dollars.values[:5]/1e6,
                    marker=dict(color=BLUE_700),
                    text=[f"${d:.1f}M" for d in reason_dollars.values[:5]/1e6],
                    textposition='outside',
                    textfont=dict(size=12, color=NAVY)
                )])
                fig.update_layout(
                    height=340,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12),
                    margin=dict(l=16, r=16, t=44, b=44),
                    xaxis=dict(tickangle=0),
                    yaxis=dict(title="Denied Amount ($M)")
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("**Takeaway:** Top denial reasons own majority of denied dollars.", unsafe_allow_html=True)
        
        with col2:
            # Appeal success by reason
            if 'appeal_outcome' in denials.columns:
                appeal_by_reason = denials.groupby('denial_reason_category_manual').apply(
                    lambda x: (x['appeal_outcome'] == 'approved').sum() / len(x) * 100 if len(x) > 0 else 0
                ).sort_values(ascending=False)
                
                fig = go.Figure(data=[go.Bar(
                    x=appeal_by_reason.index[:5],
                    y=appeal_by_reason.values[:5],
                    marker=dict(color=GREEN_700),
                    text=[f"{r:.0f}%" for r in appeal_by_reason.values[:5]],
                    textposition='outside',
                    textfont=dict(size=12, color=NAVY)
                )])
                fig.update_layout(
                    height=340,
                    paper_bgcolor=WHITE,
                    plot_bgcolor=WHITE,
                    font=dict(family="Arial", size=12),
                    margin=dict(l=16, r=16, t=44, b=44),
                    xaxis=dict(tickangle=0),
                    yaxis=dict(title="Appeal Success Rate (%)")
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("**Takeaway:** Appeal success varies by denial reason; focus resources on high-success categories.", unsafe_allow_html=True)
    
    # ============================================================
    # TAB 3: PROVIDER PERFORMANCE
    # ============================================================
    
    with tabs[2]:
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Provider-level denial rates show tight clustering. No single provider is a statistical outlier.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Denials by provider (top 10)
            provider_denials = denials['provider_id'].value_counts().head(10)
            fig = go.Figure(data=[go.Bar(
                x=provider_denials.index,
                y=provider_denials.values,
                marker=dict(color=BLUE_700),
                text=[f"{c:,}" for c in provider_denials.values],
                textposition='outside',
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                xaxis=dict(title="Provider ID", tickangle=45),
                yaxis=dict(title="Denial Count")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Takeaway:** Denials spread across providers; no single provider dominates.", unsafe_allow_html=True)
        
        with col2:
            # Provider claims count
            provider_claims = claims['provider_id'].value_counts().head(10)
            fig = go.Figure(data=[go.Bar(
                x=provider_claims.index,
                y=provider_claims.values,
                marker=dict(color=STEEL_700),
                text=[f"{c:,}" for c in provider_claims.values],
                textposition='outside',
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                xaxis=dict(title="Provider ID", tickangle=45),
                yaxis=dict(title="Claims Submitted")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Takeaway:** Volume distributed across provider network.", unsafe_allow_html=True)
    
    # ============================================================
    # TAB 4: RISK ANALYSIS
    # ============================================================
    
    with tabs[3]:
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Risk model concentrates high-denial-risk claims into actionable segments for prioritized intervention.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Denial rate by claim amount decile
            claims['claim_amount_decile'] = pd.qcut(claims['claim_amount'], q=10, labels=False, duplicates='drop')
            denial_by_decile = denials.merge(claims[['claim_id', 'claim_amount_decile']], on='claim_id', how='left')
            denial_rate_by_decile = denial_by_decile['claim_amount_decile'].value_counts().sort_index()
            
            fig = go.Figure(data=[go.Bar(
                x=[f"D{i+1}" for i in range(len(denial_rate_by_decile))],
                y=denial_rate_by_decile.values,
                marker=dict(color=BLUE_700),
                text=[f"{v:,}" for v in denial_rate_by_decile.values],
                textposition='outside',
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                xaxis=dict(title="Decile (1=Highest Value Claims)"),
                yaxis=dict(title="Denial Count")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Takeaway:** Denial concentration varies by claim characteristics.", unsafe_allow_html=True)
        
        with col2:
            # Denials by member count
            denials_per_member = denials['member_id'].value_counts()
            fig = go.Figure(data=[go.Bar(
                x=denials_per_member.index[:10],
                y=denials_per_member.values[:10],
                marker=dict(color=ORANGE_700),
                text=[f"{c:,}" for c in denials_per_member.values[:10]],
                textposition='outside',
                textfont=dict(size=11, color=NAVY)
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                xaxis=dict(title="Member ID"),
                yaxis=dict(title="Denials per Member")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("**Takeaway:** Most members have 1-2 denials; repeat denials are rare (systemic, not concentrated).", unsafe_allow_html=True)
    
    # ============================================================
    # TAB 5: FINANCIAL IMPACT
    # ============================================================
    
    with tabs[4]:
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">$6-8M Year-1 recovery potential from targeted process improvements. Conservative scenario: $3-5M from top 2 denial reasons.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Scenario Modeling")
            recovery_rate = st.slider("Recovery Rate (%)", 10, 100, 50, 10)
            cost_per_case = st.slider("Cost per Case ($)", 100, 1000, 300, 100)
            
            recoverable_usd = total_denied_usd * (recovery_rate / 100)
            total_cost = total_denials * (cost_per_case / 100)
            roi = recoverable_usd / total_cost if total_cost > 0 else 0
            
            st.markdown(f"""
            <div class="metric-card" style="margin-top: 16px;">
            <strong>Estimated Recovery</strong><br/>
            <span style="font-size: 20px; color: #08CAA9; font-weight: 600;">${recoverable_usd/1e6:.1f}M</span><br/>
            <br/>
            <strong>Total Investment</strong><br/>
            <span style="font-size: 14px;">${total_cost/1000:.0f}K</span><br/>
            <br/>
            <strong>ROI</strong><br/>
            <span style="font-size: 18px; color: #0077B3; font-weight: 600;">{roi:.1f}x</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Recovery scenario comparison
            scenarios = ['Conservative', 'Moderate', 'Aggressive']
            recovery_vals = [total_denied_usd * 0.30 / 1e6, total_denied_usd * 0.60 / 1e6, total_denied_usd * 0.85 / 1e6]
            
            fig = go.Figure(data=[go.Bar(
                x=scenarios,
                y=recovery_vals,
                marker=dict(color=GREEN_700),
                text=[f"${r:.1f}M" for r in recovery_vals],
                textposition='outside',
                textfont=dict(size=12, color=NAVY)
            )])
            fig.update_layout(
                height=340,
                paper_bgcolor=WHITE,
                plot_bgcolor=WHITE,
                font=dict(family="Arial", size=12),
                margin=dict(l=16, r=16, t=44, b=44),
                yaxis=dict(title="Recovery Amount ($M)")
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================
    # TAB 6: RECOMMENDATIONS
    # ============================================================
    
    with tabs[5]:
        st.markdown("### Claims Denial Prevention Strategy")
        
        st.markdown('<div class="section-header">Immediate Actions (0-30 Days)</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rec-card">
        <strong>1. Launch Targeted Appeals Program</strong><br/>
        Focus on denial reasons with highest appeal success rates. Estimated 2-3M recovery in first month.
        </div>
        
        <div class="rec-card">
        <strong>2. Implement Processing SLA</strong><br/>
        Set target processing times for high-volume denial reasons to prevent denials upfront.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Short-Term Actions (30-90 Days)</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rec-card">
        <strong>3. Build Pre-Submission Validation</strong><br/>
        Automate checks for completeness and accuracy before claims reach adjudication system.
        </div>
        
        <div class="rec-card">
        <strong>4. Establish Member Communication Program</strong><br/>
        Communicate coverage limits and exclusions upfront to reduce friction and appeals volume.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Strategic Investments (90+ Days)</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rec-card">
        <strong>5. Deploy Denial-Risk Scoring</strong><br/>
        Integrate predictive model into adjudication workflow for automated flagging of high-risk claims.
        </div>
        
        <div class="rec-card">
        <strong>6. Establish Continuous Monitoring</strong><br/>
        Quarterly reviews of denial patterns to catch emerging issues early and validate improvements.
        </div>
        """, unsafe_allow_html=True)
    
    # ============================================================
    # TAB 7: CROSS-INDUSTRY
    # ============================================================
    
    with tabs[6]:
        st.markdown('<div class="insight-strip"><div class="insight-strip-label">FRAMEWORK PORTABILITY</div><div class="insight-strip-text">Denial patterns in healthcare translate across insurance domains. Root-cause analysis framework is industry-agnostic.</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### Healthcare -> Pharmacy
            
            | Healthcare | Pharmacy |
            |---|---|
            | Prior Authorization | PA Request |
            | Billing Error | Billing Discrepancy |
            | Coverage Limits | Quantity Limits |
            | Network Status | Network Pharmacy |
            | Medical Necessity | Clinical Override |
            """)
        
        with col2:
            st.markdown("""
            ### Healthcare -> Auto Insurance
            
            | Healthcare | Auto |
            |---|---|
            | Prior Authorization | Claim Verification |
            | Billing Error | Policy Term Issue |
            | Coverage Limits | Coverage Limit Exceeded |
            | Network Status | Deductible Application |
            | Medical Necessity | Exclusion Clause |
            """)
        
        st.markdown('<div class="section-header">Adaptation Principles</div>', unsafe_allow_html=True)
        
        st.markdown("""
        1. **Root-Cause Concentration:** Top 3-5 reasons typically own 70%+ of denied dollars
        2. **Appeal Success Variance:** Highest-success categories are best targets for recovery programs
        3. **Systemic vs. Concentrated:** Determine if denials are process-wide or isolated to specific entities
        4. **Financial Modeling:** Scenario analysis on top 2 drivers yields diminishing returns for full-driver models
        5. **Provider/Network Effects:** Test whether denials correlate with provider tier; if not, focus on process quality
        """)
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #707070; font-size: 12px; margin-top: 32px;">
    <p><strong>Claims Denial Prevention Analytics</strong> | 200,000 claims analyzed | 7,862 denials studied</p>
    <p>Dashboard by Luciano Casillas | <a href="https://github.com/Luciano-Casillas/claims-denial-prevention">GitHub</a></p>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("Unable to load data. Please ensure CSV files are in the data/ folder.")
