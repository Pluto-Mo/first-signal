from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ipo_evidence.io import write_json
from ipo_evidence.models import Manifest


def doc_id_for_file(path: Path) -> str:
    digest = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


def company_name_from_filename(path: Path) -> str:
    stem = path.stem
    match = re.search(r"(.+?)(?:招股说明书|首次公开发行|招股书)", stem)
    if match:
        return match.group(1).strip(" _-")
    return "unknown_company"


def scan_inbox(inbox: Path, docs: Path) -> list[Manifest]:
    manifests: list[Manifest] = []
    docs.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(inbox.glob("*.pdf")):
        manifest = Manifest(
            doc_id=doc_id_for_file(pdf_path),
            company_name=company_name_from_filename(pdf_path),
            source_file=pdf_path.name,
        )
        package_dir = docs / manifest.doc_id
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = package_dir / "manifest.json"
        if not manifest_path.exists():
            write_json(manifest_path, manifest)
        manifests.append(manifest)

    return manifests
