# README Template Implementation Prompt

Use this prompt to generate a README.md for any portfolio project following Luciano's standard.

---

## Instructions for Use

1. **Copy the prompt below** into your project folder as `README_IMPLEMENTATION.txt`
2. **Fill in the bracketed sections** with your project-specific details
3. **Run the prompt** with the filled values
4. **Verify against quality gates** (see Quality Checklist at end)
5. **Never reference the job title** in the README — frame as business problem, not skill demonstration

---

## README Generation Prompt

```
You are building a professional portfolio README following these standards:

PROJECT NAME: [claims-denial-prevention OR your-project-name]
COMPANY (FICTIONAL): [Clarity Health Plans OR company-name]
DOMAIN: [Healthcare Insurance OR domain]
TARGET METRIC: [200K claims analyzed OR your metric]

STRUCTURE TO FOLLOW:
1. Title + Badge Row
2. Overview (2-3 sentences, business context)
3. Live Dashboard (link, 7-8 feature bullets)
4. Business Problem (5 questions answered)
5. Key Findings (6-7 numbered findings with $$ impact)
6. Methodology (4 subsections: Data, SQL, Modeling, Financial Framework)
7. Technical Stack (table format)
8. File Structure (tree with one-line descriptions)
9. How to Run (Local Dev, Cloud Deployment)
10. Key Metrics (table)
11. How to Adapt (Real company, Different domain)
12. Data Dictionary (Reference)
13. Interview Talking Points (30-sec pitch, highlights, impact)
14. References
15. Footer (Author, Status, Contact)

KEY CONSTRAINTS:
- Never frame as "built to demonstrate skills for X role"
- Every finding must reference REAL numbers from project
- Live Dashboard section always after Recommendations or Key Findings
- File structure uses tree format with descriptions, not bullet list
- How to Run uses code blocks with comments
- Key Metrics table shows Value + Implication columns
- Interview section is brief (elevator pitch + 3 talking points)

SECTIONS TO CUSTOMIZE:
- [Overview]: Business problem summary (1-2 sentences max)
- [Key Findings]: 6-7 findings specific to your analysis, all with numbers
- [Methodology]: 4 subsections (Data generation, SQL analysis, Modeling, Financial framework)
- [File Structure]: Tree view matching actual repo structure
- [Key Metrics]: Table with values from your actual project
- [Interview Talking Points]: 30-second pitch + 2-3 technical highlights + 2 business impact points
- [Author/Last Updated]: Your name and current date
- [GitHub Repository URL]: Replace placeholder with real repo URL

OUTPUT FORMAT:
- Markdown with proper heading hierarchy (# for main title, ## for sections)
- Badges in first line (Python version, Framework, License)
- Links to Live Dashboard (if deployed)
- Code blocks for terminal commands with comments
- Tables for Technical Stack, Key Metrics, Scenario Comparison
- File tree ASCII for directory structure
- No em dashes; use " -- " or split into sentences
- No "leveraging," "delving," "it is worth noting" filler language
```

---

## Pre-Writing Checklist

Before generating README, gather these details:

### Project Context
- [ ] Fictional company name (non-existent, cleared via Google)
- [ ] Domain (healthcare, finance, e-commerce, telecom)
- [ ] Business problem in 1-2 sentences
- [ ] Dataset size and composition
- [ ] Analysis timeline (how long did Phase 1-2 take)

### Key Findings
- [ ] 6-7 findings with specific numbers ($, %, counts)
- [ ] Biggest opportunity quantified ($M, basis for claim)
- [ ] Surprising insight (something that contradicts intuition)
- [ ] Unrecoverable segment (if applicable)

### Model Metrics
- [ ] Primary metric (AUC, RMSE, Accuracy, Lift)
- [ ] Top features (feature name + importance score)
- [ ] Baseline vs top-decile performance
- [ ] Decision on whether to report honest or inflated metrics (always honest)

### Dashboard
- [ ] 6-8 tab names and one-sentence descriptions
- [ ] Key filters available
- [ ] Chart types used (Plotly: bar, pie, scatter, line)

### File Structure
- [ ] Actual directory tree from `tree` or `ls -lR`
- [ ] One-line description for each folder/file
- [ ] Data file sizes
- [ ] Artifact locations (models, metrics JSON)

### Deployment
- [ ] Streamlit Community Cloud URL (if deployed)
- [ ] Local setup requirements (Python version, dependencies)
- [ ] Cloud deployment steps (GitHub → Streamlit Cloud)

---

## Quality Checklist

Once README is generated, verify:

**Content Quality**
- [ ] No job title mentioned ("built for Senior Analyst role") -- only business problem
- [ ] Every finding has a number ($, %, count, or metric)
- [ ] Interview section includes 30-second pitch without jargon
- [ ] Key Metrics table has Value + Implication columns
- [ ] File structure matches actual repo (run `tree` to check)

