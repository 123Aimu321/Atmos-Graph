
from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = (
    ROOT_DIR / "datasets" / "processed" /
    "gnn_training_dataset.csv"
)

MODEL_DIR = ROOT_DIR / "ml" / "saved_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE)

# Group by scenario so one disruption scenario cannot
# appear in both training and testing sets.
splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42
)

train_idx, test_idx = next(
    splitter.split(df, groups=df["scenario_id"])
)

train_df = df.iloc[train_idx].copy()
test_df = df.iloc[test_idx].copy()

# Use features that can be calculated before prediction.
# Do NOT use impact_score, status, or reachability-based
# distance_from_disruption as input features.
numeric_features = [
    "in_degree",
    "out_degree",
    "total_degree",
    "is_disrupted_entity",
]

categorical_features = [
    "node_type",
    "region",
    "disruption_type",
]

feature_columns = numeric_features + categorical_features

X_train = train_df[feature_columns]
X_test = test_df[feature_columns]

y_train = train_df["status"]
y_test = test_df["status"]

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
        (
            "numeric",
            "passthrough",
            numeric_features,
        ),
    ]
)

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=2,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
        ),
    ]
)

print("Training Random Forest baseline...")
print(f"Training scenarios: {train_df['scenario_id'].nunique()}")
print(f"Testing scenarios: {test_df['scenario_id'].nunique()}")
print(f"Training records: {len(train_df)}")
print(f"Testing records: {len(test_df)}")

model.fit(X_train, y_train)

predictions = model.predict(X_test)

class_names = ["NORMAL", "AFFECTED", "DISRUPTED"]

accuracy = accuracy_score(y_test, predictions)
macro_f1 = f1_score(
    y_test,
    predictions,
    labels=class_names,
    average="macro",
    zero_division=0,
)

weighted_f1 = f1_score(
    y_test,
    predictions,
    labels=class_names,
    average="weighted",
    zero_division=0,
)

print("\n=== Random Forest Results ===")
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1-score: {macro_f1:.4f}")
print(f"Weighted F1-score: {weighted_f1:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        labels=class_names,
        zero_division=0,
    )
)

print("\nConfusion Matrix:")
matrix = confusion_matrix(
    y_test,
    predictions,
    labels=class_names,
)

print(
    pd.DataFrame(
        matrix,
        index=[f"Actual_{x}" for x in class_names],
        columns=[f"Predicted_{x}" for x in class_names],
    ).to_string()
)

# Save the trained model
model_path = MODEL_DIR / "random_forest_baseline.joblib"
joblib.dump(model, model_path)

# Save evaluation metrics
metrics = {
    "model": "RandomForestClassifier",
    "accuracy": float(accuracy),
    "macro_f1": float(macro_f1),
    "weighted_f1": float(weighted_f1),
    "training_scenarios": sorted(
        train_df["scenario_id"].unique().tolist()
    ),
    "testing_scenarios": sorted(
        test_df["scenario_id"].unique().tolist()
    ),
    "feature_columns": feature_columns,
    "class_names": class_names,
    "confusion_matrix": matrix.tolist(),
    "data_origin": "SYNTHETIC_SIMULATION",
}

metrics_path = MODEL_DIR / "baseline_metrics.json"

with open(metrics_path, "w", encoding="utf-8") as file:
    json.dump(metrics, file, indent=4)

# Save test predictions for inspection
test_results = test_df[
    ["scenario_id", "node_id", "status"]
].copy()

test_results["predicted_status"] = predictions
test_results["correct"] = (
    test_results["status"] ==
    test_results["predicted_status"]
)

predictions_path = MODEL_DIR / "baseline_predictions.csv"
test_results.to_csv(predictions_path, index=False)

print("\nModel saved to:", model_path)
print("Metrics saved to:", metrics_path)
print("Predictions saved to:", predictions_path)
print("\nBaseline training completed successfully!")
