from pathlib import Path

from ipo_evidence.io import read_json
from ipo_evidence.pipeline import regenerate_report, run_one


def test_run_one_creates_document_package(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    pdf = inbox / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")

    doc_id = run_one(
        pdf_path=pdf,
        docs_dir=docs,
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    package = docs / doc_id
    assert (package / "manifest.json").exists()
    assert (package / "document.md").exists()
    assert (package / "blocks.jsonl").exists()
    assert (package / "source_ast.json").exists()
    assert (package / "canonical_ast.json").exists()
    assert (package / "tables" / "T-001.json").exists()
    assert (package / "evidence_packet.json").exists()
    assert (package / "report.md").exists()
    assert (package / "citation.json").exists()
    assert (package / "web_index.json").exists()


def test_regenerate_report_rewrites_report_and_citations(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    pdf = inbox / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")

    doc_id = run_one(
        pdf_path=pdf,
        docs_dir=docs,
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    package = docs / doc_id
    report_path = package / "report.md"
    citation_path = package / "citation.json"
    report_path.write_text("broken report", encoding="utf-8")
    citation_path.write_text("[]\n", encoding="utf-8")

    regenerate_report(doc_id, docs)

    report_text = report_path.read_text(encoding="utf-8")
    citations = read_json(citation_path)
    web_index = read_json(package / "web_index.json")

    assert "broken report" not in report_text
    assert "# 测试股份有限公司招股书解读" in report_text
    assert citations[0]["citation_id"] == "C-001"
    assert web_index["doc_id"] == doc_id
    assert web_index["company_name"] == "测试股份有限公司"
