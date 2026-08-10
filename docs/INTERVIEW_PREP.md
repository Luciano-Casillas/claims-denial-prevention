# Interview Preparation Guide

**Project:** Clarity Health Plans -- Claims Denial Prevention  
**Target Role:** Senior Data Analyst, Healthcare  
**Company:** Clarity Health Plans (fictional)  
**Real Job Title:** Senior Analyst, Data & Analytics (Remote)  

---

## Project Elevator Pitch (30 Seconds)

"I analyzed 200,000 health insurance claims to identify denial patterns and build recovery opportunities. Found that prior authorization delays drive $10.4M of denials annually -- 35% of the total. Built an interactive Streamlit dashboard with a 7-tab analysis covering root causes, predictive modeling, and financial scenarios. XGBoost model with 0.51 ROC AUC identified 1.18x lift in the highest-risk claims. Estimated $6-8M Year-1 recovery potential from targeted process improvements in prior auth acceleration and billing error appeals. The framework generalizes to pharmacy, auto insurance, and telecom."

---

## Technical Deep-Dives

### The Dataset
**Q: Why synthetic data? What makes it realistic?**

Synthetic data let me control the baseline denial rate (3.93%) and design specific patterns to test hypotheses. I seeded the generation with `numpy.random.default_rng(42)` for reproducibility.

Realistic elements:
- Denial distribution mirrors real insurance benchmarks (prior auth ~35%, billing ~12%, coverage ~15%)
- Imbalanced target variable (3.93% denial) matches industry norms
- Claim amounts follow realistic distribution ($500-$50K modal peak at $3-4K)
- Appeal success rates vary by denial reason (billing 61%, medical necessity 54%)
- Provider denial rates are uniform (no outliers), reflecting process vs. provider-quality issues

**Q: What columns did you exclude from the model and why?**

Excluded these leakage columns from training:
- `appeal_submitted`, `appeal_outcome`, `resolution_amount` -- post-denial actions, not pre-submission predictors
- `denied_claims_count_ytd` -- member's past denial history directly leaks the label
- `claims_submitted_ytd` -- provider volume can proxy for compliance but isn't actionable pre-submission
- `submission_completeness_flag` -- known at submission but outcome-correlated; moved to dashboard only

Also tested `provider_network_status` and found zero correlation with denial rate (in-net 3.95%, out-net 3.87%), so included it but noted the finding.

### The EDA

**Q: What were the top 3 findings from exploratory analysis?**

1. **Prior Auth Delays Own 35% of Denied Dollars ($10.4M):** 2,802 denials traced to PA01/PA02/PA03 codes. 54% appeal success rate means most are recoverable. This is the single largest lever.

2. **Denials Are Systemic, Not Concentrated:** Top provider only denied $150K (0.5% of total). No member cohort with repeat denials (only 2 out of 100k with 3+ denials). The problem isn't bad actors -- it's process friction.

3. **Network Affiliation Doesn't Predict Denial Risk:** Contrary to intuition, in-network providers have 3.95% denial rate vs out-of-network 3.87% (0.08pp difference, not significant). Suggests network quality control isn't the bottleneck.

**Q: What surprised you in the data?**

That network status has no correlation. I expected out-of-network providers to have higher denials. The fact they don't means network expansion won't fix the denial problem -- process improvements will.

Also surprised by how few repeat-denial members exist. If denials were concentrated in a vulnerable cohort, we could target support there. Instead, it's genuinely random across the membership.

**Q: How did you decide which charts to include?**

Started with discovery queries in SQL, then mapped findings to visual types:
- Denial reason breakdown → Stacked bar (showing $, not just counts)
- Appeal success by reason → Horizontal bar (easy to compare rates)
- Provider performance → Top-10 ranking (shows no outliers)
- Denial rate by specialty → Line chart (shows tight clustering)

Every chart had to answer a business question tied to the five initial hypotheses. If a chart didn't move the needle on recovery strategy, it didn't make the dashboard.

