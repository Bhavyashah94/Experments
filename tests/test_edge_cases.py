import os
import io
import time
import fitz
import pytest
from app import app
from lab_core.pdf_engine import (
    parse_color,
    split_and_scale_title,
    create_filled_header_doc,
    render_header_preview_png,
    generate_job_documents,
)
from lab_core.toc_engine import generate_toc_page
from lab_core.extractor import inspect_pdf_info

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, "Header.pdf")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_edge_case_colors():
    # Malformed hex or unknown colors should fall back safely
    assert parse_color("#12345") == (0.0, 0.0, 0.75)
    assert parse_color("not-a-color") == (0.0, 0.0, 0.75)
    assert parse_color(None) == (0.0, 0.0, 0.75)
    assert parse_color(12345) == (0.0, 0.0, 0.75)


def test_edge_case_split_long_unbroken_string():
    long_unbroken = "A" * 150
    s1, s2, fs = split_and_scale_title(long_unbroken, default_fontsize=11.0)
    assert 8.0 <= fs <= 11.0
    assert len(s1) > 0
    assert len(s2) > 0


def test_edge_case_empty_title_and_special_chars():
    data = {
        "sem": "VIII (IT)",
        "class_name": "BE & ME",
        "batch": "Special <B1>",
        "roll_no": "999",
        "name": "Jane & John Döe #123",
        "subject": "Cyber Security & Forensics (CS-801)",
        "is_assignment": True,
        "exp_no": "Assign - 10-A",
        "title": "Configuring Snort IDS & IPS rules on Linux / BSD systems!",
        "perf_date": "",
        "sub_date": "",
    }
    formatting = {
        "text_color": "#112233",
        "strikethrough_enabled": False,
        "font_size": 11,
    }
    doc = create_filled_header_doc(TEMPLATE_PATH, data, formatting)
    assert isinstance(doc, fitz.Document)
    text = doc[0].get_text()
    assert "Cyber Security" in text
    doc.close()


def test_edge_case_toc_pagination_and_many_items():
    student = {
        "name": "Heavy User",
        "roll_no": "100",
        "batch": "B1",
        "class_name": "BE IT",
        "sem": "VII",
        "subject": "Distributed Computing",
    }
    entries = []
    for i in range(1, 30):
        entries.append({
            "label": str(i),
            "is_assignment": (i % 2 == 0),
            "title": f"Laboratory Module Task {i}: Complex distributed algorithm verification and test",
            "perf_date": "01/01/2026",
            "sub_date": "08/01/2026",
            "page_range": f"{i*3}-{i*3+2}",
        })
    doc = generate_toc_page(student, entries)
    assert isinstance(doc, fitz.Document)
    assert len(doc) == 2  # 29 items paginated across 2 pages
    doc.close()


def test_edge_case_upload_non_pdf(client):
    data = {
        "file": (io.BytesIO(b"Not a PDF content"), "test.txt"),
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json()["success"] is False
    assert "Only PDF files are accepted" in res.get_json()["error"]


def test_edge_case_upload_missing_file(client):
    res = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_edge_case_invalid_hash_lookup(client):
    res = client.get("/api/file/invalid_hash_123/exists")
    assert res.status_code == 400
    assert res.get_json()["exists"] is False


def test_edge_case_extract_aim_invalid_hash(client):
    res = client.post("/api/extract-aim", json={"hash": "badhash"})
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_edge_case_generate_empty_experiments(client):
    res = client.post("/api/generate", json={"student": {}, "experiments": []})
    assert res.status_code == 400
    assert res.get_json()["success"] is False
    assert "No experiments provided" in res.get_json()["error"]


def test_storage_quota_and_health_metrics(client, monkeypatch, tmp_path):
    import app as main_app

    # Test health check returns storage stats
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert "storage" in data
    assert "used_bytes" in data["storage"]
    assert "max_bytes" in data["storage"]

    # Test LRU eviction
    test_uploads = tmp_path / "uploads_test"
    test_uploads.mkdir()
    f1 = test_uploads / "file1.pdf"
    f2 = test_uploads / "file2.pdf"
    f1.write_bytes(b"A" * 1000)
    f2.write_bytes(b"B" * 1000)

    # Set older mtime on f1
    os.utime(f1, (time.time() - 500, time.time() - 500))

    monkeypatch.setattr(main_app, "UPLOADS_DIR", str(test_uploads))
    monkeypatch.setattr(main_app, "OUTPUT_DIR", str(tmp_path / "output_test"))
    monkeypatch.setattr(main_app, "MAX_STORAGE_BYTES", 1500)
    monkeypatch.setattr(main_app, "TARGET_STORAGE_BYTES", 1000)

    main_app._enforce_storage_quota()

    # f1 should be evicted (older), f2 should remain
    assert not os.path.exists(f1)
    assert os.path.exists(f2)
