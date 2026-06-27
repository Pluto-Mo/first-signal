import { FileText } from "lucide-react";
import type { DocsIndexItem } from "../lib/types";

interface DocumentListProps {
  documents: DocsIndexItem[];
  selectedDocumentId: string | null;
  onSelect: (documentId: string) => void;
}

export function DocumentList({
  documents,
  selectedDocumentId,
  onSelect
}: DocumentListProps) {
  return (
    <section className="document-list" aria-labelledby="document-list-title">
      <div className="panel-header">
        <p className="eyebrow">文档</p>
        <h2 id="document-list-title">当前样本</h2>
      </div>
      <div className="document-items" role="list">
        {documents.map((document) => {
          const isSelected = document.doc_id === selectedDocumentId;

          return (
            <button
              key={document.doc_id}
              type="button"
              className={`document-card${isSelected ? " is-selected" : ""}`}
              onClick={() => onSelect(document.doc_id)}
              aria-pressed={isSelected}
            >
              <span className="document-card-icon" aria-hidden="true">
                <FileText size={16} />
              </span>
              <span className="document-card-body">
                <span className="document-card-title">{document.company_name}</span>
                <span className="document-card-meta">
                  {document.parse_status} · {document.quality_status}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
