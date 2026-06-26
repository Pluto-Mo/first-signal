from pathlib import Path

from ipo_evidence.io import read_json
from ipo_evidence.source_sync.models import FilterDecision, FilterResult, SyncCandidate
from ipo_evidence.source_sync.state import append_jsonl_record, load_sync_state, save_sync_state


def test_save_sync_state_writes_json_file(tmp_path: Path):
    path = tmp_path / "sync_state.json"
    save_sync_state(path, {"last_successful_run_at": "2026-06-26T10:00:00"})

    saved = read_json(path)

    assert saved["last_successful_run_at"] == "2026-06-26T10:00:00"


def test_load_sync_state_returns_defaults_when_missing(tmp_path: Path):
    state = load_sync_state(tmp_path / "missing.json")

    assert state.processed_announcement_ids == []


def test_append_jsonl_record_appends_lines(tmp_path: Path):
    log_path = tmp_path / "filter_log.jsonl"
    candidate = SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="示例公司",
        security_code="600001",
        announcement_id="1224000001",
        announcement_title="示例公司首次公开发行股票招股说明书",
        published_at="2025-07-11",
        source_url="https://example.com/detail",
        pdf_url="https://example.com/file.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
    )
    result = FilterResult(
        decision=FilterDecision.filter,
        score=6,
        matched_rules=["hard_pharma_specific_01"],
        matched_terms=["临床试验"],
        reason="偏临床研发导向且专业门槛高",
    )

    append_jsonl_record(
        log_path,
        {"candidate": candidate.model_dump(mode="json"), "result": result.model_dump(mode="json")},
    )
    append_jsonl_record(
        log_path,
        {"candidate": candidate.model_dump(mode="json"), "result": result.model_dump(mode="json")},
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
