import os
import time
import uuid
import hashlib
import threading
import shutil
from typing import Optional
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from lab_core import (
    render_header_preview_png,
    generate_job_documents,
    inspect_pdf_info,
    init_analytics_db,
    record_generation_event,
    get_analytics_summary,
    get_generation_events,
    export_analytics_csv,
    export_analytics_json,
    is_analytics_enabled,
    is_auth_required,
    verify_admin_password,
    record_upload_diagnostic,
    record_student_ground_truth,
    get_extraction_diagnostics_summary,
    get_failed_or_discrepant_samples,
    get_protected_hashes_set,
)

APP_START_TIME = time.time()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB max upload size

# Enable CORS for API routes, Header.pdf template, and assets
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        },
        r"/Header.pdf": {"origins": "*"},
        r"/assets/*": {"origins": "*"},
    },
)

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per hour", "200 per minute"],
    storage_uri="memory://",
)

# ── Standardized JSON Error Handlers (Prevents client-side JSON parse crashes) ──
@app.errorhandler(400)
def handle_400(e):
    msg = e.description if hasattr(e, "description") else "Bad request"
    return jsonify({"success": False, "error": msg}), 400

@app.errorhandler(404)
def handle_404(e):
    return jsonify({"success": False, "error": "Resource not found"}), 404

@app.errorhandler(413)
def handle_413(e):
    return jsonify({"success": False, "error": "Payload too large. Maximum file upload size is 100 MB."}), 413

