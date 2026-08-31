import os
import fitz
from lab_core.extractor import inspect_pdf_info, extract_aim_from_pdf, normalize_exp_number


def test_normalize_exp_number():
    assert normalize_exp_number("iv") == "4"
    assert normalize_exp_number("IX") == "9"
    assert normalize_exp_number("05") == "5"
    assert normalize_exp_number("4a") == "4a"


def test_inspect_pdf_info_nonexistent():
    info = inspect_pdf_info("nonexistent.pdf")
    assert info["aim"] is None
    assert info["pages"] == 0
    assert info["exp_num"] is None


def test_inspect_pdf_info_with_synthetic_pdf(tmp_path):
    pdf_path = str(tmp_path / "test_exp.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Experiment No: 5")
    page.insert_text((50, 130), "Aim: To study and implement MQTT Protocol for IoT sensor nodes.")
    page.insert_text((50, 160), "Theory: MQTT is a lightweight publish-subscribe network protocol.")
    doc.save(pdf_path)
    doc.close()

    info = inspect_pdf_info(pdf_path)
    assert info["pages"] == 1
    assert info["exp_num"] == "5"
    assert info["is_assignment"] is False
    assert "To study and implement MQTT Protocol" in info["aim"]

    aim = extract_aim_from_pdf(pdf_path)
    assert aim is not None
    assert "MQTT" in aim


def test_inspect_pdf_info_roman_and_assignment(tmp_path):
    pdf_path = str(tmp_path / "Assignment_IV.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Assignment No: IV")
    page.insert_text((50, 130), "Objective: Configure Docker Compose for Multi-Container Apps.")
    doc.save(pdf_path)
    doc.close()

    info = inspect_pdf_info(pdf_path)
    assert info["exp_num"] == "4"
    assert info["is_assignment"] is True
    assert "Configure Docker Compose" in info["aim"]


def test_inspect_pdf_info_practical_and_filename_fallback(tmp_path):
    pdf_path = str(tmp_path / "Prac_07.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Lab Session 7: Performance Evaluation of Dijkstra Routing")
    doc.save(pdf_path)
    doc.close()

    info = inspect_pdf_info(pdf_path)
    assert info["exp_num"] == "7"
    assert "Performance Evaluation" in info["aim"]
