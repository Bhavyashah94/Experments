import os
import io
import re
import time
import hashlib
import base64
import shutil
import zipfile
import threading
from flask import Flask, render_template, request, jsonify, send_file
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_HEADER  = os.path.join(BASE_DIR, "Header.pdf")
OUTPUT_DIR       = os.path.join(BASE_DIR, "output")
HEADERS_DIR      = os.path.join(OUTPUT_DIR, "headers")
UPLOADS_DIR      = os.path.join(BASE_DIR, "uploads")

for d in (HEADERS_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

# ── 24-hour TTL cleanup thread ────────────────────────────────────────────────
TTL_SECONDS  = 24 * 60 * 60   # 24 hours
SWEEP_EVERY  = 30 * 60        # run sweep every 30 minutes

def _cleanup_uploads():
    """Delete any uploaded file older than TTL_SECONDS. Re-schedules itself."""
    now = time.time()
    try:
        for fname in os.listdir(UPLOADS_DIR):
            fpath = os.path.join(UPLOADS_DIR, fname)
            if os.path.isfile(fpath):
                age = now - os.path.getmtime(fpath)
                if age > TTL_SECONDS:
                    try:
                        os.remove(fpath)
                        print(f"[cleanup] removed expired upload: {fname}")
                    except OSError:
                        pass
    except Exception as e:
        print(f"[cleanup] error: {e}")
    finally:
        t = threading.Timer(SWEEP_EVERY, _cleanup_uploads)
        t.daemon = True
        t.start()

# Start cleanup thread when app boots
_cleanup_uploads()

# ── Helpers ───────────────────────────────────────────────────────────────────
def _valid_hash(h: str) -> bool:
    """Reject anything that isn't a 64-char lowercase hex string."""
    return bool(h) and len(h) == 64 and all(c in '0123456789abcdef' for c in h)

def parse_color(color_val):
    """Parses color string or hex '#RRGGBB' into RGB float tuple."""
    if isinstance(color_val, (list, tuple)) and len(color_val) == 3:
        return tuple(color_val)
    color_val = str(color_val).lower().strip()
    color_map = {
        "blue":     (0.0, 0.0, 0.75),
        "darkblue": (0.0, 0.0, 0.5),
        "black":    (0.0, 0.0, 0.0),
        "red":      (0.8, 0.0, 0.0),
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
    return (0.0, 0.0, 0.75)

def inspect_pdf_info(pdf_path):
    """Extract Aim/Title text, Experiment/Assignment number, type, and total page count from an experiment PDF."""
    info = {"aim": None, "pages": 0, "exp_num": None, "is_assignment": None}
    try:
        doc = fitz.open(pdf_path)
        info["pages"] = len(doc)
        if len(doc) > 0:
            text = doc[0].get_text()
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            # 1. Detect Exp/Assgn Number and Type from PDF text
            for line in lines[:15]:
                match = re.search(r'\b(Exp|Experiment|Assgn|Assignment)[\s\-_.]*(?:No|Num|Number)?[\s:_.]*(\d+[a-z]?)\b', line, re.IGNORECASE)
                if match:
                    type_str = match.group(1).lower()
                    info["exp_num"] = match.group(2)
                    info["is_assignment"] = True if 'ass' in type_str else False
                    break

            # 2. Extract Aim text or Title from PDF text
            aim_lines = []
            capture = False
            
            # First check for "Experiment X: <Title>" or "Assignment X: <Title>" header line
            for line in lines[:15]:
                exp_title_match = re.search(r'\b(?:Exp|Experiment|Assgn|Assignment)[\s\-_.]*\d+[\s:_.\-]+\s*(.+)$', line, re.IGNORECASE)
                if exp_title_match:
                    found_title = exp_title_match.group(1).strip()
                    # If it's a valid descriptive title (not just numbers or short codes)
                    if len(found_title) > 3 and not found_title.lower().startswith(('date', 'roll', 'name')):
                        info["aim"] = found_title
                        break

            # If no Experiment X: Title found, or to prefer explicit "Aim:" tag
            for line in lines:
                m_aim = re.match(r'^(?:Aim|AIM|Title|TITLE|Objective|OBJECTIVE)[\s:]*(.*)$', line, re.IGNORECASE)
                if m_aim:
                    capture = True
                    val = m_aim.group(1).strip()
                    if val:
                        aim_lines.append(val)
                elif capture:
                    # Stop boundaries: Step, Task, Section, Phase, Theory, Procedure, Apparatus, Prerequisites, Requirements, Introduction, Guide/Overview, or numbered sections (1.)
                    if re.search(r'^\s*(?:Step|Task|Section|Phase|Part|\d+\.|\bObjectives?\b|\bTheory\b|\bProcedure\b|\bApparatus\b|\bPrerequisites\b|\bRequirements\b|\bIntroduction\b|\bOverview\b|\bDescription\b|\bGuide\b|\bNote\b|\bRoll\b|\bDate\b)', line, re.IGNORECASE):
                        break
                    # Length safety cap to prevent capturing entire body paragraphs
                    if sum(len(x) for x in aim_lines) + len(line) > 250:
                        break
                    aim_lines.append(line)

            clean_aim = ' '.join(aim_lines).strip()
            if clean_aim:
                info["aim"] = clean_aim
        doc.close()
    except Exception as e:
        print(f"Warning: Could not inspect PDF {pdf_path}: {e}")
    return info

def extract_aim_from_pdf(pdf_path):
    """Extract Aim/Title text from an experiment PDF."""
    info = inspect_pdf_info(pdf_path)
    return info.get("aim")

def split_and_scale_title(title, font_name='helv', max_w1=439, max_w2=480,
                           min_fontsize=8.0, default_fontsize=11.0):
    """Dynamically scale and wrap title across 2 lines to fit header box."""
    fontsize = default_fontsize
    font = fitz.Font(font_name)
    while fontsize >= min_fontsize:
        words = title.split()
        line1_words, line2_words = [], []
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
            if w2 > max_w2:
                while line2_words and font.text_length(' '.join(line2_words) + '...', fontsize) > max_w2:
                    line2_words.pop()
                str2 = ' '.join(line2_words) + '...'
            return str1, str2, fontsize
        fontsize -= 0.5

def create_filled_header_doc(data, formatting):
    """Creates a filled header PyMuPDF Document from the template."""
    if not os.path.exists(TEMPLATE_HEADER):
        raise FileNotFoundError("Header.pdf template not found.")
    doc = fitz.open(TEMPLATE_HEADER)
    page = doc[0]
    fn   = formatting.get("font_name", "helv")
    fs   = formatting.get("font_size", 11)
    fc   = parse_color(formatting.get("text_color", "blue"))
    st   = formatting.get("strikethrough_enabled", True)

    page.insert_text((100, 225), str(data.get('sem', '')),        fontsize=fs, fontname=fn, color=fc)
    page.insert_text((205, 225), str(data.get('class_name', '')), fontsize=fs, fontname=fn, color=fc)
    page.insert_text((330, 225), str(data.get('batch', '')),      fontsize=fs, fontname=fn, color=fc)
    page.insert_text((470, 225), str(data.get('roll_no', '')),    fontsize=fs, fontname=fn, color=fc)
    page.insert_text((110, 266), str(data.get('name', '')),       fontsize=fs, fontname=fn, color=fc)
    page.insert_text((125, 287), str(data.get('subject', '')),    fontsize=fs, fontname=fn, color=fc)

    is_assignment = data.get('is_assignment', False)
    if st:
        if is_assignment:
            page.draw_line(fitz.Point(62.9, 327.9), fitz.Point(174.3, 327.9), color=fc, width=1.5)
        else:
            page.draw_line(fitz.Point(170.0, 327.9), fitz.Point(285.0, 327.9), color=fc, width=1.5)

    page.insert_text((290, 330), str(data.get('exp_no', '')), fontsize=fs, fontname=fn, color=fc)

    title = str(data.get('title', ''))
    str1, str2, tfs = split_and_scale_title(title, font_name=fn, default_fontsize=fs)
    page.insert_text((106, 351), str1, fontsize=tfs, fontname=fn, color=fc)
    if str2:
        page.insert_text((63, 372), str2, fontsize=tfs, fontname=fn, color=fc)

    perf = str(data.get('perf_date', ''))
    sub  = str(data.get('sub_date', ''))
    if perf:
        page.insert_text((220, 414), perf, fontsize=fs, fontname=fn, color=fc)
    if sub:
        page.insert_text((205, 435), sub,  fontsize=fs, fontname=fn, color=fc)

    return doc

def _resolve_body_pdf(item):
    """
    Resolve the body PDF path for a document row.
    Priority:
      1. Uploaded file: uploads/<sha256>.pdf  (from item['hash'])
      2. Server-side file: Experiment N.pdf   (legacy / convenience)
      3. None — header only
    """
    h = item.get('hash', '')
    if h and _valid_hash(h):
        p = os.path.join(UPLOADS_DIR, f"{h}.pdf")
        if os.path.exists(p):
            return p

    # Legacy fallback: server-side Experiment N.pdf
    label = str(item.get('label', item.get('num', '')))
    if label.isdigit():
        p = os.path.join(BASE_DIR, f"Experiment {label}.pdf")
        if os.path.exists(p):
            return p

    return None

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ── Load defaults (generic) ───────────────────────────────────────────────────

@app.route("/api/load-defaults", methods=["GET"])
def get_defaults():
    """Returns blank student defaults and dynamically scanned experiment PDF list."""
    student_defaults = {
        "name": "", "roll_no": "", "batch": "", "class_name": "",
        "sem": "", "subject": "", "text_color": "blue",
        "strikethrough_enabled": True
    }
    experiments = []
    i = 1
    while True:
        pdf_path = os.path.join(BASE_DIR, f"Experiment {i}.pdf")
        if not os.path.exists(pdf_path):
            break
        info = inspect_pdf_info(pdf_path)
        experiments.append({
            "num": i, "label": str(i), "title": "",
            "is_assignment": False, "perf_date": "", "sub_date": "",
            "file_exists": True, "pages": info.get("pages", 0)
        })
        i += 1
    if not experiments:
        experiments.append({
            "num": 1, "label": "1", "title": "",
            "is_assignment": False, "perf_date": "", "sub_date": "",
            "file_exists": False, "pages": 0
        })
    return jsonify({"student": student_defaults, "experiments": experiments})

# ── File upload (content-addressed) ───────────────────────────────────────────

@app.route("/api/file/<hash_val>/exists", methods=["GET"])
def file_exists(hash_val):
    """Check if a file with the given SHA-256 hash exists and is not expired."""
    if not _valid_hash(hash_val):
        return jsonify({"exists": False, "error": "Invalid hash"}), 400
    fpath = os.path.join(UPLOADS_DIR, f"{hash_val}.pdf")
    if os.path.exists(fpath):
        age = time.time() - os.path.getmtime(fpath)
        if age <= TTL_SECONDS:
            info = inspect_pdf_info(fpath)
            return jsonify({"exists": True, "pages": info.get("pages", 0)})
    return jsonify({"exists": False}), 404

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Accepts a PDF file upload. Validates the SHA-256 hash matches the content.
    Stores as uploads/<sha256>.pdf. Returns { hash, size, pages }.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    f = request.files['file']
    claimed_hash = (request.form.get('hash') or '').lower().strip()

    if not f.filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "error": "Only PDF files are accepted"}), 400

    data = f.read()

    # Verify hash
    actual_hash = hashlib.sha256(data).hexdigest()
    if claimed_hash and claimed_hash != actual_hash:
        return jsonify({"success": False, "error": "Hash mismatch — file may be corrupted"}), 400

    dest = os.path.join(UPLOADS_DIR, f"{actual_hash}.pdf")
    with open(dest, 'wb') as out:
        out.write(data)

    info = inspect_pdf_info(dest)

    return jsonify({
        "success": True,
        "hash": actual_hash,
        "size": len(data),
        "pages": info.get("pages", 0),
        "aim": info.get("aim"),
        "exp_num": info.get("exp_num"),
        "is_assignment": info.get("is_assignment")
    })

