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
from typing import Dict, Any, List, Optional, Tuple

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


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a connection to SQLite database and ensures schema and indexes exist."""
    path = db_path or get_db_path()
    db_dir = os.path.dirname(path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_analytics_db(db_path: Optional[str] = None) -> None:
    """Initializes the generation_events table and required performance indexes."""
    conn = get_db_connection(db_path)
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

            # High-performance indexes for dashboard filtering and aggregation
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_timestamp ON generation_events(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_roll_no ON generation_events(roll_no);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_subject ON generation_events(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_student ON generation_events(student_name, roll_no);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_success ON generation_events(success);")
    finally:
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
                COUNT(DISTINCT CASE WHEN roll_no IS NOT NULL AND roll_no != '' THEN roll_no ELSE student_name END) as unique_students
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
            ev["id"],
            ev["timestamp"],
            ev["student_name"],
            ev["roll_no"],
            ev["batch"],
            ev["class_name"],
            ev["sem"],
            ev["subject"],
            ev["experiment_count"],
            ev["generation_type"],
            "SUCCESS" if ev["success"] else "FAILED",
            ev["duration_ms"],
            ev["error_message"] or "",
            " | ".join(exp_summary_list),
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
