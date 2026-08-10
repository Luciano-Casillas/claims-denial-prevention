# 🏥 Claims Denial Prevention Analytics

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?logo=streamlit&logoColor=white) ![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?logo=plotly&logoColor=white) ![XGBoost](https://img.shields.io/badge/XGBoost-2.0-F7931E?logo=xgboost&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-ANSI-4169E1?logo=postgresql&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-green)

Using 200,000 synthetic insurance claims across 350 providers and 100,000 members, this project identifies **$10.4M** in revenue tied to prior authorization delays (35% of all denied dollars) and builds a denial-risk model (XGBoost, test AUC 0.5114) that concentrates high-risk flags into the top decile with 1.14x lift for prioritized intervention.

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
- Network affiliation has no statistically significant correlation with denial risk: in-network denial rate **3.95%** vs out-of-network **3.87%** (two-proportion z-test: z=0.77, p=0.44) -- confirming process quality, not network tier, is the bottleneck.
- Denials are distributed, not concentrated: the top provider accounts for only **$148K** (0.5% of total denied dollars), and only **2 members** out of 100,000 have 3+ denials, indicating a systemic process issue rather than isolated bad actors.
- **Correction from an earlier internal draft:** Coverage limit denials (**$4.07M**, 14% of denials) were previously assumed to be unrecoverable ("0% appeal success, no appeal pathway"). Re-measuring directly from the denials table shows a **59% appeal success rate** for this category -- the second-highest of any denial reason. This category should be added to the active appeals program, not written off.
- The denial-risk model (XGBoost, test AUC **0.5114**) achieves **1.14x lift** in the top decile despite imbalanced data (near-random AUC reflects the limited predictive power of the available features for this synthetic label), and concentrates actionable high-risk flags for prioritized manual review or pre-submission intervention.
- **Theoretical full-scope recovery ceiling of $14.8M** (100% appeal-push across all 5 core denial reasons, including the newly-recoverable Coverage Limits category). This is a planning ceiling, not a Year-1 guarantee -- realistic Year-1 capture during program ramp-up is typically 50-70% of the $7.8M Prior Auth + Billing ceiling for the first two categories targeted.

---

## 🔍 Insights Deep Dive

### 1. Prior Authorization Delays Own 35% of Denied Dollars ($10.4M)

2,802 denials are directly traced to prior authorization processing delays (codes PA01, PA02, PA03). 54% of these appeal successfully, meaning most denials in this category are recoverable. This is the single largest lever for revenue recovery and is addressable through process automation, not policy change.

### 2. Billing Errors Appeal at 61% Success Rate -- Highest Among All Reasons

936 denials are classification as billing errors (codes BILL01, BILL02). These denials appeal at the highest rate (61% success vs 54-57% for other categories), pointing to a low-risk, high-ROI recovery target. $3.64M sits behind these denials; a targeted appeals program captures $2-3M.

### 3. Network Affiliation is a Non-Factor -- Contrary to Intuition

In-network providers have a 3.95% denial rate vs out-of-network 3.87% -- an 8 basis-point spread. A two-proportion z-test confirms this is not statistically significant (z=0.77, p=0.44; in-network 95% CI [3.85%, 4.05%], out-of-network 95% CI [3.69%, 4.05%] -- the intervals overlap substantially). Network affiliation was the initial hypothesis for explaining denial variance; this finding proves it is not a driver. Process quality, not network tier, is the bottleneck.

### 4. Denials Are Systemic, Not Concentrated in Bad Actors

Top provider denied $148K (0.5% of total). No single provider is an outlier. At the member level, only 2 members out of 100,000 have 3+ denials. Denials are spread across the membership and provider base, indicating a systemic process issue, not isolated failures to target with audits or provider retraining.

### 5. Coverage Limits Are Recoverable -- A Correction to Prior Reporting

$4.07M (14% of denials) are coverage-limit denials (codes CVRG01, CVRG02). An earlier internal draft of this analysis assumed these were policy-defined maximums with no appeal pathway (0% appeal success) and recommended writing them off. **Re-measuring appeal outcomes directly from the denials table shows this was wrong**: 282 appeals were submitted against coverage-limit denials, and 167 succeeded (approved or partial_approval) -- a **59% success rate**, the second-highest of any category. Recommendation: add Coverage Limits to the active appeals program alongside Prior Authorization and Billing Errors, and separately audit why the earlier analysis assumed a hard 0% rate without checking the data.

### 6. Incomplete Submissions Have Minimal Impact

Submission completeness (presence of required documentation) shows only a small spread in denial rates (complete: 3.92%, incomplete: 3.95%, unknown: 4.40%). This is not a major driver of denials despite intuitive appeal. It ranks low in the prioritization matrix.

### 7. The Denial-Risk Model Concentrates High-Risk Claims for Prioritized Intervention

The denial-risk model (XGBoost) achieves 1.14x lift in the top decile (4.48% denial rate vs 3.93% baseline) with honest test ROC AUC 0.5114, driven by imbalanced data and the limited predictive power of available features. Top features: claim amount (11.0%), network type (10.2%), specialty (9.7%). Real decile output is not perfectly monotonic (decile 2 dips below deciles 3-5) -- this is expected at this AUC level and is reported as-is rather than smoothed. This concentration enables prioritized high-touch review or pre-submission flagging for intervention, used as a triage signal rather than a standalone approve/deny decision.

---

## 💡 Recommendations

### Immediate Actions (0-30 Days)

**Launch targeted appeals program for billing error denials.** Billing errors (61% appeal success rate) are the easiest recovery wins. Push the $3.64M in denied billing claims through appeals with dedicated staff -- estimated $2-3M recovery in 30 days.

**Implement prior authorization processing SLA.** Set a 2-day maximum processing target (down from current 5 days). 54% appeal success on prior auth denials means most are recoverable; accelerating approvals prevents denials upfront.

**Publish the denial-risk intervention list weekly.** Model outputs already rank high-risk scheduled claims. Push this list to Collections and Member Services every Monday for targeted outreach.

### Short-Term Actions (30-90 Days)

**Build pre-submission validation to catch incomplete submissions.** While completion rates have minimal impact on denial rates, automating basic validation (coverage tier check, provider network verification) prevents preventable denials downstream.

**Add Coverage Limits to the active appeals program.** Prior internal reporting assumed this $4.07M category was unrecoverable and recommended enrollment-messaging only. The real appeal success rate is 59% -- second-highest of any category. Route these denials into the same appeals workflow as Prior Authorization and Billing Errors; upfront policy communication is still worth pursuing to reduce volume, but it should not be the only response.

**Rebalance prior authorization oversight.** Focus coaching and monitoring on prior auth bottlenecks (processing time, authorization approval rates by provider), not on billing or network metrics.

### Strategic Investments (90+ Days)

**Do not prioritize network renegotiation.** In-network providers have essentially identical denial rates to out-of-network (statistically confirmed, p=0.44). Network expansion or renegotiation will not reduce denials. Allocate capital elsewhere.

**Deploy denial-risk scoring into claims adjudication workflow.** Integrate the model's risk decile into the claims system to flag high-risk claims for human review before final adjudication. Given the model's current AUC (~0.51), treat this as a low/moderate-confidence triage signal, not a standalone approve/deny decision.

**Establish quarterly denial deep-dive reviews with appeal-outcome verification.** Continue monitoring denial patterns by reason, appeal success, and member/provider cohort -- and explicitly re-check any "this category is unrecoverable" assumption against actual appeal outcomes each quarter. This analysis revealed no provider crisis and no concentrated member cohort, but it also caught a stale assumption that had gone unverified.

---

## 🚀 Live Dashboard

| Dashboard | Link |
|---|---|
| Claims Denial Prevention Analytics | [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://claims-denial-prevention.streamlit.app/) |

---

## 🗂️ Data Structure

All data in this project is synthetic. Dataset: 200,000 rows | 7,862 denials (3.93%) | Seed: 42 | 350 providers across 4 regions | 100,000 members.

The data lives across 6 normalized tables, not one flat file, mirroring how claim data actually lives across a billing system, member enrollment database, provider directory, and appeals management platform. `clarity_claims.csv` is the primary table; member and provider attributes are joined in at analysis time via `member_id` / `provider_id`.

**`clarity_claims.csv`** (primary table, 200,000 rows):

| Column | Type | Real Observed Values |
|---|---|---|
| claim_id, member_id, provider_id | int | Sequential integer IDs |
| claim_date, service_start_date, service_end_date | date | 2025 calendar year |
| claim_amount | float ($) | $500-$50K range, modal peak $3-4K |
| claim_status | categorical | approved (87.0%), processing (5.0%), denied (3.9%), appeal_pending (2.1%), submitted (2.0%) |
| submission_completeness_flag | categorical | complete (92.0%), incomplete (5.9%), unknown (2.0%) |
| claim_category | categorical | office_visit, pharmacy, procedure, imaging, emergency, lab, inpatient (7 values) |
| network_type | categorical | in_network (78.1%), out_of_network (21.9%) |
| prior_auth_required | boolean | True / False |

**`clarity_denials.csv`** (7,862 rows, one per denied claim):

| Column | Type | Real Observed Values |
|---|---|---|
| denial_reason_code | categorical | PA01/PA02 (prior auth), CVRG01 (coverage), NW01 + free-text "provider not network" (network), BILL01 (billing), MED01 (medical necessity), free-text "missing auth", 999 (invalid), null -- messier than a clean code list, which is realistic for production claims data |
| denied_claim_amount | float ($) | Portion of the claim denied |
| appeal_submitted | boolean | True / False |
| appeal_outcome | categorical | approved, partial_approval, denied, null (not yet appealed) |
| resolution_amount | float ($) | Amount recovered via appeal |

**`clarity_providers.csv`** (350 rows): specialty (cardiology, emergency, imaging, lab, orthopedics, pharmacy, primary_care, psychiatry -- 8 values), network_status, geographic_region, claims_submitted_ytd.

**`clarity_members.csv`** (100,000 rows, used by `scripts/03_train_model.py` for model features only -- not loaded by the dashboard): age_group, plan_type, income_bracket, chronic_condition_flags, denied_claims_count_ytd.

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

> Note: The analysis-ready dataset and trained model are committed to this repo (`data/*.csv`, `models/*.json`, `models/*.pkl`). No data generation or training step is required to run the dashboard -- `app.py` loads `data/clarity_claims.csv`, `clarity_denials.csv`, `clarity_providers.csv`, and `models/model_metrics.json` directly and computes every chart and KPI live from them; nothing is hardcoded. To regenerate the dataset from scratch: `cd scripts && python 01_generate_data_simple.py` (seeded, reproducible). To retrain the model: `cd scripts && python 03_train_model.py`.

---

## 📁 File Structure

```
claims-denial-prevention/
|-- README.md                          # This file
|-- app.py                             # Streamlit dashboard (7 tabs) -- loads and aggregates
|                                       #   the CSVs in data/ live; no numbers are hardcoded
|-- requirements.txt                   # Python dependencies
|-- .streamlit/
|   |-- config.toml                    # Dashboard theme configuration
|-- scripts/
|   |-- 01_generate_data_simple.py     # Synthetic dataset generator (200K claims, seed=42)
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
|   |-- clarity_metadata.json          # Generation timestamp, seed, dataset summary
|-- sql/
|   |-- clarity_denial_analysis.sql    # 9 queries across 5 sections
|-- models/
|   |-- denial_risk_model.pkl          # Trained XGBoost denial-risk model
|   |-- label_encoders.pkl             # Per-column LabelEncoder objects used at training time
|   |-- model_metrics.json             # AUC, decile analysis, feature importance, confusion matrix
|-- docs/
|   |-- PROJECT_OVERVIEW.md            # Methodology, findings, deployment guide
|   |-- INTERVIEW_PREP.md              # Interview guide with deep-dives and Q&As
|-- README_TEMPLATE_PROMPT.md          # Reusable README template for future projects
```

> Note: All files listed above are committed to the repository, including `models/` and the supplementary `data/` files. `app.py` only reads `data/clarity_claims.csv`, `clarity_denials.csv`, `clarity_providers.csv`, and `models/model_metrics.json` at runtime; `clarity_members.csv`, `clarity_prior_auth.csv`, and `clarity_claims_detail.csv` are used by `scripts/02_analyze_data.py` and `scripts/03_train_model.py` and are committed for full reproducibility. Both generation scripts are seeded (`seed=42`), so re-running them reproduces the same claims/denials/providers rows (floating-point values may differ in the last 1-2 decimal digits across numpy/pandas versions -- this is display-precision noise, not a data change).

---

## ⚠️ Assumptions and Caveats

**Synthetic data:** All data in this project is synthetic, generated with `numpy.random.seed(42)` for reproducibility. It is designed to produce realistic denial patterns -- observed denial reason distribution: prior auth 35.6%, network 17.6%, coverage 14.2%, billing 11.9%, other/unclassified 10.9%, medical necessity 9.8% -- but does not represent any real company, member, or transaction.

**Modeling assumptions:**
- Target variable: `is_denied`, binary flag indicating claim was denied in full or partial.
- Leakage prevention: the model is trained on all 200K claims; post-denial appeal outcomes (`appeal_submitted`, `appeal_outcome`, `resolution_amount`) and member historical denial counts (`denied_claims_count_ytd`) are excluded from training features as they are not available at submission time.
- Model algorithm: `XGBoost` with a computed `scale_pos_weight` (~24x, derived from the training split's class ratio) to handle the 3.93% imbalanced target. Categorical features are `LabelEncoder`-encoded (`models/label_encoders.pkl`); no feature scaling is applied since XGBoost is tree-based and scale-invariant.
- Real test-set ROC AUC is 0.51 -- effectively no better than random on held-out data. This is reported honestly rather than smoothed; the model is used for decile-based triage concentration (1.14x lift in the top decile), not as a reliable individual-claim predictor.

**Business assumptions:**
- The Financial Impact tab's scenario simulator computes recovery scenarios directly from measured appeal success rates per denial category (Prior Auth, + Billing, + all 5 core reasons), not from estimated or benchmarked assumptions.
- Scenario dollar figures represent a **theoretical recovery ceiling** -- denied dollars in a category multiplied by that category's historical appeal success rate, i.e. what recovery would look like if every eligible denial in the category were appealed. This is a planning ceiling, not a Year-1 forecast; only ~25% of denials are appealed today, so full-scope capture requires a substantial appeals-program ramp-up, not a one-time fix.
- The prior auth and billing-error appeal success rates are observed data in the synthetic dataset, not external benchmarks. A real company's appeal success rate may differ.
- An earlier internal draft of this analysis assumed Coverage Limits had a 0% appeal success rate and excluded it from all recovery scenarios. That assumption was not checked against the underlying `appeal_outcome` data and has been corrected here (see Insight #5) -- a reminder to verify "unrecoverable" claims against actual outcomes before they become a standing recommendation.

---

## 👤 Author

**Luciano Casillas**

Senior Data Analyst & Independent Analytics Consultant

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com/in/luciano-casillas) [![GitHub](https://img.shields.io/badge/GitHub-Luciano--Casillas-lightgrey)](https://github.com/Luciano-Casillas) [![Portfolio](https://img.shields.io/badge/Portfolio-luciano--casillas.github.io-informational)](https://luciano-casillas.github.io)

<luciano.casillasjr@gmail.com>
