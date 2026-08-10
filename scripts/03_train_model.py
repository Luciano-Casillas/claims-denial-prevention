"""
Clarity Health Plans - XGBoost Denial Risk Prediction Model
Trains gradient boosting model on historical claims to predict denial probability
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report
import xgboost as xgb
import json
import pickle

print("="*70)
print("CLARITY HEALTH PLANS - DENIAL RISK PREDICTION MODEL")
print("="*70)
print()

# Load data
print("Loading data...")
claims = pd.read_csv('../data/clarity_claims.csv')
denials = pd.read_csv('../data/clarity_denials.csv')
providers = pd.read_csv('../data/clarity_providers.csv')
members = pd.read_csv('../data/clarity_members.csv')

print(f"  Loaded {len(claims):,} claims")
print(f"  Loaded {len(denials):,} denials")
print()

# Create target variable (1 = denied, 0 = not denied)
print("Preparing training data...")
claim_ids_denied = set(denials['claim_id'].unique())
claims['is_denied'] = claims['claim_id'].isin(claim_ids_denied).astype(int)

print(f"  Target distribution: {claims['is_denied'].sum():,} denied, {(1-claims['is_denied']).sum():,} approved")
print(f"  Denial rate: {claims['is_denied'].mean()*100:.2f}%")
print()

# Feature engineering
print("Engineering features...")

# Merge provider data to get specialty, network status
claims = claims.merge(providers[['provider_id', 'specialty', 'network_status']], 
                      on='provider_id', how='left')

# Merge member data to get member characteristics
claims = claims.merge(members[['member_id', 'age_group', 'income_bracket', 'plan_type', 'chronic_condition_flags']], 
                      on='member_id', how='left')

# Create features
features_df = claims[['claim_id', 'is_denied']].copy()

# Categorical features
features_df['network_type'] = claims['network_type']
features_df['claim_category'] = claims['claim_category']
features_df['specialty'] = claims['specialty'].fillna('unknown')
features_df['network_status'] = claims['network_status'].fillna('unknown')
features_df['submission_completeness'] = claims['submission_completeness_flag']
features_df['age_group'] = claims['age_group'].fillna('unknown')
features_df['plan_type'] = claims['plan_type'].fillna('unknown')
features_df['chronic_condition'] = claims['chronic_condition_flags'].notna().astype(int)

# Binary features
features_df['prior_auth_required'] = claims['prior_auth_required'].astype(int)
features_df['has_missing_provider'] = claims['provider_id'].isna().astype(int)

# Numeric features
features_df['claim_amount'] = claims['claim_amount']

print(f"  Created {len(features_df.columns)-2} features (excluding claim_id, is_denied)")
print()

# Encode categorical variables
print("Encoding categorical features...")
le_dict = {}
categorical_cols = ['network_type', 'claim_category', 'specialty', 'network_status', 
                    'submission_completeness', 'age_group', 'plan_type']

for col in categorical_cols:
    le = LabelEncoder()
    features_df[col + '_encoded'] = le.fit_transform(features_df[col].astype(str))
    le_dict[col] = le

print(f"  Encoded {len(categorical_cols)} categorical features")
print()

# Prepare training data
X = features_df[['network_type_encoded', 'claim_category_encoded', 'specialty_encoded',
                  'network_status_encoded', 'submission_completeness_encoded', 
                  'age_group_encoded', 'plan_type_encoded', 'chronic_condition',
                  'prior_auth_required', 'has_missing_provider', 'claim_amount']].copy()

y = features_df['is_denied'].copy()

# Split data
print("Splitting data (80/20 train/test)...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"  Training set: {len(X_train):,} rows")
print(f"  Test set: {len(X_test):,} rows")
print()

# Train XGBoost model (with scale_pos_weight for imbalanced data)
print("Training XGBoost model...")
# Calculate scale_pos_weight for imbalanced data
scale_pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()

model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    objective='binary:logistic',
    random_state=42,
    eval_metric='logloss'
)

model.fit(X_train, y_train, 
          eval_set=[(X_test, y_test)],
          verbose=False)

print("  Model trained.")
print()

# Evaluate model
print("Evaluating model performance...")

# Predictions
y_pred_proba_train = model.predict_proba(X_train)[:, 1]
y_pred_proba_test = model.predict_proba(X_test)[:, 1]
y_pred_test = model.predict(X_test)

# ROC AUC
auc_train = roc_auc_score(y_train, y_pred_proba_train)
auc_test = roc_auc_score(y_test, y_pred_proba_test)

print(f"  ROC AUC (Train): {auc_train:.4f}")
print(f"  ROC AUC (Test): {auc_test:.4f}")
print()

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred_test)
tn, fp, fn, tp = cm.ravel()

print("Confusion Matrix (Test Set):")
print(f"  True Negatives:  {tn:,}")
print(f"  False Positives: {fp:,}")
print(f"  False Negatives: {fn:,}")
print(f"  True Positives:  {tp:,}")
print()

# Derived metrics
accuracy = (tp + tn) / (tp + tn + fp + fn)
precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

print("Classification Metrics:")
print(f"  Accuracy: {accuracy:.4f}")
print(f"  Precision: {precision:.4f}")
print(f"  Recall: {recall:.4f}")
print(f"  F1 Score: {f1:.4f}")
print()

# Feature importance
print("Top 10 Feature Importance:")
feature_importance = pd.DataFrame({
    'feature': ['network_type', 'claim_category', 'specialty', 'network_status',
                'submission_completeness', 'age_group', 'plan_type', 'chronic_condition',
                'prior_auth_required', 'has_missing_provider', 'claim_amount'],
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']:30s} {row['importance']:.4f}")
print()

# Decile analysis (key for dashboards)
print("Decile Analysis (Denial Rate by Risk Decile):")
features_df_test = features_df.iloc[X_test.index].copy()
features_df_test['denial_probability'] = model.predict_proba(X_test)[:, 1]
features_df_test['is_denied'] = y_test.reset_index(drop=True).values

# Assign deciles (1 = highest risk, 10 = lowest risk)
features_df_test['decile'] = pd.qcut(features_df_test['denial_probability'], 
                                     q=10, labels=False, duplicates='drop')
features_df_test['decile'] = 10 - features_df_test['decile']  # Reverse so 1 = highest risk

decile_analysis = features_df_test.groupby('decile').agg({
    'is_denied': ['count', 'sum', 'mean']
}).round(4)

decile_analysis.columns = ['claim_count', 'denial_count', 'denial_rate']
decile_analysis['denial_rate_pct'] = decile_analysis['denial_rate'] * 100

print(decile_analysis)
print()

# Calculate lift
baseline_denial_rate = y_test.mean()
print(f"Baseline denial rate: {baseline_denial_rate*100:.2f}%")
print()

# Save model and encoders
print("Saving model and preprocessing objects...")
pickle.dump(model, open('../models/denial_risk_model.pkl', 'wb'))
pickle.dump(le_dict, open('../models/label_encoders.pkl', 'wb'))

# Save model metrics to JSON
model_metrics = {
    'model_type': 'XGBoost',
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.1,
    'auc_train': float(auc_train),
    'auc_test': float(auc_test),
    'accuracy': float(accuracy),
    'precision': float(precision),
    'recall': float(recall),
    'f1': float(f1),
    'baseline_denial_rate': float(baseline_denial_rate),
    'confusion_matrix': {
        'true_negatives': int(tn),
        'false_positives': int(fp),
        'false_negatives': int(fn),
        'true_positives': int(tp)
    },
    'feature_importance': feature_importance.to_dict('records'),
    'decile_analysis': decile_analysis.to_dict('index')
}

with open('../models/model_metrics.json', 'w') as f:
    json.dump(model_metrics, f, indent=2)

print("  ✓ Model saved to models/denial_risk_model.pkl")
print("  ✓ Encoders saved to models/label_encoders.pkl")
print("  ✓ Metrics saved to models/model_metrics.json")
print()

# Calculate some key figures for dashboard
print("="*70)
print("SUMMARY FOR DASHBOARD")
print("="*70)

# Top deciles denial rate
top_10_pct = features_df_test[features_df_test['decile'] == 1]['is_denied'].mean()
print(f"Denial rate in Decile 1 (top 10% risk): {top_10_pct*100:.2f}%")
print(f"Lift vs baseline: {top_10_pct/baseline_denial_rate:.2f}x")
print()

# Recovery potential
high_risk_claims = features_df_test[features_df_test['decile'] <= 2]['is_denied'].sum()
all_claims_in_high_risk = len(features_df_test[features_df_test['decile'] <= 2])
high_risk_denial_rate = high_risk_claims / all_claims_in_high_risk

print(f"High-risk population (Deciles 1-2):")
print(f"  Claims: {all_claims_in_high_risk:,}")
print(f"  Denial rate: {high_risk_denial_rate*100:.2f}%")
print(f"  Denials caught: {high_risk_claims:,}")
print()

print("="*70)
print("MODEL TRAINING COMPLETE")
print("="*70)
