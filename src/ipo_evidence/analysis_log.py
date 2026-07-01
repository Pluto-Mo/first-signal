from __future__ import annotations

from ipo_evidence.models import AnalysisLog, AnalysisLogEntry, QualityGateDecision


def build_analysis_log(doc_id: str, decisions: list[QualityGateDecision]) -> AnalysisLog:
    entries = [
        AnalysisLogEntry(
            section_key=decision.section_key,
            action=decision.action,
            reason=decision.reason,
            title=decision.title,
            evidence_count=decision.evidence_count,
            min_fact_count=decision.min_fact_count,
            strength=decision.strength,
            required_strength=decision.required_strength,
            needed_evidence=decision.needed_evidence,
            suggested_next_step=decision.suggested_next_step,
            suggested_next_steps=decision.suggested_next_steps,
        )
        for decision in decisions
        if decision.action in {"merge", "log_only"}
    ]
    return AnalysisLog(doc_id=doc_id, skipped_or_merged=entries)
