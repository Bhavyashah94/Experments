"""
Lab Header Studio - Lightweight First-Party Usage Analytics Engine
Backed by SQLite with indexing for fast queries and zero external dependencies.
"""

import os
import io
import csv
import json
import sqlite3
import hmac
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "analytics.db")


def get_db_path() -> str:
    """Returns the configured or default database path."""
    return os.environ.get("ANALYTICS_DB_PATH", DEFAULT_DB_PATH)


def is_analytics_enabled() -> bool:
    """
    Analytics is enabled by default all the time.
    Can be explicitly disabled only if ENABLE_ANALYTICS is set to 'false', '0', or 'no'.
    """
    val = os.environ.get("ENABLE_ANALYTICS", "true").lower().strip()
    return val not in ("false", "0", "no", "off")


def get_admin_password() -> str:
    """Returns the configured admin password if set in environment."""
    return (
        os.environ.get("ANALYTICS_ADMIN_PASSWORD")
        or os.environ.get("ADMIN_PASSWORD")
        or ""
    ).strip()


def is_auth_required() -> bool:
    """Returns True if an admin password has been set in the environment."""
    return bool(get_admin_password())


def verify_admin_password(candidate: Optional[str]) -> bool:
    """
    Verifies the provided password against the environment variable.
    If no admin password is configured, access is open.
    Uses constant-time comparison to prevent timing attacks.
    """
    expected = get_admin_password()
    if not expected:
        return True
    if not candidate:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


