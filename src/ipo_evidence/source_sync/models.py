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
    reason: str = ""

    @model_validator(mode="after")
    def validate_reason(self) -> "FilterResult":
        if self.decision == FilterDecision.filter and not self.reason.strip():
            raise ValueError("reason is required for filtered items")
        return self


class DownloadRecord(BaseModel):
    sync_id: str
    market: str
    exchange: str
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
