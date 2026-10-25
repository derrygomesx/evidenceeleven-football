
import json
import math
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# Project paths
EVENTS_DIR = Path("backend/data/statsbomb/events")
MODEL_DIR = Path("backend/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def extract_shots():
    rows = []

    for file in sorted(EVENTS_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            events = json.load(f)

        for event in events:
            if event.get("type", {}).get("name") != "Shot":
                continue

            shot = event.get("shot", {})
            location = event.get("location", [])

            if len(location) < 2:
                continue

            x, y = location[0], location[1]

            # StatsBomb pitch coordinates: 120 x 80.
            distance = math.sqrt((120 - x) ** 2 + (40 - y) ** 2)

            # Approximate angle between the two goalposts.
            angle = abs(
                math.atan2(44 - y, 120 - x)
                - math.atan2(36 - y, 120 - x)
            )

            def category(obj):
                if isinstance(obj, dict):
                    return obj.get("name", "Unknown")
                return "Unknown"

            def flag(value):
                if value is True:
                    return "Yes"
                if value is False:
                    return "No"
                return "Unknown"

            rows.append({
                "match_id": file.stem,
                "x": x,
                "y": y,
                "distance": distance,
                "angle": angle,
                "minute": event.get("minute", 0),
                "period": event.get("period", 1),

                "body_part": category(shot.get("body_part")),
                "technique": category(shot.get("technique")),
                "shot_type": category(shot.get("type")),
                "play_pattern": category(event.get("play_pattern")),
                "position": category(event.get("position")),

                "first_time": flag(shot.get("first_time")),
                "one_on_one": flag(shot.get("one_on_one")),
                "aerial_won": flag(shot.get("aerial_won")),
                "deflected": flag(shot.get("deflected")),
                "open_goal": flag(shot.get("open_goal")),

                # Target: 1 = goal, 0 = not a goal.
                "target": int(
                    shot.get("outcome", {}).get("name") == "Goal"
                ),

                # Used only as a held-out benchmark, not as a model input.
                "statsbomb_xg": shot.get("statsbomb_xg"),
            })

    return pd.DataFrame(rows)


df = extract_shots()

if df.empty:
    raise RuntimeError(
        f"No shots found. Check that {EVENTS_DIR} exists and contains JSON files."
    )

print("Total shots:", len(df))
print("Total goals:", int(df["target"].sum()))
print("Matches:", df["match_id"].nunique())


numeric_features = [
    "x", "y", "distance", "angle", "minute", "period"
]

categorical_features = [
    "body_part", "technique", "shot_type", "play_pattern",
    "position", "first_time", "one_on_one", "aerial_won",
    "deflected", "open_goal"
]

features = numeric_features + categorical_features
X = df[features]
y = df["target"]
groups = df["match_id"]

# Keep all shots from a match together.
splitter = GroupShuffleSplit(
    n_splits=1, test_size=0.25, random_state=42
)
train_idx, test_idx = next(splitter.split(X, y, groups=groups))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

print("\nTraining shots:", len(X_train))
print("Test shots:", len(X_test))
print("Test goals:", int(y_test.sum()))
print("Test matches:", groups.iloc[test_idx].nunique())

numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False
    )),
])

preprocessor = ColumnTransformer([
    ("numeric", numeric_transformer, numeric_features),
    ("categorical", categorical_transformer, categorical_features),
])

models = {
    "Logistic Regression": LogisticRegression(
        max_iter=2000, class_weight="balanced"
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=300,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=2,
        random_state=42,
    ),
}


def evaluate(name, probabilities):
    probabilities = probabilities.clip(1e-7, 1 - 1e-7)

    return {
        "Model": name,
        "ROC-AUC": roc_auc_score(y_test, probabilities),
        "Log Loss": log_loss(y_test, probabilities),
        "Brier Score": brier_score_loss(y_test, probabilities),
    }


results = []
fitted_models = {}

for name, model in models.items():
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", model),
    ])

    pipeline.fit(X_train, y_train)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    results.append(evaluate(name, probabilities))
    fitted_models[name] = pipeline

    safe_name = name.lower().replace(" ", "_")
    joblib.dump(
        pipeline,
        MODEL_DIR / f"{safe_name}.joblib"
    )

# Evaluate the existing StatsBomb xG values on the same held-out shots.
xg = df.iloc[test_idx]["statsbomb_xg"].astype(float)

valid = xg.notna()
if valid.any() and y_test[valid].nunique() == 2:
    results.append(
        evaluate("StatsBomb xG benchmark", xg[valid].to_numpy())
    )

comparison = pd.DataFrame(results).sort_values(
    "ROC-AUC", ascending=False
)

comparison.to_csv(
    MODEL_DIR / "model_comparison.csv", index=False
)

print("\n===== MODEL COMPARISON =====")
print(comparison.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

print("\nModels and comparison saved to:", MODEL_DIR.resolve())
print("IMPORTANT: These are preliminary results from one match-based split.")
