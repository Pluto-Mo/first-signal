import { MapPinned } from "lucide-react";
import type { Citation } from "../lib/types";

interface SourceViewProps {
  citation: Citation;
}

const orderedFields: Array<keyof Citation["location"]> = [
  "source_file",
  "page_number",
  "block_id",
  "section_path",
  "table_id",
  "table_title",
  "field_value"
];

export function SourceView({ citation }: SourceViewProps) {
  return (
    <section className="source-view" aria-labelledby="source-view-title">
      <div className="panel-header">
        <p className="eyebrow">Source View</p>
        <h2 id="source-view-title">招股说明书 第 {citation.location.page_number} 页</h2>
      </div>

      <div className="source-callout">
        <MapPinned size={16} />
        <p>保留最小定位字段，方便回到 PDF 原文人工核查。</p>
      </div>

      <dl className="source-grid">
        {orderedFields
          .filter((field) => citation.location[field] !== undefined)
          .map((field) => (
            <div key={field} className="source-row">
              <dt>{field}</dt>
              <dd>{String(citation.location[field])}</dd>
            </div>
          ))}
      </dl>
    </section>
  );
}
