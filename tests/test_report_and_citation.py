from ipo_evidence.citation_layer import build_citations
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block, EvidenceItem, EvidencePacket, QualityStatus, TableObject
from ipo_evidence.report_generator import _items_for_input_group, generate_report


def test_report_contains_citation_markers_and_citation_json():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司主要从事智能硬件产品的研发、生产和销售。",
                section_path=["发行人基本情况"],
            )
        ],
        tables=[],
    )

    draft = generate_report("测试股份有限公司", packet)
    citations = build_citations(packet)

    assert "[C-001]" in draft
    assert citations[0].citation_id == "C-001"
    assert citations[0].block_id == "B-000002"


def test_table_citations_include_table_title_for_validation():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[
            TableObject(
                table_id="T-001",
                title="产品收入结构表",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                section_path=["业务和技术"],
                columns=["产品", "2023年收入", "占比"],
                rows=[["智能控制器", "12000万元", "45.2%"]],
                quality_score=0.9,
            )
        ],
    )

    citations = build_citations(packet)

    assert citations[0].citation_id == "C-001"
    assert citations[0].table_id == "T-001"
    assert citations[0].table_title == "产品收入结构表"
    assert citations[0].fields == {
        "产品": "智能控制器",
        "2023年收入": "12000万元",
        "占比": "45.2%",
    }


def test_table_citation_uses_table_locator_without_block_id():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[
            TableObject(
                table_id="T-001",
                title="产品收入结构表",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                section_path=[],
                columns=["产品", "2023年收入"],
                rows=[["智能控制器", "12000万元"]],
                quality_score=0.9,
            )
        ],
    )

    citations = build_citations(packet)

    assert citations[0].block_id is None
    assert citations[0].table_id == "T-001"
    assert citations[0].table_title == "产品收入结构表"
    assert citations[0].fields == {"产品": "智能控制器", "2023年收入": "12000万元"}
    assert citations[0].section_path == ["未识别章节"]


def test_mixed_text_and_table_report_citations_keep_matching_order():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司主要从事智能硬件产品的研发、生产和销售。",
                section_path=["发行人基本情况"],
            )
        ],
        tables=[
            TableObject(
                table_id="T-001",
                title="产品收入结构表",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                section_path=["业务和技术"],
                columns=["产品", "2023年收入"],
                rows=[["智能控制器", "12000万元"]],
                quality_score=0.9,
            )
        ],
    )

    draft = generate_report("测试股份有限公司", packet)
    citations = build_citations(packet)

    assert "[C-001]" in draft
    assert "[C-002]" in draft
    assert "[C-003]" in draft
    assert citations[0].citation_id == "C-001"
    assert citations[0].block_id == "B-000002"
    assert citations[1].citation_id == "C-002"
    assert citations[1].block_id == "B-000002"
    assert citations[2].citation_id == "C-003"
    assert citations[2].table_id == "T-001"


def test_generate_report_creates_basic_long_form_report_from_evidence_packet():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=2,
                block_id="B-000002",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="business_and_product",
                claim_summary="公司的主要产品包括智能控制器和消费级智能终端。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-000003",
                section_path=["业务和技术"],
                quote="公司的主要产品包括智能控制器和消费级智能终端。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-003",
                canonical_section="financials",
                claim_summary="报告期内公司营业收入持续增长。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                block_id="B-000004",
                section_path=["财务会计信息"],
                quote="报告期内公司营业收入持续增长。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-004",
                canonical_section="use_of_proceeds",
                claim_summary="募集资金拟用于智能制造基地建设项目。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=5,
                block_id="B-000005",
                section_path=["募集资金运用"],
                quote="募集资金拟用于智能制造基地建设项目。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-005",
                canonical_section="risks",
                claim_summary="公司存在客户集中度较高的风险。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=6,
                block_id="B-000006",
                section_path=["风险因素"],
                quote="公司存在客户集中度较高的风险。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )

    draft = generate_report("测试股份有限公司", packet)

    assert "招股书长篇阅读" in draft
    assert "公司介绍与行业概况" in draft
    assert "个人投资视角" in draft
    assert "认知世界的方式" in draft
    assert "[C-001]" in draft
    assert "[C-005]" in draft
    assert len(draft.splitlines()) >= 45


def test_generate_report_uses_report_inputs_section_groups():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="business_and_product",
                claim_summary="产品收入结构表显示智能控制器收入占比最高。",
                source_type="table_fact",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                table_id="T-001",
                table_title="产品收入结构表",
                section_path=["业务和技术"],
                fields={"产品": "智能控制器", "占比": "45.2%"},
                quality_status=QualityStatus.safe_to_use,
            )
        ],
    )
    report_inputs = {
        "doc_id": "doc_test",
        "company_name": "测试股份有限公司",
        "outline": ["personal_investment"],
        "section_groups": [
            {
                "section_key": "personal_investment",
                "title": "个人投资视角",
                "focus_points": ["产品可信度", "收入集中度"],
                "output_order": 2,
                "evidence_refs": [{"evidence_id": "E-001", "rank": 1}],
            }
        ],
    }

    draft = generate_report("测试股份有限公司", packet, report_inputs)

    assert "个人投资视角" in draft
    assert "产品收入结构表显示：产品：智能控制器；占比：45.2%" in draft
    assert "[C-001]" in draft


def test_generate_report_handles_invalid_rank_unknown_and_duplicate_input_refs():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=2,
                block_id="B-000002",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="financials",
                claim_summary="报告期内公司营业收入持续增长。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-000003",
                section_path=["财务会计信息"],
                quote="报告期内公司营业收入持续增长。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )
    report_inputs = {
        "doc_id": "doc_test",
        "company_name": "测试股份有限公司",
        "section_groups": [
            {
                "section_key": "company_and_industry",
                "title": "公司介绍与行业概况",
                "evidence_refs": [
                    {"evidence_id": "E-001", "rank": "1"},
                    {"evidence_id": "E-002", "rank": 2},
                    {"evidence_id": "E-001", "rank": -1},
                    {"evidence_id": "E-999", "rank": 1},
                ],
            }
        ],
    }

    draft = generate_report("测试股份有限公司", packet, report_inputs)
    input_items = _items_for_input_group(
        report_inputs["section_groups"][0],
        {item.evidence_id: (index, item) for index, item in enumerate(packet.items, start=1)},
    )

    assert "[C-001]" in draft
    assert "[C-002]" in draft
    assert [item.evidence_id for _, item in input_items] == ["E-002", "E-001"]


def test_generate_report_avoids_internal_system_wording():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=2,
                block_id="B-000002",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="business_and_product",
                claim_summary="公司的主要产品包括智能控制器和消费级智能终端。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-000003",
                section_path=["业务和技术"],
                quote="公司的主要产品包括智能控制器和消费级智能终端。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )

    draft = generate_report("测试股份有限公司", packet)

    assert "公司介绍与行业概况" in draft
    assert "个人投资视角" in draft
    assert "认知世界的方式" in draft
    banned_phrases = [
        "当前报告",
        "系统链路",
        "input 层",
        "report 层",
        "生成器",
        "技术测试",
        "评估器",
        "证据清单",
    ]
    assert all(phrase not in draft for phrase in banned_phrases)
