from __future__ import annotations

from typing import Any, Literal

from ipo_evidence.models import QualityGateDecision, SectionDraft


def _min_fact_count(policy: dict[str, Any]) -> int:
    value = policy.get("min_fact_count", 2)
    return value if type(value) is int and value >= 0 else 2


def _action_for_weak(policy: dict[str, Any]) -> Literal["merge", "log_only"]:
    value = policy.get("weak_evidence", "merge_into_related_section")
    if value == "merge_into_related_section":
        return "merge"
    return "log_only"


def apply_quality_gate(
    drafts: list[SectionDraft],
    policies_by_section: dict[str, dict[str, Any]],
) -> list[QualityGateDecision]:
    decisions: list[QualityGateDecision] = []
    for draft in drafts:
        policy = policies_by_section.get(draft.section_key, {})
        min_fact_count = _min_fact_count(policy)
        fact_count = draft.internal_trace.fact_count

        if fact_count == 0:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action="log_only",
                    reason=f"证据数量 {fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的可引用证据"],
                    suggested_next_step="补充证据后重新生成该 section。",
                )
            )
            continue

        if fact_count < min_fact_count:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action=_action_for_weak(policy),
                    reason=f"证据数量 {fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的 supporting evidence"],
                    suggested_next_step="合并到相关段落，或补足证据后独立成段。",
                )
            )
            continue

        decisions.append(
            QualityGateDecision(
                section_key=draft.section_key,
                action="include",
                reason=f"证据数量 {fact_count} 达到最低要求 {min_fact_count}。",
            )
        )
    return decisions
