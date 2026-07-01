from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block
from ipo_evidence.report_inputs import build_report_inputs


EXPECTED_OUTLINE = [
    "signal_and_question",
    "business_capability_chain",
    "disclosure_gap_and_risk",
    "reader_action_map",
]


def test_build_report_inputs_groups_evidence_by_reading_view():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司主要从事智能硬件产品的研发、生产和销售。",
                section_path=["发行人基本情况"],
            ),
            Block(
                block_id="B-000003",
                page_number=3,
                text="报告期内，公司经销模式销售的主要产品为智能硬件产品。",
                section_path=["业务与技术", "主要产品或服务情况"],
            ),
        ],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    assert report_inputs["doc_id"] == "doc_test"
    assert report_inputs["company_name"] == "测试股份有限公司"
    assert report_inputs["outline"] == EXPECTED_OUTLINE
    assert report_inputs["section_groups"][0]["section_key"] == "signal_and_question"


def test_build_report_inputs_keeps_dispatch_view_lightweight():
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

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    section = report_inputs["section_groups"][0]
    assert section["title"] == "现象入口与核心问题"
    assert section["prompt_slot"] == "signal_and_question"
    assert section["focus_points"] != []
    assert section["constraints"] != []
    assert section["output_order"] == 1
    assert "quote" not in str(section)
    assert "claim_summary" not in str(section)


def test_build_report_inputs_uses_evidence_refs_not_evidence_copies():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司主要从事智能硬件产品的研发、生产和销售。",
                section_path=["发行人基本情况"],
            ),
            Block(
                block_id="B-000003",
                page_number=3,
                text="报告期内，公司经销模式销售的主要产品为智能硬件产品。",
                section_path=["业务与技术", "主要产品或服务情况"],
            ),
        ],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    first_ref = report_inputs["section_groups"][0]["evidence_refs"][0]
    assert first_ref == {
        "evidence_id": "E-001",
        "role": "primary",
        "rank": 1,
        "label": "发行人基本情况",
    }
    assert "evidence_ids" not in report_inputs["section_groups"][0]
