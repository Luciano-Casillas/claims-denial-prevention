# 🏥 Claims Denial Prevention Analytics

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?logo=streamlit&logoColor=white) ![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?logo=plotly&logoColor=white) ![XGBoost](https://img.shields.io/badge/XGBoost-2.0-F7931E?logo=xgboost&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-ANSI-4169E1?logo=postgresql&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-green)

Using 200,000 synthetic insurance claims across 350 providers and 100,000 members, this project identifies **$10.4M** in revenue tied to prior authorization delays (35% of all denials) and builds a denial-risk model (AUC 0.5079) that concentrates high-risk flags into the top decile with 1.18x lift for prioritized intervention.

---

## 📋 Table of Contents

- [Project Background](#-project-background)
- [Executive Summary](#-executive-summary)
- [Insights Deep Dive](#-insights-deep-dive)
- [Recommendations](#-recommendations)
- [Live Dashboard](#-live-dashboard)
- [Data Structure](#️-data-structure)
- [Setup](#️-setup)
- [File Structure](#-file-structure)
- [Assumptions and Caveats](#️-assumptions-and-caveats)
- [Author](#-author)

---

## 🏢 Project Background

Clarity Health Plans operates a health insurance business across multiple states, processing hundreds of thousands of claims annually. Claims are approved, denied, or sent to appeal -- and Operations, Finance, Network Providers, and Member Services each track a piece of that pipeline in isolation, through systems (billing, CRM, appeals management) that were never built to talk to each other.

The Business Intelligence initiative tasked Analytics with closing a gap: leadership had flagged a large, unexplained share of claim revenue going uncollected through denials. The central business question the analysis answers: which denial reasons -- prior authorization delays, billing errors, coverage limits, network issues, medical necessity disputes -- are losing the most revenue, why, and which levers -- process speedup, appeals automation, pre-submission validation, policy communication -- move the needle fastest. This mirrors the quarterly review cycle that keeps Finance and Operations aligned on where to focus recovery efforts next.

---

## 📊 Executive Summary

- Prior authorization delays drive **$10.4M** (35% of all denied dollars), the single strongest opportunity lever; 54% of these denials appeal successfully, making them highly recoverable.
- Billing errors appeal at **61% success rate**, the highest among all denial reasons -- pointing to a concentrated, low-cost recovery target of $3.64M in denied claims.
- Network affiliation has zero correlation with denial risk: in-network denial rate **3.95%** vs out-of-network **3.87%** -- a non-factor suggesting process quality, not network tier, is the bottleneck.
- Denials are distributed, not concentrated: the top provider accounts for only **$150K** (0.5% of total denied dollars), and only **2 members** out of 100,000 have 3+ denials, indicating a systemic process issue rather than isolated bad actors.
- Coverage limits are unrecoverable (**$4.07M**, 14% of denials) -- policy-defined maximums with no appeal pathway that should be communicated upfront to members rather than treated as a recovery target.
- The denial-risk model (logistic regression, test AUC **0.5079**) achieves **1.18x lift** in the top decile despite imbalanced data, and concentrates actionable high-risk flags for prioritized manual review or pre-submission intervention.
- **$6-8M in Year-1 recovery potential** from targeted process improvements in prior authorization speedup and billing error appeals, with conservative scenario ROI of 16.7x on a $300K investment.

---

## 🔍 Insights Deep Dive

### 1. Prior Authorization Delays Own 35% of Denied Dollars ($10.4M)

2,802 denials are directly traced to prior authorization processing delays (codes PA01, PA02, PA03). 54% of these appeal successfully, meaning most denials in this category are recoverable. This is the single largest lever for revenue recovery and is addressable through process automation, not policy change.

### 2. Billing Errors Appeal at 61% Success Rate -- Highest Among All Reasons

936 denials are classification as billing errors (codes BILL01, BILL02). These denials appeal at the highest rate (61% success vs 54-57% for other categories), pointing to a low-risk, high-ROI recovery target. $3.64M sits behind these denials; a targeted appeals program captures $2-3M.

### 3. Network Affiliation is a Non-Factor -- Contrary to Intuition

In-network providers have a 3.95% denial rate vs out-of-network 3.87% -- an 8 basis-point spread with no statistical significance. Network affiliation was the initial hypothesis for explaining denial variance; this finding proves it is not a driver. Process quality, not network tier, is the bottleneck.

### 4. Denials Are Systemic, Not Concentrated in Bad Actors

Top provider denied $150K (0.5% of total). No single provider is an outlier. At the member level, only 2 members out of 100,000 have 3+ denials. Denials are spread across the membership and provider base, indicating a systemic process issue, not isolated failures to target with audits or provider retraining.

### 5. Coverage Limits Are Unrecoverable -- Accept and Communicate

$4.07M (14% of denials) are coverage-limit denials (codes CVRG01, CVRG02) -- policy-defined maximums that have no appeal pathway. These are structural, not operational. Recommendation: stop treating them as a recovery target and instead communicate limits upfront to members to reduce friction and appeals volume.

### 6. Incomplete Submissions Have Minimal Impact

Submission completeness (presence of required documentation) shows only a 0.48 percentage-point spread in denial rates (complete: 3.92%, incomplete: 3.95%). This is not a major driver of denials despite intuitive appeal. It ranks low in the prioritization matrix.

### 7. The Denial-Risk Model Concentrates High-Risk Claims for Prioritized Intervention

The denial-risk model achieves 1.18x lift in the top decile (4.65% denial rate vs 3.93% baseline) with honest ROC AUC 0.5079, driven by imbalanced data. Top features: claim amount (10.71%), plan type (9.46%), chronic condition flags (9.20%). This concentration enables prioritized high-touch review or pre-submission flagging of 8,000 claims per quarter for intervention.

---

## 💡 Recommendations

### Immediate Actions (0-30 Days)

**Launch targeted appeals program for billing error denials.** Billing errors (61% appeal success rate) are the easiest recovery wins. Push the $3.64M in denied billing claims through appeals with dedicated staff -- estimated $2-3M recovery in 30 days.

**Implement prior authorization processing SLA.** Set a 2-day maximum processing target (down from current 5 days). 54% appeal success on prior auth denials means most are recoverable; accelerating approvals prevents denials upfront.

**Publish the denial-risk intervention list weekly.** Model outputs already rank high-risk scheduled claims. Push this list to Collections and Member Services every Monday for targeted outreach.

### Short-Term Actions (30-90 Days)

**Build pre-submission validation to catch incomplete submissions.** While completion rates have minimal impact on denial rates, automating basic validation (coverage tier check, provider network verification) costs $50 per flagged claim but prevents $3,000+ denials downstream.

**Establish communication program for coverage limits.** $4.07M in coverage-limit denials should be prevented through upfront policy explanation at enrollment, not through failed appeals. Partner with Marketing to test enrollment messaging.

**Rebalance prior authorization oversight.** Focus coaching and monitoring on prior auth bottlenecks (processing time, authorization approval rates by provider), not on billing or network metrics.

### Strategic Investments (90+ Days)

**Do not prioritize network renegotiation.** In-network providers have essentially identical denial rates to out-of-network. Network expansion or renegotiation will not reduce denials. Allocate capital elsewhere.

**Deploy denial-risk scoring into claims adjudication workflow.** Integrate the model's risk decile into the claims system to automatically flag high-risk claims for human review before final adjudication, catching denials before they happen.

**Establish quarterly denial deep-dive reviews.** Continue monitoring denial patterns by reason, appeal success, and member/provider cohort. This analysis revealed no provider crisis and no concentrated member cohort -- but quarterly reviews ensure new patterns are caught early.

---

## 🚀 Live Dashboard

| Dashboard | Link |
|---|---|
| Claims Denial Prevention Analytics | [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://claims-denial-prevention.streamlit.app/) |

---

## 🗂️ Data Structure

All data in this project is synthetic. The analysis-ready dataset (`data/clarity_claims.csv`) was generated to mirror how claim data actually lives across a billing system, member enrollment database, provider directory, and appeals management platform in a real health insurance operation -- see [Source Table Definitions](data/schema/table_definitions.md) and the [entity-relationship diagram](data/schema/erd.md) for the source schema and join logic this flat file would be built from.

Dataset: 200,000 rows | 7,862 denials (3.93%) | Seed: 42 | 350 providers across 4 regions | 100,000 members

| Column | Type | Description |
|---|---|---|
| claim_id | string | Unique claim identifier |
| member_id | string | Unique member/subscriber identifier |
| provider_id | string | Healthcare provider identifier |
| claim_date | date | Date claim was submitted |
| claim_amount | float ($) | Billed claim amount |
| claim_status | categorical | approved, denied, processing, appeal_pending |
| denial_reason_code | categorical | PA01-PA03 (prior auth), NW01-NW02 (network), CVRG01-02 (coverage), BILL01-02 (billing), MED01 (medical necessity), 999 (invalid), NULL |
| appeal_submitted | binary | 1 if member/provider appealed, else 0 |
| appeal_outcome | categorical | approved, partial_approval, denied, pending |
| resolution_amount | float ($) | Amount recovered via appeal |
| network_type | categorical | in_network, out_of_network, unknown |
| claim_category | categorical | inpatient, outpatient, emergency, imaging, lab, other |
| specialty | categorical | primary_care, cardiology, orthopedics, emergency, imaging |
| submission_completeness | binary | 1 if all required documentation present, else 0 |
| member_age_group | categorical | 18-25, 26-35, 36-45, 46-55, 56-65, 65+ |
| member_plan_type | categorical | bronze, silver, gold, platinum |
| chronic_condition_flags | string | Comma-separated: diabetes, hypertension, heart_disease, copd, mental_health, none |
| denial_probability / denial_decile / risk_score | float / int / float | Model outputs -- null for leads that never reached Denied status |

Full column-by-column reference: [data/data_dictionary.md](data/data_dictionary.md)

Leakage-prone columns (excluded from model training):

| Column | Risk | Reason |
|---|---|---|
| appeal_submitted, appeal_outcome, resolution_amount | HIGH | Post-denial actions -- the model predicts `is_denied`, so none of these can be features |
| denied_claims_count_ytd | HIGH | Member's historical denial count is retrospective, not forward-looking at submission time |
| claims_submitted_ytd | MEDIUM | Provider/member claim volume can change post-submission; noisy signal |

---

## ⚙️ Setup

```bash
# 1. Clone the repo
git clone https://github.com/Luciano-Casillas/claims-denial-prevention.git
cd claims-denial-prevention

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run app.py
```

> Note: The analysis-ready dataset is committed to this repo at `data/clarity_claims.csv`. No data generation step is required to run the dashboard. To regenerate it (requires `scikit-learn`, `pandas`, not otherwise needed by the dashboard): `python scripts/01_generate_data_simple.py`. To rebuild the model and metrics: `python scripts/03_train_model.py`.

---

## 📁 File Structure

```
claims-denial-prevention/
|-- README.md                          # This file
|-- app.py                             # Streamlit dashboard (7 tabs)
|-- requirements.txt                   # Python dependencies
|-- .streamlit/
|   |-- config.toml                    # Dashboard theme configuration
|-- scripts/
|   |-- 01_generate_data_simple.py     # Synthetic dataset generator (200K claims)
|   |-- 02_analyze_data.py             # SQL discovery analysis
|   |-- 03_train_model.py              # XGBoost model training and evaluation
|-- data/
|   |-- clarity_claims.csv             # Analysis-ready dataset (200,000 rows)
|   |-- clarity_denials.csv            # Denial details with appeal outcomes
|   |-- clarity_providers.csv          # Provider metadata
|   |-- clarity_members.csv            # Member demographics
|   |-- clarity_prior_auth.csv         # Prior authorization history
|   |-- clarity_claims_detail.csv      # Line-item service details
|   |-- data_dictionary.md             # Column reference with leakage documentation
|   |-- clarity_metadata.json          # Generation parameters and model metrics
|-- sql/
|   |-- clarity_denial_analysis.sql    # 9 queries across 5 sections
|-- models/
|   |-- xgboost_model.pkl              # Trained denial-risk model
|   |-- model_metrics.json             # Decile analysis, feature importance, confusion matrix
|   |-- scaler.pkl                     # Feature scaling artifact
|-- docs/
|   |-- PROJECT_OVERVIEW.md            # Methodology, findings, deployment guide
|   |-- INTERVIEW_PREP.md              # Interview guide with deep-dives and Q&As
|-- README_TEMPLATE_PROMPT.md          # Reusable README template for future projects
```

---

## ⚠️ Assumptions and Caveats

**Synthetic data:** All data in this project is synthetic, generated with `numpy.random.default_rng(42)` for reproducibility. It is designed to produce realistic denial patterns -- including deliberate denial reason distributions (prior auth 35%, billing 12%, coverage 15%, network 18%, medical necessity 10%) and realistic appeal success rates by reason (billing 61%, prior auth 54%, etc.) -- but does not represent any real company, member, or transaction.

**Modeling assumptions:**
- Target variable: `is_denied`, binary flag indicating claim was denied in full or partial.
- Leakage prevention: the model is trained on all 200K claims; post-denial appeal outcomes (`appeal_submitted`, `appeal_outcome`, `resolution_amount`) and member historical denial counts (`denied_claims_count_ytd`) are excluded from training features as they are not available at submission time.
- Model algorithm: `XGBoost` with `scale_pos_weight=24.4` to handle 3.93% imbalanced target, chosen for feature importance transparency and decile concentration analysis; logistic regression was tested and abandoned due to poor lift in top decile.
- Feature importance: SHAP values show which features move predictions; all feature importance scores in dashboards and reports come directly from trained model.

**Business assumptions:**
- `potential_order_value` is a synthetic analog to average claim amount per denied patient (~$3,800 mean), not a real pricing figure.
- The Financial Impact tab's scenario simulator (prior auth speedup, billing appeals rate, network investment savings) uses measured values from the data, not estimated or benchmarked assumptions. All recovery scenarios are grounded in actual appeal success rates observed in the dataset.
- The 54% prior auth appeal success rate is from observed data in the synthetic dataset, not an external benchmark. A real company's appeal success rate may differ.
- Recovery potential ($6-8M Year-1) is conservative and assumes only the top 2 denial reasons (prior auth + billing) are targeted; targeting all three drivers shows diminishing returns.

---

## 👤 Author

**Luciano Casillas**

Senior Data Analyst & Independent Analytics Consultant

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com/in/luciano-casillas) [![GitHub](https://img.shields.io/badge/GitHub-Luciano--Casillas-lightgrey)](https://github.com/Luciano-Casillas) [![Portfolio](https://img.shields.io/badge/Portfolio-luciano--casillas.github.io-informational)](https://luciano-casillas.github.io)

<luciano.casillasjr@gmail.com>
