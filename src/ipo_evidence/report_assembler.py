from __future__ import annotations

import re

from ipo_evidence.models import QualityGateDecision, SectionDraft


CITATION_RE = re.compile(r"\[(C-\d{3})\]")


def _report_title(company_name: str) -> str:
    return f"# {company_name}招股书长篇阅读"


def _decision_map(decisions: list[QualityGateDecision]) -> dict[str, QualityGateDecision]:
    return {decision.section_key: decision for decision in decisions}


def _included_drafts(
    drafts: list[SectionDraft],
    decisions: list[QualityGateDecision],
) -> list[SectionDraft]:
    decisions_by_section = _decision_map(decisions)
    included: list[SectionDraft] = []
    for draft in drafts:
        decision = decisions_by_section.get(draft.section_key)
        if not decision or decision.action != "include":
            continue
        if not draft.body.strip():
            continue
        included.append(draft)
    return included


def _citation_ids(text: str) -> set[str]:
    return set(CITATION_RE.findall(text))


def _validate_citations(drafts: list[SectionDraft], valid_citation_ids: set[str] | None) -> None:
    if valid_citation_ids is None:
        return
    for draft in drafts:
        unknown_ids = sorted(_citation_ids(draft.body) - valid_citation_ids)
        if unknown_ids:
            joined = ", ".join(unknown_ids)
            raise ValueError(f"unknown citation id in section {draft.section_key}: {joined}")


def _fallback_report(company_name: str) -> str:
    return (
        f"{_report_title(company_name)}\n\n"
        "本次材料未形成满足证据阈值的正式解读正文。"
        "系统已保留处理记录，用于后续补充证据和优化生成策略。\n"
    )


def _clean_markdown(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text + "\n"


def assemble_report(
    company_name: str,
    drafts: list[SectionDraft],
    decisions: list[QualityGateDecision],
    *,
    valid_citation_ids: set[str] | None = None,
) -> str:
    included = _included_drafts(drafts, decisions)
    if not included:
        return _fallback_report(company_name)

    _validate_citations(included, valid_citation_ids)
    lines = [
        _report_title(company_name),
        "",
        "本文基于招股说明书中已抽取的可引用证据，围绕业务定位、能力配置、商业化验证和风险约束展开阅读。",
    ]
    for draft in included:
        lines.extend(["", f"## {draft.title}", "", draft.body.strip()])
    return _clean_markdown(lines)
