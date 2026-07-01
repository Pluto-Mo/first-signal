from __future__ import annotations

from typing import Any, Literal

from ipo_evidence.models import QualityGateDecision, QualityStatus, SectionDraft


EvidenceStrength = Literal["low", "medium", "high"]

_QUALITY_STRENGTH: dict[QualityStatus, EvidenceStrength] = {
    QualityStatus.safe_to_use: "high",
    QualityStatus.manual_review: "medium",
    QualityStatus.do_not_use: "low",
}

_STRENGTH_RANK: dict[EvidenceStrength, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _min_fact_count(policy: dict[str, Any]) -> int:
    value = policy.get("min_fact_count", 2)
    return value if type(value) is int and value >= 0 else 2


def _action_for_weak(policy: dict[str, Any]) -> Literal["merge", "log_only"]:
    value = policy.get("weak_evidence", "merge_into_related_section")
    if value == "merge_into_related_section":
        return "merge"
    return "log_only"


def _min_strength(policy: dict[str, Any]) -> EvidenceStrength:
    value = policy.get("min_strength", "medium")
    if isinstance(value, str) and value in _STRENGTH_RANK:
        return value
    return "medium"


def _meets_min_strength(status: QualityStatus, min_strength: EvidenceStrength) -> bool:
    return _STRENGTH_RANK[_QUALITY_STRENGTH[status]] >= _STRENGTH_RANK[min_strength]


def _effective_fact_count(draft: SectionDraft, policy: dict[str, Any]) -> int:
    statuses = draft.internal_trace.evidence_quality_statuses
    if not statuses:
        return draft.internal_trace.fact_count

    min_strength = _min_strength(policy)
    return sum(1 for status in statuses if _meets_min_strength(status, min_strength))


def apply_quality_gate(
    drafts: list[SectionDraft],
    policies_by_section: dict[str, dict[str, Any]],
) -> list[QualityGateDecision]:
    decisions: list[QualityGateDecision] = []
    for draft in drafts:
        policy = policies_by_section.get(draft.section_key, {})
        min_fact_count = _min_fact_count(policy)
        effective_fact_count = _effective_fact_count(draft, policy)
        reason_prefix = (
            "有效证据数量"
            if draft.internal_trace.evidence_quality_statuses
            else "证据数量"
        )

        if effective_fact_count == 0:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action="log_only",
                    reason=f"{reason_prefix} {effective_fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的可引用证据"],
                    suggested_next_step="补充证据后重新生成该 section。",
                )
            )
            continue

        if effective_fact_count < min_fact_count:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action=_action_for_weak(policy),
                    reason=f"{reason_prefix} {effective_fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的 supporting evidence"],
                    suggested_next_step="合并到相关段落，或补足证据后独立成段。",
                )
            )
            continue

        decisions.append(
            QualityGateDecision(
                section_key=draft.section_key,
                action="include",
                reason=f"{reason_prefix} {effective_fact_count} 达到最低要求 {min_fact_count}。",
            )
        )
    return decisions
