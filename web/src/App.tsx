import { useEffect, useMemo, useState } from "react";
import { CitationDrawer } from "./components/CitationDrawer";
import { DocumentList } from "./components/DocumentList";
import { ReportReader } from "./components/ReportReader";
import { loadDocsIndex, loadReaderBundle } from "./lib/api";
import type { DocsIndexItem, ReaderBundle, ReaderCitation } from "./lib/types";

function buildCitationLookup(citations: ReaderCitation[]) {
  return Object.fromEntries(citations.map((citation) => [citation.id, citation]));
}

export default function App() {
  const [documents, setDocuments] = useState<DocsIndexItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [bundlesById, setBundlesById] = useState<Record<string, ReaderBundle>>({});
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [isIndexLoading, setIsIndexLoading] = useState(true);
  const [isBundleLoading, setIsBundleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function bootstrap() {
      try {
        const nextDocuments = await loadDocsIndex();

        if (!isActive) {
          return;
        }

        setDocuments(nextDocuments);
        setSelectedDocumentId(nextDocuments[0]?.doc_id ?? null);
      } catch (loadError) {
        if (!isActive) {
          return;
        }
        setError(
          loadError instanceof Error ? loadError.message : "无法加载本地文档索引。"
        );
      } finally {
        if (isActive) {
          setIsIndexLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function ensureBundle() {
      if (!selectedDocumentId || bundlesById[selectedDocumentId]) {
        return;
      }

      const selectedDocument = documents.find(
        (document) => document.doc_id === selectedDocumentId
      );
      if (!selectedDocument) {
        return;
      }

      setIsBundleLoading(true);
      setError(null);
      try {
        const bundle = await loadReaderBundle(selectedDocument.reader_bundle_path);

        if (!isActive) {
          return;
        }

        setBundlesById((current) => ({
          ...current,
          [bundle.doc_id]: bundle
        }));
      } catch (loadError) {
        if (!isActive) {
          return;
        }
        setError(
          loadError instanceof Error ? loadError.message : "无法加载阅读数据包。"
        );
      } finally {
        if (isActive) {
          setIsBundleLoading(false);
        }
      }
    }

    void ensureBundle();

    return () => {
      isActive = false;
    };
  }, [bundlesById, documents, selectedDocumentId]);

  const selectedDocument = documents.find(
    (document) => document.doc_id === selectedDocumentId
  );
  const bundle = selectedDocumentId ? bundlesById[selectedDocumentId] ?? null : null;

  useEffect(() => {
    if (!bundle) {
      setSelectedCitationId(null);
      return;
    }

    setSelectedCitationId(null);
  }, [bundle]);

  const citationLookup = useMemo(
    () => buildCitationLookup(bundle?.citations ?? []),
    [bundle?.citations]
  );

  const citation = selectedCitationId
    ? citationLookup[selectedCitationId] ?? null
    : null;

  function handleDocumentSelect(documentId: string) {
    setSelectedDocumentId(documentId);
  }

  const isLoading = isIndexLoading || (selectedDocumentId !== null && isBundleLoading && !bundle);

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

      {error ? <p className="app-status">{error}</p> : null}
      {isLoading ? <p className="app-status">正在加载本地文档包...</p> : null}
      {!isLoading && documents.length === 0 ? (
        <p className="app-status">当前没有可阅读的本地文档包。</p>
      ) : null}

      {!isLoading && selectedDocument && bundle ? (
        <main className={`workspace is-immersive${citation ? " has-drawer" : ""}`}>
          <div className="main-column">
            <DocumentList
              documents={documents}
              selectedDocumentId={selectedDocument.doc_id}
              onSelect={handleDocumentSelect}
            />
            <ReportReader
              title={bundle.report_title}
              sections={bundle.sections}
              selectedCitationId={selectedCitationId}
              citationLookup={citationLookup}
              onCitationSelect={setSelectedCitationId}
            />
          </div>

          {citation ? <CitationDrawer citation={citation} onClose={() => setSelectedCitationId(null)} /> : null}
        </main>
      ) : null}
    </div>
  );
}
