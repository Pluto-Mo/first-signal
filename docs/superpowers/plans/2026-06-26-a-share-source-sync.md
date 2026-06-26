# A-Share Source Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an A-share source sync layer that discovers a small number of real prospectus candidates from CNINFO's IPO list API, resolves their body-PDF announcements through CNINFO's announcement search API, filters them with narrow rules, downloads allowed PDFs into `data/inbox/`, and records enough metadata for later OCR handoff without changing the existing parse/report pipeline.

**Architecture:** Add a focused `source_sync` package under `src/ipo_evidence/` with clear boundaries for candidate normalization, rules-based filtering, state logging, downloading, and a separate sync CLI. Keep the existing OCR/parser/report stack untouched; the new layer ends at `data/inbox/` plus JSONL/JSON state files under `data/tmp/source_sync/`.

**Tech Stack:** Python 3.11, `requests`, `pytest`, existing `pydantic` models and IO helpers, CNINFO `ipoProspectus` + `hisAnnouncement` HTTP endpoints, local filesystem JSON/JSONL state.

---

## Scope Check

This plan covers one subsystem only: the new A-share source sync front layer. It does not implement Hong Kong support, OCR execution changes, report generation changes, or Web changes.

## File Structure

### New Files

- Create: `configs/source_sync.yaml` — source endpoint, window, throttling, and destination settings
- Create: `configs/filter_rules.yaml` — narrow filtering rules and score thresholds
- Create: `src/ipo_evidence/source_sync/__init__.py` — package marker and exports
- Create: `src/ipo_evidence/source_sync/models.py` — normalized candidate, filter result, download record, and sync state models
- Create: `src/ipo_evidence/source_sync/client.py` — CNINFO HTTP client and candidate normalization
- Create: `src/ipo_evidence/source_sync/filters.py` — body-title filtering and rules scoring
- Create: `src/ipo_evidence/source_sync/state.py` — JSONL logging and sync state persistence
- Create: `src/ipo_evidence/source_sync/downloader.py` — PDF naming, hashing, dedupe, and inbox writes
- Create: `src/ipo_evidence/source_sync/service.py` — orchestration from discovery through download
- Create: `src/ipo_evidence/source_sync/cli.py` — `sync-a-share` command entrypoint
- Create: `tests/test_source_sync_models.py`
- Create: `tests/test_source_sync_filters.py`
- Create: `tests/test_source_sync_state.py`
- Create: `tests/test_source_sync_downloader.py`
- Create: `tests/test_source_sync_service.py`

### Modified Files

- Modify: `src/ipo_evidence/config.py` — optionally add typed config helpers if loading nested sync configs becomes repetitive
- Modify: `README.md` — document the new sync command after verification
- Modify: `AGENTS.md` only if implementation reveals a design correction

## Task 1: Sync Models And Config Foundations

**Files:**
- Create: `configs/source_sync.yaml`
- Create: `configs/filter_rules.yaml`
- Create: `src/ipo_evidence/source_sync/__init__.py`
- Create: `src/ipo_evidence/source_sync/models.py`
- Create: `tests/test_source_sync_models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_source_sync_models.py`:

```python
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
```

- [ ] **Step 2: Run the model tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_source_sync_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ipo_evidence.source_sync'`.

- [ ] **Step 3: Write source sync config**

Create `configs/source_sync.yaml`:

```yaml
source: cninfo
window:
  lookback_days: 7
  overlap_days: 3
limits:
  max_candidates: 20
  max_downloads: 3
throttle:
  request_interval_seconds: 2.0
  jitter_seconds: 0.5
paths:
  inbox_dir: data/inbox
  state_dir: data/tmp/source_sync
cninfo:
  announcement_search_url: https://www.cninfo.com.cn/new/hisAnnouncement/query
  prospectus_list_url: https://www.cninfo.com.cn/data20/ipoProspectus/getIpoProspectus
  user_agent: Mozilla/5.0
  referer: https://www.cninfo.com.cn/new/commonUrl?pageOfSearch=disclosure/list/search
```

Create `configs/filter_rules.yaml`:

```yaml
thresholds:
  filter_score: 6
  observe_score: 3
body_title_exclude:
  - 提示性公告
  - 摘要
  - 英文版
  - 更正
  - 问询回复
  - 法律意见书
  - 审计报告
commercial_buffer_terms:
  - 客户
  - 收入
  - 市场
  - 量产
  - 应用场景
  - 解决方案
  - 商业化
rules:
  - rule_id: hard_pharma_specific_01
    action: filter
    score: 4
    min_hits: 2
    terms:
      - 临床试验
      - 候选药物
      - 适应症
      - 药代动力学
      - 体内外评价
    reason: 偏临床研发导向且专业门槛高
  - rule_id: hard_materials_specific_01
    action: filter
    score: 4
    min_hits: 2
    terms:
      - 前驱体
      - 溅射靶材
      - 电子特气
      - 光刻胶
      - 蒸镀材料
    reason: 偏上游工艺材料且专业门槛高
```

