from __future__ import annotations

from ipo_evidence.source_sync.models import FilterDecision, FilterResult, SyncCandidate


def is_body_prospectus_title(title: str, excluded_terms: list[str]) -> bool:
    if "招股说明书" not in title:
        return False
    return not any(term in title for term in excluded_terms)


def build_filter_result(candidate: SyncCandidate, config: dict) -> FilterResult:
    text = " ".join(
        [
            candidate.company_name,
            candidate.announcement_title,
            candidate.industry_text,
            candidate.company_summary,
            candidate.disclosure_stage,
        ]
    )
    score = 0
    matched_rules: list[str] = []
    matched_terms: list[str] = []
    reason = ""
    matched_any_rule = False

    for rule in config.get("rules", []):
        current_terms = [term for term in rule.get("terms", []) if term in text]
        if len(current_terms) >= int(rule.get("min_hits", 1)):
            score += int(rule.get("score", 0)) + len(current_terms)
            matched_rules.append(rule["rule_id"])
            matched_terms.extend(current_terms)
            reason = rule.get("reason", reason)
            matched_any_rule = True

    for term in config.get("commercial_buffer_terms", []):
        if term in text:
            score -= 1

    filter_threshold = int(config.get("thresholds", {}).get("filter_score", 6))
    observe_threshold = int(config.get("thresholds", {}).get("observe_score", 3))

    if matched_any_rule and score < observe_threshold:
        score = observe_threshold

    if score >= filter_threshold:
        decision = FilterDecision.filter
    elif score >= observe_threshold:
        decision = FilterDecision.observe
    else:
        decision = FilterDecision.allow

    return FilterResult(
        decision=decision,
        score=max(score, 0),
        matched_rules=matched_rules,
        matched_terms=sorted(set(matched_terms)),
        reason=reason if decision != FilterDecision.allow else "passed filter rules",
    )
