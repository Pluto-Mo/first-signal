from ipo_evidence.source_sync.filters import (
    build_filter_result,
    is_body_prospectus_title,
)
from ipo_evidence.source_sync.models import FilterDecision, SyncCandidate


def make_candidate(title: str, industry: str = "", summary: str = "") -> SyncCandidate:
    return SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="示例公司",
        security_code="600001",
        announcement_id="1224000001",
        announcement_title=title,
        published_at="2025-07-11",
        source_url="https://example.com/detail",
        pdf_url="https://example.com/file.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
        industry_text=industry,
        company_summary=summary,
    )


def test_is_body_prospectus_title_rejects_prompt_notice():
    assert not is_body_prospectus_title(
        "华电新能首次公开发行股票并在主板上市招股说明书提示性公告",
        ["提示性公告", "摘要"],
    )


def test_is_body_prospectus_title_accepts_main_document():
    assert is_body_prospectus_title(
        "华电新能首次公开发行股票并在主板上市招股说明书",
        ["提示性公告", "摘要"],
    )


def test_build_filter_result_marks_hard_pharma_candidate_as_filtered():
    candidate = make_candidate(
        "示例公司首次公开发行股票招股说明书",
        industry="医药制造业",
        summary="公司围绕候选药物研发、适应症拓展和临床试验推进产品管线。",
    )

    result = build_filter_result(
        candidate,
        {
            "thresholds": {"filter_score": 6, "observe_score": 3},
            "commercial_buffer_terms": ["收入", "市场"],
            "rules": [
                {
                    "rule_id": "hard_pharma_specific_01",
                    "score": 4,
                    "min_hits": 2,
                    "terms": ["候选药物", "适应症", "临床试验"],
                    "reason": "偏临床研发导向且专业门槛高",
                }
            ],
        },
    )

    assert result.decision == FilterDecision.filter
    assert "hard_pharma_specific_01" in result.matched_rules


def test_build_filter_result_downgrades_to_observe_when_commercial_context_exists():
    candidate = make_candidate(
        "示例公司首次公开发行股票招股说明书",
        industry="电子材料制造",
        summary="公司主营前驱体与蒸镀材料，同时已经形成稳定收入、客户结构和量产应用场景。",
    )

    result = build_filter_result(
        candidate,
        {
            "thresholds": {"filter_score": 6, "observe_score": 3},
            "commercial_buffer_terms": ["收入", "客户", "量产", "应用场景"],
            "rules": [
                {
                    "rule_id": "hard_materials_specific_01",
                    "score": 4,
                    "min_hits": 2,
                    "terms": ["前驱体", "蒸镀材料", "电子特气"],
                    "reason": "偏上游工艺材料且专业门槛高",
                }
            ],
        },
    )

    assert result.decision == FilterDecision.observe
    assert result.score == 2
