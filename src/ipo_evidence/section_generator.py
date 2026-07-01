from __future__ import annotations

from typing import Any

from ipo_evidence.models import EvidenceItem, EvidencePacket, InternalTrace, SectionDraft
from ipo_evidence.section_writer import write_section


def _item_index(packet: EvidencePacket) -> dict[str, tuple[int, EvidenceItem]]:
    return {
        item.evidence_id: (index, item)
        for index, item in enumerate(packet.items, start=1)
    }


def _section_groups(report_inputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report_inputs:
        return []
    groups = report_inputs.get("section_groups", [])
    if not isinstance(groups, list):
        return []
    return [group for group in groups if isinstance(group, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _rank_value(ref: dict[str, Any]) -> int:
    rank = ref.get("rank", 99)
    if type(rank) is int and rank >= 0:
        return rank
    return 99


def generate_section_drafts(
    packet: EvidencePacket,
    report_inputs: dict[str, Any] | None,
) -> list[SectionDraft]:
    indexed = _item_index(packet)
    drafts: list[SectionDraft] = []
    for group in _section_groups(report_inputs):
        section_key = group.get("section_key")
        title = group.get("title")
        if not isinstance(section_key, str) or not isinstance(title, str):
            continue

        refs = group.get("evidence_refs", [])
        items: list[tuple[int, EvidenceItem]] = []
        if isinstance(refs, list):
            seen_evidence_ids: set[str] = set()
            for ref in sorted(
                refs,
                key=lambda ref: _rank_value(ref) if isinstance(ref, dict) else 99,
            ):
                if not isinstance(ref, dict):
                    continue
                evidence_id = ref.get("evidence_id")
                if isinstance(evidence_id, str) and evidence_id in indexed:
                    if evidence_id in seen_evidence_ids:
                        continue
                    seen_evidence_ids.add(evidence_id)
                    items.append(indexed[evidence_id])

        contract = group.get("output_contract")
        if isinstance(contract, dict):
            required = _string_list(contract.get("requires"))
        else:
            required = []
        missing = [
            field
            for field in required
            if field not in {"core_claim", "evidence_chain", "reader_value"}
        ]
        prompt_slot = group.get("prompt_slot", "narrative_section")
        section_role = group.get("section_role", "main")
        skill_refs = _string_list(group.get("skill_refs"))
        normalized_prompt_slot = (
            prompt_slot if isinstance(prompt_slot, str) else "narrative_section"
        )
        write_result = write_section(
            section_key=section_key,
            title=title,
            skill_refs=skill_refs,
            prompt_slot=normalized_prompt_slot,
            indexed_items=items,
        )
        trace = InternalTrace(
            section_key=section_key,
            skill_refs=skill_refs,
            prompt_slot=normalized_prompt_slot,
            evidence_ids=[item.evidence_id for _, item in write_result.selected_items],
            citation_ids=write_result.citation_ids,
            evidence_quality_statuses=[
                item.quality_status for _, item in write_result.selected_items
            ],
            fact_count=len(write_result.selected_items),
            missing_contract_fields=missing,
            readability_warnings=write_result.readability_warnings,
        )
        drafts.append(
            SectionDraft(
                section_key=section_key,
                title=title,
                section_role=section_role if isinstance(section_role, str) else "main",
                body=write_result.body,
                citation_ids=write_result.citation_ids,
                internal_trace=trace,
            )
        )
    return drafts
