from ipo_evidence.analysis_log import build_analysis_log
from ipo_evidence.models import QualityGateDecision


def test_build_analysis_log_records_log_only_decisions():
    decisions = [
        QualityGateDecision(
            section_key="platform_dependency",
            action="log_only",
            reason="证据数量 0 低于最低要求 2。",
            needed_evidence=["补充 platform_dependency 的可引用证据"],
            suggested_next_step="补充证据后重新生成该 section。",
        )
    ]

    log = build_analysis_log("doc_test", decisions)

    assert log.doc_id == "doc_test"
    assert len(log.skipped_or_merged) == 1
    assert log.skipped_or_merged[0].section_key == "platform_dependency"


def test_build_analysis_log_excludes_include_decisions():
    decisions = [
        QualityGateDecision(
            section_key="business_model",
            action="include",
            reason="证据数量 2 达到最低要求 2。",
        ),
        QualityGateDecision(
            section_key="platform_dependency",
            action="merge",
            reason="证据数量 1 低于最低要求 2。",
            needed_evidence=["补充 platform_dependency 的 supporting evidence"],
            suggested_next_step="合并到相关段落，或补足证据后独立成段。",
        ),
        QualityGateDecision(
            section_key="customer_concentration",
            action="log_only",
            reason="证据数量 0 低于最低要求 2。",
            needed_evidence=["补充 customer_concentration 的可引用证据"],
            suggested_next_step="补充证据后重新生成该 section。",
        ),
    ]

    log = build_analysis_log("doc_test", decisions)

    assert [entry.section_key for entry in log.skipped_or_merged] == [
        "platform_dependency",
        "customer_concentration",
    ]