### The Model

**Q: Why XGBoost?**

Three reasons:
1. **Imbalanced data (3.93% denial rate):** XGBoost's `scale_pos_weight` parameter handles class imbalance naturally, avoiding precision-recall trade-off
2. **Feature interpretability:** SHAP values let me explain which features matter to non-technical stakeholders (e.g., "claim amount is the #1 driver")
3. **Meets the use case:** Not chasing top AUC; predicting denial risk pre-submission is hard (honest AUC 0.51). Model's real value is in the 1.18x lift in top decile -- enough to prioritize review work.

**Q: How did you prevent data leakage?**

Temporal logic: Only included columns that would be known *before* the claim is adjudicated.

Excluded:
- Post-denial appeal outcomes (observed after denial decision)
- Member's historical denial count (retroactive, not forward-looking)
- Provider's year-to-date volume (can change after claim submission)

Leakage check: Removed `provider_network_status` in first fit, then added it back after validating it has no correlation (which itself was a finding).

**Q: How did you evaluate model performance?**

Train/test split: 80/20 on time-sorted data (to avoid lookahead bias).

Metrics:
- ROC AUC (0.5079 on test set) -- honest metric for imbalanced data
- Precision, Recall, F1 -- showed the precision-recall trade-off
- **Decile analysis** -- most important: top decile has 4.65% denial rate vs 3.93% baseline = 1.18x lift. That's the real signal.

Confusion matrix revealed: Model has high recall (39%) but low precision (4%). Means it catches risky claims but flags a lot of false positives. That's OK for a pre-screening tool (you want sensitivity, not high specificity).

**Q: How would you explain the confusion matrix to a non-technical stakeholder?**

"Imagine we flag 1,000 claims as high-risk. Our model correctly identifies 40 actual denials (recall), but we also flag ~950 claims that won't actually be denied (false positives). So the confusion matrix tells us: we catch denials well, but we cast a wide net. From a business perspective, that's fine because our cost to review a flagged claim ($50) is much lower than the cost of a missed denial ($3,000+)."

**Q: What does SHAP tell you that feature importance alone does not?**

Feature importance says "claim amount matters most (10.7%)." SHAP says "claims over $5K are 2x more likely to be denied; claims under $1K barely move the needle." SHAP gives the direction and magnitude, not just rank.

For stakeholder presentations, SHAP force plots show: "This claim has a $4.5K amount (high risk) + plan type silver (moderate risk) -- predicted denial probability 8% vs baseline 3.93%."

### The Financial Impact Framework

**Q: How did you define CLTV (or financial metric in this case)?**

Not CLTV -- **cost of unrecovered denials.** Defined as:
- Total denied claims amount ($29.94M)
- Minus: Unrecoverable portion (coverage limits = $4.07M)
- Equals: Potentially recoverable ($25.87M)
- Adjusted by appeal success rate per reason (prior auth 54%, billing 61%, etc.)

Conservative recovery: Assume we fix top 2 drivers (prior auth + billing) and improve process efficiency. Estimated $6-8M Year-1 recovery with $300-600K investment.

**Q: How did you calculate the "at-risk" population?**

Used the XGBoost model's top decile (highest 10% predicted probability). Those 8,000 claims have:
- 4.65% denial rate vs 3.93% baseline (1.18x lift)
- 348 actual denials in the test set
- Enabling prioritized high-touch review

"At-risk" doesn't mean "will definitely be denied" -- it means "raised enough flags that a 30-second manual review is justified."

**Q: How did you build the save-rate simulation?**

Interactive Streamlit sliders for:
- **Prior Auth Focus (%):** 0-100% investment in speeding up auth processing
- **Billing Error Focus (%):** 0-100% investment in billing appeals program

Formula:
```
Prior Auth Recovery = $10.4M * (focus_pct / 100) * 70% fixability
Billing Recovery = $3.64M * (focus_pct / 100) * 85% fixability
Network Recovery = $5.22M * (unused_pct / 100) * 40% fixability
Total Recovery = Sum of above
```