@app.errorhandler(429)
def handle_429(e):
    desc = e.description if hasattr(e, "description") else "Too many requests"
    return jsonify({"success": False, "error": f"Rate limit exceeded: {desc}"}), 429

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"success": False, "error": "Internal server error."}), 500

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_HEADER = os.path.join(BASE_DIR, "Header.pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

for d in (OUTPUT_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

if is_analytics_enabled():
    try:
        init_analytics_db()
    except Exception:
        pass

# ── Storage Management & Dataset Rotation Engine ──────────────────────────────
# Scaled for Oracle Cloud VM (45GB NVMe disk)
MAX_STORAGE_BYTES = 15 * 1024 * 1024 * 1024      # 15 GB ceiling
HIGH_WATERMARK_BYTES = 12 * 1024 * 1024 * 1024   # 12 GB trigger rotation threshold
LOW_WATERMARK_BYTES = 10 * 1024 * 1024 * 1024    # 10 GB target clean size after rotation
TARGET_STORAGE_BYTES = LOW_WATERMARK_BYTES       # Alias for backward compatibility
OUTPUT_JOBS_MAX_AGE_SECONDS = 7 * 24 * 60 * 60   # 7 days for generated deliverable outputs in output/
SWEEP_EVERY_SECONDS = 30 * 60                    # run sweep every 30 minutes


def _get_dir_size(path: str) -> int:
    total = 0
    if not os.path.exists(path):
        return 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _enforce_storage_quota():
    """
    Intelligent dual-watermark storage rotation.
    Triggered when total disk usage exceeds HIGH_WATERMARK_BYTES (or MAX_STORAGE_BYTES).
    Tier 1: Prunes generated deliverable job directories in output/ older than 3 days.
    Tier 2: If still > target clean size, evicts non-protected uploads in LRU order.
    Tier 3: As a last resort, evicts oldest protected samples.
    """
    uploads_size = _get_dir_size(UPLOADS_DIR)
    output_size = _get_dir_size(OUTPUT_DIR)
    total_size = uploads_size + output_size

    trigger_threshold = min(MAX_STORAGE_BYTES, HIGH_WATERMARK_BYTES)
    target_clean = min(LOW_WATERMARK_BYTES, TARGET_STORAGE_BYTES)

    if total_size <= trigger_threshold:
        return

    current_size = total_size

    # Tier 1: Prune output job directories older than 3 days first
    now = time.time()
    try:
        for entry in os.listdir(OUTPUT_DIR):
            epath = os.path.join(OUTPUT_DIR, entry)
            if os.path.isdir(epath) and entry != "headers":
                if (now - os.path.getmtime(epath)) > (3 * 24 * 3600):
                    sz = _get_dir_size(epath)
                    shutil.rmtree(epath, ignore_errors=True)
                    current_size -= sz
                    if current_size <= target_clean:
                        return
    except OSError:
        pass

    # Tier 2: Separate uploads into unprotected vs protected
    protected_hashes = get_protected_hashes_set()
    unprotected_files = []
    protected_files = []

    try:
        for fname in os.listdir(UPLOADS_DIR):
            fpath = os.path.join(UPLOADS_DIR, fname)
            if os.path.isfile(fpath):
                file_hash = os.path.splitext(fname)[0].lower()
                mtime = os.path.getmtime(fpath)
                sz = os.path.getsize(fpath)
                if file_hash in protected_hashes:
                    protected_files.append((mtime, sz, fpath))
                else:
                    unprotected_files.append((mtime, sz, fpath))
    except OSError:
        pass

    # Sort oldest first
    unprotected_files.sort(key=lambda x: x[0])
    for _, sz, fpath in unprotected_files:
        if current_size <= target_clean:
            return
        try:
            os.remove(fpath)
            current_size -= sz
        except OSError:
            pass

    # Tier 3: If still above low watermark, rotate oldest protected files
    protected_files.sort(key=lambda x: x[0])
    for _, sz, fpath in protected_files:
        if current_size <= target_clean:
            return
        try:
            os.remove(fpath)
            current_size -= sz
        except OSError:
            pass


def _cleanup_ephemeral_storage():
    """
    Background maintenance task:
    1. Sweeps compiled deliverables in output/ older than OUTPUT_JOBS_MAX_AGE_SECONDS (7 days).
    2. Uploaded documents have NO arbitrary TTL and are kept for research/analytics.
    3. Runs storage rotation if usage exceeds 12 GB.
    4. Re-schedules itself every 30 minutes.
    """
    now = time.time()
    try:
        for entry in os.listdir(OUTPUT_DIR):
            epath = os.path.join(OUTPUT_DIR, entry)
            if os.path.isdir(epath) and entry != "headers":
                if (now - os.path.getmtime(epath)) > OUTPUT_JOBS_MAX_AGE_SECONDS:
                    shutil.rmtree(epath, ignore_errors=True)
    except Exception as e:
        print(f"[cleanup] error sweeping output jobs: {e}")

    # Enforce high-watermark storage rotation
    try:
        _enforce_storage_quota()
    except Exception as e:
        print(f"[cleanup] error enforcing storage quota: {e}")
    finally:
        t = threading.Timer(SWEEP_EVERY_SECONDS, _cleanup_ephemeral_storage)
        t.daemon = True
        t.start()


# Start background cleanup thread when app boots
_cleanup_ephemeral_storage()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _valid_hash(h: Optional[str]) -> bool:
    """Reject anything that isn't a 64-char lowercase hex string."""
    return bool(h) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.after_request
def set_cache_headers(response):
    """
    Industry-standard cache policy:
    1. HTML documents: Never cache (no-cache, no-store, must-revalidate).
       Ensures students immediately get new code without hard-refreshing.
    2. Static hashed assets (/assets/*): Cache immutably for 1 year.
       Vite generates content hashes (e.g. index-1IoDWZ5N.js), so new builds automatically
       point to new URLs while returning visitors load instantly.
    """
    if response.mimetype in ("text/html", "application/json"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif request.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@app.route("/")
def index():
    # If a pre-built SPA dist exists, serve it, otherwise render legacy index.html
    spa_dist_index = os.path.join(BASE_DIR, "frontend", "dist", "index.html")
    if os.path.exists(spa_dist_index):
        return send_file(spa_dist_index)
    return render_template("index.html")


@app.route("/assets/<path:filename>")
def serve_spa_assets(filename):
    spa_assets_dir = os.path.join(BASE_DIR, "frontend", "dist", "assets")
    if os.path.exists(os.path.join(spa_assets_dir, filename)):
        return send_from_directory(spa_assets_dir, filename)
    static_assets_dir = os.path.join(BASE_DIR, "static", "assets")
    if os.path.exists(os.path.join(static_assets_dir, filename)):
        return send_from_directory(static_assets_dir, filename)
    return ("Asset not found", 404)


@app.route("/Header.pdf")
def serve_header_template():
    """Serves the standard template Header.pdf for client-side canvas preview rendering."""
    if os.path.isfile(TEMPLATE_HEADER):
        return send_file(TEMPLATE_HEADER, mimetype="application/pdf")
    return jsonify({"error": "Template Header.pdf not found"}), 404


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Oracle/HuggingFace container monitoring and uptime checks."""
    uploads_sz = _get_dir_size(UPLOADS_DIR)
    output_sz = _get_dir_size(OUTPUT_DIR)
    return jsonify({
        "status": "ok",
        "version": "2.1.0",
        "uptime_seconds": int(time.time() - APP_START_TIME),
        "storage": {
            "used_bytes": uploads_sz + output_sz,
            "max_bytes": MAX_STORAGE_BYTES,
            "percent_used": round((uploads_sz + output_sz) / MAX_STORAGE_BYTES * 100, 1),
        },
    })


# ── Load defaults ─────────────────────────────────────────────────────────────

@app.route("/api/load-defaults", methods=["GET"])
def get_defaults():
    """Returns blank student defaults and dynamically scanned experiment PDF list."""
    student_defaults = {
        "name": "",
        "roll_no": "",
        "batch": "",
        "class_name": "",
        "sem": "",
        "subject": "",
        "text_color": "blue",
        "strikethrough_enabled": True,
    }
    experiments = []
    i = 1
    while True:
        pdf_path = os.path.join(BASE_DIR, f"Experiment {i}.pdf")
        if not os.path.exists(pdf_path):
            break
        info = inspect_pdf_info(pdf_path)
        experiments.append({
            "num": i,
            "label": str(i),
            "title": "",
            "is_assignment": False,
            "perf_date": "",
            "sub_date": "",
            "file_exists": True,
            "pages": info.get("pages", 0),
        })
        i += 1
    if not experiments:
        experiments.append({
            "num": 1,
            "label": "1",
            "title": "",
            "is_assignment": False,
            "perf_date": "",
            "sub_date": "",
            "file_exists": False,
            "pages": 0,
        })
    return jsonify({"student": student_defaults, "experiments": experiments})


# ── File upload (content-addressed streaming) ─────────────────────────────────

@app.route("/api/file/<hash_val>/exists", methods=["GET"])
def file_exists(hash_val):
    """Check if a file with the given SHA-256 hash exists on disk."""
    hash_val = hash_val.lower().strip()
    if not _valid_hash(hash_val):
        return jsonify({"exists": False, "error": "Invalid hash"}), 400

    fpath = os.path.join(UPLOADS_DIR, f"{hash_val}.pdf")
    if os.path.isfile(fpath):
        info = inspect_pdf_info(fpath)
        return jsonify({
            "exists": True,
            "pages": info.get("pages", 0),
            "aim": info.get("aim"),
            "exp_num": info.get("exp_num"),
            "is_assignment": info.get("is_assignment"),
            "extraction_method": info.get("extraction_method", "unextracted"),
        })
    return jsonify({"exists": False}), 404


@app.route("/api/upload", methods=["POST"])
@limiter.limit("40 per minute")
def upload_file():
    """
    Accepts a PDF file upload via chunked streaming to prevent 512MB RAM spikes.
    Stores as uploads/<sha256>.pdf. Logs extraction diagnostics and returns metadata.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    f = request.files["file"]
    claimed_hash = (request.form.get("hash") or "").lower().strip()

    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF files are accepted"}), 400

    # Verify %PDF- magic bytes to reject disguised non-PDF binaries
    header_peek = f.stream.read(5)
    f.stream.seek(0)
    if header_peek != b"%PDF-":
        return jsonify({"success": False, "error": "Invalid file format: must be a valid PDF document."}), 400

    # Ensure storage quota before allocating disk
    try:
        _enforce_storage_quota()
    except Exception:
        pass

    # Stream upload in 64KB chunks to temporary file while calculating hash
    hasher = hashlib.sha256()
    temp_filename = f"temp_{uuid.uuid4().hex}.pdf"
    temp_path = os.path.join(UPLOADS_DIR, temp_filename)
    total_bytes = 0

    try:
        with open(temp_path, "wb") as out:
            while True:
                chunk = f.stream.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
                total_bytes += len(chunk)

        actual_hash = hasher.hexdigest()

        if claimed_hash and claimed_hash != actual_hash:
            os.remove(temp_path)
            return jsonify({"success": False, "error": "Hash mismatch — file may be corrupted"}), 400

        dest = os.path.join(UPLOADS_DIR, f"{actual_hash}.pdf")
        if os.path.exists(dest):
            os.remove(temp_path)  # Already exists, remove temp
        else:
            os.replace(temp_path, dest)

        # Inspect PDF
        mode = request.form.get("mode", "auto")
        info = inspect_pdf_info(dest, mode=mode)

        # Check for unreadable / password-protected / corrupted PDF
        if info.get("error") or info.get("pages", 0) <= 0:
            if os.path.exists(dest):
                os.remove(dest)
            err_msg = info.get("error") or "Unreadable or corrupted PDF."
            return jsonify({"success": False, "error": err_msg}), 400

        # Safety page limit (scaled to 300 pages for project manuals)
        if info.get("pages", 0) > 300:
            if os.path.exists(dest):
                os.remove(dest)
            return jsonify({"success": False, "error": "PDF exceeds 300-page limit."}), 400

        # Record diagnostic telemetry for research and format discovery
        try:
            record_upload_diagnostic(
                sha256=actual_hash,
                filename=f.filename or f"{actual_hash}.pdf",
                file_size=total_bytes,
                pages=info.get("pages", 0),
                extracted_aim=info.get("aim"),
                extracted_exp_num=info.get("exp_num"),
                extraction_method=info.get("extraction_method", "unextracted"),
                failure_reason=info.get("failure_reason", "none"),
                text_snippet=info.get("text_snippet", ""),
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "hash": actual_hash,
            "size": total_bytes,
            "pages": info.get("pages", 0),
            "aim": info.get("aim"),
            "exp_num": info.get("exp_num"),
            "is_assignment": info.get("is_assignment"),
            "extraction_method": info.get("extraction_method", "unextracted"),
            "failure_reason": info.get("failure_reason", "none"),
        })

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return jsonify({"success": False, "error": str(e)}), 500


# ── Extract aim & PDF info ───────────────────────────────────────────────────

@app.route("/api/extract-aim", methods=["POST"])
@limiter.limit("60 per minute")
def extract_aim():
    """Extract aim/title text, exp_num, type, and page count from an uploaded PDF identified by SHA-256 hash."""
    req = request.get_json() or {}
    h = (req.get("hash") or "").lower().strip()
    mode = req.get("mode", "auto")
    if not _valid_hash(h):
        return jsonify({"success": False, "error": "Invalid hash"}), 400

    fpath = os.path.join(UPLOADS_DIR, f"{h}.pdf")
    if not os.path.exists(fpath):
        return jsonify({"success": False, "error": "File not found — may have expired"}), 404

    info = inspect_pdf_info(fpath, mode=mode)
    return jsonify({
        "success": True,
        "aim": info.get("aim"),
        "pages": info.get("pages", 0),
        "exp_num": info.get("exp_num"),
        "is_assignment": info.get("is_assignment"),
    })


# ── Preview ────────────────────────────────────────────────────────────────────

@app.route("/api/preview", methods=["POST"])
@limiter.limit("60 per minute")
def preview_header():
    """Generates a base64 PNG preview of the filled header page."""
    req_data = request.get_json() or {}
    item_data = req_data.get("item", {})
    student = req_data.get("student", {})
    is_assgn = item_data.get("is_assignment", False)
    label = str(item_data.get("label", item_data.get("num", "1")))
    exp_label = f"Assign - {label}" if is_assgn else f"Exp - {label}"

    data = {
        "sem": student.get("sem", ""),
        "class_name": student.get("class_name", ""),
        "batch": student.get("batch", ""),
        "roll_no": student.get("roll_no", ""),
        "name": student.get("name", ""),
        "subject": student.get("subject", ""),
        "is_assignment": is_assgn,
        "exp_no": label,
        "title": item_data.get("title", ""),
        "perf_date": item_data.get("perf_date") or student.get("perf_date", ""),
        "sub_date": item_data.get("sub_date") or student.get("sub_date", ""),
    }
    formatting = {
        "text_color": student.get("text_color", "blue"),
        "strikethrough_enabled": student.get("strikethrough_enabled", True),
        "font_size": 11,
        "font_name": "helv",
    }
    try:
        preview_data_url = render_header_preview_png(TEMPLATE_HEADER, data, formatting, dpi=150)
        return jsonify({"success": True, "image_data": preview_data_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Generate ───────────────────────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
@limiter.limit("20 per minute")
def generate_pdfs():
    """
    Generates filled headers, merges with body PDFs in a concurrency-safe job directory,
    and produces a combined PDF and a ZIP package.
    Records fail-safe analytics event.
    """
    start_time = time.time()
    req_data = request.get_json() or {}
    student = req_data.get("student", {})
    experiments = req_data.get("experiments", [])
    include_toc = req_data.get("include_toc", True)

    if not experiments:
        return jsonify({"success": False, "error": "No experiments provided."}), 400

    if len(experiments) > 60:
        return jsonify({"success": False, "error": "Batch limit exceeded (maximum 60 experiments allowed per compilation)."}), 400

    # Enforce quota before job directory creation
    try:
        _enforce_storage_quota()
    except Exception:
        pass

    job_id = uuid.uuid4().hex

    try:
        # Record student ground truth for research and format discovery
        try:
            record_student_ground_truth(experiments)
        except Exception:
            pass

        formatting = req_data.get("formatting", {})
        result = generate_job_documents(
            student=student,
            experiments=experiments,
            output_dir=OUTPUT_DIR,
            uploads_dir=UPLOADS_DIR,
            template_path=TEMPLATE_HEADER,
            formatting=formatting,
            include_toc=include_toc,
            base_dir=BASE_DIR,
        )
        duration_ms = (time.time() - start_time) * 1000.0
        try:
            record_generation_event(
                student=student,
                experiments=experiments,
                success=True,
                duration_ms=duration_ms,
                generation_type="batch_package",
            )
        except Exception:
            pass
        return jsonify(result)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000.0
        try:
            record_generation_event(
                student=student,
                experiments=experiments,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
                generation_type="batch_package",
            )
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500


# ── Download ───────────────────────────────────────────────────────────────────

@app.route("/api/download/<path:filepath>")
def download_file(filepath):
    """
    Serves generated PDFs and ZIP packages with strict path-traversal protection.
    Restricted strictly to OUTPUT_DIR to prevent arbitrary local file reads.
    """
    norm_path = os.path.normpath(filepath).lstrip("/\\")
    if ".." in norm_path or norm_path.startswith(("/", "\\")):
        return jsonify({"error": "Invalid path"}), 400

    # Special-case template header if requested via download route
    if norm_path == "Header.pdf" and os.path.isfile(TEMPLATE_HEADER):
        return send_file(TEMPLATE_HEADER, mimetype="application/pdf")

    # Strictly search in OUTPUT_DIR only
    candidate_output = os.path.abspath(os.path.join(OUTPUT_DIR, norm_path))
    output_root = os.path.abspath(OUTPUT_DIR)

    if candidate_output.startswith(output_root + os.sep) and os.path.isfile(candidate_output):
        return send_file(candidate_output, as_attachment=True)

    return jsonify({"error": "File not found"}), 404


# ── Analytics System ───────────────────────────────────────────────────────────

def _check_analytics_auth():
    """Checks if the incoming request is authorized to view analytics."""
    if not is_analytics_enabled():
        return False, (jsonify({"error": "Analytics is disabled"}), 404)
    if not is_auth_required():
        return True, None

    auth_header = request.headers.get("X-Analytics-Key") or request.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        auth_header = auth_header[7:]
    if verify_admin_password(auth_header):
        return True, None
    return False, (jsonify({"error": "Unauthorized", "auth_required": True}), 401)


@app.route("/analytics")
def analytics_page():
    """Dedicated hidden analytics dashboard route."""
    if not is_analytics_enabled():
        return ("Not Found", 404)
    spa_dist_index = os.path.join(BASE_DIR, "frontend", "dist", "index.html")
    if os.path.exists(spa_dist_index):
        return send_file(spa_dist_index)
    return render_template("index.html")


@app.route("/api/analytics/status", methods=["GET"])
def analytics_status():
    """Returns analytics status and whether an admin password is required."""
    enabled = is_analytics_enabled()
    if not enabled:
        return jsonify({"enabled": False, "auth_required": False}), 404
    return jsonify({
        "enabled": True,
        "auth_required": is_auth_required(),
    })


@app.route("/api/analytics/auth", methods=["POST"])
@limiter.limit("15 per minute")
def analytics_authenticate():
    """Validates the admin password."""
    if not is_analytics_enabled():
        return jsonify({"error": "Analytics is disabled"}), 404
    data = request.get_json() or {}
    candidate = data.get("password") or request.headers.get("X-Analytics-Key") or ""
    if verify_admin_password(candidate):
        return jsonify({"valid": True, "auth_required": is_auth_required()})
    return jsonify({"valid": False, "error": "Invalid admin password"}), 401


@app.route("/api/analytics/summary", methods=["GET"])
@limiter.limit("60 per minute")
def analytics_summary():
    """Returns aggregated high-level usage metrics, timeline trends, and rankings."""
    is_auth, err_resp = _check_analytics_auth()
    if not is_auth:
        return err_resp
    try:
        summary = get_analytics_summary()
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/events", methods=["GET"])
@limiter.limit("60 per minute")
def analytics_events():
    """Returns searchable, paginated generation events log."""
    is_auth, err_resp = _check_analytics_auth()
    if not is_auth:
        return err_resp

    query = request.args.get("q", "").strip() or None
    subject = request.args.get("subject", "").strip() or None
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 50, 0

    try:
        events, total = get_generation_events(query=query, subject=subject, limit=limit, offset=offset)
        return jsonify({
            "success": True,
            "data": {
                "events": events,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/export", methods=["GET"])
@limiter.limit("30 per minute")
def analytics_export():
    """Exports usage analytics in CSV or JSON format for download."""
    is_auth, err_resp = _check_analytics_auth()
    if not is_auth:
        return err_resp

    export_format = request.args.get("format", "csv").lower().strip()
    date_str = time.strftime("%Y-%m-%d")

    try:
        if export_format == "json":
            json_data = export_analytics_json()
            return Response(
                json_data,
                mimetype="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="labstudio_analytics_{date_str}.json"'
                },
            )
        else:
            csv_data = export_analytics_csv()
            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="labstudio_analytics_{date_str}.csv"'
                },
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/diagnostics", methods=["GET"])
@limiter.limit("60 per minute")
def analytics_diagnostics():
    """Returns extraction diagnostics summary and list of failed/discrepant samples for format analysis."""
    is_auth, err_resp = _check_analytics_auth()
    if not is_auth:
        return err_resp
    try:
        summary = get_extraction_diagnostics_summary()
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
        samples, total = get_failed_or_discrepant_samples(limit=limit, offset=offset)
        return jsonify({
            "success": True,
            "data": {
                "summary": summary,
                "samples": samples,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/sample/<hash_val>", methods=["GET"])
def download_diagnostic_sample(hash_val):
    """Allows authenticated admins to download a raw uploaded PDF for local format/parser analysis."""
    is_auth, err_resp = _check_analytics_auth()
    if not is_auth:
        return err_resp
    hash_val = hash_val.lower().strip()
    if not _valid_hash(hash_val):
        return jsonify({"error": "Invalid hash"}), 400
    sample_path = os.path.join(UPLOADS_DIR, f"{hash_val}.pdf")
    if os.path.isfile(sample_path):
        return send_file(sample_path, as_attachment=True, download_name=f"sample_{hash_val[:12]}.pdf")
    return jsonify({"error": "Sample PDF not found on disk"}), 404


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if is_analytics_enabled():
        try:
            init_analytics_db()
        except Exception:
            pass
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
