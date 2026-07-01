from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QualityStatus(StrEnum):
    safe_to_use = "safe_to_use"
    manual_review = "manual_review"
    do_not_use = "do_not_use"


class Manifest(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    source_url: str | None = None
    market: Literal["a_share"] = "a_share"
    document_type: str = "招股说明书"
    input_type: Literal["local_pdf"] = "local_pdf"
    parse_status: str = "discovered"
    report_status: str = "not_started"
    quality_status: QualityStatus = QualityStatus.manual_review
    tags: list[str] = Field(default_factory=list)


class Block(BaseModel):
    block_id: str
    page_number: int
    text: str
    section_path: list[str] = Field(default_factory=list)


class AstNode(BaseModel):
    title: str
    level: int = Field(ge=1)
    section_path: list[str]
    block_ids: list[str] = Field(default_factory=list)
    children: list["AstNode"] = Field(default_factory=list)


class TableObject(BaseModel):
    table_id: str
    title: str
    source_file: str
    page_number: int
    section_path: list[str]
    columns: list[str]
    rows: list[list[str]]
    notes: list[str] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    evidence_id: str
    canonical_section: str
    claim_summary: str
    source_type: Literal["text_quote", "table_fact"]
    source_file: str
    page_number: int
    block_id: str | None = None
    table_id: str | None = None
    table_title: str | None = None
    section_path: list[str]
    quote: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    quality_status: QualityStatus = QualityStatus.manual_review


class EvidencePacket(BaseModel):
    doc_id: str
    items: list[EvidenceItem]


class Citation(BaseModel):
    citation_id: str
    type: Literal["text_quote", "table_fact"]
    source_file: str
    source_url: str | None = None
    page_number: int = Field(ge=1)
    block_id: str | None = None
    table_id: str | None = None
    section_path: list[str]
    quote: str | None = None
    table_title: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    summary: str

    @field_validator("section_path")
    @classmethod
    def section_path_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("section_path must not be empty")
        return value

    @model_validator(mode="after")
    def validate_locator_for_type(self) -> "Citation":
        if self.type == "text_quote":
            if not self.block_id:
                raise ValueError("text_quote citation requires block_id")
            if not self.quote:
                raise ValueError("text_quote citation requires quote")
        if self.type == "table_fact":
            if not self.table_id:
                raise ValueError("table_fact citation requires table_id")
            if not self.table_title:
                raise ValueError("table_fact citation requires table_title")
            if not self.fields:
                raise ValueError("table_fact citation requires fields")
        return self


class WebIndex(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    quality_status: QualityStatus
    parse_status: str
    report_status: str
    tags: list[str] = Field(default_factory=list)
    report_path: str = "report.md"
    citation_path: str = "citation.json"
    reader_bundle_path: str = "reader_bundle.json"


class ReaderCitationLocation(BaseModel):
    source_file: str
    page_number: int
    section_path: list[str]
    block_id: str | None = None
    table_id: str | None = None
    table_title: str | None = None
    field_value: str | None = None


class ReaderCitation(BaseModel):
    id: str
    label: str
    summary: str
    quality: QualityStatus
    excerpt: str
    location: ReaderCitationLocation


class ReaderBlock(BaseModel):
    id: str
    kind: Literal["lead", "finding", "note"]
    title: str | None = None
    body: str
    citation_ids: list[str] = Field(default_factory=list)


class ReaderSection(BaseModel):
    id: str
    title: str
    blocks: list[ReaderBlock] = Field(default_factory=list)


class ReaderBundle(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    report_title: str
    quality_status: QualityStatus
    parse_status: str
    report_status: str
    sections: list[ReaderSection] = Field(default_factory=list)
    citations: list[ReaderCitation] = Field(default_factory=list)


class InternalTrace(BaseModel):
    section_key: str
    skill_refs: list[str] = Field(default_factory=list)
    prompt_slot: str
    evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    evidence_quality_statuses: list[QualityStatus] = Field(default_factory=list)
    fact_count: int = 0
    missing_contract_fields: list[str] = Field(default_factory=list)


class SectionDraft(BaseModel):
    section_key: str
    title: str
    section_role: str = "main"
    body: str
    citation_ids: list[str] = Field(default_factory=list)
    internal_trace: InternalTrace


class QualityGateDecision(BaseModel):
    section_key: str
    action: Literal["include", "merge", "log_only"]
    reason: str
    needed_evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class AnalysisLogEntry(BaseModel):
    section_key: str
    reason: str
    needed_evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class AnalysisLog(BaseModel):
    doc_id: str
    skipped_or_merged: list[AnalysisLogEntry] = Field(default_factory=list)


JsonDict = dict[str, Any]