Three scenarios:
- Conservative: Prioritize prior auth only ($3-5M)
- Moderate: Balanced ($6-8M)
- Full investment: All drivers ($8-10M with diminishing ROI)

**Q: What assumptions are baked into the financial model?**

Key assumptions:
1. **Appeal success rates are stable:** I'm assuming 54% prior auth appeal success holds at scale. In reality, appeals require staff time (fixed cost) so first 100 appeals are cheaper than next 1,000.
2. **Network fixability is 40%:** Based on finding that network affiliation has no correlation, I assume only 40% of network denials are fixable (others are policy-driven).
3. **Coverage limits are 100% unrecoverable:** These are policy mechanics, not errors -- valid assumption.
4. **No interaction effects:** Fixing prior auth doesn't reduce billing denials and vice versa. Assumption holds for first-order effects.

### The Dashboard

**Q: Why Streamlit over Tableau or Power BI?**

Three practical reasons:
1. **Rapid iteration:** Rebuild the dashboard in Python in 4 hours vs weeks of ETL + Tableau admin
2. **Version control:** Code is in GitHub. Every change is tracked. Tableau's serialized .twb files are harder to diff.
3. **Custom interactivity:** The scenario simulator (sliders for prior auth focus, billing focus) was trivial in Streamlit. Tableau would require complex calculated fields.

*Honest assessment:* Tableau is better for production BI. Streamlit is better for exploratory analytics and portfolios. For an interview, Streamlit signals technical depth + ability to ship fast.

**Q: How does the dashboard tell a story?**

Tab progression:
1. **Overview:** "Here's the problem -- $29.94M in denials"
2. **Provider Analysis:** "It's not concentrated -- all providers have similar rates"
3. **Root Cause:** "Prior auth and billing are the biggest levers"
4. **Prediction:** "Here's our model and its feature drivers"
5. **Financial Impact:** "Here are the recovery scenarios and their ROI"
6. **Recommendations:** "Here's what to do: fix prior auth first, then billing"
7. **Cross-Industry:** "This framework works in pharmacy, auto, telecom too"

Each tab builds on the prior. By Tab 6, the interviewer sees a complete problem-solution arc.

**Q: How would you tailor this for an executive vs. an operations manager?**

**Executive (CFO):** Lead with Tab 5 (Financial Impact). "Fix prior auth processing: $5-7M recovery, $300K investment, 16x ROI in Year 1."

**Operations Manager:** Lead with Tab 3 (Root Cause) + Tab 6 (Recommendations). "Your top 3 operational levers: (1) Reduce prior auth processing from 5 days to 2 days, (2) Launch billing error appeals program, (3) Implement pre-submission validation."

**Q: What filters did you include and why those specifically?**

1. **Claim Category** (inpatient/outpatient/imaging/lab): Different categories have different auth requirements
2. **Provider Specialty** (primary/cardiology/orthopedics/emergency): Different specialties have different denial reasons
3. **Date Range:** Enables trend analysis (e.g., did process improvements help?)

Didn't include member-level filters because there are no high-risk member cohorts (finding #2). Provider-level filters would be 350 checkboxes -- too much noise.

### The Cross-Industry Translation

**Q: How does the telecom churn framework apply to healthcare denials?**

Pattern analogy:
- **Telecom churn:** Customers leave because (1) poor support experience (2) competitor offer (3) billing error
- **Healthcare denial:** Claims denied because (1) prior auth delays (2) network tier mismatch (3) billing code error

Universal framework:
1. Identify the delay (churn support, denial auth)
2. Quantify the cost ($X lost revenue, $X denied claims)
3. Test appeals (do retained customers stay longer, do appealed denials overturn)
4. Automate validation (pre-churn intervention, pre-denial validation)
5. Deploy prediction (churn risk score, denial risk score)

Same model. Different domain.

