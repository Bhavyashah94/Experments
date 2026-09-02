import os
import io
import time
import json
import sqlite3
import pytest
from app import app, OUTPUT_DIR, UPLOADS_DIR
from lab_core.analytics import (
    init_analytics_db,
    record_generation_event,
    get_analytics_summary,
    get_generation_events,
    is_analytics_enabled,
    is_auth_required,
    verify_admin_password,
)


@pytest.fixture
def test_db_path(tmp_path):
    db_file = str(tmp_path / "test_analytics.db")
    os.environ["ANALYTICS_DB_PATH"] = db_file
    init_analytics_db(db_file)
    yield db_file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


@pytest.fixture
def client(test_db_path):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_analytics_enabled_by_default():
    # Should be True by default
    if "ENABLE_ANALYTICS" in os.environ:
        del os.environ["ENABLE_ANALYTICS"]
    assert is_analytics_enabled() is True

    os.environ["ENABLE_ANALYTICS"] = "false"
    assert is_analytics_enabled() is False

    os.environ["ENABLE_ANALYTICS"] = "true"
    assert is_analytics_enabled() is True


def test_admin_password_verification():
    os.environ["ANALYTICS_ADMIN_PASSWORD"] = "secret123"
    assert is_auth_required() is True
    assert verify_admin_password("secret123") is True
    assert verify_admin_password("wrong") is False
    assert verify_admin_password("") is False

    del os.environ["ANALYTICS_ADMIN_PASSWORD"]
    assert is_auth_required() is False
    assert verify_admin_password("anything") is True


def test_record_generation_event_and_indexes(test_db_path):
    student = {
        "name": "Bhavya Shah",
        "roll_no": "34",
        "batch": "I3",
        "class_name": "BE IT",
        "sem": "VII",
        "subject": "Internet of Things",
    }
    experiments = [
        {"label": "1", "is_assignment": False, "title": "MQTT Sensor Nodes", "hash": "abc1234567890123456789012345678901234567890123456789012345678901", "pages": 3},
        {"label": "2", "is_assignment": True, "title": "CoAP Protocol", "hash": "def1234567890123456789012345678901234567890123456789012345678901", "pages": 2},
    ]

    ok = record_generation_event(
        student=student,
        experiments=experiments,
        success=True,
        duration_ms=185.5,
        db_path=test_db_path,
    )
    assert ok is True

    # Record second event for a different student
    record_generation_event(
        student={
            "name": "Alex Smith",
            "roll_no": "42",
            "batch": "I2",
            "class_name": "BE IT",
            "sem": "VII",
            "subject": "Cloud Computing",
        },
        experiments=[{"label": "1", "is_assignment": False, "title": "AWS Lambda", "pages": 4}],
        success=True,
        duration_ms=210.0,
        db_path=test_db_path,
    )

    # Record failed event
    record_generation_event(
        student={"name": "Faulty Run", "roll_no": "99", "subject": "Internet of Things"},
        experiments=[{"label": "3", "title": "Failed Exp"}],
        success=False,
        duration_ms=45.0,
        error_message="Corrupted PDF input stream",
        db_path=test_db_path,
    )

    # Check summary
    summary = get_analytics_summary(test_db_path)
    assert summary["total_generations"] == 3
    assert summary["successful_generations"] == 2
    assert summary["failed_generations"] == 1
    assert summary["unique_students"] == 3
    assert summary["total_experiments_generated"] == 4
    assert len(summary["top_subjects"]) == 2
    assert summary["top_subjects"][0]["subject"] == "Internet of Things"


def test_get_generation_events_search_and_pagination(test_db_path):
    for i in range(5):
        record_generation_event(
            student={"name": f"Student {i}", "roll_no": f"10{i}", "subject": "Data Science"},
            experiments=[{"label": str(i + 1), "title": f"Exp {i + 1}"}],
            success=True,
            duration_ms=100 + i * 10,
            db_path=test_db_path,
        )

    # All events
    events, total = get_generation_events(db_path=test_db_path, limit=10, offset=0)
    assert total == 5
    assert len(events) == 5

    # Search query filter
    events, total = get_generation_events(query="102", db_path=test_db_path)
    assert total == 1
    assert events[0]["roll_no"] == "102"
    assert events[0]["student_name"] == "Student 2"

    # Pagination
    events, total = get_generation_events(db_path=test_db_path, limit=2, offset=0)
    assert len(events) == 2
    assert total == 5


