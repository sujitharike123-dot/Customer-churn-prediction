"""Customer churn prediction: SQL exploration, cleaning, modelling and retention targeting.

Usage (from the repo root):
    python src/churn_analysis.py                      # uses data/telco_churn.csv
    python src/churn_analysis.py path/to/file.csv     # explicit file

Expects the "Telco Customer Churn" CSV (IBM sample data on Kaggle).
"""
import json
import os
import sqlite3
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIG, RES, SQL = (os.path.join(ROOT, d) for d in ("figures", "results", "sql"))
sns.set_theme(style="whitegrid")

# ---------------------------------------------------------------- 1. load
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = os.path.join(ROOT, "data", "telco_churn.csv")
    if not os.path.exists(path):
        sys.exit("Missing data/telco_churn.csv - download the Telco Customer Churn CSV from Kaggle (see README).")
raw = pd.read_csv(path)
print(f"Loaded {len(raw):,} rows x {raw.shape[1]} cols from {os.path.relpath(path, ROOT)}")

# ---------------------------------------------------------------- 2. clean
df = raw.copy()
n_start = len(df)
dupes = int(df.duplicated(subset="customerID").sum())
df = df.drop_duplicates(subset="customerID")
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")  # blanks -> NaN
blank_total = int(df["TotalCharges"].isna().sum())
df["TotalCharges"] = df["TotalCharges"].fillna(0)  # these are tenure-0 customers, nothing billed yet
df["Churn"] = (df["Churn"] == "Yes").astype(int)
churn_rate = float(df["Churn"].mean())
print(f"Cleaning: {dupes} duplicate IDs dropped, {blank_total} blank TotalCharges filled with 0")

# ---------------------------------------------------------------- 3. SQL exploration (SQLite)
con = sqlite3.connect(":memory:")
df.to_sql("customers", con, index=False)
with open(os.path.join(SQL, "churn_queries.sql")) as f:
    blocks = [b.strip() for b in f.read().split("-- QUERY:")[1:] if b.strip()]  # [0] is the file header
sql_out = {}
for b in blocks:
    title, _, query = b.partition("\n")
    sql_out[title.strip()] = pd.read_sql_query(query, con)
    print(f"\n[SQL] {title.strip()}\n{sql_out[title.strip()].head(8).to_string(index=False)}")
with open(os.path.join(RES, "sql_results.md"), "w") as f:
    for title, res in sql_out.items():
        f.write(f"### {title}\n\n{res.to_markdown(index=False)}\n\n")

# ---------------------------------------------------------------- 4. EDA figures
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
for a, col in zip(ax, ["Contract", "InternetService", "PaymentMethod"]):
    rate = df.groupby(col)["Churn"].mean().sort_values(ascending=False) * 100
    sns.barplot(x=rate.values, y=rate.index, ax=a, color="#2b6cb0")
    a.set_title(f"Churn rate by {col}"); a.set_xlabel("Churn rate (%)"); a.set_ylabel("")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "churn_by_segment.png"), dpi=130); plt.close()

plt.figure(figsize=(7, 4))
sns.histplot(data=df, x="tenure", hue=df["Churn"].map({0: "Stayed", 1: "Churned"}), bins=36, multiple="layer", alpha=0.55)
plt.title("Tenure distribution: churned vs stayed"); plt.xlabel("Tenure (months)")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "tenure_distribution.png"), dpi=130); plt.close()

# ---------------------------------------------------------------- 5. model
X = df.drop(columns=["customerID", "Churn"])
y = df["Churn"]
num_cols = ["tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen"]
cat_cols = [c for c in X.columns if c not in num_cols]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)