# ── Extract aim & PDF info ───────────────────────────────────────────────────

@app.route("/api/extract-aim", methods=["POST"])
def extract_aim():
    """Extract aim/title text, exp_num, type, and page count from an uploaded PDF identified by SHA-256 hash."""
    req = request.get_json() or {}
    h   = (req.get('hash') or '').lower().strip()
    if not _valid_hash(h):
        return jsonify({"success": False, "error": "Invalid hash"}), 400

    fpath = os.path.join(UPLOADS_DIR, f"{h}.pdf")
    if not os.path.exists(fpath):
        return jsonify({"success": False, "error": "File not found — may have expired"}), 404

    info = inspect_pdf_info(fpath)
    return jsonify({
        "success": True,
        "aim": info.get("aim"),
        "pages": info.get("pages", 0),
        "exp_num": info.get("exp_num"),
        "is_assignment": info.get("is_assignment")
    })

# ── Preview ────────────────────────────────────────────────────────────────────

@app.route("/api/preview", methods=["POST"])
def preview_header():
    """Generates a base64 PNG preview of the filled header page."""
    req_data    = request.get_json() or {}
    item_data   = req_data.get("item", {})
    student     = req_data.get("student", {})
    is_assgn    = item_data.get("is_assignment", False)
    label       = str(item_data.get("label", item_data.get("num", "1")))
    exp_label   = f"Assgn - {label}" if is_assgn else f"Exp - {label}"

    data = {
        'sem':        student.get("sem", ""),
        'class_name': student.get("class_name", ""),
        'batch':      student.get("batch", ""),
        'roll_no':    student.get("roll_no", ""),
        'name':       student.get("name", ""),
        'subject':    student.get("subject", ""),
        'is_assignment': is_assgn,
        'exp_no':     exp_label,
        'title':      item_data.get("title", ""),
        'perf_date':  item_data.get("perf_date") or student.get("perf_date", ""),
        'sub_date':   item_data.get("sub_date")  or student.get("sub_date", ""),
    }
    formatting = {
        "text_color":           student.get("text_color", "blue"),
        "strikethrough_enabled": student.get("strikethrough_enabled", True),
        "font_size": 11, "font_name": "helv"
    }
    try:
        doc = create_filled_header_doc(data, formatting)
        pix = doc[0].get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        doc.close()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return jsonify({"success": True, "image_data": f"data:image/png;base64,{b64}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Generate ───────────────────────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate_pdfs():
    """Generates filled headers, merges with body PDFs, and produces combined file & ZIP package."""
    req_data    = request.get_json() or {}
    student     = req_data.get("student", {})
    experiments = req_data.get("experiments", [])

    formatting = {
        "text_color":           student.get("text_color", "blue"),
        "strikethrough_enabled": student.get("strikethrough_enabled", True),
        "font_size": 11, "font_name": "helv"
    }

    os.makedirs(HEADERS_DIR, exist_ok=True)

    combined_doc    = fitz.open()
    generated_files = []
    zip_entries     = []

    for item in experiments:
        label     = str(item.get('label', item.get('num', '?')))
        is_assgn  = item.get("is_assignment", False)
        exp_label = f"Assgn - {label}" if is_assgn else f"Exp - {label}"

        data = {
            'sem':        student.get("sem", ""),
            'class_name': student.get("class_name", ""),
            'batch':      student.get("batch", ""),
            'roll_no':    student.get("roll_no", ""),
            'name':       student.get("name", ""),
            'subject':    student.get("subject", ""),
            'is_assignment': is_assgn,
            'exp_no':     exp_label,
            'title':      item.get("title", ""),
            'perf_date':  item.get("perf_date") or student.get("perf_date", ""),
            'sub_date':   item.get("sub_date")  or student.get("sub_date", ""),
        }

        header_doc = create_filled_header_doc(data, formatting)
        safe_label = re.sub(r'[^\w\-]', '_', label)
        header_path = os.path.join(HEADERS_DIR, f"Header_{safe_label}.pdf")
        header_doc.save(header_path)

        merged_doc = fitz.open()
        merged_doc.insert_pdf(header_doc)

        body_path = _resolve_body_pdf(item)
        if body_path:
            body_doc = fitz.open(body_path)
            merged_doc.insert_pdf(body_doc)
            body_doc.close()

        type_prefix = "Assgn" if is_assgn else "Exp"
        merged_filename  = f"{type_prefix}_{safe_label}_with_Header.pdf"
        merged_out       = os.path.join(OUTPUT_DIR, merged_filename)
        merged_doc.save(merged_out)
        combined_doc.insert_pdf(merged_doc)

        generated_files.append({
            "label":      label,
            "merged_pdf": merged_filename,
        })
        zip_entries.append((merged_out, merged_filename))

        header_doc.close()
        merged_doc.close()

    combined_path = os.path.join(OUTPUT_DIR, "All_Documents_Combined.pdf")
    combined_doc.save(combined_path)
    combined_doc.close()
    shutil.copy(combined_path, os.path.join(BASE_DIR, "All_Documents_Combined.pdf"))

    # Create ZIP archive containing all individual files + combined PDF
    zip_filename = "All_Documents_Package.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(combined_path, "All_Documents_Combined.pdf")
        for fpath, arcname in zip_entries:
            zf.write(fpath, os.path.join("Individual_Files", arcname))

    return jsonify({
        "success":      True,
        "combined_pdf": "All_Documents_Combined.pdf",
        "zip_package":  zip_filename,
        "files":        generated_files
    })

# ── Download ───────────────────────────────────────────────────────────────────

@app.route("/api/download/<path:filename>")
def download_file(filename):
    """Serves generated PDFs and ZIP packages for download."""
    for base in (OUTPUT_DIR, BASE_DIR):
        p = os.path.join(base, filename)
        if os.path.exists(p):
            return send_file(p, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