def test_analytics_api_endpoints_open(client, test_db_path):
    if "ANALYTICS_ADMIN_PASSWORD" in os.environ:
        del os.environ["ANALYTICS_ADMIN_PASSWORD"]
    os.environ["ENABLE_ANALYTICS"] = "true"

    # Status check
    res = client.get("/api/analytics/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["enabled"] is True
    assert data["auth_required"] is False

    # Summary endpoint
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Events endpoint
    res = client.get("/api/analytics/events")
    assert res.status_code == 200
    assert res.get_json()["success"] is True


def test_analytics_api_endpoints_protected_with_password(client, test_db_path):
    os.environ["ANALYTICS_ADMIN_PASSWORD"] = "admin_pass_99"
    os.environ["ENABLE_ANALYTICS"] = "true"

    # Status check indicates auth required
    res = client.get("/api/analytics/status")
    assert res.status_code == 200
    assert res.get_json()["auth_required"] is True

    # Accessing summary without key -> 401
    res = client.get("/api/analytics/summary")
    assert res.status_code == 401

    # Authenticate endpoint with invalid password
    res = client.post("/api/analytics/auth", json={"password": "wrong"})
    assert res.status_code == 401
    assert res.get_json()["valid"] is False

    # Authenticate endpoint with valid password
    res = client.post("/api/analytics/auth", json={"password": "admin_pass_99"})
    assert res.status_code == 200
    assert res.get_json()["valid"] is True

    # Accessing summary with valid header -> 200
    res = client.get("/api/analytics/summary", headers={"X-Analytics-Key": "admin_pass_99"})
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    del os.environ["ANALYTICS_ADMIN_PASSWORD"]


def test_analytics_disabled_behavior(client, test_db_path):
    os.environ["ENABLE_ANALYTICS"] = "false"

    # Status returns 404
    res = client.get("/api/analytics/status")
    assert res.status_code == 404

    # Direct /analytics route returns 404
    res = client.get("/analytics")
    assert res.status_code == 404

    # Summary returns 404
    res = client.get("/api/analytics/summary")
    assert res.status_code == 404

    os.environ["ENABLE_ANALYTICS"] = "true"


def test_resilience_analytics_failure_does_not_break_generation(client, monkeypatch):
    """Verifies that if analytics fails (e.g. database error), document generation still succeeds 100%."""
    os.environ["ENABLE_ANALYTICS"] = "true"

    def broken_record(*args, **kwargs):
        raise sqlite3.OperationalError("Simulated database write failure")

    monkeypatch.setattr("app.record_generation_event", broken_record)

    payload = {
        "student": {
            "name": "Test Resilient",
            "roll_no": "99",
            "batch": "I1",
            "class_name": "BE IT",
            "sem": "VII",
            "subject": "IoT",
            "text_color": "#0000bf",
            "strikethrough_enabled": True,
        },
        "experiments": [
            {
                "label": "1",
                "is_assignment": False,
                "title": "Resilience Test",
                "perf_date": "01/09/2026",
                "sub_date": "08/09/2026",
            }
        ],
        "include_toc": True,
    }

    res = client.post("/api/generate", json=payload)
    # Document generation must succeed completely despite analytics error!
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "zip_file" in data or "combined_pdf" in data


def test_export_analytics_csv_and_json(client, test_db_path):
    record_generation_event(
        student={"name": "Alice Export", "roll_no": "77", "subject": "Networks"},
        experiments=[{"label": "1", "title": "Socket Programming"}],
        success=True,
        duration_ms=150.0,
        db_path=test_db_path,
    )

    # Test CSV export
    res_csv = client.get("/api/analytics/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    csv_text = res_csv.data.decode("utf-8")
    assert "Alice Export" in csv_text
    assert "Socket Programming" in csv_text
    assert "SUCCESS" in csv_text

    # Test JSON export
    res_json = client.get("/api/analytics/export?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.content_type
    json_data = json.loads(res_json.data.decode("utf-8"))
    assert json_data["total_records"] == 1
    assert json_data["events"][0]["student_name"] == "Alice Export"

