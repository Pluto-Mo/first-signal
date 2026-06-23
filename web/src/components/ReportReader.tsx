import { Quote } from "lucide-react";
import type { Citation, ReportSection } from "../lib/types";

interface ReportReaderProps {
  title: string;
  sections: ReportSection[];
  selectedSectionId: string;
  selectedCitationId: string;
  citationLookup: Record<string, Citation>;
  onSectionSelect: (sectionId: string) => void;
  onCitationSelect: (citationId: string) => void;
}

export function ReportReader({
  title,
  sections,
  selectedSectionId,
  selectedCitationId,
  citationLookup,
  onSectionSelect,
  onCitationSelect
}: ReportReaderProps) {
  const section =
    sections.find((item) => item.id === selectedSectionId) ?? sections[0];

  return (
    <section className="report-reader" aria-labelledby="report-reader-title">
      <div className="panel-header reader-header">
        <div>
          <p className="eyebrow">阅读</p>
          <h2 id="report-reader-title">{title}</h2>
        </div>
      </div>

      <div className="section-tabs" role="tablist" aria-label="报告章节">
        {sections.map((item) => {
          const isActive = item.id === section.id;

          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`section-tab${isActive ? " is-active" : ""}`}
              onClick={() => onSectionSelect(item.id)}
            >
              {item.title}
            </button>
          );
        })}
      </div>

      <article className="report-article">
        {section.blocks.map((block) => (
          <section key={block.id} className={`report-block block-${block.kind}`}>
            {block.title ? <h3>{block.title}</h3> : null}
            <p>
              {block.body}
              <span className="citation-inline-list">
                {block.citationIds.map((citationId) => {
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
                      <Quote size={14} />
                      {citationId}
                    </button>
                  );
                })}
              </span>
            </p>
          </section>
        ))}
      </article>
    </section>
  );
}