_INITIALIZED_DBS = set()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a connection to SQLite database and ensures schema and indexes exist."""
    path = db_path or get_db_path()
    db_dir = os.path.dirname(path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 15000;")
    except Exception:
        pass

    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    student_name TEXT,
                    roll_no TEXT,
                    batch TEXT,
                    class_name TEXT,
                    sem TEXT,
                    subject TEXT,
                    experiment_count INTEGER NOT NULL DEFAULT 0,
                    experiments_json TEXT,
                    generation_type TEXT NOT NULL DEFAULT 'batch_package',
                    success INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT,
                    duration_ms REAL NOT NULL DEFAULT 0.0
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_timestamp ON generation_events(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_roll_no ON generation_events(roll_no);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_subject ON generation_events(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_student ON generation_events(student_name, roll_no);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_success ON generation_events(success);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_class_batch ON generation_events(class_name, batch);")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS extraction_diagnostics (
                    sha256 TEXT PRIMARY KEY,
                    filename TEXT,
                    file_size INTEGER,
                    pages INTEGER,
                    extracted_aim TEXT,
                    extracted_exp_num TEXT,
                    extraction_method TEXT,
                    failure_reason TEXT,
                    student_submitted_title TEXT,
                    student_submitted_num TEXT,
                    discrepancy INTEGER DEFAULT 0,
                    text_snippet TEXT,
                    uploaded_at TEXT,
                    is_sample_preserved INTEGER DEFAULT 0
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diag_method ON extraction_diagnostics(extraction_method);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diag_failure ON extraction_diagnostics(failure_reason);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diag_discrepancy ON extraction_diagnostics(discrepancy);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diag_uploaded ON extraction_diagnostics(uploaded_at);")
    except Exception as e:
        logger.warning(f"Failed to initialize schema for {path}: {e}")

    return conn


def init_analytics_db(db_path: Optional[str] = None) -> None:
    """Explicitly initializes the generation_events table and required performance indexes."""
    conn = get_db_connection(db_path)
    conn.close()


def record_generation_event(
    student: Dict[str, Any],
    experiments: List[Dict[str, Any]],
    success: bool = True,
    duration_ms: float = 0.0,
    error_message: Optional[str] = None,
    generation_type: str = "batch_package",
    db_path: Optional[str] = None,
) -> bool:
    """
    Safely records a document generation event.
    Fail-safe: any database error is logged and suppressed so document generation never fails.
    """
    if not is_analytics_enabled():
        return False

    try:
        # Extract and sanitize experiments metadata (NO binary or PDF payloads)
        exp_metadata = []
        for exp in experiments or []:
            if isinstance(exp, dict):
                exp_metadata.append({
                    "label": str(exp.get("label", "")),
                    "is_assignment": bool(exp.get("is_assignment", False)),
                    "title": str(exp.get("title", "")),
                    "hash": str(exp.get("hash", "")) if exp.get("hash") else None,
                    "pages": int(exp.get("pages", 0)) if exp.get("pages") else 0,
                    "perf_date": str(exp.get("perf_date", "")),
                    "sub_date": str(exp.get("sub_date", "")),
                })

        timestamp_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        experiments_json = json.dumps(exp_metadata)

        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO generation_events (
                        timestamp,
                        student_name,
                        roll_no,
                        batch,
                        class_name,
                        sem,
                        subject,
                        experiment_count,
                        experiments_json,
                        generation_type,
                        success,
                        error_message,
                        duration_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    timestamp_iso,
                    str(student.get("name", "")).strip() or None,
                    str(student.get("roll_no", "")).strip() or None,
                    str(student.get("batch", "")).strip() or None,
                    str(student.get("class_name", "")).strip() or None,
                    str(student.get("sem", "")).strip() or None,
                    str(student.get("subject", "")).strip() or None,
                    len(exp_metadata),
                    experiments_json,
                    generation_type,
                    1 if success else 0,
                    error_message,
                    round(float(duration_ms), 2),
                ))
            return True
        finally:
            conn.close()
    except Exception as e:
        logger.warning("Failed to record usage analytics event: %s", e)
        return False


def get_analytics_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes overall summary statistics, daily generation trends, top subjects, and top experiments.
    """
    init_analytics_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        # 1. Total counts & overall success metrics
        cur.execute("""
            SELECT
                COUNT(*) as total_events,
                COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successful_events,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as failed_events,
                COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms,
                COALESCE(SUM(experiment_count), 0) as total_experiments_generated,
                COUNT(DISTINCT CASE
                    WHEN roll_no IS NOT NULL AND TRIM(roll_no) != '' THEN 'roll_' || roll_no
                    WHEN student_name IS NOT NULL AND TRIM(student_name) != '' THEN 'name_' || student_name
                    ELSE 'anon_' || id
                END) as unique_students
            FROM generation_events;
        """)
        row = cur.fetchone()
        total_events = row["total_events"]
        successful_events = row["successful_events"]
        failed_events = row["failed_events"]
        avg_duration_ms = round(row["avg_duration_ms"], 1)
        total_experiments = row["total_experiments_generated"]
        unique_students = row["unique_students"]

        success_rate = round((successful_events / total_events * 100), 1) if total_events > 0 else 100.0

        # 2. Daily volume timeline (last 30 days)
        cur.execute("""
            SELECT
                SUBSTR(timestamp, 1, 10) as day,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
            FROM generation_events
            GROUP BY day
            ORDER BY day ASC
            LIMIT 30;
        """)
        daily_trends = [{"date": r["day"], "count": r["total"], "successes": r["successes"]} for r in cur.fetchall()]

        # 3. Top subjects ranking
        cur.execute("""
            SELECT
                COALESCE(subject, 'Unspecified') as subject_name,
                COUNT(*) as count,
                COUNT(DISTINCT roll_no) as student_count
            FROM generation_events
            WHERE subject IS NOT NULL AND subject != ''
            GROUP BY subject_name
            ORDER BY count DESC
            LIMIT 10;
        """)
        top_subjects = [{"subject": r["subject_name"], "count": r["count"], "students": r["student_count"]} for r in cur.fetchall()]

        # 4. Top experiments frequency
        cur.execute("""
            SELECT experiments_json
            FROM generation_events
            WHERE experiments_json IS NOT NULL AND experiments_json != '' AND success = 1
            ORDER BY id DESC
            LIMIT 500;
        """)
        exp_counts: Dict[str, int] = {}
        for r in cur.fetchall():
            try:
                items = json.loads(r["experiments_json"])
                for item in items:
                    title = (item.get("title") or "").strip()
                    label = (item.get("label") or "").strip()
                    is_assgn = item.get("is_assignment", False)
                    prefix = "Assign" if is_assgn else "Exp"
                    key = f"{prefix} {label}: {title}" if title else f"{prefix} {label}"
                    exp_counts[key] = exp_counts.get(key, 0) + 1
            except Exception:
                pass

        top_experiments = sorted(
            [{"name": k, "count": v} for k, v in exp_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        return {
            "total_generations": total_events,
            "successful_generations": successful_events,
            "failed_generations": failed_events,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration_ms,
            "total_experiments_generated": total_experiments,
            "unique_students": unique_students,
            "daily_trends": daily_trends,
            "top_subjects": top_subjects,
            "top_experiments": top_experiments,
        }
    finally:
        conn.close()


def get_generation_events(
    query: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns filtered and paginated generation events with total matching count.
    """
    init_analytics_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        conditions = []
        params: List[Any] = []

        if query:
            q_clean = f"%{query.strip()}%"
            conditions.append("(student_name LIKE ? OR roll_no LIKE ? OR batch LIKE ? OR class_name LIKE ?)")
            params.extend([q_clean, q_clean, q_clean, q_clean])

        if subject:
            conditions.append("subject = ?")
            params.append(subject.strip())

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Total count query
        cur.execute(f"SELECT COUNT(*) as total FROM generation_events {where_clause};", params)
        total_count = cur.fetchone()["total"]

        # Paginated rows query
        query_params = list(params) + [limit, offset]
        cur.execute(f"""
            SELECT
                id,
                timestamp,
                student_name,
                roll_no,
                batch,
                class_name,
                sem,
                subject,
                experiment_count,
                experiments_json,
                generation_type,
                success,
                error_message,
                duration_ms
            FROM generation_events
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
        """, query_params)

        rows = []
        for r in cur.fetchall():
            exp_items = []
            if r["experiments_json"]:
                try:
                    exp_items = json.loads(r["experiments_json"])
                except Exception:
                    pass
            rows.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "student_name": r["student_name"] or "Anonymous",
                "roll_no": r["roll_no"] or "—",
                "batch": r["batch"] or "—",
                "class_name": r["class_name"] or "—",
                "sem": r["sem"] or "—",
                "subject": r["subject"] or "—",
                "experiment_count": r["experiment_count"],
                "experiments": exp_items,
                "generation_type": r["generation_type"],
                "success": bool(r["success"]),
                "error_message": r["error_message"],
                "duration_ms": r["duration_ms"],
            })

        return rows, total_count
    finally:
        conn.close()


def _sanitize_csv_cell(val: Any) -> Any:
    """Escapes leading spreadsheet formula injection characters (=, +, -, @, \\t, \\r)."""
    if isinstance(val, str):
        s = val.strip()
        if s.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{s}"
    return val


def export_analytics_csv(db_path: Optional[str] = None) -> str:
    """
    Exports all recorded generation events as standard RFC 4180 CSV string.
    """
    events, _ = get_generation_events(limit=100000, offset=0, db_path=db_path)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header Row
    writer.writerow([
        "Event ID",
        "Timestamp (UTC)",
        "Student Name",
        "Roll Number",
        "Batch",
        "Class",
        "Semester",
        "Subject",
        "Experiment Count",
        "Generation Type",
        "Status",
        "Duration (ms)",
        "Error Message",
        "Experiments List",
    ])

    for ev in events:
        exp_summary_list = []
        for exp in ev.get("experiments", []):
            prefix = "Assign" if exp.get("is_assignment") else "Exp"
            lbl = exp.get("label", "")
            title = exp.get("title", "")
            exp_summary_list.append(f"{prefix} {lbl}: {title}" if title else f"{prefix} {lbl}")

        writer.writerow([
            _sanitize_csv_cell(ev["id"]),
            _sanitize_csv_cell(ev["timestamp"]),
            _sanitize_csv_cell(ev["student_name"]),
            _sanitize_csv_cell(ev["roll_no"]),
            _sanitize_csv_cell(ev["batch"]),
            _sanitize_csv_cell(ev["class_name"]),
            _sanitize_csv_cell(ev["sem"]),
            _sanitize_csv_cell(ev["subject"]),
            _sanitize_csv_cell(ev["experiment_count"]),
            _sanitize_csv_cell(ev["generation_type"]),
            _sanitize_csv_cell("SUCCESS" if ev["success"] else "FAILED"),
            _sanitize_csv_cell(ev["duration_ms"]),
            _sanitize_csv_cell(ev["error_message"] or ""),
            _sanitize_csv_cell(" | ".join(exp_summary_list)),
        ])

    return output.getvalue()


def export_analytics_json(db_path: Optional[str] = None) -> str:
    """
    Exports complete analytics metrics and raw events log as structured JSON.
    """
    summary = get_analytics_summary(db_path=db_path)
    events, total = get_generation_events(limit=100000, offset=0, db_path=db_path)
    payload = {
        "export_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_records": total,
        "summary": summary,
        "events": events,
    }
    return json.dumps(payload, indent=2)


# ── Student-Wise Analytics & Dossiers ─────────────────────────────────────────

def get_students_summary(
    query: Optional[str] = None,
    class_name: Optional[str] = None,
    batch: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "last_active",
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, List[str], List[str]]:
    """
    Aggregates generation events grouped by student identity (roll_no, student_name).
    Returns (students_list, total_count, available_classes, available_batches).
    """
    init_analytics_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        # Fetch distinct classes and batches for UI filters
        cur.execute("SELECT DISTINCT class_name FROM generation_events WHERE class_name IS NOT NULL AND TRIM(class_name) != '' ORDER BY class_name ASC;")
        available_classes = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT DISTINCT batch FROM generation_events WHERE batch IS NOT NULL AND TRIM(batch) != '' ORDER BY batch ASC;")
        available_batches = [r[0] for r in cur.fetchall()]

        conditions = []
        params: List[Any] = []

        if query:
            q_clean = f"%{query.strip()}%"
            conditions.append("(student_name LIKE ? OR roll_no LIKE ?)")
            params.extend([q_clean, q_clean])

        if class_name:
            conditions.append("class_name = ?")
            params.append(class_name.strip())

        if batch:
            conditions.append("batch = ?")
            params.append(batch.strip())

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Total unique students count matching filter
        cur.execute(f"""
            SELECT COUNT(*) as total_students FROM (
                SELECT 1
                FROM generation_events
                {where_clause}
                GROUP BY
                    COALESCE(NULLIF(TRIM(roll_no), ''), '—'),
                    COALESCE(NULLIF(TRIM(student_name), ''), 'Anonymous')
            );
        """, params)
        total_students = cur.fetchone()["total_students"]

        # Sort order mapping
        sort_clause = "ORDER BY last_active DESC"
        if sort_by == "compilations":
            sort_clause = "ORDER BY total_compilations DESC, last_active DESC"
        elif sort_by == "experiments":
            sort_clause = "ORDER BY total_experiments DESC, last_active DESC"
        elif sort_by == "roll_no":
            sort_clause = "ORDER BY roll_no ASC, last_active DESC"
        elif sort_by == "name":
            sort_clause = "ORDER BY student_name ASC, last_active DESC"

        query_params = list(params) + [limit, offset]
        cur.execute(f"""
            SELECT
                COALESCE(NULLIF(TRIM(roll_no), ''), '—') as roll_no,
                COALESCE(NULLIF(TRIM(student_name), ''), 'Anonymous') as student_name,
                COALESCE(MAX(NULLIF(TRIM(class_name), '')), '—') as class_name,
                COALESCE(MAX(NULLIF(TRIM(batch), '')), '—') as batch,
                COALESCE(MAX(NULLIF(TRIM(sem), '')), '—') as sem,
                COUNT(*) as total_compilations,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_compilations,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_compilations,
                SUM(experiment_count) as total_experiments,
                GROUP_CONCAT(DISTINCT subject) as subjects_csv,
                COUNT(DISTINCT subject) as subjects_count,
                MIN(timestamp) as first_active,
                MAX(timestamp) as last_active
            FROM generation_events
            {where_clause}
            GROUP BY
                COALESCE(NULLIF(TRIM(roll_no), ''), '—'),
                COALESCE(NULLIF(TRIM(student_name), ''), 'Anonymous')
            {sort_clause}
            LIMIT ? OFFSET ?;
        """, query_params)

        rows = []
        for r in cur.fetchall():
            subjects_csv = r["subjects_csv"] or ""
            subjects_list = [s.strip() for s in subjects_csv.split(",") if s.strip()]
            unique_subjects = list(dict.fromkeys(subjects_list))

            rows.append({
                "roll_no": r["roll_no"],
                "student_name": r["student_name"],
                "class_name": r["class_name"],
                "batch": r["batch"],
                "sem": r["sem"],
                "total_compilations": r["total_compilations"],
                "successful_compilations": r["successful_compilations"],
                "failed_compilations": r["failed_compilations"],
                "total_experiments": r["total_experiments"] or 0,
                "subjects": unique_subjects,
                "subjects_count": len(unique_subjects),
                "first_active": r["first_active"],
                "last_active": r["last_active"],
            })

        return rows, total_students, available_classes, available_batches
    finally:
        conn.close()


def get_student_detail(
    roll_no: Optional[str] = None,
    student_name: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Returns full student dossier: profile metrics and chronological timeline
    of every compilation event for this student.
    """
    init_analytics_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        conditions = []
        params = []
        if roll_no and roll_no != "—":
            conditions.append("roll_no = ?")
            params.append(roll_no.strip())
        if student_name and student_name != "Anonymous":
            conditions.append("student_name = ?")
            params.append(student_name.strip())

        if not conditions:
            return None

        where_clause = "WHERE " + " AND ".join(conditions)

        cur.execute(f"""
            SELECT
                id,
                timestamp,
                student_name,
                roll_no,
                batch,
                class_name,
                sem,
                subject,
                experiment_count,
                experiments_json,
                generation_type,
                success,
                error_message,
                duration_ms
            FROM generation_events
            {where_clause}
            ORDER BY id DESC;
        """, params)

        raw_events = cur.fetchall()
        if not raw_events:
            return None

        # Build chronological timeline
        timeline = []
        all_subjects = []
        total_experiments = 0
        total_duration = 0.0

        for r in raw_events:
            exp_items = []
            if r["experiments_json"]:
                try:
                    exp_items = json.loads(r["experiments_json"])
                except Exception:
                    pass

            if r["subject"]:
                all_subjects.append(r["subject"])
            total_experiments += (r["experiment_count"] or 0)
            total_duration += (r["duration_ms"] or 0.0)

            timeline.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "subject": r["subject"] or "—",
                "experiment_count": r["experiment_count"],
                "experiments": exp_items,
                "generation_type": r["generation_type"],
                "success": bool(r["success"]),
                "error_message": r["error_message"],
                "duration_ms": r["duration_ms"],
            })

        latest = raw_events[0]
        unique_subjects = list(dict.fromkeys(all_subjects))

        return {
            "roll_no": latest["roll_no"] or "—",
            "student_name": latest["student_name"] or "Anonymous",
            "class_name": latest["class_name"] or "—",
            "batch": latest["batch"] or "—",
            "sem": latest["sem"] or "—",
            "total_compilations": len(raw_events),
            "successful_compilations": sum(1 for r in raw_events if r["success"]),
            "failed_compilations": sum(1 for r in raw_events if not r["success"]),
            "total_experiments": total_experiments,
            "avg_duration_ms": round(total_duration / len(raw_events), 1) if raw_events else 0.0,
            "subjects": unique_subjects,
            "subjects_count": len(unique_subjects),
            "first_active": raw_events[-1]["timestamp"],
            "last_active": raw_events[0]["timestamp"],
            "timeline": timeline,
        }
    finally:
        conn.close()


def export_students_csv(db_path: Optional[str] = None) -> str:
    """
    Exports all student profiles as RFC 4180 CSV spreadsheet.
    """
    students, _, _, _ = get_students_summary(limit=100000, offset=0, db_path=db_path)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Roll Number",
        "Student Name",
        "Class",
        "Batch",
        "Semester",
        "Total Compilations",
        "Successful Compilations",
        "Failed Compilations",
        "Total Experiments Processed",
        "Unique Subjects Count",
        "Subjects Enrolled",
        "First Active (UTC)",
        "Last Active (UTC)",
    ])

    for s in students:
        writer.writerow([
            _sanitize_csv_cell(s["roll_no"]),
            _sanitize_csv_cell(s["student_name"]),
            _sanitize_csv_cell(s["class_name"]),
            _sanitize_csv_cell(s["batch"]),
            _sanitize_csv_cell(s["sem"]),
            _sanitize_csv_cell(s["total_compilations"]),
            _sanitize_csv_cell(s["successful_compilations"]),
            _sanitize_csv_cell(s["failed_compilations"]),
            _sanitize_csv_cell(s["total_experiments"]),
            _sanitize_csv_cell(s["subjects_count"]),
            _sanitize_csv_cell(" | ".join(s["subjects"])),
            _sanitize_csv_cell(s["first_active"]),
            _sanitize_csv_cell(s["last_active"]),
        ])

    return output.getvalue()


