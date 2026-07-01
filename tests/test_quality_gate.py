from ipo_evidence.models import InternalTrace, QualityStatus, SectionDraft
from ipo_evidence.quality_gate import apply_quality_gate


def _draft(
    section_key: str,
    fact_count: int,
    evidence_quality_statuses: list[QualityStatus] | None = None,
) -> SectionDraft:
    return SectionDraft(
        section_key=section_key,
        title=section_key,
        section_role="main",
        body="",
        citation_ids=[],
        internal_trace=InternalTrace(
            section_key=section_key,
            skill_refs=["disclosure_gap_scan"],
            prompt_slot="narrative_section",
            evidence_ids=[],
            citation_ids=[],
            fact_count=fact_count,
            evidence_quality_statuses=evidence_quality_statuses or [],
        ),
    )


def test_quality_gate_logs_empty_required_section():
    draft = _draft("platform_dependency", 0)
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


def test_quality_gate_logs_section_when_all_evidence_below_medium_strength():
    draft = _draft(
        "platform_dependency",
        2,
        [QualityStatus.do_not_use, QualityStatus.do_not_use],
    )
    policies = {
        "platform_dependency": {
            "min_fact_count": 2,
            "min_strength": "medium",
            "weak_evidence": "merge_into_related_section",
        }
    }

    decisions = apply_quality_gate([draft], policies)

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "log_only"
    assert decisions[0].reason == "有效证据数量 0 低于最低要求 2。"


def test_quality_gate_counts_only_safe_evidence_when_min_strength_is_high():
    draft = _draft(
        "platform_dependency",
        2,
        [QualityStatus.safe_to_use, QualityStatus.manual_review],
    )
    policies = {
        "platform_dependency": {
            "min_fact_count": 2,
            "min_strength": "high",
            "weak_evidence": "merge_into_related_section",
        }
    }

    decisions = apply_quality_gate([draft], policies)

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "merge"
    assert decisions[0].reason == "有效证据数量 1 低于最低要求 2。"


def test_quality_gate_defaults_missing_min_strength_to_medium():
    draft = _draft(
        "platform_dependency",
        2,
        [QualityStatus.manual_review, QualityStatus.do_not_use],
    )

    decisions = apply_quality_gate(
        [draft],
        {"platform_dependency": {"min_fact_count": 1}},
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "include"
    assert decisions[0].reason == "有效证据数量 1 达到最低要求 1。"


def test_quality_gate_defaults_invalid_min_strength_to_medium():
    draft = _draft(
        "platform_dependency",
        2,
        [QualityStatus.manual_review, QualityStatus.do_not_use],
    )

    decisions = apply_quality_gate(
        [draft],
        {"platform_dependency": {"min_fact_count": 1, "min_strength": "invalid"}},
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "include"
    assert decisions[0].reason == "有效证据数量 1 达到最低要求 1。"


def test_quality_gate_defaults_non_string_min_strength_to_medium():
    draft = _draft(
        "platform_dependency",
        2,
        [QualityStatus.manual_review, QualityStatus.do_not_use],
    )

    decisions = apply_quality_gate(
        [draft],
        {"platform_dependency": {"min_fact_count": 1, "min_strength": ["high"]}},
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "include"
    assert decisions[0].reason == "有效证据数量 1 达到最低要求 1。"


def test_quality_gate_includes_section_when_fact_count_meets_minimum():
    draft = _draft("business_model", 2)

    decisions = apply_quality_gate(
        [draft],
        {"business_model": {"min_fact_count": 2}},
    )

    assert decisions[0].section_key == "business_model"
    assert decisions[0].action == "include"
    assert decisions[0].reason == "证据数量 2 达到最低要求 2。"


def test_quality_gate_merges_weak_section_when_policy_requests_merge():
    draft = _draft("platform_dependency", 1)

    decisions = apply_quality_gate(
        [draft],
        {
            "platform_dependency": {
                "min_fact_count": 2,
                "weak_evidence": "merge_into_related_section",
            }
        },
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "merge"
    assert decisions[0].reason == "证据数量 1 低于最低要求 2。"


def test_quality_gate_logs_weak_section_when_policy_does_not_request_merge():
    draft = _draft("platform_dependency", 1)

    decisions = apply_quality_gate(
        [draft],
        {
            "platform_dependency": {
                "min_fact_count": 2,
                "weak_evidence": "log_only",
            }
        },
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "log_only"
    assert decisions[0].reason == "证据数量 1 低于最低要求 2。"


def test_quality_gate_defaults_min_fact_count_to_two():
    draft = _draft("platform_dependency", 1)

    decisions = apply_quality_gate([draft], {})

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "merge"
    assert decisions[0].reason == "证据数量 1 低于最低要求 2。"


def test_quality_gate_falls_back_to_two_for_invalid_min_fact_count():
    draft = _draft("platform_dependency", 1)

    decisions = apply_quality_gate(
        [draft],
        {"platform_dependency": {"min_fact_count": "invalid"}},
    )

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "merge"
    assert decisions[0].reason == "证据数量 1 低于最低要求 2。"
