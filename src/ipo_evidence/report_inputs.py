from __future__ import annotations

from functools import lru_cache
from typing import Any

from ipo_evidence.config import load_yaml


@lru_cache(maxsize=1)
def load_report_prompt_config() -> dict[str, Any]:
    return load_yaml("configs/report_prompt.yaml")


def _input_view_templates() -> dict[str, dict[str, Any]]:
    config = load_report_prompt_config()
    views = config.get("input_views", {})
    if not isinstance(views, dict):
        return {}
    return {key: value for key, value in views.items() if isinstance(value, dict)}


def _build_evidence_ref(evidence_id: str, section_path: list[str], rank: int) -> dict:
    return {
        "evidence_id": evidence_id,
        "role": "primary" if rank == 1 else "supporting",
        "rank": rank,
        "label": section_path[-1] if section_path else None,
    }


def build_report_inputs(doc_id: str, company_name: str, packet) -> dict:
    section_groups: list[dict] = []
    templates = sorted(
        _input_view_templates().items(),
        key=lambda pair: pair[1].get("output_order", 99),
    )
    for section_key, template in templates:
        source_sections = set(template.get("source_sections", []))
        refs = []
        for item in packet.items:
            if item.canonical_section not in source_sections:
                continue
            refs.append(
                _build_evidence_ref(item.evidence_id, item.section_path, len(refs) + 1)
            )
        section_groups.append(
            {
                "section_key": section_key,
                "title": template["title"],
                "prompt_slot": template["prompt_slot"],
                "focus_points": template["focus_points"],
                "constraints": template["constraints"],
                "output_order": template["output_order"],
                "token_budget": template["token_budget"],
                "evidence_refs": refs,
            }
        )

    return {
        "doc_id": doc_id,
        "company_name": company_name,
        "outline": [group["section_key"] for group in section_groups],
        "section_groups": section_groups,
    }