# ── Extraction Diagnostics & Ground-Truth Format Discovery ────────────────────

def record_upload_diagnostic(
    sha256: str,
    filename: str,
    file_size: int,
    pages: int,
    extracted_aim: Optional[str],
    extracted_exp_num: Optional[str],
    extraction_method: str,
    failure_reason: str,
    text_snippet: str,
    db_path: Optional[str] = None,
) -> None:
    """
    Records extraction diagnostic signals for every uploaded PDF.
    Helps internal analysis of why heuristics fail and discover new university formats.
    """
    if not is_analytics_enabled():
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    initial_preserved = 1 if (failure_reason and failure_reason != "none") else 0
    conn = None
    try:
        conn = get_db_connection(db_path)
        with conn:
            conn.execute("""
                INSERT INTO extraction_diagnostics (
                    sha256, filename, file_size, pages, extracted_aim,
                    extracted_exp_num, extraction_method, failure_reason,
                    text_snippet, uploaded_at, is_sample_preserved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sha256) DO UPDATE SET
                    filename = excluded.filename,
                    file_size = excluded.file_size,
                    pages = excluded.pages,
                    extracted_aim = excluded.extracted_aim,
                    extracted_exp_num = excluded.extracted_exp_num,
                    extraction_method = excluded.extraction_method,
                    failure_reason = excluded.failure_reason,
                    text_snippet = excluded.text_snippet,
                    is_sample_preserved = CASE
                        WHEN excluded.failure_reason != 'none' THEN 1
                        ELSE is_sample_preserved
                    END;
            """, (
                sha256, filename, file_size, pages, extracted_aim,
                extracted_exp_num, extraction_method, failure_reason,
                text_snippet, now_iso, initial_preserved
            ))
    except Exception as e:
        logger.warning(f"Failed to record upload diagnostic: {e}")
    finally:
        if conn:
            conn.close()


