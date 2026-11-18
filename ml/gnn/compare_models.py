
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "ml" / "saved_model"

with open(MODEL_DIR / "baseline_metrics.json", encoding="utf-8") as f:
    rf = json.load(f)

with open(MODEL_DIR / "gnn_metrics.json", encoding="utf-8") as f:
    gnn = json.load(f)

print("\n========== AtmoGraph Model Comparison ==========\n")

print(f"{'Metric':<20} {'Random Forest':<18} {'GraphSAGE':<18}")
print("-" * 56)

for key, label in [
    ("accuracy", "Accuracy"),
    ("macro_f1", "Macro F1"),
    ("weighted_f1", "Weighted F1"),
]:
    print(
        f"{label:<20} "
        f"{rf[key]:<18.4f} "
        f"{gnn[key]:<18.4f}"
    )

same_test = (
    set(rf["testing_scenarios"]) ==
    set(gnn["testing_scenarios"])
)

print("\nSame test scenarios:", same_test)

if not same_test:
    print("WARNING: Models were evaluated on different scenarios.")

best_model = (
    "GraphSAGE"
    if gnn["macro_f1"] > rf["macro_f1"]
    else "Random Forest"
)

print("Best model by Macro F1:", best_model)
print("\nComparison completed successfully!")
