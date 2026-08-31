import os
import sys
import subprocess
import pytest
import fitz
from fill_headers import load_config


def test_load_config_nonexistent(tmp_path):
    assert load_config(str(tmp_path / "nonexistent.json")) == {}


def test_load_config_valid(tmp_path):
    cfg_file = tmp_path / "test_config.json"
    cfg_file.write_text('{"student": {"name": "Test User"}}', encoding="utf-8")
    loaded = load_config(str(cfg_file))
    assert loaded["student"]["name"] == "Test User"


def test_cli_help():
    res = subprocess.run([sys.executable, "fill_headers.py", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Configurable Experiment / Assignment Header Filler" in res.stdout


def test_cli_execution_no_files(tmp_path):
    res = subprocess.run(
        [sys.executable, "fill_headers.py", "--output-dir", str(tmp_path / "out")],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "No 'Experiment <N>.pdf' files found" in res.stdout


def test_cli_execution_with_synthetic_files(tmp_path):
    # Create synthetic experiment file in working dir or temp
    out_dir = tmp_path / "cli_out"
    exp_file = "Experiment 1.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Experiment 1: Introduction to CLI Testing")
    page.insert_text((50, 130), "Aim: Verify CLI execution.")
    doc.save(exp_file)
    doc.close()

    try:
        res = subprocess.run(
            [
                sys.executable,
                "fill_headers.py",
                "--name", "CLI Student",
                "--roll-no", "77",
                "--batch", "C2",
                "--class-name", "BE IT",
                "--sem", "VIII",
                "--subject", "Automated QA",
                "--output-dir", str(out_dir),
                "--assignments", "1",
            ],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "SUCCESS! Processed 1 headers" in res.stdout
        assert os.path.exists(out_dir / "Experiment_1_with_Header.pdf")
        assert os.path.exists(out_dir / "headers" / "Header_Exp_1.pdf")
        assert os.path.exists(out_dir / "All_Documents_Combined.pdf") or os.path.exists(out_dir / "All_Experiments_Combined.pdf")
    finally:
        if os.path.exists(exp_file):
            os.remove(exp_file)
