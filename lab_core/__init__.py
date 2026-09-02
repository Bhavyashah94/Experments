"""
Lab Header Studio - Core Processing Engine
"""

from .pdf_engine import (
    parse_color,
    split_and_scale_title,
    create_filled_header_doc,
    render_header_preview_png,
    generate_job_documents,
)

from .extractor import (
    inspect_pdf_info,
    extract_aim_from_pdf,
)

from .toc_engine import (
    generate_toc_page,
)

from .analytics import (
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

__all__ = [
    "parse_color",
    "split_and_scale_title",
    "create_filled_header_doc",
    "render_header_preview_png",
    "generate_job_documents",
    "generate_toc_page",
    "inspect_pdf_info",
    "extract_aim_from_pdf",
    "init_analytics_db",
    "record_generation_event",
    "get_analytics_summary",
    "get_generation_events",
    "export_analytics_csv",
    "export_analytics_json",
    "is_analytics_enabled",
    "is_auth_required",
    "verify_admin_password",
    "record_upload_diagnostic",
    "record_student_ground_truth",
    "get_extraction_diagnostics_summary",
    "get_failed_or_discrepant_samples",
    "get_protected_hashes_set",
]