def record_student_ground_truth(
    experiments: List[Dict[str, Any]],
    db_path: Optional[str] = None,
) -> None:
    """
    When students submit /api/generate, compare their submitted title and experiment number
    against the extracted values. If different, record as discrepancy (ground truth).
    """
    if not is_analytics_enabled() or not experiments:
        return

    conn = None
    try:
        conn = get_db_connection(db_path)
        with conn:
            for item in experiments:
                file_hash = str(item.get("hash") or "").strip().lower()
                submitted_title = str(item.get("title") or "").strip()
                submitted_num = str(item.get("label") or item.get("num") or "").strip()

                if not file_hash or len(file_hash) != 64:
                    continue

                # Query existing diagnostic record
                cursor = conn.execute(
                    "SELECT extracted_aim, extracted_exp_num FROM extraction_diagnostics WHERE sha256 = ?",
                    (file_hash,)
                )
                row = cursor.fetchone()
                if row:
                    extracted_aim = (row["extracted_aim"] or "").strip()
                    extracted_num = (row["extracted_exp_num"] or "").strip()

                    # Discrepancy if title was missing or changed by student
                    has_discrepancy = 0
                    if not extracted_aim or (submitted_title and submitted_title.lower() != extracted_aim.lower()):
                        has_discrepancy = 1
                    if extracted_num and submitted_num and extracted_num != submitted_num:
                        has_discrepancy = 1

                    conn.execute("""
                        UPDATE extraction_diagnostics
                        SET student_submitted_title = ?,
                            student_submitted_num = ?,
                            discrepancy = ?,
                            is_sample_preserved = CASE
                                WHEN ? = 1 THEN 1
                                ELSE is_sample_preserved
                            END
                        WHERE sha256 = ?;
                    """, (submitted_title, submitted_num, has_discrepancy, has_discrepancy, file_hash))
    except Exception as e:
        logger.warning(f"Failed to record student ground truth: {e}")
    finally:
        if conn:
            conn.close()