- [ ] **Step 4: Implement source sync models**

Create `src/ipo_evidence/source_sync/models.py`:

```python
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FilterDecision(StrEnum):
    allow = "allow"
    observe = "observe"
    filter = "filter"


class SyncCandidate(BaseModel):
    sync_id: str
    market: str
    exchange: str
    company_name: str
    security_code: str
    announcement_id: str
    announcement_title: str
    published_at: str
    source_url: str
    pdf_url: str
    document_type: str
    disclosure_stage: str
    industry_text: str = ""
    company_summary: str = ""

    @property
    def company_latest_key(self) -> str:
        return f"{self.market}::{self.company_name}"


class FilterResult(BaseModel):
    decision: FilterDecision
    score: int = 0
    matched_rules: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    reason: str

    @model_validator(mode="after")
    def validate_reason(self) -> "FilterResult":
        if self.decision == FilterDecision.filter and not self.reason.strip():
            raise ValueError("reason is required for filtered items")
        return self


class DownloadRecord(BaseModel):
    sync_id: str
    company_name: str
    announcement_id: str
    announcement_title: str
    published_at: str
    source_url: str
    local_pdf_path: str
    file_sha256: str
    disclosure_stage: str
    download_status: str
    ocr_status: str


class SyncState(BaseModel):
    last_successful_run_at: str | None = None
    last_window_start: str | None = None
    processed_announcement_ids: list[str] = Field(default_factory=list)
```

Create `src/ipo_evidence/source_sync/__init__.py`:

```python
from ipo_evidence.source_sync.models import (
    DownloadRecord,
    FilterDecision,
    FilterResult,
    SyncCandidate,
    SyncState,
)

__all__ = [
    "DownloadRecord",
    "FilterDecision",
    "FilterResult",
    "SyncCandidate",
    "SyncState",
]
```

- [ ] **Step 5: Run the model tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_source_sync_models.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 6: Commit**

```powershell
git add configs/source_sync.yaml configs/filter_rules.yaml src/ipo_evidence/source_sync tests/test_source_sync_models.py
git commit -m "feat: add source sync config and models"
```

## Task 2: Prospectus Filtering Rules

**Files:**
- Create: `src/ipo_evidence/source_sync/filters.py`
- Create: `tests/test_source_sync_filters.py`

- [ ] **Step 1: Write the failing filter tests**

Create `tests/test_source_sync_filters.py`:

```python
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
```

- [ ] **Step 2: Run the filter tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_source_sync_filters.py -q
```

Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'is_body_prospectus_title'`.

- [ ] **Step 3: Implement the filtering helpers**

Create `src/ipo_evidence/source_sync/filters.py`:

```python
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

    decision_score = score

    if decision_score >= filter_threshold:
        decision = FilterDecision.filter
    elif decision_score >= observe_threshold or matched_any_rule:
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
```

这个任务的规则口径以测试行为为准：专业规则命中后，基础分由“规则分数 + 命中术语数”构成，再减去商业缓冲词命中数；如果命中过专业规则但原始分数仍低于观察线，`decision` 至少进入 `observe`，但返回的 `score` 仍保留原始值，便于后续排序、回溯和调规则。

- [ ] **Step 4: Run the filter tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_source_sync_filters.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/ipo_evidence/source_sync/filters.py tests/test_source_sync_filters.py
git commit -m "feat: add narrow prospectus filter rules"
```

## Task 3: State Logging And Inbox Downloader

**Files:**
- Create: `src/ipo_evidence/source_sync/state.py`
- Create: `src/ipo_evidence/source_sync/downloader.py`
- Create: `tests/test_source_sync_state.py`
- Create: `tests/test_source_sync_downloader.py`

- [ ] **Step 1: Write the failing state and downloader tests**

Create `tests/test_source_sync_state.py`:

```python
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

    append_jsonl_record(log_path, {"candidate": candidate.model_dump(mode="json"), "result": result.model_dump(mode="json")})
    append_jsonl_record(log_path, {"candidate": candidate.model_dump(mode="json"), "result": result.model_dump(mode="json")})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
