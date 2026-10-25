from fastapi.testclient import TestClient
from main import app, matches, add_match

client = TestClient(app)


def setup_function():
    matches.clear()
    sample = [
        {"type": {"name": "Pass"}, "team": {"name": "North FC"}, "pass": {}},
        {"type": {"name": "Pass"}, "team": {"name": "North FC"}, "pass": {"outcome": {"name": "Incomplete"}}},
        {"type": {"name": "Shot"}, "team": {"name": "North FC"}, "shot": {"outcome": {"name": "Goal"}}},
        {"type": {"name": "Shot"}, "team": {"name": "North FC"}, "shot": {"outcome": {"name": "Saved"}}},
        {"type": {"name": "Pass"}, "team": {"name": "South FC"}, "pass": {}},
        {"type": {"name": "Pass"}, "team": {"name": "South FC"}, "pass": {}},
        {"type": {"name": "Shot"}, "team": {"name": "South FC"}, "shot": {"outcome": {"name": "Saved"}}},
        {"type": {"name": "Shot"}, "team": {"name": "South FC"}, "shot": {"outcome": {"name": "Off T"}}},
    ]
    add_match("test", "Test match", sample)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_has_both_teams():
    response = client.get("/api/matches/test/overview")
    assert response.status_code == 200
    assert response.json()["event_count"] == 8
    assert len(response.json()["team_stats"]) == 2


def test_shot_conversion_audit_reports_small_sample():
    response = client.post("/api/analyze", json={
        "match_id": "test",
        "team": "North FC",
        "metric": "shot_conversion",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "Insufficient data"
    assert response.json()["selected_team"]["denominator"] == 2


def test_invalid_metric_rejected():
    response = client.post("/api/analyze", json={
        "match_id": "test",
        "team": "North FC",
        "metric": "make_up_a_metric",
    })
    assert response.status_code == 422
