from pathlib import Path

from ipo_evidence.parser.api_stub import ApiStubParser


def test_api_stub_parser_creates_normalized_output(tmp_path: Path):
    source = Path("tests/fixtures/sample_prospectus.txt")
    pdf = tmp_path / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")

    output = ApiStubParser(fixture_path=source).parse(pdf)

    assert output.markdown.startswith("# 测试股份有限公司招股说明书")
    assert output.blocks[0].block_id == "B-000001"
    assert output.blocks[0].page_number == 1
    assert output.raw_tables[0]["title"] == "产品收入结构表"
    assert output.parse_report["quality_status"] == "safe_to_use"