```

Create `tests/test_source_sync_downloader.py`:

```python
from pathlib import Path

from ipo_evidence.source_sync.downloader import SyncDownloader, build_inbox_filename, write_pdf_bytes
from ipo_evidence.source_sync.models import SyncCandidate


def make_candidate() -> SyncCandidate:
    return SyncCandidate(
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


def test_build_inbox_filename_is_stable():
    filename = build_inbox_filename(make_candidate())

    assert filename == "2025-07-11__华电新能__1224131325.pdf"


def test_write_pdf_bytes_persists_file_and_hash(tmp_path: Path):
    pdf_path, sha256 = write_pdf_bytes(
        tmp_path,
        "2025-07-11__华电新能__1224131325.pdf",
        b"%PDF-1.4\nsample",
    )

    assert pdf_path.exists()
    assert pdf_path.name.endswith(".pdf")
    assert len(sha256) == 64


def test_sync_downloader_returns_handoff_record(tmp_path: Path):
    downloader = SyncDownloader(tmp_path)
    record = downloader.download_candidate(make_candidate(), content=b"%PDF-1.4\nsample")

    assert record["download_status"] == "downloaded"
    assert record["ocr_status"] == "ocr_not_started"
    assert Path(record["local_pdf_path"]).exists()
```

- [ ] **Step 2: Run the state and downloader tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_source_sync_state.py tests/test_source_sync_downloader.py -q
```

Expected: FAIL with missing `ipo_evidence.source_sync.state` and `downloader`.

- [ ] **Step 3: Implement state helpers**

Create `src/ipo_evidence/source_sync/state.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from ipo_evidence.io import ensure_dir, read_json, write_json
from ipo_evidence.source_sync.models import SyncState


def load_sync_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    return SyncState.model_validate(read_json(path))


def save_sync_state(path: Path, payload: dict) -> None:
    write_json(path, payload)


def append_jsonl_record(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
```

Create `src/ipo_evidence/source_sync/downloader.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path

import requests

from ipo_evidence.io import ensure_dir
from ipo_evidence.source_sync.models import SyncCandidate


def build_inbox_filename(candidate: SyncCandidate) -> str:
    return f"{candidate.published_at}__{candidate.company_name}__{candidate.announcement_id}.pdf"


def write_pdf_bytes(inbox_dir: Path, filename: str, content: bytes) -> tuple[Path, str]:
    ensure_dir(inbox_dir)
    pdf_path = inbox_dir / filename
    pdf_path.write_bytes(content)
    return pdf_path, hashlib.sha256(content).hexdigest()


class SyncDownloader:
    def __init__(self, inbox_dir: Path | str):
        self.inbox_dir = Path(inbox_dir)

    def download_candidate(self, candidate: SyncCandidate, content: bytes | None = None) -> dict:
        pdf_bytes = content
        if pdf_bytes is None:
            response = requests.get(candidate.pdf_url, timeout=60)
            response.raise_for_status()
            pdf_bytes = response.content
        filename = build_inbox_filename(candidate)
        pdf_path, sha256 = write_pdf_bytes(self.inbox_dir, filename, pdf_bytes)
        return {
            "sync_id": candidate.sync_id,
            "company_name": candidate.company_name,
            "announcement_id": candidate.announcement_id,
            "announcement_title": candidate.announcement_title,
            "published_at": candidate.published_at,
            "source_url": candidate.source_url,
            "local_pdf_path": str(pdf_path),
            "file_sha256": sha256,
            "disclosure_stage": candidate.disclosure_stage,
            "download_status": "downloaded",
            "ocr_status": "ocr_not_started",
        }
```

- [ ] **Step 4: Run the state and downloader tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_source_sync_state.py tests/test_source_sync_downloader.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/ipo_evidence/source_sync/state.py src/ipo_evidence/source_sync/downloader.py tests/test_source_sync_state.py tests/test_source_sync_downloader.py
git commit -m "feat: add source sync state and downloader helpers"
```

## Task 4: CNINFO Client And Orchestration Service

**Files:**
- Create: `src/ipo_evidence/source_sync/client.py`
- Create: `src/ipo_evidence/source_sync/service.py`
- Create: `tests/test_source_sync_service.py`

- [ ] **Step 1: Write the failing service tests**

Create `tests/test_source_sync_service.py`:

```python
from ipo_evidence.source_sync.models import FilterDecision, FilterResult, SyncCandidate
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
    newer = older.model_copy(update={
        "sync_id": "sync-newer",
        "announcement_id": "1224000002",
        "announcement_title": "华电新能首次公开发行股票并在主板上市招股说明书",
        "published_at": "2025-07-11",
        "pdf_url": "https://example.com/new.pdf",
    })
    other = older.model_copy(update={
        "sync_id": "sync-other",
        "company_name": "屹唐股份",
        "announcement_id": "1224000003",
        "announcement_title": "屹唐股份首次公开发行股票并在科创板上市招股说明书",
        "published_at": "2025-07-11",
        "source_url": "https://example.com/other",
        "pdf_url": "https://example.com/other.pdf",
    })

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


def test_run_sync_downloads_allow_and_observe_candidates_only(tmp_path):
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
            "body_title_exclude": ["提示性公告"],
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
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_source_sync_service.py -q
```

Expected: FAIL with missing `ipo_evidence.source_sync.service`.

- [ ] **Step 3: Implement the client and selection logic**

Create `src/ipo_evidence/source_sync/client.py`:

```python
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

import requests

from ipo_evidence.source_sync.models import SyncCandidate


@dataclass
class CNInfoClient:
    announcement_search_url: str
    user_agent: str
    referer: str
    request_interval_seconds: float

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Referer": self.referer,
        }

    def discover_prospectus_candidates(self, days: int, limit: int) -> list[SyncCandidate]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        response = requests.post(
            self.announcement_search_url,
            data={
                "pageNum": 1,
                "pageSize": limit,
                "searchkey": "招股说明书",
                "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
                "sortName": "time",
                "sortType": "desc",
                "isHLtitle": "true",
            },
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        time.sleep(self.request_interval_seconds)
        announcements = response.json().get("announcements") or []
        candidates: list[SyncCandidate] = []
        for item in announcements:
            candidates.append(
                SyncCandidate(
                    sync_id=str(uuid4()),
                    market="a_share",
                    exchange="unknown",
                    company_name=item.get("secName", ""),
                    security_code=item.get("secCode", ""),
                    announcement_id=item["announcementId"],
                    announcement_title=item["announcementTitle"].replace("<em>", "").replace("</em>", ""),
                    published_at=item["adjunctUrl"].split("/")[1],
                    source_url=f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={item['announcementId']}",
                    pdf_url=f"https://static.cninfo.com.cn/{item['adjunctUrl']}",
                    document_type="prospectus",
                    disclosure_stage="unknown",
                    industry_text="",
                    company_summary="",
                )
            )
        return candidates
```

Create `src/ipo_evidence/source_sync/service.py`:

```python
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
    return sorted(selected.values(), key=lambda item: (item.published_at, item.company_name))


def run_sync(
    client,
    filter_config: dict,
    days: int,
    limit: int,
    downloader,
) -> dict:
    discovered = client.discover_prospectus_candidates(days=days, limit=limit)
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
    for candidate in selected:
        records.append(downloader.download_candidate(candidate))
    return {
        "candidates": discovered,
        "decisions": decisions,
        "downloads": records,
    }
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_source_sync_service.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/ipo_evidence/source_sync/client.py src/ipo_evidence/source_sync/service.py tests/test_source_sync_service.py
git commit -m "feat: add cninfo candidate discovery service"
```

## Task 5: Sync CLI And Local Smoke Workflow

**Files:**
- Create: `src/ipo_evidence/source_sync/cli.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing CLI smoke test**

Append this test to `tests/test_source_sync_service.py`:

```python
from ipo_evidence.source_sync.cli import build_parser


def test_sync_cli_accepts_days_and_limit():
    parser = build_parser()
    args = parser.parse_args(["sync-a-share", "--days", "7", "--limit", "3"])

    assert args.command == "sync-a-share"
    assert args.days == 7
    assert args.limit == 3
```

- [ ] **Step 2: Run the CLI smoke test to verify it fails**

Run:

```powershell
python -m pytest tests/test_source_sync_service.py::test_sync_cli_accepts_days_and_limit -q
```

Expected: FAIL with missing `ipo_evidence.source_sync.cli`.

- [ ] **Step 3: Implement the sync CLI**

Create `src/ipo_evidence/source_sync/cli.py`:

```python
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from ipo_evidence.config import load_yaml
from ipo_evidence.source_sync.client import CNInfoClient
from ipo_evidence.source_sync.downloader import SyncDownloader

from ipo_evidence.source_sync.service import run_sync
from ipo_evidence.source_sync.state import append_jsonl_record, save_sync_state


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ipo-evidence-source-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser("sync-a-share")
    sync.add_argument("--days", type=positive_int, default=7)
    sync.add_argument("--limit", type=positive_int, default=3)
    sync.set_defaults(handler=handle_sync_a_share)
    return parser


def handle_sync_a_share(args: argparse.Namespace) -> int:
    sync_config = load_yaml("configs/source_sync.yaml")
    filter_config = load_yaml("configs/filter_rules.yaml")
    client = CNInfoClient(
        announcement_search_url=sync_config["cninfo"]["announcement_search_url"],
        user_agent=sync_config["cninfo"]["user_agent"],
        referer=sync_config["cninfo"]["referer"],
        request_interval_seconds=float(sync_config["throttle"]["request_interval_seconds"]),
    )
    downloader = SyncDownloader(sync_config["paths"]["inbox_dir"])
    summary = run_sync(
        client=client,
        filter_config=filter_config,
        days=args.days,
        limit=args.limit,
        downloader=downloader,
    )
    state_dir = Path(sync_config["paths"]["state_dir"])
    for candidate in summary["candidates"]:
        append_jsonl_record(
            state_dir / "discovery_log.jsonl",
            candidate.model_dump(mode="json"),
        )
        decision = summary["decisions"][candidate.sync_id]
        if decision.decision != "allow":
            append_jsonl_record(
                state_dir / "filter_log.jsonl",
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "result": decision.model_dump(mode="json"),
                },
            )
    for record in summary["downloads"]:
        append_jsonl_record(state_dir / "download_log.jsonl", record)
    save_sync_state(
        state_dir / "sync_state.json",
        {
            "last_successful_run_at": datetime.now().isoformat(timespec="seconds"),
            "last_window_start": f"lookback:{args.days}",
            "processed_announcement_ids": [
                record["announcement_id"] for record in summary["downloads"]
            ],
        },
    )
    print(f"downloaded={len(summary['downloads'])}")
    return 0
```

- [ ] **Step 4: Run the CLI smoke test to verify it passes**

Run:

```powershell
python -m pytest tests/test_source_sync_service.py::test_sync_cli_accepts_days_and_limit -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Document the sync command**

Modify `README.md` to add:

```markdown
## A-share source sync

```powershell
python -m ipo_evidence.source_sync.cli sync-a-share --days 7 --limit 3
```

This command discovers a small number of recent A-share prospectus announcements, applies narrow filtering rules, and downloads allowed PDFs into `data/inbox/` without automatically triggering OCR.
```

- [ ] **Step 6: Run focused verification**

Run:

```powershell
python -m pytest tests/test_source_sync_models.py tests/test_source_sync_filters.py tests/test_source_sync_state.py tests/test_source_sync_downloader.py tests/test_source_sync_service.py -q
git status --short
```

Expected:

```text
all source sync tests pass
```

and `git status --short` shows only the planned source sync files plus any existing unrelated worktree changes.

- [ ] **Step 7: Manual live smoke test**

Run:

```powershell
python -m ipo_evidence.source_sync.cli sync-a-share --days 7 --limit 3
Get-ChildItem data/inbox
Get-ChildItem data/tmp/source_sync
```

Expected:

```text
1-3 PDF files appear in data/inbox/
discovery_log.jsonl, filter_log.jsonl, download_log.jsonl, and sync_state.json appear in data/tmp/source_sync/
```

This is a live network check, so exact companies will vary. If zero body PDFs are downloaded, inspect `filter_log.jsonl` and `discovery_log.jsonl` before changing rules.

- [ ] **Step 8: Commit**

```powershell
git add src/ipo_evidence/source_sync/cli.py README.md tests/test_source_sync_service.py
git commit -m "feat: add a-share source sync cli"
```

---

## Self-Review

### Spec Coverage

- A-share only: Tasks 1-5 stay within A-share CNINFO scope.
- No OCR execution changes: all tasks stop at `data/inbox/` and state logs.
- Filtered records retained: Task 3 state logging plus Task 5 smoke verification cover the retained logs.
- Narrow rules, no broad industry blacklist: Task 2 implements term-combination scoring with buffer terms.
- Observe items still enter inbox for now: Task 4 selection keeps `allow` and `observe`, excluding only `filter`.

### Placeholder Scan

- No `TODO`, `TBD`, or “similar to above” placeholders remain.
- Every code-writing step includes concrete code.
- Every verification step includes exact commands and expected output.

### Type Consistency

- `SyncCandidate`, `FilterResult`, `DownloadRecord`, and `SyncState` are defined in Task 1 and reused consistently.
- `FilterDecision.filter` is the only state excluded from the selection step.
- `sync-a-share` CLI naming matches the approved design doc.
