import os
import re
import json
import argparse
import shutil
import fitz  # PyMuPDF

from lab_core import (
    parse_color,
    split_and_scale_title,
    create_filled_header_doc,
    inspect_pdf_info,
    generate_toc_page,
)

DEFAULT_CONFIG_FILE = "config.json"
TEMPLATE_HEADER_FILE = "Header.pdf"


def load_config(config_path):
    """Loads configuration file if it exists."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {config_path}: {e}")
    return {}


def main():
    parser = argparse.ArgumentParser(description="Configurable Experiment / Assignment Header Filler")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help="Path to config JSON file")
    parser.add_argument("--template", default=TEMPLATE_HEADER_FILE, help="Path to template Header PDF")
    parser.add_argument("--sem", help="Semester (e.g. VII)")
    parser.add_argument("--class-name", help="Class Name (e.g. BE IT)")
    parser.add_argument("--batch", help="Batch (e.g. I3)")
    parser.add_argument("--roll-no", help="Roll Number (e.g. 34)")
    parser.add_argument("--name", help="Student Name (e.g. Bhavya Shah)")
    parser.add_argument("--subject", help="Subject Name (e.g. Internet of Things)")
    parser.add_argument("--perf-date", help="Date of Performance")
    parser.add_argument("--sub-date", help="Date of Submission")
    parser.add_argument("--color", help="Text color (blue, darkblue, black, #HEX)")
    parser.add_argument("--assignments", nargs="+", type=int, help="List of experiment numbers that are assignments (e.g. --assignments 2 4 6)")
    parser.add_argument("--type", choices=["experiment", "assignment"], help="Force all documents to experiment or assignment")
    parser.add_argument("--no-strikethrough", action="store_true", help="Disable strikethrough lines")
    parser.add_argument("--include-toc", action="store_true", default=True, help="Include Index (TOC) sheet in combined PDF")
    parser.add_argument("--no-toc", action="store_false", dest="include_toc", help="Disable Index (TOC) sheet")
    parser.add_argument("--aim-mode", default="auto", choices=["auto", "first_period", "header_title"], help="Aim extraction heuristic mode")
    parser.add_argument("--output-dir", help="Output directory")

    args = parser.parse_args()

    # Load config file
    config = load_config(args.config)
    student_cfg = config.get("student", {})
    dates_cfg = config.get("dates", {})
    fmt_cfg = config.get("formatting", {})
    out_cfg = config.get("output", {})
    exp_cfg_list = config.get("experiments", [])

    # Merge CLI options over Config file options
    name = args.name or student_cfg.get("name", "Bhavya Shah")
    roll_no = args.roll_no or student_cfg.get("roll_no", "34")
    batch = args.batch or student_cfg.get("batch", "I3")
    class_name = args.class_name or student_cfg.get("class_name", "BE IT")
    sem = args.sem or student_cfg.get("sem", "VII")
    subject = args.subject or student_cfg.get("subject", "Internet of Things")

    perf_date_global = args.perf_date if args.perf_date is not None else dates_cfg.get("performance_date", "")
    sub_date_global = args.sub_date if args.sub_date is not None else dates_cfg.get("submission_date", "")

    text_color = args.color or fmt_cfg.get("text_color", "blue")
    strikethrough_enabled = not args.no_strikethrough if args.no_strikethrough else fmt_cfg.get("strikethrough_enabled", True)
    include_toc = args.include_toc

    font_size = fmt_cfg.get("font_size", 11)
    font_name = fmt_cfg.get("font_name", "helv")

    output_dir = args.output_dir or out_cfg.get("output_dir", "output")
    combine_pdf = out_cfg.get("combine_all_experiments", True)
    copy_to_root = out_cfg.get("copy_combined_to_root", True)

    formatting = {
        "text_color": text_color,
        "strikethrough_enabled": strikethrough_enabled,
        "font_size": font_size,
        "font_name": font_name,
    }

    template_file = args.template
    if not os.path.exists(template_file):
        print(f"Error: Template PDF '{template_file}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    headers_dir = os.path.join(output_dir, "headers")
    os.makedirs(headers_dir, exist_ok=True)

    print("=" * 60)
    print("      EXPERIMENT / ASSIGNMENT HEADER GENERATOR")
    print("=" * 60)
    print(f" Config File    : {args.config if os.path.exists(args.config) else 'None (Defaults)'}")
    print(f" Template       : {template_file}")
    print(f" Name           : {name}")
    print(f" Roll No        : {roll_no}")
    print(f" Batch          : {batch}")
    print(f" Class          : {class_name}")
    print(f" Semester       : {sem}")
    print(f" Subject        : {subject}")
    print(f" Index (TOC)    : {'Enabled' if include_toc else 'Disabled'}")
    print(f" Strikethrough  : {'Enabled' if strikethrough_enabled else 'Disabled'}")
    print(f" Text Color     : {text_color}")
    print(f" Output Dir     : {output_dir}")
    print("=" * 60)

    exp_map = {item.get("num"): item for item in exp_cfg_list if isinstance(item, dict) and "num" in item}
    assignment_set = set(args.assignments) if args.assignments else None

    # Discover candidate files in current directory
    found_files = []
    for i in range(1, 51):
        candidates = [
            f"Experiment {i}.pdf",
            f"Exp_{i}.pdf",
            f"Exp {i}.pdf",
            f"Assignment {i}.pdf",
            f"Assign_{i}.pdf",
            f"Assign {i}.pdf",
        ]
        for cand in candidates:
            if os.path.exists(cand):
                found_files.append((i, cand))
                break

    if not found_files:
        print("No 'Experiment <N>.pdf' files found to process.")
        return

    combined_doc = fitz.open() if combine_pdf else None
    toc_entries = []
    if include_toc:
        total_found = len(found_files)
        toc_page_count = 1 if total_found <= 20 else 1 + math.ceil((total_found - 20) / 24)
    else:
        toc_page_count = 0
    current_page_counter = toc_page_count + 1 if include_toc else 1
    processed_count = 0

    student_data = {
        "name": name,
        "roll_no": roll_no,
        "batch": batch,
        "class_name": class_name,
        "sem": sem,
        "subject": subject,
    }

    for i, exp_file in found_files:
        custom_exp_cfg = exp_map.get(i, {})
        custom_title = custom_exp_cfg.get("title")

        info = inspect_pdf_info(exp_file, mode=args.aim_mode)
        if custom_title and custom_title != "Auto":
            title = custom_title
        else:
            title = info.get("aim") or f"Experiment {i}"

        p_date = custom_exp_cfg.get("perf_date") or perf_date_global
        s_date = custom_exp_cfg.get("sub_date") or sub_date_global

        if args.type == "assignment":
            is_assignment = True
        elif args.type == "experiment":
            is_assignment = False
        elif assignment_set is not None:
            is_assignment = (i in assignment_set)
        elif info.get("is_assignment") is not None:
            is_assignment = info.get("is_assignment")
        else:
            is_assignment = custom_exp_cfg.get("is_assignment", False)

        doc_type_str = "Assignment" if is_assignment else "Experiment"
        type_prefix = "Assign" if is_assignment else "Exp"

        data = {
            "sem": sem,
            "class_name": class_name,
            "batch": batch,
            "roll_no": roll_no,
            "name": name,
            "subject": subject,
            "is_assignment": is_assignment,
            "exp_no": str(i),
            "title": title,
            "perf_date": p_date,
            "sub_date": s_date,
        }

        # 1. Fill Header PDF
        header_doc = create_filled_header_doc(template_file, data, formatting)
        header_out = os.path.join(headers_dir, f"Header_Exp_{i}.pdf")
        header_doc.save(header_out, garbage=4, deflate=True)

        # 2. Merge Header + Body PDF
        merged_doc = fitz.open()
        merged_doc.insert_pdf(header_doc)

        body_doc = fitz.open(exp_file)
        body_pages = len(body_doc)
        merged_doc.insert_pdf(body_doc)
        body_doc.close()

        merged_filename = f"Experiment_{i}_with_Header.pdf"
        merged_out = os.path.join(output_dir, merged_filename)
        merged_doc.save(merged_out, garbage=4, deflate=True, clean=True)

        # Track page numbers for TOC
        total_exp_pages = 1 + body_pages
        start_p = current_page_counter
        end_p = current_page_counter + total_exp_pages - 1
        page_range_str = f"{start_p}" if start_p == end_p else f"{start_p}-{end_p}"
        current_page_counter += total_exp_pages

        toc_entries.append({
            "label": str(i),
            "is_assignment": is_assignment,
            "title": title,
            "perf_date": p_date,
            "sub_date": s_date,
            "page_range": page_range_str,
            "start_page": start_p,
        })

        if combined_doc is not None:
            combined_doc.insert_pdf(merged_doc)

        header_doc.close()
        merged_doc.close()
        processed_count += 1
        print(f"[{processed_count}/{len(found_files)}] Processed: {doc_type_str} {i} ({exp_file})")

    # Finalize Combined Document
    if combined_doc is not None:
        if include_toc and toc_entries:
            toc_doc = generate_toc_page(student_data, toc_entries, formatting)
            master_doc = fitz.open()
            master_doc.insert_pdf(toc_doc)
            master_doc.insert_pdf(combined_doc)
            toc_doc.close()
            combined_doc.close()
            combined_doc = master_doc

        # Interactive Bookmarks
        bookmarks = []
        if include_toc:
            bookmarks.append([1, "Index / Table of Contents", 1])
        for entry in toc_entries:
            prefix = "Assignment" if entry["is_assignment"] else "Experiment"
            bookmarks.append([1, f"{prefix} {entry['label']}: {entry['title']}", entry["start_page"]])
        if bookmarks:
            try:
                combined_doc.set_toc(bookmarks)
            except Exception:
                pass

        # Construct filename
        name_parts = []
        if roll_no:
            name_parts.append(str(roll_no))
        if subject:
            name_parts.append(str(subject))
        elif name:
            name_parts.append(str(name))
        stem = re.sub(r"[^\w\-]", "_", "_".join(name_parts)).strip("_") or "Lab_Report"
        combined_filename = f"{stem}_Combined.pdf"

        final_combined_path = os.path.join(output_dir, combined_filename)
        combined_doc.save(final_combined_path, garbage=4, deflate=True, clean=True)

        # Also save legacy All_Experiments_Combined.pdf for compatibility
        legacy_path = os.path.join(output_dir, "All_Experiments_Combined.pdf")
        shutil.copy2(final_combined_path, legacy_path)

        combined_doc.close()

        if copy_to_root:
            shutil.copy2(final_combined_path, combined_filename)
            print(f"\n[OK] Combined PDF generated: {combined_filename}")

    print("=" * 60)
    print(f"SUCCESS! Processed {processed_count} headers.")
    print("=" * 60)


if __name__ == "__main__":
    main()
