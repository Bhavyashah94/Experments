import os
import pytest
import fitz
from lab_core.pdf_engine import (
    parse_color,
    split_and_scale_title,
    create_filled_header_doc,
    render_header_preview_png,
    generate_job_documents,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, "Header.pdf")


def test_parse_color():
    # Named colors
    assert parse_color("blue") == (0.0, 0.0, 0.75)
    assert parse_color("black") == (0.0, 0.0, 0.0)
    assert parse_color("red") == (0.8, 0.0, 0.0)
    assert parse_color("darkblue") == (0.0, 0.0, 0.5)

    # Hex colors
    assert parse_color("#000000") == (0.0, 0.0, 0.0)
    assert parse_color("#ffffff") == (1.0, 1.0, 1.0)
    assert parse_color("#0000bf") == pytest.approx((0.0, 0.0, 191 / 255.0), rel=1e-3)

    # Fallback default
    assert parse_color("invalid_color") == (0.0, 0.0, 0.75)
    assert parse_color((0.2, 0.4, 0.6)) == (0.2, 0.4, 0.6)


def test_split_and_scale_title_short():
    title = "Short Title"
    s1, s2, fs = split_and_scale_title(title, default_fontsize=11.0)
    assert s1 == "Short Title"
    assert s2 == ""
    assert fs == 11.0


def test_split_and_scale_title_long():
    title = "This is a very long title for an experiment that demonstrates configuring IoT gateways using MQTT and CoAP protocols in simulation environments"
    s1, s2, fs = split_and_scale_title(title, default_fontsize=11.0)
    assert len(s1) > 0
    assert len(s2) > 0
    assert fs <= 11.0


def test_create_filled_header_doc():
    data = {
        "sem": "VII",
        "class_name": "BE IT",
        "batch": "I3",
        "roll_no": "34",
        "name": "Test Student",
        "subject": "Internet of Things",
        "is_assignment": False,
        "exp_no": "Exp - 1",
        "title": "Study of Raspberry Pi and Sensors",
        "perf_date": "01/08/2026",
        "sub_date": "08/08/2026",
    }
    formatting = {
        "text_color": "#0000bf",
        "strikethrough_enabled": True,
        "font_size": 11,
        "font_name": "helv",
    }
    doc = create_filled_header_doc(TEMPLATE_PATH, data, formatting)
    assert isinstance(doc, fitz.Document)
    assert len(doc) == 1
    text = doc[0].get_text()
    assert "Test Student" in text
    assert "Internet of Things" in text
    doc.close()


def test_render_header_preview_png():
    data = {
        "name": "Preview Student",
        "subject": "Cloud Computing",
        "exp_no": "Assign - 2",
        "is_assignment": True,
    }
    formatting = {"text_color": "black", "strikethrough_enabled": True}
    data_url = render_header_preview_png(TEMPLATE_PATH, data, formatting, dpi=72)
    assert data_url.startswith("data:image/png;base64,")
    assert len(data_url) > 100


def test_generate_job_documents(tmp_path):
    output_dir = str(tmp_path / "output")
    uploads_dir = str(tmp_path / "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    student = {
        "name": "Job Student",
        "roll_no": "42",
        "batch": "A1",
        "class_name": "TE IT",
        "sem": "VI",
        "subject": "Network Security",
        "text_color": "blue",
        "strikethrough_enabled": True,
    }
    experiments = [
        {
            "num": 1,
            "label": "1",
            "title": "Implementation of RSA Algorithm",
            "is_assignment": False,
            "perf_date": "10/01/2026",
            "sub_date": "17/01/2026",
        },
        {
            "num": 2,
            "label": "2",
            "title": "Study of Diffie-Hellman Key Exchange",
            "is_assignment": True,
            "perf_date": "17/01/2026",
            "sub_date": "24/01/2026",
        },
    ]

    job_id = "test_job_123"
    result = generate_job_documents(
        job_id=job_id,
        template_path=TEMPLATE_PATH,
        uploads_dir=uploads_dir,
        output_dir=output_dir,
        student=student,
        experiments=experiments,
        include_toc=True,
    )

    assert result["success"] is True
    assert result["job_id"] == job_id
    assert len(result["files"]) == 2

    # Check generated files exist in job-scoped folder
    job_dir = os.path.join(output_dir, job_id)
    assert os.path.exists(os.path.join(output_dir, result["combined_pdf"]))
    assert os.path.exists(os.path.join(output_dir, result["zip_package"]))
    assert os.path.exists(os.path.join(job_dir, "Exp_1_with_Header.pdf"))
    assert os.path.exists(os.path.join(job_dir, "Assign_2_with_Header.pdf"))


def test_generate_toc_page():
    from lab_core.toc_engine import generate_toc_page

    student = {
        "name": "TOC Student",
        "roll_no": "15",
        "batch": "T1",
        "class_name": "BE Comp",
        "sem": "VIII",
        "subject": "Distributed Systems",
    }
    entries = [
        {
            "label": "1",
            "is_assignment": False,
            "title": "MapReduce Implementation",
            "perf_date": "01/02/2026",
            "sub_date": "08/02/2026",
            "page_range": "2-5",
        },
        {
            "label": "2",
            "is_assignment": True,
            "title": "Paxos Consensus Algorithm",
            "perf_date": "08/02/2026",
            "sub_date": "15/02/2026",
            "page_range": "6-10",
        },
    ]
    doc = generate_toc_page(student, entries)
    assert isinstance(doc, fitz.Document)
    assert len(doc) == 1
    text = doc[0].get_text()
    assert "INDEX / TABLE OF CONTENTS" in text
    assert "MapReduce Implementation" in text
    assert "Paxos Consensus Algorithm" in text
    assert "2-5" in text
    doc.close()

