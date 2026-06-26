from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

import requests

from ipo_evidence.source_sync.models import SyncCandidate

TITLE_TAG_RE = re.compile(r"</?em>")
DEFAULT_BODY_EXCLUDED_TERMS = (
    "提示性公告",
    "摘要",
    "英文版",
    "更正",
    "问询回复",
    "法律意见书",
    "审计报告",
    "H股",
    "港股",
    "香港公开发售",
    "全球发售",
)


def strip_em_tags(text: str) -> str:
    return TITLE_TAG_RE.sub("", text or "").strip()


def infer_exchange(page_column: str) -> str:
    normalized = (page_column or "").upper()
    if "SZ" in normalized:
        return "szse"
    if "SH" in normalized:
        return "sse"
    return "unknown"


def derive_published_at(announcement: dict) -> str:
    adjunct_url = announcement.get("adjunctUrl", "")
    parts = adjunct_url.split("/")
    if len(parts) >= 3:
        return parts[1]
    return ""


@dataclass
class CNInfoClient:
    prospectus_list_url: str
    announcement_search_url: str
    user_agent: str
    referer: str
    request_interval_seconds: float = 0.0

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Referer": self.referer,
        }

    def _pause(self) -> None:
        if self.request_interval_seconds > 0:
            time.sleep(self.request_interval_seconds)

    def _get_latest_ipo_records(self, limit: int) -> list[dict]:
        page_size = max(limit * 5, 20)
        response = requests.get(
            self.prospectus_list_url,
            params={"pageNum": 1, "pageSize": page_size},
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        self._pause()
        return response.json().get("data", {}).get("records", []) or []

    def _search_announcements(self, searchkey: str, days: int, page_size: int = 10) -> list[dict]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        response = requests.post(
            self.announcement_search_url,
            data={
                "pageNum": 1,
                "pageSize": page_size,
                "searchkey": searchkey,
                "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
                "sortName": "time",
                "sortType": "desc",
                "isHLtitle": "true",
            },
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        self._pause()
        return response.json().get("announcements") or []

    def _is_body_candidate(self, announcement: dict, company_name: str) -> bool:
        title = strip_em_tags(announcement.get("announcementTitle", ""))
        if "招股说明书" not in title:
            return False
        if any(term in title for term in DEFAULT_BODY_EXCLUDED_TERMS):
            return False
        sec_name = strip_em_tags(announcement.get("secName", ""))
        return not company_name or sec_name == company_name

    def _build_candidate(self, announcement: dict, pool_record: dict | None) -> SyncCandidate:
        company_name = strip_em_tags(announcement.get("secName", "")) or (pool_record or {}).get(
            "SECNAME", ""
        )
        exchange = infer_exchange(announcement.get("pageColumn", ""))
        security_code = announcement.get("secCode", "") or (pool_record or {}).get("SECCODE", "")
        announcement_id = announcement["announcementId"]
        published_at = derive_published_at(announcement)
        return SyncCandidate(
            sync_id=str(uuid4()),
            market="a_share",
            exchange=exchange,
            company_name=company_name,
            security_code=security_code,
            announcement_id=announcement_id,
            announcement_title=strip_em_tags(announcement.get("announcementTitle", "")),
            published_at=published_at,
            source_url=f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={announcement_id}",
            pdf_url=f"https://static.cninfo.com.cn/{announcement['adjunctUrl']}",
            document_type="prospectus",
            disclosure_stage=(pool_record or {}).get("F004V", ""),
            industry_text=(pool_record or {}).get("F002V", ""),
            company_summary=(pool_record or {}).get("F005V", ""),
        )

    def _resolve_candidate_from_pool_record(self, record: dict, days: int) -> SyncCandidate | None:
        company_name = record.get("SECNAME", "")
        search_queries = [f"{company_name} 招股说明书"]
        security_code = record.get("SECCODE", "")
        if security_code:
            search_queries.append(f"{security_code} 招股说明书")

        for query in search_queries:
            announcements = self._search_announcements(query, days=days)
            for announcement in announcements:
                if self._is_body_candidate(announcement, company_name=company_name):
                    return self._build_candidate(announcement, pool_record=record)
        return None

    def _fallback_latest_body_announcements(
        self,
        days: int,
        limit: int,
        pool_index: dict[str, dict],
    ) -> list[SyncCandidate]:
        announcements = self._search_announcements("招股说明书", days=days, page_size=max(limit * 5, 10))
        candidates: list[SyncCandidate] = []
        seen_ids: set[str] = set()
        for announcement in announcements:
            company_name = strip_em_tags(announcement.get("secName", ""))
            if not self._is_body_candidate(announcement, company_name=company_name):
                continue
            if announcement["announcementId"] in seen_ids:
                continue
            pool_record = pool_index.get(company_name)
            candidates.append(self._build_candidate(announcement, pool_record=pool_record))
            seen_ids.add(announcement["announcementId"])
            if len(candidates) >= limit:
                break
        return candidates

    def discover_prospectus_candidates(self, days: int, limit: int) -> list[SyncCandidate]:
        pool_records = self._get_latest_ipo_records(limit=limit)
        pool_index = {record.get("SECNAME", ""): record for record in pool_records if record.get("SECNAME")}

        candidates: list[SyncCandidate] = []
        seen_ids: set[str] = set()

        for record in pool_records:
            candidate = self._resolve_candidate_from_pool_record(record, days=days)
            if candidate is None or candidate.announcement_id in seen_ids:
                continue
            candidates.append(candidate)
            seen_ids.add(candidate.announcement_id)
            if len(candidates) >= limit:
                return candidates

        for candidate in self._fallback_latest_body_announcements(days=days, limit=limit, pool_index=pool_index):
            if candidate.announcement_id in seen_ids:
                continue
            candidates.append(candidate)
            seen_ids.add(candidate.announcement_id)
            if len(candidates) >= limit:
                break

        return candidates
