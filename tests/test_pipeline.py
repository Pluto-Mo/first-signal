import json
from pathlib import Path

import pytest

from ipo_evidence.cli import main
from ipo_evidence.io import read_json
from ipo_evidence.models import Block
from ipo_evidence.parser.base import ParserOutput
from ipo_evidence import pipeline as pipeline_module
from ipo_evidence.pipeline import regenerate_report, run_one


@pytest.fixture(autouse=True)
def stub_parser_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pipeline_module,
        "load_yaml",
        lambda _relative_path: {"provider": "api_stub"},
    )


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
    assert (package / "report_inputs.json").exists()
    assert (package / "report.md").exists()
    assert (package / "citation.json").exists()
    assert (package / "web_index.json").exists()
    docs_index = read_json(docs / "index.json")
    assert docs_index[0]["doc_id"] == doc_id


def test_run_one_uses_parser_selected_from_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    docs = tmp_path / "docs"
    pdf = tmp_path / "002194_20260525_8AU9.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")
    captured: dict[str, object] = {}

    class FakeParser:
        def parse(self, _pdf_path: Path) -> ParserOutput:
            return ParserOutput(
                markdown="# 测试股份有限公司招股说明书\n\n## 第一节 发行人基本情况",
                blocks=[
                    Block(
                        block_id="B-000001",
                        page_number=1,
                        text="## 第一节 发行人基本情况",
                        section_path=[],
                    )
                ],
                raw_tables=[],
                parse_report={"quality_status": "safe_to_use"},
            )

    def fake_load_yaml(_relative_path: str) -> dict:
        return {"provider": "paddleocr_vl"}

    def fake_create_parser(config: dict, fixture_path: Path | None = None) -> FakeParser:
        captured["provider"] = config["provider"]
        captured["fixture_path"] = fixture_path
        return FakeParser()

    monkeypatch.setattr(pipeline_module, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(pipeline_module, "create_parser", fake_create_parser)

    doc_id = run_one(
        pdf_path=pdf,
        docs_dir=docs,
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    assert doc_id.startswith("doc_")
    assert captured["provider"] == "paddleocr_vl"
    assert (docs / doc_id / "document.md").exists()


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


def test_regenerate_report_updates_manifest_and_web_index_status(tmp_path: Path):
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
    manifest_path = package / "manifest.json"
    web_index_path = package / "web_index.json"
    manifest = read_json(manifest_path)
    manifest["report_status"] = "not_started"
    web_index = read_json(web_index_path)
    web_index["report_status"] = "not_started"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    web_index_path.write_text(json.dumps(web_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    regenerate_report(doc_id, docs)

    refreshed_manifest = read_json(manifest_path)
    refreshed_web_index = read_json(web_index_path)
    docs_index = read_json(docs / "index.json")

    assert refreshed_manifest["report_status"] == "reported"
    assert refreshed_web_index["report_status"] == "reported"
    assert docs_index[0]["report_status"] == "reported"


def test_regenerate_report_requires_manifest(tmp_path: Path):
    docs = tmp_path / "docs"
    package = docs / "demo-doc"
    package.mkdir(parents=True)
    (package / "evidence_packet.json").write_text('{"doc_id":"demo-doc","items":[]}\n', encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing required artifact"):
        regenerate_report("demo-doc", docs)


def test_regenerate_report_rejects_manifest_doc_id_mismatch(tmp_path: Path):
    docs = tmp_path / "docs"
    package = docs / "demo-doc"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        (
            '{"doc_id":"other-doc","company_name":"测试股份有限公司","source_file":"sample.pdf",'
            '"parse_status":"parsed","report_status":"not_started","quality_status":"safe_to_use"}\n'
        ),
        encoding="utf-8",
    )
    (package / "evidence_packet.json").write_text('{"doc_id":"demo-doc","items":[]}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="manifest doc_id mismatch"):
        regenerate_report("demo-doc", docs)


def test_main_generate_report_raises_for_missing_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    docs = tmp_path / "docs"
    package = docs / "demo-doc"
    package.mkdir(parents=True)
    (package / "evidence_packet.json").write_text('{"doc_id":"demo-doc","items":[]}\n', encoding="utf-8")
    monkeypatch.setattr("ipo_evidence.cli.docs_dir", lambda: docs)

    with pytest.raises(FileNotFoundError, match="missing required artifact"):
        main(["generate-report", "--doc-id", "demo-doc"])


def test_main_generate_report_raises_for_manifest_doc_id_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    docs = tmp_path / "docs"
    package = docs / "demo-doc"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        (
            '{"doc_id":"other-doc","company_name":"测试股份有限公司","source_file":"sample.pdf",'
            '"parse_status":"parsed","report_status":"not_started","quality_status":"safe_to_use"}\n'
        ),
        encoding="utf-8",
    )
    (package / "evidence_packet.json").write_text('{"doc_id":"demo-doc","items":[]}\n', encoding="utf-8")
    monkeypatch.setattr("ipo_evidence.cli.docs_dir", lambda: docs)

    with pytest.raises(ValueError, match="manifest doc_id mismatch"):
        main(["generate-report", "--doc-id", "demo-doc"])


def test_main_generate_report_runs_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    docs = tmp_path / "docs"
    expected_doc_id = "demo-doc"
    captured: dict[str, object] = {}

    monkeypatch.setattr("ipo_evidence.cli.docs_dir", lambda: docs)

    def fake_regenerate_report(doc_id: str, base_dir: Path) -> None:
        captured["doc_id"] = doc_id
        captured["docs_dir"] = base_dir

    monkeypatch.setattr("ipo_evidence.cli.regenerate_report", fake_regenerate_report)

    exit_code = main(["generate-report", "--doc-id", expected_doc_id])

    assert exit_code == 0
    assert captured == {"doc_id": expected_doc_id, "docs_dir": docs}
    assert capsys.readouterr().out == f"reported={expected_doc_id}\n"


def test_main_loads_project_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Path] = {}

    monkeypatch.setattr("ipo_evidence.cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "ipo_evidence.cli.load_dotenv",
        lambda path: captured.setdefault("path", Path(path)),
    )
    monkeypatch.setattr("ipo_evidence.cli.handle_scan_inbox", lambda _args: 0)

    exit_code = main(["scan-inbox"])

    assert exit_code == 0
    assert captured["path"] == tmp_path / ".env"


def test_run_one_keeps_manifest_not_started_when_report_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    pdf = inbox / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")
    doc_id = pipeline_module.doc_id_for_file(pdf)
    original_write_text = pipeline_module.write_text

    def flaky_write_text(path: Path, text: str) -> None:
        if path.name == "report.md":
            raise RuntimeError("report write failed")
        original_write_text(path, text)

    monkeypatch.setattr(pipeline_module, "write_text", flaky_write_text)

    with pytest.raises(RuntimeError, match="report write failed"):
        run_one(
            pdf_path=pdf,
            docs_dir=docs,
            fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
        )

    manifest = read_json(docs / doc_id / "manifest.json")

    assert manifest["report_status"] == "not_started"
    assert not (docs / doc_id / "report.md").exists()


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_main_run_rejects_non_positive_limit(limit: str):
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--limit", limit])

    assert exc_info.value.code == 2
