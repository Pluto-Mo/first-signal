from ipo_evidence.models import InternalTrace, SectionDraft
from ipo_evidence.quality_gate import apply_quality_gate


def test_quality_gate_logs_empty_required_section():
    draft = SectionDraft(
        section_key="platform_dependency",
        title="平台依赖",
        section_role="main",
        body="",
        citation_ids=[],
        internal_trace=InternalTrace(
            section_key="platform_dependency",
            skill_refs=["disclosure_gap_scan"],
            prompt_slot="narrative_section",
            evidence_ids=[],
            citation_ids=[],
            fact_count=0,
        ),
    )
    policies = {
        "platform_dependency": {
            "min_fact_count": 2,
            "weak_evidence": "merge_into_related_section",
            "no_evidence": "log_only",
        }
    }

    decisions = apply_quality_gate([draft], policies)

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "log_only"
    assert decisions[0].reason == "证据数量 0 低于最低要求 2。"
