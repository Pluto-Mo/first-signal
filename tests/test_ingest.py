from pathlib import Path

from ipo_evidence.ingest import scan_inbox


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
