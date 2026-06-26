from pathlib import Path

from ipo_evidence.source_sync.downloader import SyncDownloader, build_inbox_filename, write_pdf_bytes
from ipo_evidence.source_sync.models import SyncCandidate


def make_candidate() -> SyncCandidate:
    return SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="华电新能",
        security_code="600000",
        announcement_id="1224131325",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
        published_at="2025-07-11",
        source_url="https://example.com/detail",
        pdf_url="https://example.com/file.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
    )


def test_build_inbox_filename_is_stable():
    filename = build_inbox_filename(make_candidate())

    assert filename == "2025-07-11__华电新能__1224131325.pdf"


def test_write_pdf_bytes_persists_file_and_hash(tmp_path: Path):
    pdf_path, sha256 = write_pdf_bytes(
        tmp_path,
        "2025-07-11__华电新能__1224131325.pdf",
        b"%PDF-1.4\nsample",
    )

    assert pdf_path.exists()
    assert pdf_path.name.endswith(".pdf")
    assert len(sha256) == 64


def test_sync_downloader_returns_handoff_record(tmp_path: Path):
    downloader = SyncDownloader(tmp_path)

    record = downloader.download_candidate(
        make_candidate(),
        content=b"%PDF-1.4\nsample",
    )

    assert record["market"] == "a_share"
    assert record["exchange"] == "sse"
    assert record["ocr_status"] == "ocr_not_started"
    assert Path(record["local_pdf_path"]).exists()
