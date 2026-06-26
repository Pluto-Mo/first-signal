from pathlib import Path

import pytest

from ipo_evidence.source_sync.models import (
    DownloadRecord,
    FilterDecision,
    FilterResult,
    SyncCandidate,
    SyncState,
)


def test_sync_candidate_builds_company_latest_key():
    candidate = SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="华电新能",
        security_code="600000",
        announcement_id="1224131325",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
        published_at="2025-07-11",
        source_url="https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1224131325",
        pdf_url="https://static.cninfo.com.cn/finalpage/2025-07-11/1224131325.PDF",
        document_type="prospectus",
        disclosure_stage="上市",
        industry_text="电力、热力生产和供应业",
        company_summary="公司主营新能源发电项目投资运营。",
    )

    assert candidate.company_latest_key == "a_share::华电新能"


def test_filter_result_requires_reason_for_filtered_item():
    with pytest.raises(ValueError, match="reason"):
        FilterResult(
            decision=FilterDecision.filter,
            score=6,
            matched_rules=["hard_pharma_specific_01"],
            matched_terms=["临床试验"],
            reason="",
        )


def test_download_record_tracks_ocr_handoff_fields():
    record = DownloadRecord(
        sync_id="sync-001",
        company_name="华电新能",
        announcement_id="1224131325",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
        published_at="2025-07-11",
        source_url="https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1224131325",
        local_pdf_path="data/inbox/2025-07-11__华电新能__1224131325.pdf",
        file_sha256="abc123",
        disclosure_stage="上市",
        download_status="downloaded",
        ocr_status="ocr_not_started",
    )

    assert record.ocr_status == "ocr_not_started"
    assert Path(record.local_pdf_path).suffix.lower() == ".pdf"


def test_sync_state_defaults_to_empty_cursor():
    state = SyncState()

    assert state.last_successful_run_at is None
    assert state.last_window_start is None
    assert state.processed_announcement_ids == []
