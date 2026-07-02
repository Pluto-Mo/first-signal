import json
from datetime import datetime
from pathlib import Path

from ipo_evidence.io import read_json
from ipo_evidence.models import Manifest, QualityStatus
from ipo_evidence.web_index import build_web_index, refresh_docs_index


def test_build_web_index_adds_navigation_metadata():
    manifest = Manifest(
        doc_id="doc_ai",
        company_name="思必驰科技股份有限公司",
        source_file="2026-07-02-思必驰科技股份有限公司招股说明书.pdf",
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )

    web_index = build_web_index(manifest)

    assert web_index.industry == "人工智能"
    assert web_index.created_at == int(datetime(2026, 7, 2).timestamp() * 1000)


def test_build_web_index_prefers_source_sync_published_at(tmp_path: Path):
    sync_root = tmp_path / "source_sync"
    sync_root.mkdir()
    (sync_root / "download_log.jsonl").write_text(
        json.dumps(
            {
                "company_name": "永励精密",
                "announcement_id": "1225382347",
                "published_at": "2026-06-22",
                "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1225382347",
                "local_pdf_path": str(
                    tmp_path / "inbox" / "2026-07-01__永励精密__1225382347.pdf"
                ),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = Manifest(
        doc_id="doc_yongli",
        company_name="浙江永励精密制造股份有限公司",
        source_file="2026-07-01__永励精密__1225382347.pdf",
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )

    web_index = build_web_index(manifest, source_sync_root=sync_root)

    assert web_index.published_at == "2026-06-22"
    assert web_index.created_at == int(datetime(2026, 6, 22).timestamp() * 1000)


def test_build_web_index_does_not_use_generated_time_without_disclosure_date():
    manifest = Manifest(
        doc_id="doc_manual",
        company_name="思必驰科技股份有限公司",
        source_file="思必驰科技股份有限公司.pdf",
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )

    web_index = build_web_index(manifest, source_sync_root=Path("missing-source-sync"))

    assert web_index.published_at is None
    assert web_index.created_at is None


def test_refresh_docs_index_backfills_navigation_metadata(tmp_path: Path):
    package = tmp_path / "doc_demo"
    package.mkdir(parents=True)
    web_index_path = package / "web_index.json"
    web_index_path.write_text(
        json.dumps(
            {
                "doc_id": "doc_demo",
                "company_name": "华润新能源控股有限公司",
                "source_file": "2026-06-26__华润新能源__1225389172.pdf",
                "quality_status": "safe_to_use",
                "parse_status": "parsed",
                "report_status": "reported",
                "tags": [],
                "report_path": "report.md",
                "citation_path": "citation.json",
                "reader_bundle_path": "reader_bundle.json",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    items = refresh_docs_index(tmp_path)
    docs_index = read_json(tmp_path / "index.json")

    assert items[0]["industry"] == "新能源"
    assert items[0]["published_at"] == "2026-06-26"
    assert isinstance(items[0]["created_at"], int)
    assert docs_index[0]["reader_bundle_path"] == "doc_demo/reader_bundle.json"


def test_refresh_docs_index_replaces_generated_time_with_official_published_at(
    tmp_path: Path,
    monkeypatch,
):
    docs_root = tmp_path / "docs"
    package = docs_root / "doc_yongli"
    package.mkdir(parents=True)
    (package / "web_index.json").write_text(
        json.dumps(
            {
                "doc_id": "doc_yongli",
                "company_name": "浙江永励精密制造股份有限公司",
                "source_file": "2026-07-01__永励精密__1225382347.pdf",
                "quality_status": "safe_to_use",
                "parse_status": "parsed",
                "report_status": "reported",
                "tags": [],
                "created_at": int(datetime(2026, 7, 1).timestamp() * 1000),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    sync_root = tmp_path / "source_sync"
    sync_root.mkdir()
    (sync_root / "download_log.jsonl").write_text(
        json.dumps(
            {
                "announcement_id": "1225382347",
                "published_at": "2026-06-22",
                "local_pdf_path": str(
                    tmp_path / "inbox" / "2026-07-01__永励精密__1225382347.pdf"
                ),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("ipo_evidence.web_index.DEFAULT_SOURCE_SYNC_ROOT", sync_root)

    items = refresh_docs_index(docs_root)

    assert items[0]["published_at"] == "2026-06-22"
    assert items[0]["created_at"] == int(datetime(2026, 6, 22).timestamp() * 1000)
