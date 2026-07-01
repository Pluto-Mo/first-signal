from __future__ import annotations

from ipo_evidence.models import AnalysisLog, AnalysisLogEntry, QualityGateDecision


def build_analysis_log(doc_id: str, decisions: list[QualityGateDecision]) -> AnalysisLog:
    entries = [
        AnalysisLogEntry(
            section_key=decision.section_key,
            reason=decision.reason,
            needed_evidence=decision.needed_evidence,
            suggested_next_step=decision.suggested_next_step,
        )
        for decision in decisions
        if decision.action in {"merge", "log_only"}
    ]
    return AnalysisLog(doc_id=doc_id, skipped_or_merged=entries)
