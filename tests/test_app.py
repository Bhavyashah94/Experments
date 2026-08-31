import os
import io
import hashlib
import json
import pytest
from app import app, OUTPUT_DIR, UPLOADS_DIR


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"LabStudio" in res.data or b"Lab Header" in res.data
    assert "no-cache" in res.headers.get("Cache-Control", "")
    assert "no-store" in res.headers.get("Cache-Control", "")


def test_serve_spa_assets(client):
    # Find an asset in frontend/dist/assets
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist", "assets")
    if os.path.exists(assets_dir):
        files = os.listdir(assets_dir)
        if files:
            res = client.get(f"/assets/{files[0]}")
            assert res.status_code == 200
            assert "immutable" in res.headers.get("Cache-Control", "")


def test_load_defaults(client):
    res = client.get("/api/load-defaults")
    assert res.status_code == 200
    data = res.get_json()
    assert "student" in data
    assert "experiments" in data


def test_preview_endpoint(client):
    payload = {
        "student": {
            "name": "Alex",
            "roll_no": "10",
            "subject": "Cloud Computing",
            "text_color": "#0000bf",
            "strikethrough_enabled": True,
        },
        "item": {
            "label": "1",
            "title": "AWS EC2 Deployment",
            "is_assignment": False,
        },
    }
    res = client.post("/api/preview", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["image_data"].startswith("data:image/png;base64,")


def test_upload_and_extract(client):
    import fitz

    # Create in-memory test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Experiment 3: Study of Docker Containers")
    page.insert_text((50, 130), "Aim: Build and deploy containerized microservices.")
    pdf_bytes = doc.tobytes()
    doc.close()

    content_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Test upload
    data = {
        "file": (io.BytesIO(pdf_bytes), "exp3.pdf"),
        "hash": content_hash,
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    upload_res = res.get_json()
    assert upload_res["success"] is True
    assert upload_res["hash"] == content_hash
    assert upload_res["pages"] == 1
    assert upload_res["exp_num"] == "3"

    # Test file exists
    res_exists = client.get(f"/api/file/{content_hash}/exists")
    assert res_exists.status_code == 200
    assert res_exists.get_json()["exists"] is True

    # Test extract-aim
    res_aim = client.post("/api/extract-aim", json={"hash": content_hash})
    assert res_aim.status_code == 200
    assert "containerized microservices" in res_aim.get_json()["aim"]


def test_generate_and_download(client):
    payload = {
        "student": {
            "name": "Concurrency Tester",
            "roll_no": "99",
            "batch": "B1",
            "class_name": "BE IT",
            "sem": "VII",
            "subject": "Deep Learning",
            "text_color": "blue",
            "strikethrough_enabled": True,
        },
        "experiments": [
            {
                "num": 1,
                "label": "1",
                "title": "Convolutional Neural Networks",
                "is_assignment": False,
                "perf_date": "05/02/2026",
                "sub_date": "12/02/2026",
            }
        ],
    }
    res = client.post("/api/generate", json=payload)
    assert res.status_code == 200
    gen_data = res.get_json()
    assert gen_data["success"] is True
    assert "job_id" in gen_data
    combined_rel_path = gen_data["combined_pdf"]
    zip_rel_path = gen_data["zip_package"]

    # Test downloads
    dl_combined = client.get(f"/api/download/{combined_rel_path}")
    assert dl_combined.status_code == 200
    assert dl_combined.data.startswith(b"%PDF")

    dl_zip = client.get(f"/api/download/{zip_rel_path}")
    assert dl_zip.status_code == 200
    assert dl_zip.data.startswith(b"PK")

    # Test directory traversal protection
    dl_bad = client.get("/api/download/../../etc/passwd")
    assert dl_bad.status_code in (400, 404)
