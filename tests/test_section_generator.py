from ipo_evidence.models import EvidenceItem, EvidencePacket, QualityStatus
from ipo_evidence.section_generator import generate_section_drafts


def test_generate_section_drafts_uses_section_evidence_refs_and_trace():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="sample.pdf",
                page_number=2,
                block_id="B-001",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            )
        ],
    )
    report_inputs = {
        "doc_id": "doc_test",
        "company_name": "测试股份有限公司",
        "section_groups": [
            {
                "section_key": "company_and_industry",
                "title": "公司介绍与行业概况",
                "prompt_slot": "narrative_section",
                "skill_refs": ["business_goal_decompose"],
                "evidence_refs": [{"evidence_id": "E-001", "rank": 1}],
                "evidence_policy": {"min_fact_count": 1, "no_evidence": "log_only"},
                "output_contract": {
                    "shape": "narrative_section",
                    "requires": ["core_claim", "evidence_chain", "reader_value"],
                },
                "section_role": "main",
            }
        ],
    }

    drafts = generate_section_drafts(packet, report_inputs)

    assert len(drafts) == 1
    assert drafts[0].section_key == "company_and_industry"
    assert drafts[0].title == "公司介绍与行业概况"
    assert drafts[0].body == "公司主要从事智能硬件产品的研发、生产和销售。[C-001]"
    assert drafts[0].citation_ids == ["C-001"]
    assert drafts[0].internal_trace.skill_refs == ["business_goal_decompose"]
    assert drafts[0].internal_trace.evidence_ids == ["E-001"]
    assert drafts[0].internal_trace.evidence_quality_statuses == [QualityStatus.safe_to_use]
    assert drafts[0].internal_trace.fact_count == 1


def test_generate_section_drafts_handles_invalid_rank_unknown_and_duplicate_refs():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="sample.pdf",
                page_number=2,
                block_id="B-001",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="business",
                claim_summary="报告期内，公司 AI 硬件产品收入占比较高。",
                source_type="text_quote",
                source_file="sample.pdf",
                page_number=3,
                block_id="B-002",
                section_path=["业务与技术"],
                quote="报告期内，公司 AI 硬件产品收入占比较高。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-003",
                canonical_section="business",
                claim_summary="公司持续加大核心技术研发投入。",
                source_type="text_quote",
                source_file="sample.pdf",
                page_number=4,
                block_id="B-003",
                section_path=["业务与技术"],
                quote="公司持续加大核心技术研发投入。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )
    report_inputs = {
        "section_groups": [
            {
                "section_key": "company_and_industry",
                "title": "公司介绍与行业概况",
                "evidence_refs": [
                    {"evidence_id": "E-001", "rank": "1"},
                    {"evidence_id": "E-002", "rank": 2},
                    {"evidence_id": "E-001", "rank": -1},
                    {"evidence_id": "E-003", "rank": True},
                    {"evidence_id": "E-999", "rank": 1},
                ],
            }
        ],
    }

    drafts = generate_section_drafts(packet, report_inputs)

    assert drafts[0].citation_ids == ["C-002", "C-001", "C-003"]
    assert drafts[0].internal_trace.citation_ids == ["C-002", "C-001", "C-003"]
    assert drafts[0].internal_trace.evidence_ids == ["E-002", "E-001", "E-003"]
    assert drafts[0].internal_trace.evidence_quality_statuses == [
        QualityStatus.safe_to_use,
        QualityStatus.safe_to_use,
        QualityStatus.safe_to_use,
    ]
    assert drafts[0].internal_trace.fact_count == 3
