from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block
from ipo_evidence.report_inputs import build_report_inputs


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
                text="报告期内，公司经销模式销售的主要产品为 AI 芯片及智慧办公领域的 AI 硬件产品。",
                section_path=["业务与技术", "主要产品或服务情况"],
            ),
        ],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    assert report_inputs["doc_id"] == "doc_test"
    assert report_inputs["company_name"] == "测试股份有限公司"
    assert report_inputs["outline"] == [
        "company_and_industry",
        "personal_investment",
        "cognitive_worldview",
    ]
    assert report_inputs["section_groups"][0]["section_key"] == "company_and_industry"


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
    assert section["title"] == "公司介绍与行业概况"
    assert section["prompt_slot"] == "company_and_industry"
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
                text="报告期内，公司经销模式销售的主要产品为 AI 芯片及智慧办公领域的 AI 硬件产品。",
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


def test_build_report_inputs_adds_architecture_dispatch_contract():
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

    assert section["skill_refs"] == [
        "business_goal_decompose",
        "capability_match",
        "reader_value_translate",
    ]
    assert section["evidence_policy"] == {
        "min_fact_count": 2,
        "min_strength": "medium",
        "weak_evidence": "merge_into_related_section",
        "no_evidence": "log_only",
    }
    assert section["output_contract"] == {
        "shape": "narrative_section",
        "requires": ["core_claim", "evidence_chain", "reader_value"],
    }
    assert section["section_role"] == "main"


def test_build_report_inputs_defensively_handles_dispatch_contract(monkeypatch):
    templates = {
        "fallback_view": {
            "title": "Fallback View",
            "prompt_slot": "fallback_view",
            "focus_points": [],
            "constraints": [],
            "output_order": 1,
            "token_budget": 100,
            "skill_refs": ["reader_value_translate", "", 123],
            "evidence_policy": "invalid",
            "output_contract": None,
            "section_role": 123,
            "source_sections": [],
        },
        "configured_view": {
            "title": "Configured View",
            "prompt_slot": "configured_view",
            "focus_points": [],
            "constraints": [],
            "output_order": 2,
            "token_budget": 100,
            "skill_refs": "invalid",
            "evidence_policy": {"min_fact_count": 1},
            "output_contract": {
                "shape": "custom_section",
                "requires": ["custom_claim"],
            },
            "section_role": "supporting",
            "source_sections": [],
        },
        "missing_view": {
            "title": "Missing View",
            "prompt_slot": "missing_view",
            "focus_points": [],
            "constraints": [],
            "output_order": 3,
            "token_budget": 100,
            "source_sections": [],
        },
    }
    monkeypatch.setattr(
        "ipo_evidence.report_inputs._input_view_templates", lambda: templates
    )
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)
    fallback_section = report_inputs["section_groups"][0]
    configured_section = report_inputs["section_groups"][1]
    missing_section = report_inputs["section_groups"][2]

    assert fallback_section["skill_refs"] == ["reader_value_translate"]
    assert fallback_section["evidence_policy"] == {
        "min_fact_count": 2,
        "min_strength": "medium",
        "weak_evidence": "merge_into_related_section",
        "no_evidence": "log_only",
    }
    assert fallback_section["output_contract"] == {
        "shape": "narrative_section",
        "requires": ["core_claim", "evidence_chain", "reader_value"],
    }
    assert configured_section["skill_refs"] == []
    assert configured_section["evidence_policy"] == {"min_fact_count": 1}
    assert configured_section["output_contract"] == {
        "shape": "custom_section",
        "requires": ["custom_claim"],
    }
    assert missing_section["skill_refs"] == []
    assert missing_section["evidence_policy"] == {
        "min_fact_count": 2,
        "min_strength": "medium",
        "weak_evidence": "merge_into_related_section",
        "no_evidence": "log_only",
    }
    assert missing_section["output_contract"] == {
        "shape": "narrative_section",
        "requires": ["core_claim", "evidence_chain", "reader_value"],
    }
    assert missing_section["section_role"] == "main"

    fallback_section["output_contract"]["requires"].append("mutated_fallback")
    configured_section["output_contract"]["requires"].append("mutated_config")

    next_report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    assert next_report_inputs["section_groups"][0]["output_contract"] == {
        "shape": "narrative_section",
        "requires": ["core_claim", "evidence_chain", "reader_value"],
    }
    assert next_report_inputs["section_groups"][1]["output_contract"] == {
        "shape": "custom_section",
        "requires": ["custom_claim"],
    }
    assert fallback_section["section_role"] == "main"
    assert configured_section["section_role"] == "supporting"
