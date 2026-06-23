from ipo_evidence.citation_layer import build_citations
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block, TableObject
from ipo_evidence.report_generator import generate_report


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
    assert citations[0].citation_id == "C-001"
    assert citations[0].block_id == "B-000002"
    assert citations[1].citation_id == "C-002"
    assert citations[1].table_id == "T-001"
