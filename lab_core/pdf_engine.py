import os
import re
import math
import uuid
import base64
import zipfile
import pymupdf as fitz
from typing import Dict, Any, List, Optional, Tuple

# Default institutional Header.pdf template path
DEFAULT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Header.pdf"
)


def parse_color(color: Any) -> Tuple[float, float, float]:
    """
    Parses a color string (named or hex) or tuple into normalized RGB floats for PyMuPDF.

    :param color: e.g. '#0000bf', 'blue', 'black', (0.2, 0.4, 0.6)
    :return: (r, g, b) tuple where 0.0 <= c <= 1.0
    """
    if isinstance(color, (list, tuple)) and len(color) == 3:
        return (float(color[0]), float(color[1]), float(color[2]))

    NAMED_COLORS = {
        "blue": (0.0, 0.0, 0.75),
        "black": (0.0, 0.0, 0.0),
        "red": (0.8, 0.0, 0.0),
        "darkblue": (0.0, 0.0, 0.5),
        "navy": (0.0, 0.0, 0.5),
        "green": (0.0, 0.5, 0.0),
        "purple": (0.5, 0.0, 0.5),
        "white": (1.0, 1.0, 1.0),
    }

    if not isinstance(color, str):
        return (0.0, 0.0, 0.75)

    c_str = color.strip().lower()
    if c_str in NAMED_COLORS:
        return NAMED_COLORS[c_str]

    c_clean = c_str.lstrip("#")
    if len(c_clean) == 3:
        try:
            r = int(c_clean[0] * 2, 16) / 255.0
            g = int(c_clean[1] * 2, 16) / 255.0
            b = int(c_clean[2] * 2, 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0.0, 0.0, 0.75)
    elif len(c_clean) == 6:
        try:
            r = int(c_clean[0:2], 16) / 255.0
            g = int(c_clean[2:4], 16) / 255.0
            b = int(c_clean[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0.0, 0.0, 0.75)

    return (0.0, 0.0, 0.75)


def split_and_scale_title(
    title: str,
    font_name: str = "helv",
    max_w1: float = 435.0,
    max_w2: float = 478.0,
    min_font_size: float = 8.0,
    max_font_size: float = 11.0,
    default_fontsize: Optional[float] = None,
) -> Tuple[str, str, float]:
    """
    Calculates the optimum font size and two-line split for long experiment titles.

    :param title: Experiment or assignment title string.
    :param font_name: Base font name recognized by PyMuPDF (default 'helv').
    :param max_w1: Max printable width on Line 1 in PDF points (106 to 541).
    :param max_w2: Max printable width on Line 2 in PDF points (63 to 541).
    :param min_font_size: Minimum permissible font size (default 8.0).
    :param max_font_size: Maximum permissible font size (default 11.0).
    :param default_fontsize: Optional alias for max_font_size.
    :return: (line1, line2, font_size)
    """
    if default_fontsize is not None:
        max_font_size = default_fontsize

    title = title.strip()
    if not title:
        return ("", "", max_font_size)

    # Fast path: fits comfortably on line 1 at max font size
    if fitz.get_text_length(title, fontname=font_name, fontsize=max_font_size) <= max_w1:
        return (title, "", max_font_size)

    words = title.split()

    # Search downward from max_font_size to min_font_size
    current_size = max_font_size
    while current_size >= min_font_size:
        # Check single line fit at current size
        if fitz.get_text_length(title, fontname=font_name, fontsize=current_size) <= max_w1:
            return (title, "", current_size)

        # Word-chunk split across two lines
        if len(words) > 1:
            line1_words = []
            line2_words = []
            w1 = 0
            for idx, w in enumerate(words):
                ww = fitz.get_text_length(w + " ", fontname=font_name, fontsize=current_size)
                if w1 + ww <= max_w1:
                    line1_words.append(w)
                    w1 += ww
                else:
                    line2_words = words[idx:]
                    break

            str1 = " ".join(line1_words)
            str2 = " ".join(line2_words)
            w2 = fitz.get_text_length(str2, fontname=font_name, fontsize=current_size) if line2_words else 0

            if w2 <= max_w2 or current_size <= min_font_size:
                if w2 > max_w2:
                    while line2_words and fitz.get_text_length(" ".join(line2_words) + "...", fontname=font_name, fontsize=current_size) > max_w2:
                        line2_words.pop()
                    str2 = " ".join(line2_words) + "..."
                return (str1, str2, current_size)

        current_size -= 0.5

    # Fallback for single unbroken long words: hard character split
    mid = len(title) // 2
    l1 = title[:mid]
    l2 = title[mid:]
    return (l1, l2, min_font_size)


def create_filled_header_doc(
    template_path: str,
    data: Dict[str, Any],
    formatting: Optional[Dict[str, Any]] = None,
) -> fitz.Document:
    """
    Opens the Header.pdf template and inserts all student, experiment, and date metadata.

    :param template_path: Absolute path to Header.pdf
    :param data: Dictionary containing:
           sem, class_name, batch, roll_no, name, subject,
           is_assignment, exp_no, title, perf_date, sub_date
    :param formatting: Dictionary containing:
           text_color (hex), font_name, strikethrough_enabled (bool)
    :return: Filled PyMuPDF Document
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Header template not found: {template_path}")

    fmt = formatting or {}
    font_color = parse_color(fmt.get("text_color", "#000000"))
    font_name = fmt.get("font_name", "helv")
    font_size = 11.0
    strikethrough_enabled = fmt.get("strikethrough_enabled", True)

    doc = fitz.open(template_path)
    page = doc[0]

    # 1. Top Student Details Line (Y ~ 225)
    page.insert_text((100, 225), str(data.get("sem", "")), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((205, 225), str(data.get("class_name", "")), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((330, 225), str(data.get("batch", "")), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((470, 225), str(data.get("roll_no", "")), fontsize=font_size, fontname=font_name, color=font_color)

    # 2. Name & Subject
    page.insert_text((110, 266), str(data.get("name", "")), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((125, 287), str(data.get("subject", "")), fontsize=font_size, fontname=font_name, color=font_color)

    # 3. Experiment vs Assignment Strikethrough
    is_assignment = data.get("is_assignment", False)
    if strikethrough_enabled:
        if is_assignment:
            # Strike through 'EXPERIMENT NO. /'
            page.draw_line(fitz.Point(62.9, 327.9), fitz.Point(174.3, 327.9), color=font_color, width=1.5)
        else:
            # Strike through '/ ASSIGNMENT NO.'
            page.draw_line(fitz.Point(170.0, 327.9), fitz.Point(285.0, 327.9), color=font_color, width=1.5)

    # 4. Experiment / Assignment Number (Clean number only, stripped of any prefix)
    exp_num_raw = str(data.get("exp_no", ""))
    exp_num_str = re.sub(r'^(?:Exp|Experiment|Assign|Assgn|Assignment)[\s:_.\-]*', '', exp_num_raw, flags=re.IGNORECASE).strip()
    page.insert_text((290, 330), exp_num_str, fontsize=font_size, fontname=font_name, color=font_color)

    # 5. Title with dynamic two-line wrap
    title_str = str(data.get("title", ""))
    if title_str:
        l1, l2, t_size = split_and_scale_title(title_str, font_name=font_name)
        if l1:
            page.insert_text((106, 351), l1, fontsize=t_size, fontname=font_name, color=font_color)
        if l2:
            page.insert_text((63, 372), l2, fontsize=t_size, fontname=font_name, color=font_color)

    # 6. Dates
    page.insert_text((220, 414), str(data.get("perf_date", "")), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((205, 435), str(data.get("sub_date", "")), fontsize=font_size, fontname=font_name, color=font_color)

    return doc


def render_header_preview_png(
    template_path: str,
    data: Dict[str, Any],
    formatting: Optional[Dict[str, Any]] = None,
    dpi: int = 150,
) -> str:
    """
    Fills a header page and renders it to a base64 Data URL PNG image for live preview.

    :return: Data URL string (e.g. 'data:image/png;base64,...')
    """
    doc = create_filled_header_doc(template_path, data, formatting)
    try:
        page = doc[0]
        pix = page.get_pixmap(dpi=dpi)
        b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    finally:
        doc.close()


def resolve_body_pdf(
    item: Dict[str, Any],
    uploads_dir: str,
    base_dir: str = "",
) -> Optional[str]:
    """
    Resolves the physical filesystem path for an experiment's attached body PDF.
    Strictly validates content-addressed hashes to prevent Local File Inclusion (LFI).
    """
    # 1. Content-addressed hash lookup (used by Web UI)
    file_hash = str(item.get("hash") or "").strip().lower()
    if file_hash and len(file_hash) == 64 and all(c in "0123456789abcdef" for c in file_hash):
        candidate = os.path.abspath(os.path.join(uploads_dir, f"{file_hash}.pdf"))
        uploads_root = os.path.abspath(uploads_dir)
        if candidate.startswith(uploads_root + os.sep) and os.path.isfile(candidate):
            return candidate

    # 2. Safe local filename lookup (used by CLI fill_headers.py and tests)
    filename = item.get("filename")
    if filename and base_dir:
        safe_fn = os.path.basename(filename)
        cand = os.path.abspath(os.path.join(base_dir, safe_fn))
        base_root = os.path.abspath(base_dir)
        if cand.startswith(base_root + os.sep) and os.path.isfile(cand):
            return cand

    return None


def generate_job_documents(
    student: Dict[str, Any],
    experiments: List[Dict[str, Any]],
    output_dir: str,
    uploads_dir: str,
    template_path: str = DEFAULT_TEMPLATE_PATH,
    formatting: Optional[Dict[str, Any]] = None,
    include_toc: bool = True,
    base_dir: str = "",
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Core batch processing pipeline. Generates:
    - Filled standalone header PDFs in headers/
    - Merged Exp_X_with_Header.pdf files for each experiment
    - Master combined PDF with clickable outline bookmarks and multi-page TOC (if enabled)
    - Full ZIP package containing all individual files + combined PDF

    :return: dict with success, job_id, combined_pdf, zip_package, files
    """
    from .toc_engine import generate_toc_page

    if not job_id:
        job_id = f"job_{uuid.uuid4().hex[:10]}"

    if not experiments:
        return {
            "success": False,
            "error": "No experiment documents provided.",
            "job_id": job_id,
        }

    job_output_dir = os.path.join(output_dir, job_id)
    os.makedirs(job_output_dir, exist_ok=True)

    combined_doc = fitz.open()
    generated_files = []
    zip_entries = []
    toc_entries = []

    # Calculate exact dynamic TOC page count
    if include_toc:
        rows_page1 = 20
        rows_subsequent = 24
        total_entries = len(experiments)
        if total_entries <= rows_page1:
            toc_page_count = 1
        else:
            toc_page_count = 1 + math.ceil((total_entries - rows_page1) / rows_subsequent)
    else:
        toc_page_count = 0

    # Experiment body pages start after the TOC
    current_page_counter = toc_page_count + 1

    try:
        for item in experiments:
            label = str(item.get("label", item.get("num", "?")))
            is_assgn = item.get("is_assignment", False)

            perf_d = item.get("perf_date") or student.get("perf_date", "")
            sub_d = item.get("sub_date") or student.get("sub_date", "")
            title = item.get("title", "")

            data = {
                "sem": student.get("sem", ""),
                "class_name": student.get("class_name", ""),
                "batch": student.get("batch", ""),
                "roll_no": student.get("roll_no", ""),
                "name": student.get("name", ""),
                "subject": student.get("subject", ""),
                "is_assignment": is_assgn,
                "exp_no": label,
                "title": title,
                "perf_date": perf_d,
                "sub_date": sub_d,
            }

            # 1. Fill header in-memory (no dead standalone disk write)
            header_doc = create_filled_header_doc(template_path, data, formatting)
            safe_label = re.sub(r"[^\w\-]", "_", label)

            # 2. Merge header + experiment body
            merged_doc = fitz.open()
            merged_doc.insert_pdf(header_doc)
            body_pages_count = 0

            body_path = resolve_body_pdf(item, uploads_dir, base_dir)
            if body_path:
                try:
                    body_doc = fitz.open(body_path)
                    if body_doc.is_encrypted:
                        if not body_doc.authenticate(""):
                            raise fitz.PasswordError("Encrypted PDF without open permission.")
                    body_pages_count = len(body_doc)
                    merged_doc.insert_pdf(body_doc)
                    body_doc.close()
                except Exception:
                    body_pages_count = 0

            # Page count for this experiment is 1 (header) + body pages
            total_exp_pages = 1 + body_pages_count
            start_p = current_page_counter
            end_p = current_page_counter + total_exp_pages - 1
            page_range_str = f"{start_p}" if start_p == end_p else f"{start_p}-{end_p}"
            current_page_counter += total_exp_pages

            toc_entries.append({
                "label": label,
                "is_assignment": is_assgn,
                "title": title or (f"Assignment {label}" if is_assgn else f"Experiment {label}"),
                "perf_date": perf_d,
                "sub_date": sub_d,
                "page_range": page_range_str,
                "start_page": start_p,
            })

            type_prefix = "Assign" if is_assgn else "Exp"
            merged_filename = f"{type_prefix}_{safe_label}_with_Header.pdf"
            merged_out = os.path.join(job_output_dir, merged_filename)
            merged_doc.save(
                merged_out,
                garbage=4,
                deflate=True,
                clean=True,
                deflate_images=True,
                deflate_fonts=True,
            )

            # Append to master document
            combined_doc.insert_pdf(merged_doc)

            generated_files.append({
                "label": label,
                "merged_pdf": f"{job_id}/{merged_filename}",
            })
            zip_entries.append((merged_out, merged_filename))

            header_doc.close()
            merged_doc.close()

        # Generate & Prepend TOC page(s) if enabled (Zero-copy in-memory prepend)
        if include_toc:
            with generate_toc_page(student, toc_entries, formatting) as toc_doc:
                combined_doc.insert_pdf(toc_doc, start_at=0)

            # Add in-page clickable table row links now that combined_doc contains all destination pages
            try:
                entry_idx = 0
                for page_num in range(toc_page_count):
                    toc_p = combined_doc[page_num]
                    page_cap = 20 if page_num == 0 else 24
                    table_top = 148 if page_num == 0 else 80
                    row_height = 28
                    curr_y = table_top + 22
                    page_entries = toc_entries[entry_idx : entry_idx + page_cap]
                    entry_idx += len(page_entries)
                    for item in page_entries:
                        target_p = item.get("start_page")
                        if target_p and 0 <= (target_p - 1) < len(combined_doc):
                            row_rect = fitz.Rect(45, curr_y, 565, curr_y + row_height)
                            toc_p.insert_link({"kind": fitz.LINK_GOTO, "from": row_rect, "page": target_p - 1})
                        curr_y += row_height
            except Exception:
                pass

        # Construct meaningful, student-friendly filenames
        roll_no = str(student.get("roll_no", "")).strip()
        subject = str(student.get("subject", "")).strip()
        name = str(student.get("name", "")).strip()

        name_parts = []
        if roll_no:
            name_parts.append(roll_no)
        if subject:
            name_parts.append(subject)
        elif name:
            name_parts.append(name)

        base_stem = "_".join(name_parts) if name_parts else "Lab_Report"
        safe_stem = re.sub(r"[^\w\-]", "_", base_stem).strip("_")
        if not safe_stem:
            safe_stem = "Lab_Report"

        combined_filename = f"{safe_stem}_Combined.pdf"
        zip_filename = f"{safe_stem}_Package.zip"

        # Build clickable interactive PDF Bookmarks / Outline
        bookmarks = []
        if include_toc:
            bookmarks.append([1, "Index / Table of Contents", 1])

        for entry in toc_entries:
            prefix = "Assignment" if entry["is_assignment"] else "Experiment"
            bm_title = f"{prefix} {entry['label']}: {entry['title']}"
            bookmarks.append([1, bm_title, entry["start_page"]])

        if bookmarks:
            try:
                combined_doc.set_toc(bookmarks)
            except Exception:
                pass  # Fallback gracefully if bookmarks cannot be set

        # Save master combined PDF with maximum compression
        combined_path = os.path.join(job_output_dir, combined_filename)
        combined_doc.save(
            combined_path,
            garbage=4,
            deflate=True,
            clean=True,
            deflate_images=True,
            deflate_fonts=True,
        )

        # Create ZIP archive inside job_output_dir using ZIP_STORED (fast packaging of deflated PDFs)
        zip_path = os.path.join(job_output_dir, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            zf.write(combined_path, combined_filename)
            for fpath, arcname in zip_entries:
                zf.write(fpath, os.path.join("Individual_Files", arcname))

    finally:
        if combined_doc is not None:
            combined_doc.close()

    return {
        "success": True,
        "job_id": job_id,
        "combined_pdf": f"{job_id}/{combined_filename}",
        "zip_package": f"{job_id}/{zip_filename}",
        "files": generated_files,
    }
