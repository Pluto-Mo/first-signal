export type QualityStatus = "safe_to_use" | "manual_review" | "do_not_use";

export interface DocsIndexItem {
  doc_id: string;
  company_name: string;
  source_file: string;
  industry?: string | null;
  published_at?: string | null;
  created_at?: number | null;
  quality_status: QualityStatus;
  parse_status: string;
  report_status: string;
  tags: string[];
  report_path: string;
  citation_path: string;
  reader_bundle_path: string;
}

export interface DocumentGroup {
  id: string;
  label: string;
  icon: string;
  documents: DocsIndexItem[];
}

export type GroupingMode = "time" | "industry";

export interface ReaderCitationLocation {
  source_file: string;
  page_number: number;
  section_path: string[];
  block_id?: string | null;
  table_id?: string | null;
  table_title?: string | null;
  field_value?: string | null;
}

export interface ReaderCitation {
  id: string;
  label: string;
  summary: string;
  quality: QualityStatus;
  excerpt: string;
  location: ReaderCitationLocation;
}

export interface ReaderBlock {
  id: string;
  kind: "lead" | "finding" | "note";
  title?: string;
  body: string;
  citation_ids: string[];
}

export interface ReaderSection {
  id: string;
  title: string;
  blocks: ReaderBlock[];
}

export interface ReaderBundle {
  doc_id: string;
  company_name: string;
  source_file: string;
  report_title: string;
  quality_status: QualityStatus;
  parse_status: string;
  report_status: string;
  sections: ReaderSection[];
  citations: ReaderCitation[];
}
