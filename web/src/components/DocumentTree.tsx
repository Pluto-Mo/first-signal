import {
  Bot,
  Building2,
  CalendarDays,
  Car,
  ChevronDown,
  ChevronRight,
  Cpu,
  Folder,
  Pill,
  ShoppingBag,
  Zap
} from "lucide-react";
import { useEffect, useState } from "react";
import { formatDocumentDate } from "../lib/grouping";
import type { DocumentGroup } from "../lib/types";

interface DocumentTreeProps {
  groups: DocumentGroup[];
  selectedDocumentId: string | null;
  onSelect: (documentId: string) => void;
}

const groupIcons = {
  bot: Bot,
  building: Building2,
  calendar: CalendarDays,
  car: Car,
  cpu: Cpu,
  folder: Folder,
  pill: Pill,
  "shopping-bag": ShoppingBag,
  zap: Zap
};

export function DocumentTree({
  groups,
  selectedDocumentId,
  onSelect
}: DocumentTreeProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string> | null>(null);

  useEffect(() => {
    setExpandedGroups(new Set(groups.map((group) => group.id)));
  }, [groups]);

  function toggleGroup(groupId: string) {
    setExpandedGroups((currentGroups) => {
      const nextGroups = new Set(
        currentGroups ?? groups.map((group) => group.id)
      );
      if (nextGroups.has(groupId)) {
        nextGroups.delete(groupId);
      } else {
        nextGroups.add(groupId);
      }
      return nextGroups;
    });
  }

  return (
    <nav className="document-tree" aria-label="招股书文档">
      {groups.map((group) => {
        const activeExpandedGroups =
          expandedGroups ?? new Set(groups.map((currentGroup) => currentGroup.id));
        const isExpanded = activeExpandedGroups.has(group.id);
        const GroupIcon = groupIcons[group.icon as keyof typeof groupIcons] ?? Building2;

        return (
          <section key={group.id} className="tree-group">
            <button
              type="button"
              className="tree-group-header"
              aria-expanded={isExpanded}
              aria-label={`${group.label}，${group.documents.length} 份文档`}
              onClick={() => toggleGroup(group.id)}
            >
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span className="tree-group-icon" aria-hidden="true">
                <GroupIcon size={16} />
              </span>
              <span className="tree-group-label">{group.label}</span>
              <span className="tree-group-count">{group.documents.length}</span>
            </button>

            {isExpanded ? (
              <div className="tree-group-items">
                {group.documents.map((document) => {
                  const isSelected = document.doc_id === selectedDocumentId;

                  return (
                    <button
                      key={document.doc_id}
                      type="button"
                      className={`tree-item${isSelected ? " is-selected" : ""}`}
                      aria-current={isSelected ? "page" : undefined}
                      onClick={() => onSelect(document.doc_id)}
                    >
                      <span className="tree-item-name">{document.company_name}</span>
                      <span className="tree-item-date">{formatDocumentDate(document)}</span>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </section>
        );
      })}
    </nav>
  );
}
