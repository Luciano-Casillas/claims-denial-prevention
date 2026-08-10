"""
Clarity Health Plans - Claims Denial Prevention Intelligence Dashboard
Author: Luciano Casillas
Version: 1.0

Interactive analysis of health insurance claims denial patterns, root causes,
and financial recovery opportunities. Powered by analysis and metrics-driven
discovery on 200,000 historical claims.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

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
# MOCK DATA GENERATION
# ============================================================

@st.cache_data
def load_mock_data():
    """Generate realistic mock data for demonstration."""
    np.random.seed(42)
    
    # Summary metrics
    total_claims = 200000
    total_denials = 7862
    denied_dollars = 29940000
    
    # Denial reasons
    denial_reasons = {
        'Prior Authorization': {'count': 2802, 'denied_usd': 10400000, 'appeal_success': 0.539},
        'Billing Error': {'count': 936, 'denied_usd': 3640000, 'appeal_success': 0.607},
        'Coverage Limits': {'count': 1113, 'denied_usd': 4070000, 'appeal_success': 0.0},
        'Network Issue': {'count': 1381, 'denied_usd': 5220000, 'appeal_success': 0.569},
        'Medical Necessity': {'count': 770, 'denied_usd': 2980000, 'appeal_success': 0.539},
    }
    
    return {
        'total_claims': total_claims,
        'total_denials': total_denials,
        'denial_rate': (total_denials / total_claims) * 100,
        'denied_dollars': denied_dollars,
        'avg_denied_claim': denied_dollars / total_denials,
        'denial_reasons': denial_reasons,
        'members': 100000,
        'providers': 350,
    }

data = load_mock_data()

# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown("### Filters")

claim_categories = st.sidebar.multiselect(
    "Claim Category",
    ['Inpatient', 'Outpatient', 'Emergency', 'Imaging', 'Lab', 'Other'],
    default=['Inpatient', 'Outpatient', 'Emergency', 'Imaging', 'Lab', 'Other'],
    key='claim_category'
)

specialties = st.sidebar.multiselect(
    "Provider Specialty",
    ['Primary Care', 'Cardiology', 'Orthopedics', 'Emergency', 'Imaging'],
    default=['Primary Care', 'Cardiology', 'Orthopedics', 'Emergency', 'Imaging'],
    key='specialty'
)

st.sidebar.markdown("---")
if st.sidebar.button("Reset All Filters"):
    st.rerun()

# ============================================================
# KPI HEADER
# ============================================================

st.markdown("### Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Claims",
        f"{data['total_claims']:,}",
        "+3.2%",
        delta_color="inverse"
    )

with col2:
    st.metric(
        "Denial Rate",
        f"{data['denial_rate']:.2f}%",
        "-0.4%"
    )

with col3:
    st.metric(
        "Total Denied $",
        f"${data['denied_dollars']/1e6:.1f}M",
        "+5.8%",
        delta_color="inverse"
    )

with col4:
    st.metric(
        "Recovery Potential",
        f"${6}M - ${8}M",
        "Year-1"
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
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Prior authorization delays drive $10.4M annually (35% of all denials). 54% appeal successfully, making this the highest-ROI recovery target.</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Denial status pie chart
        denial_status = {
            'Approved': 192138,
            'Denied': 7862
        }
        fig = go.Figure(data=[go.Pie(
            labels=list(denial_status.keys()),
            values=list(denial_status.values()),
            textposition='outside',
            marker=dict(colors=['#08CAA9', '#FF8A39'])
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
        st.markdown("**Takeaway:** 3.93% of claims are denied; 25.3% of denials proceed to appeal.", unsafe_allow_html=True)
    
    with col2:
        # Denial reasons bar chart
        reasons = list(data['denial_reasons'].keys())
        counts = [data['denial_reasons'][r]['count'] for r in reasons]
        
        fig = go.Figure(data=[go.Bar(
            x=reasons,
            y=counts,
            marker=dict(color=BLUE_700),
            text=[f"{c:,}" for c in counts],
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
        st.markdown("**Takeaway:** Prior auth delays (2,802) and network issues (1,381) account for 52% of all denials.", unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Executive Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
        <strong>Top Denial Reason</strong><br/>
        Prior Authorization<br/>
        <span style="color: #0077B3; font-weight: 600;">$10.4M | 35% of denials</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
        <strong>Highest Appeal Success</strong><br/>
        Billing Errors<br/>
        <span style="color: #0077B3; font-weight: 600;">61% | $3.64M at risk</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
        <strong>Network Correlation</strong><br/>
        No Difference<br/>
        <span style="color: #0077B3; font-weight: 600;">In: 3.95% | Out: 3.87%</span>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# TAB 2: ROOT CAUSE ANALYSIS
# ============================================================

with tabs[1]:
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">Billing errors appeal at 61% success rate (highest), followed by prior auth (54%). Coverage limits have zero appeal pathway.</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Denied $ by reason
        reasons = list(data['denial_reasons'].keys())
        dollars = [data['denial_reasons'][r]['denied_usd']/1e6 for r in reasons]
        
        fig = go.Figure(data=[go.Bar(
            x=reasons,
            y=dollars,
            marker=dict(color=BLUE_700),
            text=[f"${d:.1f}M" for d in dollars],
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
        st.markdown("**Takeaway:** Prior auth ($10.4M) and coverage limits ($4.07M) own 48% of denied dollars.", unsafe_allow_html=True)
    
    with col2:
        # Appeal success rate by reason
        reasons = list(data['denial_reasons'].keys())
        appeal_rates = [data['denial_reasons'][r]['appeal_success']*100 for r in reasons]
        
        fig = go.Figure(data=[go.Bar(
            x=reasons,
            y=appeal_rates,
            marker=dict(color=GREEN_700),
            text=[f"{r:.0f}%" for r in appeal_rates],
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
        st.markdown("**Takeaway:** Billing errors (61%) > Prior auth (54%). Coverage limits (0%) are unrecoverable by design.", unsafe_allow_html=True)

# ============================================================
# TAB 3: PROVIDER PERFORMANCE
# ============================================================

with tabs[2]:
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">No provider is an outlier. Top provider denied $150K (0.5% of total). Denials are systemic, not concentrated.</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        specialties = ['Primary Care', 'Cardiology', 'Orthopedics', 'Emergency', 'Imaging']
        denial_rates = [3.87, 4.05, 3.92, 3.60, 4.13]
        
        fig = go.Figure(data=[go.Bar(
            x=specialties,
            y=denial_rates,
            marker=dict(color=BLUE_700),
            text=[f"{r:.2f}%" for r in denial_rates],
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
            yaxis=dict(title="Denial Rate (%)")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Takeaway:** Tight clustering (3.60% to 4.13%). No specialty is a consistent outlier.", unsafe_allow_html=True)
    
    with col2:
        networks = ['In-Network', 'Out-of-Network']
        in_rates = [3.95, 3.87]
        
        fig = go.Figure(data=[go.Bar(
            x=networks,
            y=in_rates,
            marker=dict(color=[BLUE_700, BLUE_500]),
            text=[f"{r:.2f}%" for r in in_rates],
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
            yaxis=dict(title="Denial Rate (%)")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Takeaway:** Network affiliation has ZERO correlation. In-network (3.95%) vs Out (3.87%) -- no difference.", unsafe_allow_html=True)

# ============================================================
# TAB 4: RISK MODEL
# ============================================================

with tabs[3]:
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">XGBoost model achieves 1.18x lift in top decile (4.65% denial rate vs 3.93% baseline). Top features: claim amount (10.71%), plan type (9.46%), chronic condition (9.20%).</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        deciles = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        denial_rates_by_decile = [4.65, 4.21, 4.05, 3.98, 3.95, 3.88, 3.81, 3.72, 3.65, 3.52]
        
        fig = go.Figure(data=[go.Bar(
            x=[f"D{d}" for d in deciles],
            y=denial_rates_by_decile,
            marker=dict(color=[BLUE_700 if d <= 2 else STEEL_700 for d in deciles]),
            text=[f"{r:.2f}%" for r in denial_rates_by_decile],
            textposition='outside',
            textfont=dict(size=11, color=NAVY)
        )])
        fig.update_layout(
            height=340,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=44, b=44),
            xaxis=dict(title="Decile (1=Highest Risk)"),
            yaxis=dict(title="Denial Rate (%)")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Takeaway:** Top 2 deciles concentrate 31% of denials from 20% of volume (1.54x lift).", unsafe_allow_html=True)
    
    with col2:
        features = ['Claim Amount', 'Plan Type', 'Chronic Condition', 'Network Status', 'Specialty', 'Prior Auth Required']
        importance = [0.1071, 0.0946, 0.0920, 0.0910, 0.0910, 0.0890]
        
        fig = go.Figure(data=[go.Barh(
            x=importance,
            y=features,
            marker=dict(color=BLUE_700),
            text=[f"{i*100:.1f}%" for i in importance],
            textposition='outside',
            textfont=dict(size=11, color=NAVY)
        )])
        fig.update_layout(
            height=340,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=44, b=44),
            xaxis=dict(title="Feature Importance"),
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Takeaway:** Claim amount (10.7%) is the strongest predictor. Top 3 features explain 28% of variance.", unsafe_allow_html=True)

# ============================================================
# TAB 5: FINANCIAL IMPACT
# ============================================================

with tabs[4]:
    st.markdown('<div class="insight-strip"><div class="insight-strip-label">KEY FINDING</div><div class="insight-strip-text">$6-8M Year-1 recovery potential from process improvements. Conservative scenario: $3-5M from prior auth speedup alone (16.7x ROI on $300K investment).</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Scenario Analysis")
        save_rate = st.slider("Prior Auth Appeal Success Rate", 0.40, 0.70, 0.54, 0.01)
        cost_per_contact = st.slider("Cost per Appeal ($)", 100, 500, 300, 50)
        
        # Calculate recovery
        prior_auth_denials = 2802
        pa_denied_usd = 10400000
        estimated_recovery = pa_denied_usd * save_rate
        total_cost = prior_auth_denials * cost_per_contact
        roi = estimated_recovery / total_cost if total_cost > 0 else 0
        
        st.markdown(f"""
        <div class="metric-card" style="margin-top: 16px;">
        <strong>Estimated Recovery</strong><br/>
        <span style="font-size: 20px; color: #08CAA9; font-weight: 600;">${estimated_recovery/1e6:.1f}M</span><br/>
        <br/>
        <strong>Total Investment</strong><br/>
        <span style="font-size: 14px;">${total_cost/1000:.0f}K</span><br/>
        <br/>
        <strong>ROI</strong><br/>
        <span style="font-size: 18px; color: #0077B3; font-weight: 600;">{roi:.1f}x</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        scenarios = ['Conservative\n(Prior Auth Only)', 'Moderate\n(Prior Auth + Billing)', 'Full\n(All Drivers)']
        recovery = [4.5, 7.0, 9.0]
        investment = [300, 600, 1000]
        roi_vals = [r*1e6/(i*1000) for r, i in zip(recovery, investment)]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=scenarios,
            y=recovery,
            name='Recovery Potential ($M)',
            marker=dict(color=GREEN_700),
            text=[f"${r:.0f}M" for r in recovery],
            textposition='outside'
        ))
        fig.update_layout(
            height=340,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            font=dict(family="Arial", size=12),
            margin=dict(l=16, r=16, t=44, b=44),
            yaxis=dict(title="Recovery Amount ($M)"),
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 6: RECOMMENDATIONS
# ============================================================

with tabs[5]:
    st.markdown("### Claim Denial Prevention Strategy")
    
    st.markdown('<div class="section-header">Immediate Actions (0-30 Days)</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
    <strong>1. Launch Targeted Appeals Program for Billing Errors</strong><br/>
    Billing errors appeal at 61% success rate (highest among all reasons). Push the $3.64M in denied billing claims through appeals with dedicated staff. Estimated $2-3M recovery in 30 days.
    </div>
    
    <div class="rec-card">
    <strong>2. Implement Prior Authorization Processing SLA</strong><br/>
    Set a 2-day maximum processing target (down from current 5 days). 54% appeal success on prior auth denials means most are recoverable; accelerating approvals prevents denials upfront.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Short-Term Actions (30-90 Days)</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
    <strong>3. Build Pre-Submission Validation</strong><br/>
    While completion rates have minimal impact on denial rates, automating basic validation (coverage tier check, provider network verification) prevents $3,000+ denials downstream.
    </div>
    
    <div class="rec-card">
    <strong>4. Establish Communication Program for Coverage Limits</strong><br/>
    $4.07M in coverage-limit denials should be prevented through upfront policy explanation at enrollment, not through failed appeals.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Strategic Investments (90+ Days)</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="rec-card">
    <strong>5. Deploy Denial-Risk Scoring in Adjudication</strong><br/>
    Integrate the model's risk decile into the claims system to automatically flag high-risk claims for human review before final adjudication.
    </div>
    
    <div class="rec-card">
    <strong>6. Establish Quarterly Denial Deep-Dive Reviews</strong><br/>
    Continue monitoring denial patterns by reason, appeal success, and member/provider cohort. Quarterly reviews ensure new patterns are caught early.
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
    2. **Appeal Success Variance:** Build appeals strategy around highest-success categories (billing errors, prior auth > coverage limits, exclusions)
    3. **Network/Provider Effects:** Test whether denials correlate with provider/network tier; if not, focus on process quality instead
    4. **Systemic vs. Concentrated:** Determine if denials are spread (process problem) or concentrated (bad actors/outliers)
    5. **Financial Modeling:** Build scenario analysis around top 2-3 levers; full-driver models show diminishing returns
    """)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #707070; font-size: 12px; margin-top: 32px;">
<p><strong>Claims Denial Prevention Analytics</strong> | 200,000 claims | 7,862 denials | $29.94M denied</p>
<p>Dashboard built by Luciano Casillas | <a href="https://github.com/Luciano-Casillas/claims-denial-prevention">GitHub</a></p>
</div>
""", unsafe_allow_html=True)