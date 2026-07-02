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


def _strongest_strength(statuses: list[QualityStatus]) -> EvidenceStrength | None:
    if not statuses:
        return None
    return max((_QUALITY_STRENGTH[status] for status in statuses), key=lambda strength: _STRENGTH_RANK[strength])


def _readability_reason(warnings: list[str]) -> str | None:
    if not warnings:
        return None
    labels = {
        "contains_raw_data_literal": "包含原始表格字面量",
        "paragraph_too_long": "段落过长",
        "too_many_citations": "引用过密",
        "section_too_long": "section 过长",
    }
    joined = "、".join(labels.get(warning, warning) for warning in warnings)
    return f"section draft 可读性未达标：{joined}。"


def _body_readability_warnings(body: str) -> list[str]:
    warnings: list[str] = []
    if "{'" in body or "对应数据为" in body:
        warnings.append("contains_raw_data_literal")
    paragraphs = [paragraph for paragraph in body.split("\n\n") if paragraph.strip()]
    if any(len(paragraph) > 900 for paragraph in paragraphs):
        warnings.append("paragraph_too_long")
    if body.count("[C-") > 14:
        warnings.append("too_many_citations")
    if len(body) > 6500:
        warnings.append("section_too_long")
    return warnings


def _merged_readability_warnings(draft: SectionDraft) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for warning in [
        *draft.internal_trace.readability_warnings,
        *_body_readability_warnings(draft.body),
    ]:
        if warning in seen:
            continue
        warnings.append(warning)
        seen.add(warning)
    return warnings


def _readability_next_steps(warnings: list[str]) -> list[str]:
    steps_by_warning = {
        "contains_raw_data_literal": "重写 section draft，移除原始表格字面量。",
        "too_many_citations": "压缩 section draft，减少引用密度。",
        "paragraph_too_long": "拆分或压缩过长段落。",
        "section_too_long": "压缩 section draft，保留核心证据。",
    }
    return [
        steps_by_warning.get(warning, "重写 section draft，移除不可读内容。")
        for warning in warnings
    ]


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
        min_strength = _min_strength(policy)
        readability_warnings = _merged_readability_warnings(draft)
        readability_reason = _readability_reason(readability_warnings)
        if readability_reason:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action="log_only",
                    reason=readability_reason,
                    title=draft.title,
                    evidence_count=draft.internal_trace.fact_count,
                    min_fact_count=min_fact_count,
                    strength=_strongest_strength(draft.internal_trace.evidence_quality_statuses),
                    required_strength=min_strength,
                    needed_evidence=[],
                    suggested_next_step="重写 section draft，移除不可读内容。",
                    suggested_next_steps=_readability_next_steps(readability_warnings),
                )
            )
            continue

        effective_fact_count = _effective_fact_count(draft, policy)
        strength = _strongest_strength(draft.internal_trace.evidence_quality_statuses)
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
                    title=draft.title,
                    evidence_count=effective_fact_count,
                    min_fact_count=min_fact_count,
                    strength=strength,
                    required_strength=min_strength,
                    needed_evidence=[f"补充 {draft.section_key} 的可引用证据"],
                    suggested_next_step="补充证据后重新生成该 section。",
                    suggested_next_steps=["补充证据后重新生成该 section。"],
                )
            )
            continue

        if effective_fact_count < min_fact_count:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action=_action_for_weak(policy),
                    reason=f"{reason_prefix} {effective_fact_count} 低于最低要求 {min_fact_count}。",
                    title=draft.title,
                    evidence_count=effective_fact_count,
                    min_fact_count=min_fact_count,
                    strength=strength,
                    required_strength=min_strength,
                    needed_evidence=[f"补充 {draft.section_key} 的 supporting evidence"],
                    suggested_next_step="合并到相关段落，或补足证据后独立成段。",
                    suggested_next_steps=["合并到相关段落，或补足证据后独立成段。"],
                )
            )
            continue

        decisions.append(
            QualityGateDecision(
                section_key=draft.section_key,
                action="include",
                reason=f"{reason_prefix} {effective_fact_count} 达到最低要求 {min_fact_count}。",
                title=draft.title,
                evidence_count=effective_fact_count,
                min_fact_count=min_fact_count,
                strength=strength,
                required_strength=min_strength,
            )
        )
    return decisions
