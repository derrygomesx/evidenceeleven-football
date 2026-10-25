
import json
from pathlib import Path
from collections import Counter

events_dir = Path("backend/data/statsbomb/events")

shot_count = 0
feature_counts = Counter()
outcome_counts = Counter()
example_shot = None

for file in events_dir.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        events = json.load(f)

    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue

        shot_count += 1
        shot = event.get("shot", {})
        outcome = shot.get("outcome", {}).get("name", "Unknown")
        outcome_counts[outcome] += 1

        if example_shot is None:
            example_shot = event

        for key, value in shot.items():
            if value is not None:
                feature_counts[key] += 1

print("===== SHOT FEATURE AUDIT =====")
print("Total shots:", shot_count)

print("\nAvailable shot features:")
for feature, count in feature_counts.most_common():
    print(f"{feature}: {count}/{shot_count}")

print("\nShot outcomes:")
for outcome, count in outcome_counts.most_common():
    print(f"{outcome}: {count}")

print("\nExample shot event:")
print(json.dumps(example_shot, indent=2)[:5000])
