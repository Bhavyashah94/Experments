import os
import io
import time
import pytest
import pymupdf as fitz
from app import app, UPLOADS_DIR, OUTPUT_DIR
from lab_core import (
    record_upload_diagnostic,
    record_student_ground_truth,
    get_extraction_diagnostics_summary,
    get_failed_or_discrepant_samples,
    get_protected_hashes_set,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _create_synthetic_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    if text:
        page.insert_text((50, 100), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_upload_records_diagnostics(client, tmp_path):
    """Verifies that uploading a PDF logs diagnostic signals and failure reasons."""
    # Synthetic PDF without Aim keyword
    pdf_data = _create_synthetic_pdf("Introduction to Database Systems. Chapter 1.")
    data = {
        "file": (io.BytesIO(pdf_data), "unconventional_lab.pdf"),
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    res_json = res.get_json()
    assert res_json["success"] is True
    file_hash = res_json["hash"]

    # Check that diagnostic summary recorded the upload
    summary = get_extraction_diagnostics_summary()
    assert summary["total_documents"] >= 1
    assert any("no_aim_keyword" in k or "no_exp_number_found" in k for k in summary["failures"])


def test_student_ground_truth_discrepancy(client):
    """Verifies that student corrections in /api/generate mark discrepancy and store ground truth."""
    pdf_data = _create_synthetic_pdf("Experiment 1: Database Setup\nAim: Initial setup.")
    data = {
        "file": (io.BytesIO(pdf_data), "lab1.pdf"),
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    file_hash = res.get_json()["hash"]

    # Student provides a corrected/different title
    student_title = "Advanced Database Indexing & B-Trees"
    experiments = [
        {
            "hash": file_hash,
            "title": student_title,
            "label": "1",
            "is_assignment": False,
        }
    ]
    record_student_ground_truth(experiments)

    samples, total = get_failed_or_discrepant_samples(limit=10, offset=0)
    matching = [s for s in samples if s["sha256"] == file_hash]
    assert len(matching) == 1
    assert matching[0]["discrepancy"] == 1
    assert matching[0]["student_submitted_title"] == student_title


def test_admin_diagnostics_and_sample_download(client):
    """Verifies that admin diagnostics API returns summary and allows downloading sample PDF."""
    pdf_data = _create_synthetic_pdf("Problem Statement: Implement Dijkstra algorithm.")
    data = {
        "file": (io.BytesIO(pdf_data), "dijkstra.pdf"),
    }
    res = client.post("/api/upload", data=data, content_type="multipart/form-data")
    file_hash = res.get_json()["hash"]

    # Admin diagnostics endpoint
    diag_res = client.get("/api/analytics/diagnostics")
    assert diag_res.status_code == 200
    diag_json = diag_res.get_json()
    assert diag_json["success"] is True
    assert "summary" in diag_json["data"]

    # Admin sample download endpoint
    sample_res = client.get(f"/api/analytics/sample/{file_hash}")
    assert sample_res.status_code == 200
    assert sample_res.data.startswith(b"%PDF")


def test_protected_hashes_retention():
    """Verifies that get_protected_hashes_set identifies failed or discrepant uploads."""
    record_upload_diagnostic(
        sha256="a" * 64,
        filename="failed_sample.pdf",
        file_size=1024,
        pages=2,
        extracted_aim=None,
        extracted_exp_num=None,
        extraction_method="unextracted",
        failure_reason="no_aim_keyword",
        text_snippet="Sample raw text",
    )
    protected = get_protected_hashes_set()
    assert ("a" * 64) in protected


def test_ordinary_upload_unprotected_vs_discrepancy():
    """
    Verifies that:
    1. An ordinary successful upload (failure_reason='none') starts UNPROTECTED.
    2. It is not in get_protected_hashes_set(), so storage quota Tier 2 can evict it.
    3. When a discrepancy is submitted, it BECOMES protected.
    """
    clean_hash = "b" * 64
    record_upload_diagnostic(
        sha256=clean_hash,
        filename="clean_sample.pdf",
        file_size=2048,
        pages=3,
        extracted_aim="Original Aim",
        extracted_exp_num="1",
        extraction_method="aim_keyword",
        failure_reason="none",
        text_snippet="Sample text",
    )
    # 1. Must NOT be protected initially
    assert clean_hash not in get_protected_hashes_set()

    # 2. Student confirms same aim (no discrepancy)
    record_student_ground_truth([
        {"hash": clean_hash, "title": "Original Aim", "label": "1"}
    ])
    assert clean_hash not in get_protected_hashes_set()

    # 3. Another upload with student correction (discrepancy)
    discrepant_hash = "c" * 64
    record_upload_diagnostic(
        sha256=discrepant_hash,
        filename="discrepant_sample.pdf",
        file_size=2048,
        pages=3,
        extracted_aim="Wrong Auto Aim",
        extracted_exp_num="2",
        extraction_method="aim_keyword",
        failure_reason="none",
        text_snippet="Sample text",
    )
    assert discrepant_hash not in get_protected_hashes_set()

    # Student corrects the title
    record_student_ground_truth([
        {"hash": discrepant_hash, "title": "Corrected Student Title", "label": "2"}
    ])
    # Now it MUST be protected
    assert discrepant_hash in get_protected_hashes_set()


def test_stale_temp_file_cleanup(tmp_path, monkeypatch):
    """
    Verifies that _cleanup_ephemeral_storage():
    1. Deletes temp_<32hex>.pdf files older than 2 hours.
    2. Preserves recent temp_<32hex>.pdf files.
    3. Preserves normal <64hex>.pdf files.
    4. Preserves unrelated files.
    """
    import app as main_app

    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir()
    test_output = tmp_path / "output"
    test_output.mkdir()

    monkeypatch.setattr(main_app, "UPLOADS_DIR", str(test_uploads))
    monkeypatch.setattr(main_app, "OUTPUT_DIR", str(test_output))

    now = time.time()

    # 1. Stale temp file (3 hours old)
    stale_temp = test_uploads / "temp_11112222333344445555666677778888.pdf"
    stale_temp.write_bytes(b"%PDF-1.4 stale temp")
    os.utime(stale_temp, (now - 10800, now - 10800))

    # 2. Recent temp file (30 seconds old)
    recent_temp = test_uploads / "temp_aaaabbbbccccddddeeeeffff00001111.pdf"
    recent_temp.write_bytes(b"%PDF-1.4 recent temp")
    os.utime(recent_temp, (now - 30, now - 30))

    # 3. Normal upload file (64-char hash)
    normal_pdf = test_uploads / f"{'f'*64}.pdf"
    normal_pdf.write_bytes(b"%PDF-1.4 normal upload")
    os.utime(normal_pdf, (now - 10800, now - 10800))

    # 4. Unrelated file
    other_file = test_uploads / "notes.txt"
    other_file.write_text("important notes")

    # Run cleanup
    main_app._cleanup_ephemeral_storage()

    # Assertions
    assert not os.path.exists(stale_temp), "Stale temp file should have been deleted"
    assert os.path.exists(recent_temp), "Recent temp file must be preserved"
    assert os.path.exists(normal_pdf), "Normal upload must be preserved"
    assert os.path.exists(other_file), "Unrelated file must be preserved"

