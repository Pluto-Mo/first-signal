from __future__ import annotations

import re
import json
from datetime import datetime
from pathlib import Path

from ipo_evidence.io import read_json, write_json
from ipo_evidence.models import Manifest, WebIndex

SOURCE_DATE_PATTERN = re.compile(r"^(\d{4})[-_/年](\d{1,2})[-_/月](\d{1,2})")
ANNOUNCEMENT_ID_PATTERN = re.compile(r"__(\d+)\.pdf$", re.IGNORECASE)
DEFAULT_SOURCE_SYNC_ROOT = Path("data/tmp/source_sync")


def build_web_index(
    manifest: Manifest,
    source_sync_root: Path | None = None,
) -> WebIndex:
    published_at = published_at_for_manifest(
        manifest,
        source_sync_root=source_sync_root or DEFAULT_SOURCE_SYNC_ROOT,
    )
    return WebIndex(
        doc_id=manifest.doc_id,
        company_name=manifest.company_name,
        source_file=manifest.source_file,
        industry=infer_industry(
            company_name=manifest.company_name,
            source_file=manifest.source_file,
            tags=manifest.tags,
        ),
        published_at=published_at,
        created_at=created_at_from_published_at(published_at)
        or created_at_from_source_file(manifest.source_file),
        quality_status=manifest.quality_status,
        parse_status=manifest.parse_status,
        report_status=manifest.report_status,
        tags=manifest.tags,
    )


def refresh_docs_index(docs_root: Path) -> list[dict]:
    items: list[dict] = []
    for web_index_path in sorted(docs_root.glob("*/web_index.json")):
        payload = read_json(web_index_path)
        if isinstance(payload, dict):
            doc_id = payload.get("doc_id")
            if isinstance(doc_id, str) and doc_id:
                for path_key in ("report_path", "citation_path", "reader_bundle_path"):
                    path_value = payload.get(path_key)
                    if isinstance(path_value, str) and path_value and "/" not in path_value:
                        payload[path_key] = f"{doc_id}/{path_value}"
                source_file = payload.get("source_file")
                source_url = payload.get("source_url")
                synced_published_at = (
                    published_at_from_source_sync(
                        source_file=source_file,
                        source_url=source_url if isinstance(source_url, str) else None,
                        source_sync_root=DEFAULT_SOURCE_SYNC_ROOT,
                    )
                    if isinstance(source_file, str)
                    else None
                )
                published_at = (
                    synced_published_at
                    or (
                        str(payload.get("published_at"))
                        if isinstance(payload.get("published_at"), str)
                        else None
                    )
                    or (
                        published_at_from_source_file(source_file)
                        if isinstance(source_file, str)
                        else None
                    )
                )
                if published_at:
                    payload["published_at"] = published_at
                    payload["created_at"] = created_at_from_published_at(published_at)
                else:
                    payload.pop("created_at", None)
                if not payload.get("industry"):
                    payload["industry"] = infer_industry(
                        company_name=str(payload.get("company_name") or ""),
                        source_file=str(payload.get("source_file") or ""),
                        tags=payload.get("tags") if isinstance(payload.get("tags"), list) else [],
                    )
            items.append(payload)
    write_json(docs_root / "index.json", items)
    return items


def published_at_for_manifest(
    manifest: Manifest,
    source_sync_root: Path = DEFAULT_SOURCE_SYNC_ROOT,
) -> str | None:
    return published_at_from_source_sync(
        source_file=manifest.source_file,
        source_url=manifest.source_url,
        source_sync_root=source_sync_root,
    ) or published_at_from_source_file(manifest.source_file)


def published_at_from_source_sync(
    source_file: str,
    source_url: str | None,
    source_sync_root: Path = DEFAULT_SOURCE_SYNC_ROOT,
) -> str | None:
    announcement_id = announcement_id_from_source_file(source_file)
    for log_name in ("download_log.jsonl", "discovery_log.jsonl"):
        log_path = source_sync_root / log_name
        if not log_path.exists():
            continue
        for record in read_jsonl(log_path):
            if not isinstance(record, dict):
                continue
            published_at = record.get("published_at")
            if not isinstance(published_at, str) or not published_at:
                continue
            if announcement_id and record.get("announcement_id") == announcement_id:
                return published_at
            if source_url and record.get("source_url") == source_url:
                return published_at
            local_pdf_path = record.get("local_pdf_path")
            if isinstance(local_pdf_path, str) and Path(local_pdf_path).name == source_file:
                return published_at
    return None


def read_jsonl(path: Path) -> list[object]:
    rows: list[object] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def announcement_id_from_source_file(source_file: str) -> str | None:
    match = ANNOUNCEMENT_ID_PATTERN.search(source_file)
    if not match:
        return None
    return match.group(1)


def published_at_from_source_file(source_file: str) -> str | None:
    match = SOURCE_DATE_PATTERN.match(source_file)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def created_at_from_source_file(source_file: str) -> int | None:
    published_at = published_at_from_source_file(source_file)
    return created_at_from_published_at(published_at)


def created_at_from_published_at(published_at: str | None) -> int | None:
    if not published_at:
        return None
    try:
        return int(datetime.strptime(published_at, "%Y-%m-%d").timestamp() * 1000)
    except ValueError:
        return None


def infer_industry(company_name: str, source_file: str, tags: list[object]) -> str:
    haystack = " ".join(
        [company_name, source_file, *[str(tag) for tag in tags]]
    )

    if re.search(r"思必驰|人工智能|语音|大模型|智能|AI", haystack, re.IGNORECASE):
        return "人工智能"
    if re.search(r"半导体|芯片|集成电路|晶圆|封装", haystack):
        return "半导体"
    if re.search(r"新能源|光伏|储能|风电|锂电", haystack):
        return "新能源"
    if re.search(r"医药|医疗|生物|制药", haystack):
        return "医药"
    if re.search(r"汽车|车载|新能源车|永励", haystack):
        return "汽车"
    if re.search(r"消费|食品|零售|服饰", haystack):
        return "消费"
    if re.search(r"金融|银行|证券|保险", haystack):
        return "金融"

    return "未分类"
