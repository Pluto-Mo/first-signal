from __future__ import annotations

import hashlib
from pathlib import Path

import requests

from ipo_evidence.io import ensure_dir
from ipo_evidence.source_sync.models import DownloadRecord, SyncCandidate


def build_inbox_filename(candidate: SyncCandidate) -> str:
    return f"{candidate.published_at}__{candidate.company_name}__{candidate.announcement_id}.pdf"


def write_pdf_bytes(inbox_dir: Path | str, filename: str, content: bytes) -> tuple[Path, str]:
    inbox_path = ensure_dir(Path(inbox_dir))
    pdf_path = inbox_path / filename
    pdf_path.write_bytes(content)
    return pdf_path, hashlib.sha256(content).hexdigest()


class SyncDownloader:
    def __init__(self, inbox_dir: Path | str):
        self.inbox_dir = Path(inbox_dir)

    def download_candidate(
        self,
        candidate: SyncCandidate,
        content: bytes | None = None,
    ) -> dict:
        pdf_bytes = content
        if pdf_bytes is None:
            response = requests.get(candidate.pdf_url, timeout=60)
            response.raise_for_status()
            pdf_bytes = response.content
        filename = build_inbox_filename(candidate)
        pdf_path, sha256 = write_pdf_bytes(self.inbox_dir, filename, pdf_bytes)
        record = DownloadRecord(
            sync_id=candidate.sync_id,
            market=candidate.market,
            exchange=candidate.exchange,
            company_name=candidate.company_name,
            announcement_id=candidate.announcement_id,
            announcement_title=candidate.announcement_title,
            published_at=candidate.published_at,
            source_url=candidate.source_url,
            local_pdf_path=str(pdf_path),
            file_sha256=sha256,
            disclosure_stage=candidate.disclosure_stage,
            download_status="downloaded",
            ocr_status="ocr_not_started",
        )
        return record.model_dump(mode="json")
