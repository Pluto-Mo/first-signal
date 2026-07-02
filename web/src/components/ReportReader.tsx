import { Quote } from "lucide-react";
import type { ReaderCitation, ReaderSection } from "../lib/types";

interface ReportReaderProps {
  title: string;
  sections: ReaderSection[];
  selectedCitationId: string | null;
  citationLookup: Record<string, ReaderCitation>;
  onCitationSelect: (citationId: string) => void;
}

export function ReportReader({
  title,
  sections,
  selectedCitationId,
  citationLookup,
  onCitationSelect
}: ReportReaderProps) {
  if (sections.length === 0) {
    return null;
  }

  return (
    <section className="report-reader" aria-labelledby="report-reader-title">
      <div className="panel-header reader-header">
        <div>
          <h2 id="report-reader-title">{title}</h2>
        </div>
      </div>

      <article className="report-article">
        {sections.map((section) => (
          <section key={section.id} className="report-section">
            <h3 className="report-section-title">{section.title}</h3>
            {section.blocks.map((block) => (
              <section key={block.id} className={`report-block block-${block.kind}`}>
                {block.title ? <h4>{block.title}</h4> : null}
                <p>
                  {block.body}
                  <span className="citation-inline-list">
                    {block.citation_ids.map((citationId) => {
                      const citation = citationLookup[citationId];
                      const isSelected = citationId === selectedCitationId;

                      if (!citation) {
                        return null;
                      }

                      return (
                        <button
                          key={citationId}
                          type="button"
                          className={`citation-chip${isSelected ? " is-selected" : ""}`}
                          onClick={() => onCitationSelect(citationId)}
                          aria-label={`查看引用 ${citationId}`}
                        >
                          <Quote size={12} />
                          {citationId}
                        </button>
                      );
                    })}
                  </span>
                </p>
              </section>
            ))}
          </section>
        ))}
      </article>
    </section>
  );
}