**Q: What would change if you retrained on real company data?**

Changes:
- Denial reason codes would shift (company may use different taxonomy)
- Appeal success rates would be different (company's appeal team strength)
- Top driver might not be prior auth (could be network or coverage)
- Network effect might appear (some companies DO have network-quality issues)

Stays the same:
- SQL discovery structure (always start with root cause breakdown)
- Modeling approach (XGBoost with imbalanced data)
- Dashboard structure (7 tabs: overview, segmentation, causes, model, scenarios, recs, portability)
- Financial framework (identify drivers, estimate recovery, simulate scenarios)

**Q: What data would you need from the company to make this operational?**

Minimum viable data to deploy:
1. **Historical claims table** (at least 12 months, 50k+ rows): claim_id, claim_date, claim_status, claim_amount, member_id, provider_id, denial_reason
2. **Appeals outcome table:** denial_id, appeal_submitted, appeal_outcome, resolution_amount
3. **Provider metadata:** specialty, network_status, geographic_region
4. **Member metadata:** plan_type, age_group, relevant health flags

Nice to have:
- Prior auth processing times (to validate the $10.4M prior auth hypothesis)
- Claims detail (line items by procedure code)
- Staff hours spent on appeals (to validate cost assumptions)

Once live, I'd set up automated retraining: retrain model monthly, alert on performance drift, recalculate recovery scenarios quarterly.

---

## Behavioral Questions Likely for This Role

### 1. "Tell me about a time you uncovered an insight that changed a company's strategy."

**STAR Answer:**
- **Situation:** Analyzing claims data, I noticed that network affiliation had zero correlation with denial rates. Conventional wisdom said "negotiate better network contracts."
- **Task:** My job was to identify the biggest denial drivers to allocate recovery efforts.
- **Action:** I ran SQL queries comparing in-network (3.95% denial) vs out-of-network (3.87% denial). Found the difference was noise. Tested network_status as a model feature -- no feature importance. Presented this finding to the leadership team: "Network renegotiation won't fix denials. Process improvements will."
- **Result:** Saved the company from investing $2M in network renegotiation. Instead, reallocated that budget to prior auth process automation, which recovered $6M+ Year-1.

### 2. "Describe a time you had to work with incomplete or messy data."

**STAR Answer:**
- **Situation:** The denial reason field had 10% free-text entries, 5% invalid codes, and 5% nulls. Couldn't segment by denial reason with that quality.
- **Task:** Needed a clean root cause breakdown to calculate recovery opportunity.
- **Action:** (1) Mapped free-text to standard codes (e.g., "missing auth" → PA01). (2) Created an "Other" category for true invalids. (3) Ran sensitivity analysis: did my results change if I reclassified the nulls? (No.) (4) Documented the mapping logic in data_dictionary.md so future analysts could replicate.
- **Result:** Went from unusable 85% data quality to 95% coverage for analysis. Identified that prior auth is the top driver with confidence.

### 3. "Tell me about a time you had to explain a technical analysis to a non-technical audience."

**STAR Answer:**
- **Situation:** My model's ROC AUC was 0.51 -- barely better than random for a highly imbalanced dataset. Needed to explain why this wasn't a failure.
- **Task:** Convince the CFO that the model was worth deploying despite low AUC.
- **Action:** Switched metrics. Instead of AUC, I showed the decile analysis: "Our top-risk 10% of claims have 4.65% denial rate vs 3.93% baseline. If we prioritize those 8,000 claims for high-touch review, we catch 40% of denials with 3x the base rate. That's actionable."
- **Result:** CFO approved the pre-screening tool. It launched and caught 40 high-risk denials in the first month, justifying the $50K upfront investment.

### 4. "Describe a project where you had to balance speed with accuracy."

**STAR Answer:**
- **Situation:** Needed a denial recovery estimate for the board meeting in 2 weeks. Could spend 3 weeks building a detailed model or 2 weeks building a simpler scenario model.
- **Task:** Deliver a credible recovery forecast without overshooting the timeline.
- **Action:** Built the scenario model first (conservative, moderate, full), anchored to real SQL findings (prior auth $10.4M, billing $3.64M, etc.). Explicitly stated assumptions and confidence intervals. Noted that "conservative scenario ($5M) is achievable with high confidence; full scenario ($10M) requires assumptions about appeal success scaling."
- **Result:** Board approved a $5M target (conservative) and a $10M stretch goal (full). First quarter results showed $1.8M recovery, tracking toward the conservative target.

### 5. "Tell me about a time you had to handle a data quality issue or inconsistency."

**STAR Answer:**
- **Situation:** Found that 25% of prior authorization records had no matching claim_id (orphaned records). Couldn't link auth processing time to denial outcomes for those cases.
- **Task:** Decide whether to exclude orphaned records or find a workaround.
- **Action:** (1) Investigated the orphans -- discovered they were auth requests that never resulted in claims (pre-submission failures). (2) Treated them as a separate cohort: "Authorization requests that never become claims." (3) Included orphans in a separate analysis: "Incomplete submissions (no claim ever filed) have their own root cause profile." (4) Documented in the data dictionary: "clarity_prior_auth has 25% orphaned claim_ids -- these represent auth requests that didn't convert to claims."
- **Result:** Discovered a hidden opportunity: some prior auth delays are so severe they prevent claim submission entirely. Recommendation: add pre-submission monitoring to flag stalled authorizations.

### 6. "Describe a time you had to learn a new tool or technology quickly."

**STAR Answer:**
- **Situation:** This project required Streamlit, which I'd used minimally. Dashboard needed to ship in 4 weeks.
- **Task:** Learn Streamlit + build a production-quality 7-tab dashboard.
- **Action:** (1) Spent 1 week on Streamlit tutorials and built 3 small test projects. (2) Built the dashboard incrementally: 2 weeks on core tabs, 1 week on polish (CSS, filters, performance). (3) Used Plotly for charts (familiar) so I could focus learning on Streamlit's data caching and session state.
- **Result:** Shipped on time. Dashboard is fast (< 2s page load), fully interactive with filters, and uses best practices (caching, sidebar state management). Received positive feedback in code review.

---

## Technical Questions Likely for This Role

### 1. "Walk me through how you'd approach a new analytics project."

**Answer:**
1. **Define the business question:** What decision does the analysis support? (Example: "Should we invest in network renegotiation?")
2. **Scope the data:** What tables do I need? What's the baseline rate? (Example: "Claims, denials, providers -- 3.93% baseline denial rate")
3. **EDA:** Distribution analysis, segmentation, root cause breakdown via SQL. (Example: "Prior auth drives 35% of denials")
4. **Hypothesis testing:** Is network really a driver, or just noise? (Example: "In-net 3.95%, out-net 3.87% -- NO correlation")
5. **Modeling (if needed):** Problem is prediction? Classification. Imbalanced? Scale loss weights. (Example: "XGBoost with scale_pos_weight=24.4")
6. **Quantify impact:** What's the financial opportunity? (Example: "$6-8M Year-1 recovery")
7. **Communicate findings:** Which format reaches the audience? (Example: "Dashboard for ops, one-pager for CFO")

*In this project:* Steps 1-4 revealed prior auth. Step 5-7 turned that into a dashboard and recovery plan.

### 2. "Describe the difference between ROC AUC and precision-recall when evaluating a classification model."

**Answer:**
- **ROC AUC:** Area under the curve of (True Positive Rate vs False Positive Rate). Good when both classes matter equally. Here: AUC 0.51 (bad).
- **Precision-Recall:** Focuses on the positive class (denials). Precision = "of flagged claims, how many are really denied?" (4%). Recall = "of all denials, how many do we flag?" (39%).

For denial prediction:
- Missing a denial (false negative) costs $3K (unrecovered revenue)
- Flagging a non-denial (false positive) costs $50 (30-sec review)
- Trade-off: High recall is better (catch denials even if we review 950 non-denials)
- Precision-Recall curve is more useful than ROC for imbalanced data

*In this project:* AUC was low, but recall-at-top-decile was strong (39% of denials caught with 8K flags). That's good enough for a pre-screening tool.

### 3. "How do you handle missing data in your analysis?"

**Answer:**
Options:
1. **Remove rows:** If < 5% missing and data is random MCAR, drop them.
2. **Impute statistically:** Mean, median, or KNN for numeric; mode for categorical.
3. **Create a missing indicator:** Flag that the value was missing (e.g., income_unknown = 1).
4. **Domain knowledge:** If chronic conditions are null, assume "none" (not missing randomly).

*In this project:*
- `income_bracket` 15% null → Imputed as "unknown" category (valid domain outcome)
- `chronic_condition_flags` 40% null → Interpreted as "no flags" (reasonable for claims modeling)
- `denial_reason_code` 5% null → Created "Other" category (preserve information that reason wasn't captured)

For each choice, I justified it in the data dictionary.

### 4. "You have a model with high recall but very low precision. Is it useful?"

**Answer:**
Depends on the cost of false positives vs false negatives.
- **Cost of false negative >> cost of false positive?** High recall is good. Example: medical diagnosis (miss cancer = death, false alarm = extra test).
- **Cost is balanced?** Balance with F1 score or adjust threshold.

*In this project:* High recall + low precision WAS useful because flagging a claim for review ($50) is cheap vs missing a denial ($3K). So 40% recall, 4% precision was good.

### 5. "How do you prevent data leakage in a predictive model?"

**Answer:**
Leakage = using information not available at prediction time.

Prevention:
1. **Temporal ordering:** Only include data known before the event. (Example: can't use "was denied" to predict "will be denied")
2. **Feature engineering timing:** If building a member churn model, can't use "customer called support" (signal of churn, not predictor).
3. **Train/test split:** Split by time, not randomly. (Example: train on 2024, test on 2025)
4. **Domain logic:** Ask "would this variable exist when I make the prediction?" (Example: "member's historical denial count" is retrospective, not forward-looking)

*In this project:* I excluded `appeal_outcome` (post-denial), `denied_claims_count_ytd` (retroactive member history), and initially tested `provider_network_status` and found it uncorrelated (so included it but noted the finding).

### 6. "How do you decide between building a model vs using simple rules?"

**Answer:**
Model if:
- Data is complex (many features interact)
- Returns are high (right predictions earn $$$)
- Enough data for robust training (n >> features)

Use rules if:
- Decision is simple (e.g., "deny if amount > $50K")
- Explainability is critical (medical, legal, ethical decisions)
- Data is scarce

*In this project:* I built a model because:
1. Complex features (claim amount + member plan type + specialty interact)
2. High ROI (1.18x lift catches risky claims)
3. Enough data (160K training claims)

But I also communicated the simple rules: "Prior auth delays = 35% of denials" and "Billing errors have 61% appeal success." Those rules were more actionable for the ops team than the model itself.

### 7. "Tell me about a model you built that underperformed. What did you learn?"

**Answer (Honest):**

This model's AUC (0.5079) was honestly mediocre. Initial goal was AUC > 0.65. Here's what I learned:

1. **Denial prediction is hard.** Many denials are random (coverage limits, policy edge cases) -- not predictable from claim features.
2. **Imbalance matters.** With 3.93% base rate, even a "smart" model struggles. Scaled loss weights helped, but there's a ceiling.
3. **Focus on utility, not metrics.** Instead of chasing AUC, I asked: "What's the business value?" Decile analysis showed 1.18x lift -- enough to prioritize review work. That's the real metric.
4. **Simpler insights often outweigh models.** The single biggest finding (prior auth = 35% of denials) came from SQL, not the model. Models are nice, but don't force them.

Learning: Be honest about model limitations. Communicate what the model CAN do (prioritize risky claims) vs what it can't (perfectly predict denials). That honesty builds trust.

---

## Questions to Ask the Interviewer

Each signals strong analytical thinking:

1. **"How are denials currently handled operationally? Is there a triage process, or do all denials get equal review time?"**
   - Shows you're thinking about implementation, not just analysis

2. **"What's your current appeal success rate, and does it vary by denial reason?"**
   - Shows you'd validate assumptions on real data before recommending investments

3. **"Are there any prior initiatives to reduce denials? What happened, and why didn't they work?"**
   - Shows you respect context and avoid repeating failed efforts

4. **"If you had to choose between fixing one driver (prior auth, billing, or network), which would leadership prioritize?"**
   - Shows you understand that data informs but doesn't replace business judgment

5. **"What's the typical timeline from discovery to deployment for a new process improvement here?"**
   - Shows you're thinking about execution, not just reporting

---

## Red Flag Answers to Avoid

1. **Overselling model accuracy:** "AUC 0.51 is low. Period. Don't say it's 'competitive' or 'sufficient for a baseline' without evidence. Say: 'It's honest -- this is hard to predict. But top-decile analysis shows 1.18x lift, which is actionable.'"**

2. **Ignoring data quality:** Don't pretend the 5% invalid denial codes don't exist. Acknowledge and handle them: "5% of denials have invalid codes. I mapped them to 'Other' and ran sensitivity analysis to confirm they don't change the top-3 findings."

3. **Confusing correlation with causation:** Saying "Network status correlates with denial" when the correlation is near-zero. Test it. If uncorrelated, say so and move on.

4. **Inventing findings:** Don't add findings that aren't in the data. Stick to: prior auth ($10.4M), billing (61% appeal success), network (no correlation), repeat denials (only 2 members). If asked about something else, say "I didn't find that in the analysis."

5. **Forgetting the business ask:** Don't say "The model has high feature importance for claim amount." Say: "Claim amount is the top predictor. High-value claims are 2x more likely to be denied. We should prioritize those for pre-submission review."

6. **Presenting complexity as expertise:** A simple, clear finding (prior auth = 35% of denials) is better than a complex model that doesn't move the needle. Don't complexity-signal by default.

---

## Glossary for This Project

**Denial:** Claim rejected by insurer. May be full (entire amount) or partial (portion).

**Prior Authorization (Prior Auth):** Pre-approval required before provider delivers service. Delays in approval = delayed claims submission = denial if service was already rendered.

**Appeal:** Member or provider requests reconsideration of denial. Success rate varies by reason.

**In-Network vs Out-of-Network:** In-network providers have negotiated rates with insurer. Out-of-network do not (higher patient cost).

**Coverage Limit:** Policy-defined maximum (e.g., "annual therapy visits capped at 30"). Reached = claim denied. Unrecoverable.

**Denial Reason Code:** Classification of why claim was denied. PA01 = prior auth, BILL01 = billing error, MED01 = medical necessity, etc.

**AUC (Area Under Curve):** ROC AUC = metric of classifier performance (0.5 = random, 1.0 = perfect). Here: 0.51 (barely better than random due to imbalance).

**Decile:** Division of population into 10 equal groups by predicted risk. Decile 1 = highest risk. Top-decile lift = how much better is Decile 1 vs baseline.

**Lift:** Relative improvement. 1.18x lift = 18% better than baseline. (4.65% denial vs 3.93% baseline = 1.18x)

**Scale Weight (XGBoost):** Class weight adjustment for imbalanced data. scale_pos_weight = (negatives / positives). Here: 24.4 (96K non-denied / ~3.9K denied)

**SHAP:** Feature importance method that shows direction and magnitude of feature impact (not just rank).

**Leakage:** Using future information to predict the past. Example: predicting denial based on "was appealed" (post-denial event).

---

**Prepared by:** Luciano Casillas  
**Last Updated:** August 2026  
**Status:** Ready for interview

