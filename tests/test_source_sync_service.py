from ipo_evidence.source_sync.models import FilterDecision, FilterResult, SyncCandidate
from ipo_evidence.source_sync.cli import build_parser
from ipo_evidence.source_sync.service import run_sync, select_latest_allowed_candidates


def test_select_latest_allowed_candidates_keeps_latest_per_company():
    older = SyncCandidate(
        sync_id="sync-older",
        market="a_share",
        exchange="sse",
        company_name="华电新能",
        security_code="600000",
        announcement_id="1224000001",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书（旧）",
        published_at="2025-07-10",
        source_url="https://example.com/old",
        pdf_url="https://example.com/old.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
    )
    newer = older.model_copy(
        update={
            "sync_id": "sync-newer",
            "announcement_id": "1224000002",
            "announcement_title": "华电新能首次公开发行股票并在主板上市招股说明书",
            "published_at": "2025-07-11",
            "pdf_url": "https://example.com/new.pdf",
        }
    )
    other = older.model_copy(
        update={
            "sync_id": "sync-other",
            "company_name": "屹唐股份",
            "announcement_id": "1224000003",
            "announcement_title": "屹唐股份首次公开发行股票并在科创板上市招股说明书",
            "published_at": "2025-07-11",
            "source_url": "https://example.com/other",
            "pdf_url": "https://example.com/other.pdf",
        }
    )

    candidates = [older, newer, other]
    decisions = {
        "sync-older": FilterResult(decision=FilterDecision.allow, score=0, reason="passed filter rules"),
        "sync-newer": FilterResult(decision=FilterDecision.allow, score=0, reason="passed filter rules"),
        "sync-other": FilterResult(decision=FilterDecision.observe, score=3, reason="observation candidate"),
    }

    selected = select_latest_allowed_candidates(candidates, decisions)

    assert [item.announcement_id for item in selected] == ["1224000002", "1224000003"]


class FakeClient:
    def discover_prospectus_candidates(self, days: int, limit: int) -> list[SyncCandidate]:
        assert days == 7
        assert limit == 3
        return [
            SyncCandidate(
                sync_id="sync-001",
                market="a_share",
                exchange="sse",
                company_name="华电新能",
                security_code="600000",
                announcement_id="1224131325",
                announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
                published_at="2025-07-11",
                source_url="https://example.com/detail",
                pdf_url="https://example.com/file.pdf",
                document_type="prospectus",
                disclosure_stage="上市",
                industry_text="电力、热力生产和供应业",
                company_summary="公司主营新能源发电项目投资运营。",
            )
        ]


class FakeDownloader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def download_candidate(self, candidate: SyncCandidate, content=None) -> dict:
        self.calls.append((candidate.company_name, candidate.announcement_id))
        return {
            "sync_id": candidate.sync_id,
            "market": candidate.market,
            "exchange": candidate.exchange,
            "company_name": candidate.company_name,
            "announcement_id": candidate.announcement_id,
            "announcement_title": candidate.announcement_title,
            "published_at": candidate.published_at,
            "source_url": candidate.source_url,
            "local_pdf_path": "data/inbox/2025-07-11__华电新能__1224131325.pdf",
            "file_sha256": "abc123",
            "disclosure_stage": candidate.disclosure_stage,
            "download_status": "downloaded",
            "ocr_status": "ocr_not_started",
        }


def test_run_sync_downloads_allow_and_observe_candidates_only():
    candidate_allow = SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="华电新能",
        security_code="600000",
        announcement_id="1224131325",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
        published_at="2025-07-11",
        source_url="https://example.com/detail",
        pdf_url="https://example.com/file.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
        industry_text="电力、热力生产和供应业",
        company_summary="公司主营新能源发电项目投资运营。",
    )
    candidate_filter = candidate_allow.model_copy(
        update={
            "sync_id": "sync-002",
            "company_name": "示例药业",
            "announcement_id": "1224131999",
            "announcement_title": "示例药业首次公开发行股票招股说明书",
        }
    )

    fake_client = FakeClient()
    fake_client.discover_prospectus_candidates = lambda days, limit: [candidate_allow, candidate_filter]
    fake_downloader = FakeDownloader()

    summary = run_sync(
        client=fake_client,
        filter_config={
            "body_title_exclude": ["提示性公告", "H股", "港股", "香港公开发售"],
            "thresholds": {"filter_score": 6, "observe_score": 3},
            "commercial_buffer_terms": ["收入", "市场"],
            "rules": [
                {
                    "rule_id": "hard_pharma_specific_01",
                    "score": 6,
                    "min_hits": 1,
                    "terms": ["示例药业"],
                    "reason": "偏临床研发导向且专业门槛高",
                }
            ],
        },
        days=7,
        limit=3,
        downloader=fake_downloader,
    )

    assert [record["announcement_id"] for record in summary["downloads"]] == ["1224131325"]
    assert fake_downloader.calls == [("华电新能", "1224131325")]
    assert summary["decisions"]["sync-002"].decision == FilterDecision.filter


def test_run_sync_skips_existing_processed_announcements():
    candidate = SyncCandidate(
        sync_id="sync-001",
        market="a_share",
        exchange="sse",
        company_name="华电新能",
        security_code="600000",
        announcement_id="1224131325",
        announcement_title="华电新能首次公开发行股票并在主板上市招股说明书",
        published_at="2025-07-11",
        source_url="https://example.com/detail",
        pdf_url="https://example.com/file.pdf",
        document_type="prospectus",
        disclosure_stage="上市",
    )
    fake_client = FakeClient()
    fake_client.discover_prospectus_candidates = lambda days, limit: [candidate]
    fake_downloader = FakeDownloader()

    summary = run_sync(
        client=fake_client,
        filter_config={
            "body_title_exclude": ["提示性公告"],
            "thresholds": {"filter_score": 6, "observe_score": 3},
            "commercial_buffer_terms": [],
            "rules": [],
        },
        days=7,
        limit=3,
        downloader=fake_downloader,
        processed_announcement_ids={"1224131325"},
    )

    assert summary["downloads"] == []
    assert [item.announcement_id for item in summary["skipped_existing"]] == ["1224131325"]
    assert fake_downloader.calls == []


def test_sync_cli_accepts_days_and_limit():
    parser = build_parser()
    args = parser.parse_args(["sync-a-share", "--days", "7", "--limit", "3"])

    assert args.command == "sync-a-share"
    assert args.days == 7
    assert args.limit == 3
