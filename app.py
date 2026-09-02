import os
import time
import uuid
import hashlib
import threading
import shutil
from typing import Optional
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
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
    is_analytics_enabled,
    is_auth_required,
    verify_admin_password,
)

APP_START_TIME = time.time()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload size

# Enable CORS for development (Vite port 5173) and production CDN domains
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per hour", "200 per minute"],
    storage_uri="memory://",
)

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_HEADER = os.path.join(BASE_DIR, "Header.pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

for d in (OUTPUT_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

# ── Background Ephemeral Sweeper & LRU Storage Quota Manager ──────────────────
UPLOADS_TTL_SECONDS = 24 * 60 * 60   # 24 hours for uploaded files
JOBS_TTL_SECONDS = 2 * 60 * 60       # 2 hours for generated job output packages
SWEEP_EVERY_SECONDS = 15 * 60        # run sweep every 15 minutes
MAX_STORAGE_BYTES = 750 * 1024 * 1024  # 750 MB max storage cap on Render
TARGET_STORAGE_BYTES = 350 * 1024 * 1024 # Target clean size during eviction


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
    Enforces maximum disk quota using Least Recently Used (LRU) eviction.
    If total disk usage across uploads/ and output/ exceeds MAX_STORAGE_BYTES,
    oldest files and job folders are deleted until usage is below TARGET_STORAGE_BYTES.
    """
    uploads_size = _get_dir_size(UPLOADS_DIR)
    output_size = _get_dir_size(OUTPUT_DIR)
    total_size = uploads_size + output_size

    if total_size <= MAX_STORAGE_BYTES:
        return

    items = []

    # Uploaded files
    try:
        for fname in os.listdir(UPLOADS_DIR):
            fpath = os.path.join(UPLOADS_DIR, fname)
            if os.path.isfile(fpath):
                try:
                    items.append((os.path.getmtime(fpath), os.path.getsize(fpath), fpath, True))
                except OSError:
                    pass
    except OSError:
        pass

    # Output job directories
    try:
        for entry in os.listdir(OUTPUT_DIR):
            epath = os.path.join(OUTPUT_DIR, entry)
            if os.path.isdir(epath) and entry != "headers":
                try:
                    sz = _get_dir_size(epath)
                    items.append((os.path.getmtime(epath), sz, epath, False))
                except OSError:
                    pass
    except OSError:
        pass

    # Sort oldest first (ascending mtime)
    items.sort(key=lambda x: x[0])

    current_size = total_size
    for _, sz, item_path, is_file in items:
        if current_size <= TARGET_STORAGE_BYTES:
            break
        try:
            if is_file:
                os.remove(item_path)
            else:
                shutil.rmtree(item_path, ignore_errors=True)
            current_size -= sz
        except Exception:
            pass


def _cleanup_ephemeral_storage():
    """
    1. Sweeps TTL-expired uploads (> 24h) and expired job outputs (> 2h).
    2. Enforces maximum storage quota via LRU eviction.
    3. Re-schedules itself periodically.
    """
    now = time.time()
    # 1. Sweep uploads directory
    try:
        for fname in os.listdir(UPLOADS_DIR):
            fpath = os.path.join(UPLOADS_DIR, fname)
            if os.path.isfile(fpath):
                if (now - os.path.getmtime(fpath)) > UPLOADS_TTL_SECONDS:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
    except Exception as e:
        print(f"[cleanup] error sweeping uploads: {e}")

    # 2. Sweep job-scoped output directories
    try:
        for entry in os.listdir(OUTPUT_DIR):
            epath = os.path.join(OUTPUT_DIR, entry)
            if os.path.isdir(epath) and entry != "headers":
                if (now - os.path.getmtime(epath)) > JOBS_TTL_SECONDS:
                    try:
                        shutil.rmtree(epath, ignore_errors=True)
                    except Exception:
                        pass
    except Exception as e:
        print(f"[cleanup] error sweeping output jobs: {e}")

    # 3. Enforce LRU storage quota
    try:
        _enforce_storage_quota()
    except Exception as e:
        print(f"[cleanup] error enforcing quota: {e}")
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


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Render/HuggingFace cold-start handshakes and monitoring."""
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
    """Check if a file with the given SHA-256 hash exists and is not expired."""
    hash_val = hash_val.lower().strip()
    if not _valid_hash(hash_val):
        return jsonify({"exists": False, "error": "Invalid hash"}), 400

    fpath = os.path.join(UPLOADS_DIR, f"{hash_val}.pdf")
    if os.path.exists(fpath):
        age = time.time() - os.path.getmtime(fpath)
        if age <= UPLOADS_TTL_SECONDS:
            info = inspect_pdf_info(fpath)
            return jsonify({"exists": True, "pages": info.get("pages", 0)})
    return jsonify({"exists": False}), 404


@app.route("/api/upload", methods=["POST"])
@limiter.limit("40 per minute")
def upload_file():
    """
    Accepts a PDF file upload via chunked streaming to prevent 512MB RAM spikes.
    Stores as uploads/<sha256>.pdf. Returns metadata.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    f = request.files["file"]
    claimed_hash = (request.form.get("hash") or "").lower().strip()

    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF files are accepted"}), 400

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

        # Max page safety limit
        if info.get("pages", 0) > 100:
            if os.path.exists(dest):
                os.remove(dest)
            return jsonify({"success": False, "error": "PDF exceeds 100-page limit."}), 400

        return jsonify({
            "success": True,
            "hash": actual_hash,
            "size": total_bytes,
            "pages": info.get("pages", 0),
            "aim": info.get("aim"),
            "exp_num": info.get("exp_num"),
            "is_assignment": info.get("is_assignment"),
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

    # Enforce quota before job directory creation
    try:
        _enforce_storage_quota()
    except Exception:
        pass

    job_id = uuid.uuid4().hex

    try:
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
    Serves generated PDFs and ZIP packages with path-traversal protection.
    """
    norm_path = os.path.normpath(filepath).lstrip("/\\")
    if ".." in norm_path:
        return jsonify({"error": "Invalid path"}), 400

    # 1. Search in OUTPUT_DIR
    candidate_output = os.path.join(OUTPUT_DIR, norm_path)
    if os.path.isfile(candidate_output) and os.path.abspath(candidate_output).startswith(os.path.abspath(OUTPUT_DIR)):
        return send_file(candidate_output, as_attachment=True)

    # 2. Search in BASE_DIR
    candidate_base = os.path.join(BASE_DIR, norm_path)
    if os.path.isfile(candidate_base) and os.path.abspath(candidate_base).startswith(os.path.abspath(BASE_DIR)):
        return send_file(candidate_base, as_attachment=True)

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


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if is_analytics_enabled():
        try:
            init_analytics_db()
        except Exception:
            pass
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
