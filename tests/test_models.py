import pytest
from pydantic import ValidationError

from ipo_evidence.models import Citation, Manifest, QualityStatus
from ipo_evidence.paths import doc_dir


def test_manifest_defaults_to_local_pdf_input():
    manifest = Manifest(
        doc_id="doc_abc123",
        company_name="测试股份有限公司",
        source_file="测试股份有限公司招股说明书.pdf",
    )

    assert manifest.input_type == "local_pdf"
    assert manifest.market == "a_share"
    assert manifest.quality_status == QualityStatus.manual_review


def test_citation_requires_local_locator_when_url_is_missing():
    citation = Citation(
        citation_id="C-001",
        type="text_quote",
        source_file="测试股份有限公司招股说明书.pdf",
        source_url=None,
        page_number=18,
        block_id="B-000018",
        section_path=["发行人基本情况", "主营业务"],
        quote="公司主要从事智能硬件产品的研发、生产和销售。",
        summary="公司主营业务为智能硬件。",
    )

    assert citation.source_url is None
    assert citation.page_number == 18
    assert citation.block_id == "B-000018"


def test_text_quote_citation_requires_block_id():
    with pytest.raises(ValidationError):
        Citation(
            citation_id="C-002",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=18,
            section_path=["发行人基本情况", "主营业务"],
            quote="公司主要从事智能硬件产品的研发、生产和销售。",
            summary="公司主营业务为智能硬件。",
        )


def test_text_quote_citation_requires_quote():
    with pytest.raises(ValidationError):
        Citation(
            citation_id="C-003",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=18,
            block_id="B-000018",
            section_path=["发行人基本情况", "主营业务"],
            summary="公司主营业务为智能硬件。",
        )


def test_table_fact_citation_requires_table_fields():
    with pytest.raises(ValidationError):
        Citation(
            citation_id="C-004",
            type="table_fact",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=42,
            section_path=["财务会计信息", "主要财务指标"],
            summary="报告期内营业收入持续增长。",
        )


def test_table_fact_citation_with_table_fields_passes():
    citation = Citation(
        citation_id="C-005",
        type="table_fact",
        source_file="测试股份有限公司招股说明书.pdf",
        page_number=42,
        table_id="T-001",
        table_title="主要财务指标",
        section_path=["财务会计信息", "主要财务指标"],
        fields={"营业收入": "1000万元"},
        summary="报告期内营业收入持续增长。",
    )

    assert citation.table_id == "T-001"
    assert citation.fields == {"营业收入": "1000万元"}


def test_citation_requires_non_empty_section_path():
    with pytest.raises(ValidationError):
        Citation(
            citation_id="C-006",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=18,
            block_id="B-000018",
            section_path=[],
            quote="公司主要从事智能硬件产品的研发、生产和销售。",
            summary="公司主营业务为智能硬件。",
        )


def test_doc_dir_rejects_path_traversal():
    with pytest.raises(ValueError):
        doc_dir("../tmp")


def test_doc_dir_rejects_doc_id_containing_dot_dot():
    with pytest.raises(ValueError):
        doc_dir("doc..tmp")
