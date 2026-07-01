from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ipo_evidence.config import load_yaml
from ipo_evidence.models import EvidencePacket


DEFAULT_REPORT_PROFILE_KEY = "base"


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


def default_report_profile_key() -> str:
    return DEFAULT_REPORT_PROFILE_KEY


def select_report_profile(company_name: str, packet: EvidencePacket) -> str:
    """Compatibility wrapper for the weak default preset.

    The report layer intentionally does not infer an industry profile from
    prospectus text. Views and skills own interpretation; profile is only a
    weak preset unless explicitly configured elsewhere.
    """
    _ = company_name, packet
    return default_report_profile_key()
