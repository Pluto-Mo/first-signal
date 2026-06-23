from __future__ import annotations

from ipo_evidence.models import Manifest, WebIndex


def build_web_index(manifest: Manifest) -> WebIndex:
    return WebIndex(
        doc_id=manifest.doc_id,
        company_name=manifest.company_name,
        source_file=manifest.source_file,
        quality_status=manifest.quality_status,
        parse_status=manifest.parse_status,
        report_status=manifest.report_status,
        tags=manifest.tags,
    )
