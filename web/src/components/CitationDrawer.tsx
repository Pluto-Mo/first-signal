import { X } from "lucide-react";
import { CitationPanel } from "./CitationPanel";
import { SourceView } from "./SourceView";
import type { ReaderCitation } from "../lib/types";

interface CitationDrawerProps {
  citation: ReaderCitation;
  onClose: () => void;
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  return (
    <aside className="citation-drawer" aria-label="引用抽屉">
      <div className="citation-drawer-header">
        <p className="eyebrow">Citation</p>
        <button
          type="button"
          className="drawer-close-button"
          onClick={onClose}
          aria-label="关闭引用"
        >
          <X size={16} />
          关闭引用
        </button>
      </div>
      <div className="citation-drawer-body">
        <CitationPanel citation={citation} />
        <SourceView citation={citation} />
      </div>
    </aside>
  );
}
