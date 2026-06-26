from __future__ import annotations

from ipo_evidence.source_sync.filters import build_filter_result, is_body_prospectus_title
from ipo_evidence.source_sync.models import FilterDecision, FilterResult, SyncCandidate


def select_latest_allowed_candidates(
    candidates: list[SyncCandidate],
    decisions: dict[str, FilterResult],
) -> list[SyncCandidate]:
    selected: dict[str, SyncCandidate] = {}
    for candidate in candidates:
        decision = decisions[candidate.sync_id].decision
        if decision == FilterDecision.filter:
            continue
        previous = selected.get(candidate.company_latest_key)
        if previous is None or candidate.published_at > previous.published_at:
            selected[candidate.company_latest_key] = candidate
    return list(selected.values())


def run_sync(
    client,
    filter_config: dict,
    days: int,
    limit: int,
    downloader,
    processed_announcement_ids: set[str] | None = None,
) -> dict:
    discovered = client.discover_prospectus_candidates(days=days, limit=limit)
    processed_ids = processed_announcement_ids or set()
    decisions: dict[str, FilterResult] = {}
    for candidate in discovered:
        if not is_body_prospectus_title(
            candidate.announcement_title,
            filter_config.get("body_title_exclude", []),
        ):
            decisions[candidate.sync_id] = FilterResult(
                decision=FilterDecision.filter,
                score=99,
                matched_rules=["body_title_exclude"],
                matched_terms=["non_body_title"],
                reason="标题不属于正文招股说明书",
            )
            continue
        decisions[candidate.sync_id] = build_filter_result(candidate, filter_config)

    selected = select_latest_allowed_candidates(discovered, decisions)
    records: list[dict] = []
    skipped_existing: list[SyncCandidate] = []
    for candidate in selected:
        if candidate.announcement_id in processed_ids:
            skipped_existing.append(candidate)
            continue
        records.append(downloader.download_candidate(candidate))
    return {
        "candidates": discovered,
        "decisions": decisions,
        "downloads": records,
        "skipped_existing": skipped_existing,
    }
