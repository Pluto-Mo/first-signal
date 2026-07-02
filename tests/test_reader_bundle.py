from ipo_evidence.models import Citation, EvidenceItem, EvidencePacket, Manifest, QualityStatus
from ipo_evidence.reader_bundle import build_reader_bundle


def test_build_reader_bundle_maps_report_and_citations():
    manifest = Manifest(
        doc_id="doc_test",
        company_name="测试股份有限公司",
        source_file="测试股份有限公司招股说明书.pdf",
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )
    report = (
        "# 测试股份有限公司招股书长篇阅读\n\n"
        "导语判断，适合作为总览入口。[C-001]\n\n"
        "## 一、业务概况\n\n"
        "公司主营业务集中在智能控制器。[C-002][C-003]\n\n"
        "第二段补充说明。\n"
    )
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="导语判断，适合作为总览入口。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=2,
                block_id="B-000001",
                section_path=["发行人基本情况"],
                quote="导语判断，适合作为总览入口。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="business_and_product",
                claim_summary="公司主营业务集中在智能控制器。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-000002",
                section_path=["业务和技术", "主营业务"],
                quote="公司主营业务集中在智能控制器。",
                quality_status=QualityStatus.manual_review,
            ),
            EvidenceItem(
                evidence_id="E-003",
                canonical_section="business_and_product",
                claim_summary="产品收入结构表显示智能控制器收入占比 45.2%。",
                source_type="table_fact",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                table_id="T-001",
                table_title="产品收入结构表",
                section_path=["业务和技术", "收入结构"],
                fields={"产品": "智能控制器", "占比": "45.2%"},
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )
    citations = [
        Citation(
            citation_id="C-001",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=2,
            block_id="B-000001",
            section_path=["发行人基本情况"],
            quote="导语判断，适合作为总览入口。",
            summary="导语判断，适合作为总览入口。",
        ),
        Citation(
            citation_id="C-002",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=3,
            block_id="B-000002",
            section_path=["业务和技术", "主营业务"],
            quote="公司主营业务集中在智能控制器。",
            summary="公司主营业务集中在智能控制器。",
        ),
        Citation(
            citation_id="C-003",
            type="table_fact",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=4,
            table_id="T-001",
            table_title="产品收入结构表",
            section_path=["业务和技术", "收入结构"],
            fields={"产品": "智能控制器", "占比": "45.2%"},
            summary="产品收入结构表显示智能控制器收入占比 45.2%。",
        ),
    ]

    bundle = build_reader_bundle(manifest, report, citations, packet)

    assert bundle.report_title == "测试股份有限公司招股书长篇阅读"
    assert bundle.sections[0].title == "总览"
    assert bundle.sections[0].blocks[0].body == "导语判断，适合作为总览入口。"
    assert bundle.sections[1].title == "一、业务概况"
    assert bundle.sections[1].blocks[0].citation_ids == ["C-002", "C-003"]
    assert bundle.citations[1].quality == "manual_review"
    assert bundle.citations[2].location.table_id == "T-001"
    assert bundle.citations[2].location.field_value == "产品：智能控制器；占比：45.2%"


def test_build_reader_bundle_maps_tertiary_headings_to_block_titles():
    manifest = Manifest(
        doc_id="doc_test",
        company_name="测试股份有限公司",
        source_file="测试股份有限公司招股说明书.pdf",
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )
    report = (
        "# 测试股份有限公司招股书长篇阅读\n\n"
        "## 这份招股书能告诉你什么\n\n"
        "### 如果你是该行业的从业者\n\n"
        "从业者应该关注标准化产品机会。[C-001]\n\n"
        "### 如果你是消费者\n\n"
        "消费者应该关注真实体验。[C-001]\n"
    )
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="business_and_product",
                claim_summary="公司产品已进入真实场景。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-000001",
                section_path=["业务和技术"],
                quote="公司产品已进入真实场景。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )
    citations = [
        Citation(
            citation_id="C-001",
            type="text_quote",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=3,
            block_id="B-000001",
            section_path=["业务和技术"],
            quote="公司产品已进入真实场景。",
            summary="公司产品已进入真实场景。",
        )
    ]

    bundle = build_reader_bundle(manifest, report, citations, packet)

    section = bundle.sections[0]
    assert section.title == "这份招股书能告诉你什么"
    assert section.blocks[0].title == "如果你是该行业的从业者"
    assert section.blocks[0].body == "从业者应该关注标准化产品机会。"
    assert section.blocks[1].title == "如果你是消费者"
    assert section.blocks[1].body == "消费者应该关注真实体验。"
    assert all("###" not in block.body for block in section.blocks)
