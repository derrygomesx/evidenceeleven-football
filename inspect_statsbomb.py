
import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("backend/data/statsbomb")
EVENTS_DIR = DATA_DIR / "events"
MATCHES_FILE = DATA_DIR / "matches" / "55" / "282.json"

with MATCHES_FILE.open(encoding="utf-8") as file:
    matches = json.load(file)

event_files = list(EVENTS_DIR.glob("*.json"))

event_types = Counter()
shot_outcomes = Counter()
total_events = 0
total_shots = 0
matches_with_errors = []

for event_file in event_files:
    try:
        with event_file.open(encoding="utf-8") as file:
            events = json.load(file)

        if not isinstance(events, list):
            raise ValueError("Expected a list of events")

        total_events += len(events)

        for event in events:
            event_type = event.get("type", {}).get("name", "Unknown")
            event_types[event_type] += 1

            if event_type == "Shot":
                total_shots += 1
                outcome = event.get("shot", {}).get(
                    "outcome", {}
                ).get("name", "Unknown")
                shot_outcomes[outcome] += 1

    except Exception as error:
        matches_with_errors.append(
            f"{event_file.name}: {error}"
        )

print("===== STATSBOMB DATA AUDIT =====")
print(f"Matches in catalogue: {len(matches)}")
print(f"Event files found: {len(event_files)}")
print(f"Total events: {total_events}")
print(f"Total shots: {total_shots}")

print("\nShot outcomes:")
for outcome, count in shot_outcomes.most_common():
    print(f"  {outcome}: {count}")

print("\nEvent types:")
for name, count in event_types.most_common(15):
    print(f"  {name}: {count}")

print(f"\nFiles with errors: {len(matches_with_errors)}")
for error in matches_with_errors:
    print(f"  {error}")
