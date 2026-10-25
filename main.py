from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="EvidenceX1 Football API",
    version="0.1.0",
    description="Transparent, event-based football evidence audits.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_EVENTS = 500_000
matches: dict[str, dict[str, Any]] = {}


def nested(obj: Any, *keys: str, default=None):
    value = obj
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def event_name(event: dict) -> str:
    return nested(event, "type", "name", default="Unknown")


def team_name(event: dict) -> str | None:
    return nested(event, "team", "name")


def valid_location(event: dict):
    value = event.get("location")
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(n, (int, float)) and math.isfinite(n) for n in value[:2])
    ):
        return value
    return None


def parse_events(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError("Expected a JSON array of football events.")
    if not raw:
        raise ValueError("The event file is empty.")
    if len(raw) > MAX_EVENTS:
        raise ValueError(f"The file exceeds the limit of {MAX_EVENTS:,} events.")

    events = [
        event for event in raw
        if isinstance(event, dict) and isinstance(event.get("type"), dict)
        and isinstance(event["type"].get("name"), str)
    ]
    if not events:
        raise ValueError("No valid typed football events were found.")

    # Inspect normalized fields with Pandas to catch malformed/empty schemas.
    frame = pd.json_normalize(events, sep=".")
    if "type.name" not in frame.columns:
        raise ValueError("Required event type information is missing.")
    return events


def add_match(match_id: str, label: str, raw: Any):
    try:
        events = parse_events(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    teams = sorted({team_name(e) for e in events if team_name(e)})
    if len(teams) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least two team names are required for a comparison.",
        )

    matches[match_id] = {
        "id": match_id,
        "label": label,
        "events": events,
        "teams": teams,
    }


def get_match(match_id: str):
    match = matches.get(match_id)
    if not match:
        raise HTTPException(
            status_code=404,
            detail="Match not found. Load the sample or upload a StatsBomb event JSON.",
        )
    return match


def is_pass(event: dict) -> bool:
    return event_name(event) == "Pass"


def is_shot(event: dict) -> bool:
    return event_name(event) == "Shot"


def is_goal(event: dict) -> bool:
    return is_shot(event) and nested(event, "shot", "outcome", "name") == "Goal"


def pass_completed(event: dict) -> bool:
    # In StatsBomb, failed passes have an outcome such as Incomplete or Out.
    # A missing outcome is treated as completed by convention in this MVP.
    return nested(event, "pass", "outcome", "name") is None


def overview(match: dict) -> dict:
    events = match["events"]
    type_counts = Counter(event_name(event) for event in events)
    team_stats = []

    for team in match["teams"]:
        own = [event for event in events if team_name(event) == team]
        passes = [event for event in own if is_pass(event)]
        shots = [event for event in own if is_shot(event)]
        goals = sum(is_goal(event) for event in shots)
        completed = sum(pass_completed(event) for event in passes)

        team_stats.append({
            "team": team,
            "events": len(own),
            "passes": len(passes),
            "completed_passes": completed,
            "pass_completion_pct": round(100 * completed / len(passes), 1) if passes else None,
            "shots": len(shots),
            "goals": goals,
            "shot_conversion_pct": round(100 * goals / len(shots), 1) if shots else None,
        })

    return {
        "id": match["id"],
        "label": match["label"],
        "teams": match["teams"],
        "event_count": len(events),
        "event_types": dict(type_counts.most_common(12)),
        "team_stats": team_stats,
        "data_quality": {
            "events_with_team": sum(team_name(e) is not None for e in events),
            "events_with_location": sum(valid_location(e) is not None for e in events),
            "events_without_location": sum(valid_location(e) is None for e in events),
            "note": "Missing coordinates remain missing; they are never inferred.",
        },
    }


class AnalyzeRequest(BaseModel):
    match_id: str = Field(min_length=1, max_length=200)
    team: str = Field(min_length=1, max_length=200)
    metric: str = Field(pattern="^(pass_completion|shot_conversion)$")


@app.get("/api/health")
def health():
    return {"status": "ok", "loaded_matches": len(matches)}


@app.get("/api/matches")
def list_matches():
    return [
        {
            "id": match["id"],
            "label": match["label"],
            "teams": match["teams"],
            "event_count": len(match["events"]),
        }
        for match in matches.values()
    ]


@app.post("/api/sample")
def load_sample():
    # Public StatsBomb Open Data event file. Users can upload another JSON
    # through the UI if this sample moves or is unavailable.
    url = (
        "https://raw.githubusercontent.com/statsbomb/open-data/"
        "master/data/events/3869685.json"
    )
    try:
        request = Request(url, headers={"User-Agent": "EvidenceX1Football/0.1"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(MAX_FILE_BYTES + 1)
        if len(payload) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Remote sample is too large.")
        raw = json.loads(payload.decode("utf-8"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not fetch the StatsBomb sample. Check your internet "
                "connection or upload a JSON file from the official open-data repository."
            ),
        ) from exc

    add_match("statsbomb-sample", "StatsBomb Open Data sample", raw)
    return overview(matches["statsbomb-sample"])


@app.post("/api/matches/upload")
async def upload_matches(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Choose JSON event files.")
    if len(files) > 20:
        raise HTTPException(status_code=413, detail="Upload no more than 20 files at once.")

    uploaded = []
    for file in files:
        filename = file.filename or "uploaded_match.json"
        if not filename.lower().endswith(".json"):
            raise HTTPException(status_code=415, detail=f"{filename}: upload a .json file.")

        content = await file.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"{filename}: maximum file size is 25 MB.")
        try:
            raw = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=f"{filename}: invalid UTF-8 JSON.") from exc

        base = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(filename).stem)[:80] or "match"
        match_id = f"upload_{base}"
        suffix = 2
        while match_id in matches:
            match_id = f"upload_{base}_{suffix}"
            suffix += 1

        add_match(match_id, filename, raw)
        uploaded.append(overview(matches[match_id]))

    return {"uploaded": uploaded}


@app.get("/api/matches/{match_id}/overview")
def get_overview(match_id: str):
    return overview(get_match(match_id))


def build_audit(match: dict, team: str, metric: str) -> dict:
    if team not in match["teams"]:
        raise HTTPException(status_code=422, detail="Selected team is not present in this match.")
    opponents = [name for name in match["teams"] if name != team]
    if len(opponents) != 1:
        raise HTTPException(
            status_code=422,
            detail="This MVP expects a two-team match for direct comparison.",
        )
    opponent = opponents[0]
    events = match["events"]

    def calculate(team_label: str):
        own = [e for e in events if team_name(e) == team_label]
        if metric == "pass_completion":
            relevant = [e for e in own if is_pass(e)]
            numerator = sum(pass_completed(e) for e in relevant)
            denominator = len(relevant)
            min_n = 20
            numerator_label, denominator_label = "completed passes", "passes"
            definition = (
                "Completed recorded passes divided by all recorded pass events. "
                "A pass with no outcome is treated as completed in this MVP."
            )
        else:
            relevant = [e for e in own if is_shot(e)]
            numerator = sum(is_goal(e) for e in relevant)
            denominator = len(relevant)
            min_n = 3
            numerator_label, denominator_label = "goals", "shots"
            definition = (
                "Recorded goals divided by recorded shots. This does not adjust "
                "for shot quality, expected goals, or game state."
            )
        rate = numerator / denominator if denominator else None
        return {
            "team": team_label,
            "numerator": numerator,
            "denominator": denominator,
            "rate": rate,
            "rate_pct": round(rate * 100, 1) if rate is not None else None,
            "numerator_label": numerator_label,
            "denominator_label": denominator_label,
            "minimum_sample": min_n,
            "sufficient_sample": denominator >= min_n,
        }

    a, b = calculate(team), calculate(opponent)

    if not a["sufficient_sample"] or not b["sufficient_sample"]:
        status = "Insufficient data"
        conclusion = (
            "At least one team did not meet the predefined minimum sample. "
            "The observed values are shown, but a reliable comparison is not claimed."
        )
    elif math.isclose(a["rate"], b["rate"], abs_tol=1e-12):
        status = "Mixed evidence"
        conclusion = "The observed rates are equal; this test does not favor either team."
    elif a["rate"] > b["rate"]:
        status = "Supported by the observed evidence"
        conclusion = f"{team} has the higher observed rate in this match. This is descriptive, not causal."
    else:
        status = "Contradicted by the observed evidence"
        conclusion = f"{opponent} has the higher observed rate in this match. This is descriptive, not causal."

    delta = (
        round((a["rate"] - b["rate"]) * 100, 1)
        if a["rate"] is not None and b["rate"] is not None
        else None
    )
    claim = (
        f"{team} has a higher pass-completion rate than {opponent}."
        if metric == "pass_completion"
        else f"{team} has a higher shot-conversion rate than {opponent}."
    )

    return {
        "claim": claim,
        "definition": definition,
        "status": status,
        "conclusion": conclusion,
        "metric": metric,
        "match_id": match["id"],
        "sample_size": {"selected_team": a["denominator"], "comparison_team": b["denominator"]},
        "selected_team": a,
        "comparison_team": b,
        "difference_percentage_points": delta,
        "supporting_evidence": [
            f"{a['numerator']} {a['numerator_label']} from {a['denominator']} {a['denominator_label']} for {team}.",
            f"Observed rate: {a['rate_pct']}%." if a["rate_pct"] is not None else "Selected-team rate unavailable.",
        ],
        "contradictory_evidence": [
            f"{b['numerator']} {b['numerator_label']} from {b['denominator']} {b['denominator_label']} for {opponent}.",
            f"Observed comparison rate: {b['rate_pct']}%." if b["rate_pct"] is not None else "Comparison rate unavailable.",
        ],
        "limitations": [
            "This audit uses one match at a time and does not establish consistency across matches.",
            "Minimum sample sizes are screening safeguards, not statistical significance tests.",
            "Event data alone does not fully capture defensive shape, pressure, tactical intent, or video context.",
            "These metrics are descriptive and do not establish causation.",
        ],
    }


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    return build_audit(get_match(request.match_id), request.team, request.metric)
