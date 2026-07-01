import pytest

from ipo_evidence.models import InternalTrace, QualityGateDecision, SectionDraft
from ipo_evidence.report_assembler import assemble_report


def _draft(section_key: str, title: str, body: str) -> SectionDraft:
    return SectionDraft(
        section_key=section_key,
        title=title,
        section_role="main",
        body=body,
        citation_ids=[],
        internal_trace=InternalTrace(
            section_key=section_key,
            skill_refs=[],
            prompt_slot="narrative_section",
        ),
    )


def _decision(section_key: str, action: str) -> QualityGateDecision:
    return QualityGateDecision(
        section_key=section_key,
        action=action,
        reason=f"{section_key} {action}",
    )


def test_assemble_report_includes_only_include_decisions_in_draft_order():
    drafts = [
        _draft("first", "第一节", "第一节正文。[C-001]"),
        _draft("second", "第二节", "第二节正文。[C-002]"),
        _draft("third", "第三节", "第三节正文。[C-003]"),
        _draft("missing_decision", "缺少决策", "不应输出。[C-004]"),
        _draft("empty", "空正文", "   "),
    ]
    decisions = [
        _decision("third", "include"),
        _decision("first", "include"),
        _decision("second", "merge"),
        _decision("extra", "include"),
        _decision("empty", "include"),
    ]

    report = assemble_report(
        "测试股份有限公司",
        drafts,
        decisions,
        valid_citation_ids={"C-001", "C-002", "C-003", "C-004"},
    )

    assert report.startswith("# 测试股份有限公司招股书长篇阅读\n\n")
    assert "本文基于招股说明书中已抽取的可引用证据" in report
    assert report.index("## 第一节") < report.index("## 第三节")
    assert "第一节正文。[C-001]" in report
    assert "第三节正文。[C-003]" in report
    assert "## 第二节" not in report
    assert "## 缺少决策" not in report
    assert "## 空正文" not in report
    assert "## extra" not in report
    assert report.endswith("\n")


def test_assemble_report_returns_citation_free_fallback_when_nothing_qualifies():
    report = assemble_report(
        "测试股份有限公司",
        [_draft("weak", "弱证据", "弱证据正文。[C-001]")],
        [_decision("weak", "log_only")],
        valid_citation_ids={"C-001"},
    )

    assert report == (
        "# 测试股份有限公司招股书长篇阅读\n\n"
        "本次材料未形成满足证据阈值的正式解读正文。"
        "系统已保留处理记录，用于后续补充证据和优化生成策略。\n"
    )
    assert "[C-" not in report


def test_assemble_report_rejects_unknown_citation_ids():
    with pytest.raises(ValueError, match="unknown citation id"):
        assemble_report(
            "测试股份有限公司",
            [_draft("first", "第一节", "第一节正文。[C-999]")],
            [_decision("first", "include")],
            valid_citation_ids={"C-001"},
        )
