import math
import fitz
from typing import Dict, Any, List, Optional
from .pdf_engine import parse_color


def generate_toc_page(
    student: Dict[str, Any],
    experiment_entries: List[Dict[str, Any]],
    formatting: Optional[Dict[str, Any]] = None,
) -> fitz.Document:
    """
    Generates a standardized institutional Index / Table of Contents A4 PDF document.
    Dynamically paginates across multiple pages if experiment_entries exceed single page capacity.

    :param student: dict with name, roll_no, batch, class_name, sem, subject
    :param experiment_entries: list of dicts with:
           label, title, perf_date, sub_date, page_range, is_assignment
    :param formatting: dict with text_color, font_name
    :return: PyMuPDF Document containing the generated Index page(s).
    """
    fmt = formatting or {}
    font_color = parse_color(fmt.get("text_color", "#000000"))
    border_color = (0.2, 0.2, 0.2)
    header_bg = (0.93, 0.93, 0.95)

    doc = fitz.open()

    # Column coordinates & titles
    col_x = [36, 75, 145, 390, 445, 505, 559]
    col_titles = ["Sr No", "Perf. Date", "Experiment / Assignment Title", "Page No", "Sub. Date", "Sign"]
    row_height = 28

    total_entries = len(experiment_entries)
    
    # Page 1 capacity: 20 rows (room for student box & header)
    # Subsequent pages: 24 rows
    rows_page1 = 20
    rows_subsequent = 24

    if total_entries <= rows_page1:
        total_pages = 1
    else:
        total_pages = 1 + math.ceil((total_entries - rows_page1) / rows_subsequent)

    entry_idx = 0

    for page_num in range(1, total_pages + 1):
        page = doc.new_page(width=595.32, height=841.92)  # A4 size

        # 1. Main Header Title
        title_text = "INDEX / TABLE OF CONTENTS" if total_pages == 1 else f"INDEX / TABLE OF CONTENTS (Page {page_num} of {total_pages})"
        page.draw_rect(fitz.Rect(36, 36, 559, 70), color=border_color, fill=(0.95, 0.95, 0.97), width=1)
        page.insert_text(
            (190 if total_pages > 1 else 210, 58),
            title_text,
            fontsize=12 if total_pages > 1 else 13,
            fontname="helv",
            color=(0, 0, 0),
        )

        if page_num == 1:
            # 2. Student Details Box (Only on Page 1)
            page.draw_rect(fitz.Rect(36, 78, 559, 138), color=border_color, width=1)
            page.insert_text((45, 96), f"Name: {student.get('name', '')}", fontsize=10, fontname="helv", color=font_color)
            page.insert_text((400, 96), f"Roll No: {student.get('roll_no', '')}", fontsize=10, fontname="helv", color=font_color)
            page.insert_text((45, 114), f"Subject: {student.get('subject', '')}", fontsize=10, fontname="helv", color=font_color)
            page.insert_text(
                (400, 114),
                f"Class: {student.get('class_name', '')} ({student.get('batch', '')})",
                fontsize=10,
                fontname="helv",
                color=font_color,
            )
            page.insert_text((45, 131), f"Semester: {student.get('sem', '')}", fontsize=10, fontname="helv", color=font_color)
            table_top = 148
            page_capacity = rows_page1
        else:
            table_top = 80
            page_capacity = rows_subsequent

        # 3. Table Column Headers
        page.draw_rect(
            fitz.Rect(col_x[0], table_top, col_x[-1], table_top + 22),
            color=border_color,
            fill=header_bg,
            width=1,
        )

        for i in range(len(col_titles)):
            tx = col_x[i] + 4
            ty = table_top + 15
            page.insert_text((tx, ty), col_titles[i], fontsize=8.5, fontname="helv", color=(0, 0, 0))
            page.draw_line(fitz.Point(col_x[i], table_top), fitz.Point(col_x[i], table_top + 22), color=border_color, width=1)
        page.draw_line(fitz.Point(col_x[-1], table_top), fitz.Point(col_x[-1], table_top + 22), color=border_color, width=1)

        # 4. Table Data Rows for this page
        current_y = table_top + 22
        page_entries = experiment_entries[entry_idx : entry_idx + page_capacity]
        entry_idx += len(page_entries)

        for item in page_entries:
            row_rect = fitz.Rect(col_x[0], current_y, col_x[-1], current_y + row_height)
            page.draw_rect(row_rect, color=border_color, width=0.75)

            for x in col_x:
                page.draw_line(fitz.Point(x, current_y), fitz.Point(x, current_y + row_height), color=border_color, width=0.75)

            label = str(item.get("label", ""))
            is_assgn = item.get("is_assignment", False)
            sr_str = f"A-{label}" if is_assgn else f"E-{label}"
            perf_d = str(item.get("perf_date", ""))
            sub_d = str(item.get("sub_date", ""))
            page_range = str(item.get("page_range", ""))
            title = str(item.get("title", ""))

            if len(title) > 48:
                title = title[:45] + "..."

            page.insert_text((col_x[0] + 5, current_y + 17), sr_str, fontsize=8.5, fontname="helv", color=font_color)
            page.insert_text((col_x[1] + 4, current_y + 17), perf_d, fontsize=8, fontname="helv", color=font_color)
            page.insert_text((col_x[2] + 4, current_y + 17), title, fontsize=8.5, fontname="helv", color=font_color)
            page.insert_text((col_x[3] + 8, current_y + 17), page_range, fontsize=8.5, fontname="helv", color=font_color)
            page.insert_text((col_x[4] + 4, current_y + 17), sub_d, fontsize=8, fontname="helv", color=font_color)

            current_y += row_height

        # If on the last page and items are few, fill up to minimum 8 rows
        if page_num == total_pages:
            remaining_fill = max(0, 8 - len(page_entries))
            for _ in range(remaining_fill):
                if current_y + row_height > 780:
                    break
                row_rect = fitz.Rect(col_x[0], current_y, col_x[-1], current_y + row_height)
                page.draw_rect(row_rect, color=border_color, width=0.75)
                for x in col_x:
                    page.draw_line(fitz.Point(x, current_y), fitz.Point(x, current_y + row_height), color=border_color, width=0.75)
                current_y += row_height

            # Teacher Signature Footer on last page
            page.insert_text((45, 800), "Teacher In-Charge Signature: _______________________", fontsize=9, fontname="helv", color=(0, 0, 0))
            page.insert_text((420, 800), "Date of Evaluation: _____________", fontsize=9, fontname="helv", color=(0, 0, 0))

    return doc