prep = ColumnTransformer([
    ("num", StandardScaler(), num_cols),
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
])
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                            random_state=SEED, n_jobs=-1),
}
metrics, fitted, probas = {}, {}, {}
for name, clf in models.items():
    pipe = Pipeline([("prep", prep), ("clf", clf)]).fit(X_tr, y_tr)
    p = pipe.predict_proba(X_te)[:, 1]
    pred = (p >= 0.5).astype(int)
    metrics[name] = {
        "accuracy": accuracy_score(y_te, pred), "precision": precision_score(y_te, pred),
        "recall": recall_score(y_te, pred), "f1": f1_score(y_te, pred), "roc_auc": roc_auc_score(y_te, p),
    }
    fitted[name], probas[name] = pipe, p
metrics = {k: {m: round(float(v), 4) for m, v in d.items()} for k, d in metrics.items()}
best = max(metrics, key=lambda k: metrics[k]["roc_auc"])
print("\nModel comparison:\n", pd.DataFrame(metrics).T.to_string())
print("Best by ROC-AUC:", best)

# class-imbalance check: same model WITHOUT class weights, to show why it matters
plain = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))]).fit(X_tr, y_tr)
plain_recall = float(recall_score(y_te, plain.predict(X_te)))

# ROC + confusion matrix
plt.figure(figsize=(5.5, 5))
for name, p in probas.items():
    fpr, tpr, _ = roc_curve(y_te, p)
    plt.plot(fpr, tpr, label=f"{name} (AUC {metrics[name]['roc_auc']:.3f})")
plt.plot([0, 1], [0, 1], "k--", lw=1); plt.xlabel("False positive rate"); plt.ylabel("True positive rate")
plt.title("ROC curves"); plt.legend(loc="lower right"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "roc_curves.png"), dpi=130); plt.close()

fig, ax = plt.subplots(figsize=(4.8, 4.2))
ConfusionMatrixDisplay.from_predictions(y_te, (probas[best] >= 0.5).astype(int), display_labels=["Stayed", "Churned"],
                                        cmap="Blues", ax=ax, colorbar=False)
ax.set_title(f"Confusion matrix - {best}"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "confusion_matrix.png"), dpi=130); plt.close()

# ---------------------------------------------------------------- 6. churn drivers
rf = fitted["Random Forest"]
names = rf.named_steps["prep"].get_feature_names_out()
imp = pd.Series(rf.named_steps["clf"].feature_importances_, index=names).sort_values(ascending=False)
clean = lambda s: s.replace("num__", "").replace("cat__", "")
top = imp.head(10)
plt.figure(figsize=(7, 4.5))
sns.barplot(x=top.values, y=[clean(i) for i in top.index], color="#2b6cb0")
plt.title("Top 10 churn drivers (Random Forest importance)"); plt.xlabel("Importance")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "feature_importance.png"), dpi=130); plt.close()

# ---------------------------------------------------------------- 7. retention targeting
p = probas[best]
order = np.argsort(-p)
top_n = int(0.2 * len(y_te))
captured = int(y_te.to_numpy()[order[:top_n]].sum())
total_churners = int(y_te.sum())
targeting = {
    "contacted_pct": 20, "customers_contacted": top_n, "churners_captured": captured,
    "total_churners_in_test": total_churners,
    "pct_of_churners_captured": round(100 * captured / total_churners, 1),
    "lift_vs_random": round((captured / top_n) / (total_churners / len(y_te)), 2),
}
print("\nTargeting top 20% by risk:", targeting)

summary = {
    "data_file": os.path.relpath(path, ROOT), "rows_loaded": int(n_start), "rows_after_cleaning": int(len(df)),
    "duplicates_dropped": dupes, "blank_total_charges_filled": blank_total,
    "overall_churn_rate_pct": round(100 * churn_rate, 1), "test_set_size": int(len(y_te)),
    "metrics": metrics, "best_model": best,
    "logistic_recall_without_class_weights": round(plain_recall, 4),
    "top_drivers": [clean(i) for i in imp.head(5).index],
    "retention_targeting": targeting,
}
with open(os.path.join(RES, "metrics.json"), "w") as f:
    json.dump(summary, f, indent=2)
print("\nSaved results/metrics.json, results/sql_results.md and figures/*.png")
