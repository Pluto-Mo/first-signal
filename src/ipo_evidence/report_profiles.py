from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ipo_evidence.config import load_yaml
from ipo_evidence.models import EvidencePacket


@dataclass(frozen=True)
class ReportProfile:
    profile_key: str
    title: str
    attention_fields: list[str]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _load_profile_yaml(profile_key: str) -> dict:
    try:
        return load_yaml(f"configs/report_profiles/{profile_key}.yaml")
    except FileNotFoundError:
        return {}


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def load_report_profile(profile_key: str) -> ReportProfile:
    config = _load_profile_yaml(profile_key)
    if not config:
        raise ValueError(f"unknown report profile: {profile_key}")

    attention_fields = []
    parent_key = config.get("extends")
    if isinstance(parent_key, str) and parent_key:
        parent = load_report_profile(parent_key)
        attention_fields.extend(parent.attention_fields)
    attention_fields.extend(_string_list(config.get("attention_fields")))

    return ReportProfile(
        profile_key=config.get("profile_key", profile_key),
        title=config.get("title", profile_key),
        attention_fields=_dedupe_preserving_order(attention_fields),
    )


def _packet_text(packet: EvidencePacket) -> str:
    values: list[str] = []
    for item in packet.items:
        values.append(item.claim_summary)
        values.extend(item.section_path)
        if item.quote:
            values.append(item.quote)
        if item.table_title:
            values.append(item.table_title)
    return " ".join(values)


def select_report_profile(company_name: str, packet: EvidencePacket) -> str:
    text = f"{company_name} {_packet_text(packet)}"
    technology_keywords = ["AI", "芯片", "算法", "核心技术", "研发", "专利", "产品化"]
    strong_technology_keywords = ["芯片", "算法", "核心技术", "产品化"]
    if (
        sum(1 for keyword in technology_keywords if keyword in text) >= 2
        and any(keyword in text for keyword in strong_technology_keywords)
    ):
        return "technology_company"

    keyword_groups = (
        (
            "consumer_product",
            ["消费", "渠道", "电商", "零售", "售后", "价格带", "供应链"],
        ),
        (
            "cyclical_industry",
            ["产能", "原材料", "库存", "资本开支", "价格周期", "供需"],
        ),
    )
    for profile_key, keywords in keyword_groups:
        matches = sum(1 for keyword in keywords if keyword in text)
        if matches >= 2:
            return profile_key
    return "base"
