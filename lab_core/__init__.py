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

__all__ = [
    "parse_color",
    "split_and_scale_title",
    "create_filled_header_doc",
    "render_header_preview_png",
    "generate_job_documents",
    "generate_toc_page",
    "inspect_pdf_info",
    "extract_aim_from_pdf",
]