def get_extraction_diagnostics_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Summarizes extraction performance, failure breakdown, and discrepancy counts.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        # Total diagnostic records
        cur.execute("SELECT COUNT(*) FROM extraction_diagnostics;")
        total = cur.fetchone()[0]

        # By extraction method
        cur.execute("""
            SELECT extraction_method, COUNT(*) as count
            FROM extraction_diagnostics
            GROUP BY extraction_method
            ORDER BY count DESC;
        """)
        methods = {row["extraction_method"]: row["count"] for row in cur.fetchall()}

        # By failure reason
        cur.execute("""
            SELECT failure_reason, COUNT(*) as count
            FROM extraction_diagnostics
            WHERE failure_reason != 'none'
            GROUP BY failure_reason
            ORDER BY count DESC;
        """)
        failures = {row["failure_reason"]: row["count"] for row in cur.fetchall()}

        # Total discrepancies (student override or missing title filled)
        cur.execute("SELECT COUNT(*) FROM extraction_diagnostics WHERE discrepancy = 1;")
        discrepancies = cur.fetchone()[0]

        success_count = methods.get("aim_keyword", 0) + methods.get("header_title", 0)
        success_rate = round((success_count / total * 100), 1) if total > 0 else 100.0

        return {
            "total_documents": total,
            "success_rate_percent": success_rate,
            "methods": methods,
            "failures": failures,
            "discrepancies_count": discrepancies,
        }
    finally:
        conn.close()


