import { BookMarked, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import type { ReaderCitation } from "../lib/types";

interface CitationPanelProps {
  citation: ReaderCitation;
}

function qualityIcon(quality: ReaderCitation["quality"]) {
  if (quality === "safe_to_use") {
    return <ShieldCheck size={16} />;
  }

  if (quality === "manual_review") {
    return <ShieldAlert size={16} />;
  }

  return <ShieldX size={16} />;
}

function qualityLabel(quality: ReaderCitation["quality"]) {
  if (quality === "safe_to_use") {
    return "safe_to_use";
  }

  if (quality === "manual_review") {
    return "manual_review";
  }

  return "do_not_use";
}

export function CitationPanel({ citation }: CitationPanelProps) {
  return (
    <section className="citation-panel" aria-labelledby="citation-panel-title">
      <div className="panel-header">
        <p className="eyebrow">引用</p>
        <h2 id="citation-panel-title">引用 {citation.id}</h2>
      </div>

      <div className="citation-summary">
        <div className="citation-label-row">
          <BookMarked size={16} />
          <strong>{citation.label}</strong>
        </div>
        <p>{citation.summary}</p>
      </div>

      <div className="quality-badge" data-quality={citation.quality}>
        {qualityIcon(citation.quality)}
        <span>{qualityLabel(citation.quality)}</span>
      </div>

      <blockquote className="citation-excerpt">{citation.excerpt}</blockquote>
    </section>
  );
}