**Writing Quality**
- [ ] No em dashes (use " -- " or split sentence)
- [ ] No filler: "leveraging," "delving," "it is worth noting," "exciting"
- [ ] Heading hierarchy consistent (# → ## → ###, no skipping)
- [ ] Code blocks have comments and proper syntax highlighting
- [ ] All links work (test before push)

**Technical Quality**
- [ ] Terminal commands are copy-paste ready
- [ ] Paths are relative or environment-agnostic
- [ ] Requirements.txt is referenced correctly
- [ ] Data paths match actual file structure
- [ ] Model training/loading code is documented

**Portfolio Quality**
- [ ] Opens with business context, not technical jargon
- [ ] Dashboard section shows real value (not just "it's interactive")
- [ ] Financial impact quantified (recovery $, ROI, time savings)
- [ ] Cross-industry portability mentioned (if applicable)
- [ ] Metrics prove the analysis is real (not made up)

---

## Example Sections (Copy/Modify)

### Key Findings Template
```markdown
**N. [Finding Title] ($Impact)**
- [Main observation with number]
- [Supporting detail]
- [Business implication]
```

Example:
```markdown
**1. Prior Authorization Delays Dominate ($10.4M, 35% of denials)**
- 2,802 denials traced to authorization processing delays
- 54% appeal success rate -- most are recoverable
- Single largest lever for recovery
```

### Interview Talking Points Template
```markdown
**Problem Statement (30 seconds):**
"[1-2 sentences on what you analyzed]. Found that [biggest finding with number]. Built [model type] with [metric] that [real capability]. Dashboard shows [3-4 features]. Estimated [financial opportunity]."

**Technical Highlights:**
- [SQL/modeling insight #1]
- [Surprising finding #2]
- [Methodology innovation #3]

**Business Impact:**
- [Financial savings or opportunity]
- [Process improvement]
- [Preventable cost identified]
```

### File Structure Template
```
project-name/
├── README.md                          (Documentation and project overview)
├── requirements.txt                   (Python dependencies: streamlit, plotly, xgboost)
├── app.py                             (Streamlit dashboard -- main entry point)
│
├── data/
│   ├── [primary_data].csv             ([N]K rows -- [business entity])
│   ├── [secondary_data].csv           ([N]K rows -- [business entity])
│   └── data_dictionary.md             (Column definitions and leakage prevention)
│
├── sql/
│   └── [project]_analysis.sql         ([N]-query discovery and root cause analysis)
│
├── scripts/
│   ├── 01_generate_data.py            (Synthetic data generation)
│   ├── 02_analyze_data.py             (SQL execution and summary statistics)
│   └── 03_train_model.py              (Model training and evaluation)
│
├── models/
│   ├── [model_name].pkl               (Trained model artifact)
│   └── [metrics_name].json            (Decile analysis, feature importance, confusion matrix)
│
└── docs/
    ├── PROJECT_OVERVIEW.md            (Full methodology, findings, deployment)
    └── INTERVIEW_PREP.md              (Interview guide: technical deep-dives, behavioral Q&As)
```

---

## Common README Mistakes (Avoid These)

1. **Framing as skill demonstration:**
   - ❌ "This project demonstrates my ability to build XGBoost models and Streamlit dashboards."
   - ✅ "Analyzed 200K claims to identify $10.4M in recovery opportunities from prior auth delays."

2. **Vague findings:**
   - ❌ "The model identified important patterns in denial rates."
   - ✅ "Prior auth delays drive $10.4M annually (35% of all denials) with 54% appeal success rate."

3. **Missing business impact:**
   - ❌ "Built a predictive model with 0.51 AUC."
   - ✅ "Model achieves 1.18x lift in top decile, enabling prioritized high-touch review of 8K claims."

4. **Incomplete file structure:**
   - ❌ "See files for details" or "scripts" folder with no description
   - ✅ Tree format with one-line purpose for every folder

5. **No deployment instructions:**
   - ❌ "Run streamlit run app.py"
   - ✅ "Step-by-step commands, path setup, cloud deployment with screenshots if needed"

---

## Deployment Checklist

Before pushing to GitHub:

- [ ] README.md is committed
- [ ] All links in README are tested (especially live dashboard)
- [ ] File paths in README match actual repo structure
- [ ] Code blocks use proper syntax highlighting (```python, ```bash, etc.)
- [ ] Badges in header are accurate (Python version, status, license)
- [ ] Author name and date are current
- [ ] No sensitive data (API keys, passwords, real company names) in README
- [ ] GitHub repository description (60 chars) matches README title

---

## Post-README Tasks

1. **Create GitHub repository** with description from README first paragraph
2. **Add topics/labels:** `data-analytics`, `python`, `portfolio`, `streamlit`, `xgboost`, `[domain]`
3. **Set up GitHub Pages** (optional) to link to live dashboard
4. **Pin README** in repo to show first on landing page
5. **Share on LinkedIn** with a 2-3 sentence summary and link to repo
6. **Update portfolio site** (luciano-casillas.github.io) with project card

---

**Template Version:** 1.0  
**Last Updated:** August 2026  
**Author:** Luciano Casillas
