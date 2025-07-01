import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from lightgbm import LGBMClassifier
import warnings
warnings.filterwarnings('ignore')

# Load Dataset
df = pd.read_csv("Synthetic_Payment_Recommendation_10K_Noise.csv")

# Feature & Target Setup
features = [
    "Transaction_Amount", "Category", "Preferred_Payment_Method",
    "Last_Used_Credit_Card_Days", "Last_Used_UPI_Days", "UPI_Usage_Count",
    "Card_Usage_Count", "Wallet_Usage_Count", "EMI_Usage_Count",
    "Bank_Offer_Active", "Bank_Name", "Is_High_Value",
    "Failure_Rate_Last10", "Time_of_Day"
]
target = "Recommended_Payment_Method"

X = df[features]
y = df[target]

#  Label & One-Hot Encoding
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

categorical_features = ["Category", "Preferred_Payment_Method", "Bank_Name", "Time_of_Day"]
encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')

X_encoded = pd.DataFrame(encoder.fit_transform(X[categorical_features]),
                         columns=encoder.get_feature_names_out(categorical_features))

X_numeric = X.drop(columns=categorical_features).reset_index(drop=True)
X_final = pd.concat([X_numeric, X_encoded], axis=1)

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X_final, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

#  LightGBM Training with Hyperparameter Tuning
param_grid = {
    'num_leaves': [31, 64],
    'learning_rate': [0.05, 0.1],
    'feature_fraction': [0.7, 0.9]
}

cv = StratifiedKFold(n_splits=5)
model = LGBMClassifier(objective='multiclass', n_estimators=500, random_state=42)

grid = GridSearchCV(model, param_grid, cv=cv, scoring='accuracy', n_jobs=-1)
grid.fit(X_train, y_train)

best_model = grid.best_estimator_

#  Evaluation
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)
confidence_scores = np.max(y_proba, axis=1)

print(f"✅ Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("📊 Classification Report:\n", classification_report(y_test, y_pred, target_names=label_encoder.classes_))
print("🧾 Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

#SHAP Explainability (Safe CPU-based)
explainer = shap.TreeExplainer(best_model)
shap_values = explainer.shap_values(X_test)

# Plot & Save
shap.summary_plot(shap_values, X_test)
plt.tight_layout()
plt.savefig("shap_summary_plot.png")

#  Save Model & Encoders
joblib.dump(best_model, "recommender_model.pkl")
joblib.dump(encoder, "ohe_encoder.pkl")
joblib.dump(label_encoder, "label_encoder.pkl")

print("✅ Model and encoders saved.")