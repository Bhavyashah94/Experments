import os
import re
import json
import argparse
import fitz  # PyMuPDF

DEFAULT_CONFIG_FILE = "config.json"

def parse_color(color_val):
    """Parses color string ('blue', 'black', 'darkblue', or hex '#RRGGBB') into RGB float tuple."""
    if isinstance(color_val, (list, tuple)) and len(color_val) == 3:
        return tuple(color_val)
    
    color_val = str(color_val).lower().strip()
    color_map = {
        "blue": (0.0, 0.0, 0.75),
        "darkblue": (0.0, 0.0, 0.5),
        "black": (0.0, 0.0, 0.0),
        "red": (0.8, 0.0, 0.0)
    }
    if color_val in color_map:
        return color_map[color_val]
        
    if color_val.startswith("#") and len(color_val) == 7:
        try:
            r = int(color_val[1:3], 16) / 255.0
            g = int(color_val[3:5], 16) / 255.0
            b = int(color_val[5:7], 16) / 255.0
            return (r, g, b)
        except ValueError:
            pass
            
    return (0.0, 0.0, 0.75) # Default blue

def extract_aim(pdf_path):
    """Extract Aim text from an experiment PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = doc[0].get_text()
        doc.close()
        
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        aim_lines = []
        capture = False
        for line in lines:
            if line.startswith('Aim:'):
                capture = True
                aim_lines.append(line[4:].strip())
            elif capture:
                if re.match(r'^\d+\.|\bObjectives\b', line):
                    break
                aim_lines.append(line)
        aim = ' '.join(aim_lines)
        return aim if aim else None
    except Exception as e:
        print(f"Warning: Could not extract aim from {pdf_path}: {e}")
        return None

def split_and_scale_title(title, font_name='helv', max_w1=439, max_w2=480, min_fontsize=8.0, default_fontsize=11.0):
    """Dynamically scales font size down and wraps text across 2 lines to fit long titles perfectly."""
    fontsize = default_fontsize
    font = fitz.Font(font_name)
    
    while fontsize >= min_fontsize:
        words = title.split()
        line1_words = []
        line2_words = []
        
        w1 = 0
        for idx, w in enumerate(words):
            ww = font.text_length(w + ' ', fontsize)
            if w1 + ww <= max_w1:
                line1_words.append(w)
                w1 += ww
            else:
                line2_words = words[idx:]
                break
                
        str1 = ' '.join(line1_words)
        str2 = ' '.join(line2_words)
        
        w2 = font.text_length(str2, fontsize)
        if w2 <= max_w2 or fontsize <= min_fontsize:
            # If line 2 still overflows at minimum font size, truncate gracefully with ...
            if w2 > max_w2:
                while line2_words and font.text_length(' '.join(line2_words) + '...', fontsize) > max_w2:
                    line2_words.pop()
                str2 = ' '.join(line2_words) + '...'
            return str1, str2, fontsize
            
        fontsize -= 0.5

def fill_header(template_path, data, formatting):
    """Creates a filled header PyMuPDF Document page object from template."""
    doc = fitz.open(template_path)
    page = doc[0]
    
    font_name = formatting.get("font_name", "helv")
    font_size = formatting.get("font_size", 11)
    font_color = parse_color(formatting.get("text_color", "blue"))
    strikethrough_enabled = formatting.get("strikethrough_enabled", True)
    
    # 1. SEM, CLASS, BATCH, ROLL NO
    page.insert_text((100, 225), str(data.get('sem', '')), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((205, 225), str(data.get('class_name', '')), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((330, 225), str(data.get('batch', '')), fontsize=font_size, fontname=font_name, color=font_color)
    page.insert_text((470, 225), str(data.get('roll_no', '')), fontsize=font_size, fontname=font_name, color=font_color)
    
    # 2. NAME
    page.insert_text((110, 266), str(data.get('name', '')), fontsize=font_size, fontname=font_name, color=font_color)
    
    # 3. SUBJECT
    page.insert_text((125, 287), str(data.get('subject', '')), fontsize=font_size, fontname=font_name, color=font_color)
    
    # 4. EXPERIMENT NO. / ASSIGNMENT NO. & STRIKETHROUGH TOGGLE
    is_assignment = data.get('is_assignment', False)
    
    if strikethrough_enabled:
        if is_assignment:
            # Strike through 'EXPERIMENT NO. /' (Leaving ASSIGNMENT NO. active)
            page.draw_line(fitz.Point(62.9, 327.9), fitz.Point(174.3, 327.9), color=font_color, width=1.5)
        else:
            # Strike through '/ ASSIGNMENT NO.' (Leaving EXPERIMENT NO. active)
            page.draw_line(fitz.Point(170.0, 327.9), fitz.Point(285.0, 327.9), color=font_color, width=1.5)

    exp_num_str = str(data.get('exp_no', ''))
    page.insert_text((290, 330), exp_num_str, fontsize=font_size, fontname=font_name, color=font_color)

    # 5. TITLE (Auto-scaled dynamic font size wrapping)
    title = str(data.get('title', ''))
    str1, str2, title_fontsize = split_and_scale_title(title, font_name=font_name, default_fontsize=font_size)
    
    page.insert_text((106, 351), str1, fontsize=title_fontsize, fontname=font_name, color=font_color)
    if str2:
        page.insert_text((63, 372), str2, fontsize=title_fontsize, fontname=font_name, color=font_color)
        
    # 6. DATES
    perf_date = str(data.get('perf_date', ''))
    sub_date = str(data.get('sub_date', ''))
    if perf_date:
        page.insert_text((220, 414), perf_date, fontsize=font_size, fontname=font_name, color=font_color)
    if sub_date:
        page.insert_text((205, 435), sub_date, fontsize=font_size, fontname=font_name, color=font_color)
        
    return doc

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
    
    font_size = fmt_cfg.get("font_size", 11)
    font_name = fmt_cfg.get("font_name", "helv")
    
    output_dir = args.output_dir or out_cfg.get("output_dir", "output")
    combine_pdf = out_cfg.get("combine_all_experiments", True)
    combined_pdf_name = out_cfg.get("combined_pdf_name", "All_Experiments_Combined.pdf")
    copy_to_root = out_cfg.get("copy_combined_to_root", True)
    
    formatting = {
        "text_color": text_color,
        "strikethrough_enabled": strikethrough_enabled,
        "font_size": font_size,
        "font_name": font_name
    }
    
    os.makedirs(output_dir, exist_ok=True)
    headers_dir = os.path.join(output_dir, "headers")
    os.makedirs(headers_dir, exist_ok=True)
    
    combined_doc = fitz.open() if combine_pdf else None
    
    print("=" * 60)
    print("      EXPERIMENT / ASSIGNMENT HEADER GENERATOR")
    print("=" * 60)
    print(f" Config File    : {args.config if os.path.exists(args.config) else 'None (Defaults)'}")
    print(f" Name           : {name}")
    print(f" Roll No        : {roll_no}")
    print(f" Batch          : {batch}")
    print(f" Class          : {class_name}")
    print(f" Semester       : {sem}")
    print(f" Subject        : {subject}")
    print(f" Strikethrough  : {'Enabled' if strikethrough_enabled else 'Disabled'}")
    print(f" Text Color     : {text_color}")
    print(f" Output Dir     : {output_dir}")
    print("=" * 60)
    
    exp_map = {item.get("num"): item for item in exp_cfg_list if isinstance(item, dict) and "num" in item}
    assignment_set = set(args.assignments) if args.assignments else None
    
    for i in range(1, 10):
        exp_file = f"Experiment {i}.pdf"
        if not os.path.exists(exp_file):
            print(f"Skipping {exp_file}: File not found.")
            continue
            
        custom_exp_cfg = exp_map.get(i, {})
        custom_title = custom_exp_cfg.get("title")
        
        if custom_title and custom_title != "Auto":
            title = custom_title
        else:
            title = extract_aim(exp_file) or f"Experiment {i}"
            
        p_date = custom_exp_cfg.get("perf_date") or perf_date_global
        s_date = custom_exp_cfg.get("sub_date") or sub_date_global
        
        # Determine if this item is an assignment or experiment
        if args.type == "assignment":
            is_assignment = True
        elif args.type == "experiment":
            is_assignment = False
        elif assignment_set is not None:
            is_assignment = (i in assignment_set)
        else:
            is_assignment = custom_exp_cfg.get("is_assignment", False)
            
        doc_type_str = "Assignment" if is_assignment else "Experiment"
        label_str = f"Assgn - {i}" if is_assignment else f"Exp - {i}"
        
        data = {
            'sem': sem,
            'class_name': class_name,
            'batch': batch,
            'roll_no': roll_no,
            'name': name,
            'subject': subject,
            'is_assignment': is_assignment,
            'exp_no': label_str,
            'title': title,
            'perf_date': p_date,
            'sub_date': s_date
        }
        
        # 1. Fill Header PDF
        header_doc = fill_header("Header.pdf", data, formatting)
        
        # Save standalone header PDF
        standalone_path = os.path.join(headers_dir, f"Header_Exp_{i}.pdf")
        header_doc.save(standalone_path)
        
        # 2. Merge Header + Original Experiment PDF
        exp_doc = fitz.open(exp_file)
        merged_doc = fitz.open()
        
        # Prepend filled header as Page 1
        merged_doc.insert_pdf(header_doc)
        # Append all pages of original experiment
        merged_doc.insert_pdf(exp_doc)
        
        merged_output_path = os.path.join(output_dir, f"Experiment_{i}_with_Header.pdf")
        merged_doc.save(merged_output_path)
        
        if combined_doc is not None:
            combined_doc.insert_pdf(merged_doc)
            
        strike_desc = "EXPERIMENT NO. /" if is_assignment else "/ ASSIGNMENT NO."
        print(f" [OK] Exp {i}: Type={doc_type_str:<10} | Strikethrough='{strike_desc}' -> {merged_output_path}")
        
        header_doc.close()
        exp_doc.close()
        merged_doc.close()
        
    if combined_doc is not None:
        combined_output_path = os.path.join(output_dir, combined_pdf_name)
        combined_doc.save(combined_output_path)
        combined_doc.close()
        
        if copy_to_root:
            import shutil
            shutil.copy(combined_output_path, combined_pdf_name)
            print(f" [OK] Copied master PDF to root workspace -> {combined_pdf_name}")
            
    print("=" * 60)
    print(f" SUCCESS! All 9 headers and merged experiments created in '{output_dir}/'")
    print("=" * 60)

if __name__ == "__main__":
    main()
