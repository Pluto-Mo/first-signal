from __future__ import annotations

from pathlib import Path

from ipo_evidence.io import read_json, write_json
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


def refresh_docs_index(docs_root: Path) -> list[dict]:
    items: list[dict] = []
    for web_index_path in sorted(docs_root.glob("*/web_index.json")):
        payload = read_json(web_index_path)
        if isinstance(payload, dict):
            doc_id = payload.get("doc_id")
            if isinstance(doc_id, str) and doc_id:
                for path_key in ("report_path", "citation_path", "reader_bundle_path"):
                    path_value = payload.get(path_key)
                    if isinstance(path_value, str) and path_value and "/" not in path_value:
                        payload[path_key] = f"{doc_id}/{path_value}"
            items.append(payload)
    write_json(docs_root / "index.json", items)
    return items
