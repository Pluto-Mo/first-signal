import { useMemo, useState } from "react";
import { CitationPanel } from "./components/CitationPanel";
import { DocumentList } from "./components/DocumentList";
import { ReportReader } from "./components/ReportReader";
import { SourceView } from "./components/SourceView";
import { documents, getDocumentById } from "./lib/data";
import type { Citation } from "./lib/types";

function buildCitationLookup(citations: Citation[]) {
  return Object.fromEntries(citations.map((citation) => [citation.id, citation]));
}

function firstCitationId(document: ReturnType<typeof getDocumentById>) {
  for (const section of document.sections) {
    for (const block of section.blocks) {
      if (block.citationIds.length > 0) {
        return block.citationIds[0];
      }
    }
  }
  return document.citations[0]?.id ?? "";
}

export default function App() {
  const [selectedDocumentId, setSelectedDocumentId] = useState(documents[0].id);
  const document = getDocumentById(selectedDocumentId);
  const [selectedSectionId, setSelectedSectionId] = useState(document.sections[0].id);
  const [selectedCitationId, setSelectedCitationId] = useState(firstCitationId(document));

  const citationLookup = useMemo(
    () => buildCitationLookup(document.citations),
    [document.citations]
  );

  const citation =
    citationLookup[selectedCitationId] ?? document.citations[0];

  function handleDocumentSelect(documentId: string) {
    const nextDocument = getDocumentById(documentId);

    setSelectedDocumentId(documentId);
    setSelectedSectionId(nextDocument.sections[0].id);
    setSelectedCitationId(firstCitationId(nextDocument));
  }

  function handleSectionSelect(sectionId: string) {
    const nextSection =
      document.sections.find((section) => section.id === sectionId) ??
      document.sections[0];

    setSelectedSectionId(nextSection.id);
    if (nextSection.blocks[0].citationIds[0]) {
      setSelectedCitationId(nextSection.blocks[0].citationIds[0]);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">IPO Evidence Intelligence</p>
          <h1>A股招股书证据阅读台</h1>
        </div>
        <p className="app-subtitle">
          正文优先阅读，引用与来源定位放在右侧，适合边读边核。
        </p>
      </header>

      <main className="workspace">
        <div className="main-column">
          <DocumentList
            documents={documents}
            selectedDocumentId={document.id}
            onSelect={handleDocumentSelect}
          />
          <ReportReader
            title={document.reportTitle}
            sections={document.sections}
            selectedSectionId={selectedSectionId}
            selectedCitationId={selectedCitationId}
            citationLookup={citationLookup}
            onSectionSelect={handleSectionSelect}
            onCitationSelect={setSelectedCitationId}
          />
        </div>

        <div className="side-column">
          <CitationPanel citation={citation} />
          <SourceView citation={citation} sourceMarkdown={document.sourceMarkdown} />
        </div>
      </main>
    </div>
  );
}
