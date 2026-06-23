import { FileText } from "lucide-react";
import type { DocumentRecord } from "../lib/types";

interface DocumentListProps {
  documents: DocumentRecord[];
  selectedDocumentId: string;
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
          const isSelected = document.id === selectedDocumentId;

          return (
            <button
              key={document.id}
              type="button"
              className={`document-card${isSelected ? " is-selected" : ""}`}
              onClick={() => onSelect(document.id)}
              aria-pressed={isSelected}
            >
              <span className="document-card-icon" aria-hidden="true">
                <FileText size={16} />
              </span>
              <span className="document-card-body">
                <span className="document-card-title">{document.companyName}</span>
                <span className="document-card-meta">
                  {document.exchange} · {document.reportDate}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
