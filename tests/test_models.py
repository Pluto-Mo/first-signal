from ipo_evidence.models import Citation, Manifest, QualityStatus


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