def get_failed_or_discrepant_samples(
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns documents where extraction failed or where students corrected the title.
    """
    docs, total, _ = get_failed_aim_documents(limit=limit, offset=offset, db_path=db_path)
    return docs, total


def get_failed_aim_documents(
    query: Optional[str] = None,
    reason: Optional[str] = None,
    method: Optional[str] = None,
    discrepancy_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
    """
    Queries documents where extraction failed or where students corrected the extracted title.
    Supports search by filename/aim, filter by failure reason, and filter by extraction method.
    Returns (documents_list, total_count, summary_stats).
    """
    init_analytics_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        summary = get_extraction_diagnostics_summary(db_path)

        conditions = []
        params: List[Any] = []

        if discrepancy_only:
            conditions.append("discrepancy = 1")
        else:
            conditions.append("(discrepancy = 1 OR failure_reason != 'none')")

        if query:
            q_clean = f"%{query.strip()}%"
            conditions.append("(filename LIKE ? OR extracted_aim LIKE ? OR student_submitted_title LIKE ?)")
            params.extend([q_clean, q_clean, q_clean])

        if reason and reason.lower() != "all":
            conditions.append("failure_reason = ?")
            params.append(reason.strip())

        if method and method.lower() != "all":
            conditions.append("extraction_method = ?")
            params.append(method.strip())

        where_clause = "WHERE " + " AND ".join(conditions)

        cur.execute(f"SELECT COUNT(*) as total FROM extraction_diagnostics {where_clause};", params)
        total_count = cur.fetchone()["total"]

        query_params = list(params) + [limit, offset]
        cur.execute(f"""
            SELECT
                sha256,
                filename,
                file_size,
                pages,
                extracted_aim,
                extracted_exp_num,
                extraction_method,
                failure_reason,
                student_submitted_title,
                student_submitted_num,
                discrepancy,
                text_snippet,
                uploaded_at,
                is_sample_preserved
            FROM extraction_diagnostics
            {where_clause}
            ORDER BY uploaded_at DESC
            LIMIT ? OFFSET ?;
        """, query_params)

        docs = [dict(r) for r in cur.fetchall()]
        return docs, total_count, summary
    finally:
        conn.close()


def get_protected_hashes_set(db_path: Optional[str] = None) -> Set[str]:
    """
    Returns the set of SHA-256 hashes for failed/discrepant uploads that should be
    protected from storage rotation so the research dataset remains intact.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT sha256 FROM extraction_diagnostics
            WHERE discrepancy = 1 OR failure_reason != 'none' OR is_sample_preserved = 1;
        """)
        return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()
