from pathlib import Path

from ipo_evidence.io import write_json
from ipo_evidence.ingest import scan_inbox
from ipo_evidence.models import Manifest


def test_scan_inbox_creates_manifest_for_pdf(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "测试股份有限公司招股说明书.pdf").write_bytes(b"%PDF-1.4\nsample")

    created = scan_inbox(inbox, docs)

    assert len(created) == 1
    manifest_path = docs / created[0].doc_id / "manifest.json"
    assert manifest_path.exists()
    assert created[0].company_name == "测试股份有限公司"
    assert created[0].source_file == "测试股份有限公司招股说明书.pdf"


def test_scan_inbox_is_idempotent(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "测试股份有限公司招股说明书.pdf").write_bytes(b"%PDF-1.4\nsample")

    first = scan_inbox(inbox, docs)
    second = scan_inbox(inbox, docs)

    assert [doc.doc_id for doc in first] == [doc.doc_id for doc in second]


def test_scan_inbox_preserves_existing_manifest(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    source_file = "测试股份有限公司招股说明书.pdf"
    (inbox / source_file).write_bytes(b"%PDF-1.4\nsample")

    first = scan_inbox(inbox, docs)
    manifest_path = docs / first[0].doc_id / "manifest.json"
    existing_manifest = Manifest(
        doc_id=first[0].doc_id,
        company_name="人工修正公司",
        source_file=source_file,
        source_url="https://example.com/source.pdf",
        tags=["manual"],
    )
    write_json(manifest_path, existing_manifest)
    original_content = manifest_path.read_text(encoding="utf-8")

    created = scan_inbox(inbox, docs)

    assert len(created) == 1
    assert created[0].company_name == "人工修正公司"
    assert created[0].tags == ["manual"]
    assert created[0].source_url == "https://example.com/source.pdf"
    assert manifest_path.read_text(encoding="utf-8") == original_content


def test_scan_inbox_scans_uppercase_pdf(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "测试股份有限公司招股说明书.PDF").write_bytes(b"%PDF-1.4\nsample")

    created = scan_inbox(inbox, docs)

    assert len(created) == 1
    assert created[0].source_file == "测试股份有限公司招股说明书.PDF"


def test_scan_inbox_ignores_pdf_named_directory_and_non_pdf_file(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "fake.pdf").mkdir()
    (inbox / "notes.txt").write_text("not a pdf", encoding="utf-8")

    created = scan_inbox(inbox, docs)

    assert created == []
