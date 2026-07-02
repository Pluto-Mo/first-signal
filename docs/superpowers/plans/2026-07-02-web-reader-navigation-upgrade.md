# Web Reader Navigation Upgrade - Phase 4

> **Status:** Ready for execution (Phase 3 completed successfully)
>
> **Goal:** 升级 Web 阅读器的左侧导航，从横向文档列表改为树形目录结构，支持时间分类和行业分类，方便管理大量招股书。

**Current State:**
- ✅ 报告质量高（4,791 字，结构化研报）
- ✅ Web 阅读器基本功能完整（React + TypeScript）
- ✅ Citation 抽屉交互良好

**Current Problems:**
- ❌ 左侧是横向文档列表，文档多了不好找
- ❌ 没有分类（时间、行业）
- ❌ 标题"A股招股书证据阅读台"不够简洁
- ❌ 有冗余的说明文字

**Phase 4 Goals:**
- ✅ 左侧改为树形目录（时间分类 + 行业分类）
- ✅ 支持 Tab 切换（按时间 / 按行业）
- ✅ 改标题为"IPO 招股书研报"
- ✅ 删除冗余文案

**Tech Stack:** React 18 + TypeScript + Vite

---

## 1. Design

### 1.1 新的左侧导航结构

**按时间分类（默认）：**
```
┌─────────────────────────┐
│ [按时间] 按行业          │ ← Tab 切换
├─────────────────────────┤
│ 📅 最近三天 (2)          │
│   ├─ 思必驰科技          │
│   │   2026-07-02         │
│   └─ 另一家公司          │
│       2026-07-01         │
├─────────────────────────┤
│ 📅 本周 (5)              │
│   ├─ ...                │
├─────────────────────────┤
│ 📅 更早 (10)             │
│   └─ ...                │
└─────────────────────────┘
```

**按行业分类：**
```
┌─────────────────────────┐
│ 按时间 [按行业]          │ ← Tab 切换
├─────────────────────────┤
│ 🏢 人工智能 (3)          │
│   ├─ 思必驰科技          │
│   ├─ 商汤科技            │
│   └─ 云从科技            │
├─────────────────────────┤
│ 🏢 半导体 (5)            │
│   ├─ ...                │
├─────────────────────────┤
│ 🏢 新能源 (8)            │
│   └─ ...                │
└─────────────────────────┘
```

### 1.2 时间分类逻辑

```typescript
function classifyByTime(documents: DocsIndexItem[]): TimeGroup[] {
  const now = Date.now();
  const threeDaysAgo = now - 3 * 24 * 60 * 60 * 1000;
  const oneWeekAgo = now - 7 * 24 * 60 * 60 * 1000;

  return [
    {
      id: 'recent-3-days',
      label: '最近三天',
      icon: '📅',
      documents: documents.filter(d => d.created_at > threeDaysAgo)
    },
    {
      id: 'this-week',
      label: '本周',
      icon: '📅',
      documents: documents.filter(d => d.created_at > oneWeekAgo && d.created_at <= threeDaysAgo)
    },
    {
      id: 'older',
      label: '更早',
      icon: '📅',
      documents: documents.filter(d => d.created_at <= oneWeekAgo)
    }
  ];
}
```

### 1.3 行业分类逻辑

**需要在 `docs_index.json` 中添加 `industry` 字段：**
```json
{
  "documents": [
    {
      "doc_id": "doc_beaac21be4b3",
      "company_name": "思必驰科技股份有限公司",
      "industry": "人工智能",  // 新增
      "created_at": 1719936000000,
      "reader_bundle_path": "data/docs/doc_beaac21be4b3/reader_bundle.json"
    }
  ]
}
```

**分类逻辑：**
```typescript
function classifyByIndustry(documents: DocsIndexItem[]): IndustryGroup[] {
  const industryMap = new Map<string, DocsIndexItem[]>();

  documents.forEach(doc => {
    const industry = doc.industry || '未分类';
    if (!industryMap.has(industry)) {
      industryMap.set(industry, []);
    }
    industryMap.get(industry)!.push(doc);
  });

  return Array.from(industryMap.entries()).map(([industry, docs]) => ({
    id: `industry-${industry}`,
    label: industry,
    icon: getIndustryIcon(industry),
    documents: docs
  }));
}

function getIndustryIcon(industry: string): string {
  const iconMap: Record<string, string> = {
    '人工智能': '🤖',
    '半导体': '💾',
    '新能源': '⚡',
    '医药': '💊',
    '汽车': '🚗',
    '未分类': '📁'
  };
  return iconMap[industry] || '🏢';
}
```
---

## 2. Implementation Plan

### Step 1: Update Data Types

修改 `web/src/lib/types.ts`：

```typescript
export interface DocsIndexItem {
  doc_id: string;
  company_name: string;
  industry?: string;  // 新增：行业分类
  created_at: number;  // 时间戳（毫秒）
  reader_bundle_path: string;
}

export interface DocumentGroup {
  id: string;
  label: string;
  icon: string;
  documents: DocsIndexItem[];
}

export type GroupingMode = 'time' | 'industry';
```

### Step 2: Create New Components

**创建 `web/src/components/DocumentTree.tsx`：**

```typescript
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { DocumentGroup, DocsIndexItem } from '../lib/types';

interface DocumentTreeProps {
  groups: DocumentGroup[];
  selectedDocumentId: string | null;
  onSelect: (documentId: string) => void;
}

export function DocumentTree({ groups, selectedDocumentId, onSelect }: DocumentTreeProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(groups.map(g => g.id))
  );

  function toggleGroup(groupId: string) {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }

  return (
    <div className="document-tree">
      {groups.map(group => (
        <div key={group.id} className="tree-group">
          <button
            className="tree-group-header"
            onClick={() => toggleGroup(group.id)}
          >
            {expandedGroups.has(group.id) ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
            <span className="tree-group-icon">{group.icon}</span>
            <span className="tree-group-label">{group.label}</span>
            <span className="tree-group-count">({group.documents.length})</span>
          </button>

          {expandedGroups.has(group.id) && (
            <div className="tree-group-items">
              {group.documents.map(doc => (
                <button
                  key={doc.doc_id}
                  className={`tree-item${doc.doc_id === selectedDocumentId ? ' is-selected' : ''}`}
                  onClick={() => onSelect(doc.doc_id)}
                >
                  <div className="tree-item-name">{doc.company_name}</div>
                  <div className="tree-item-date">
                    {formatDate(doc.created_at)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}
```

**创建 `web/src/components/GroupingTabs.tsx`：**

```typescript
import type { GroupingMode } from '../lib/types';

interface GroupingTabsProps {
  mode: GroupingMode;
  onModeChange: (mode: GroupingMode) => void;
}

export function GroupingTabs({ mode, onModeChange }: GroupingTabsProps) {
  return (
    <div className="grouping-tabs">
      <button
        className={`grouping-tab${mode === 'time' ? ' is-active' : ''}`}
        onClick={() => onModeChange('time')}
      >
        按时间
      </button>
      <button
        className={`grouping-tab${mode === 'industry' ? ' is-active' : ''}`}
        onClick={() => onModeChange('industry')}
      >
        按行业
      </button>
    </div>
  );
}
```

### Step 3: Create Grouping Utilities

创建 `web/src/lib/grouping.ts`：

```typescript
import type { DocumentGroup, DocsIndexItem } from './types';

export function groupByTime(documents: DocsIndexItem[]): DocumentGroup[] {
  const now = Date.now();
  const threeDaysAgo = now - 3 * 24 * 60 * 60 * 1000;
  const oneWeekAgo = now - 7 * 24 * 60 * 60 * 1000;

  const recentDocs = documents.filter(d => d.created_at > threeDaysAgo);
  const thisWeekDocs = documents.filter(
    d => d.created_at > oneWeekAgo && d.created_at <= threeDaysAgo
  );
  const olderDocs = documents.filter(d => d.created_at <= oneWeekAgo);

  const groups: DocumentGroup[] = [];

  if (recentDocs.length > 0) {
    groups.push({
      id: 'recent-3-days',
      label: '最近三天',
      icon: '📅',
      documents: recentDocs.sort((a, b) => b.created_at - a.created_at)
    });
  }

  if (thisWeekDocs.length > 0) {
    groups.push({
      id: 'this-week',
      label: '本周',
      icon: '📅',
      documents: thisWeekDocs.sort((a, b) => b.created_at - a.created_at)
    });
  }

  if (olderDocs.length > 0) {
    groups.push({
      id: 'older',
      label: '更早',
      icon: '📅',
      documents: olderDocs.sort((a, b) => b.created_at - a.created_at)
    });
  }

  return groups;
}

export function groupByIndustry(documents: DocsIndexItem[]): DocumentGroup[] {
  const industryMap = new Map<string, DocsIndexItem[]>();

  documents.forEach(doc => {
    const industry = doc.industry || '未分类';
    if (!industryMap.has(industry)) {
      industryMap.set(industry, []);
    }
    industryMap.get(industry)!.push(doc);
  });

  return Array.from(industryMap.entries())
    .map(([industry, docs]) => ({
      id: `industry-${industry}`,
      label: industry,
      icon: getIndustryIcon(industry),
      documents: docs.sort((a, b) => b.created_at - a.created_at)
    }))
    .sort((a, b) => b.documents.length - a.documents.length);
}

function getIndustryIcon(industry: string): string {
  const iconMap: Record<string, string> = {
    '人工智能': '🤖',
    '半导体': '💾',
    '新能源': '⚡',
    '医药': '💊',
    '汽车': '🚗',
    '生物科技': '🧬',
    '消费': '🛒',
    '金融': '💰',
    '未分类': '📁'
  };
  return iconMap[industry] || '🏢';
}
```

### Step 4: Update App.tsx

修改 `web/src/App.tsx`：

```typescript
import { useMemo, useState } from "react";
import { CitationDrawer } from "./components/CitationDrawer";
import { DocumentTree } from "./components/DocumentTree";
import { GroupingTabs } from "./components/GroupingTabs";
import { ReportReader } from "./components/ReportReader";
import { loadDocsIndex, loadReaderBundle } from "./lib/api";
import { groupByIndustry, groupByTime } from "./lib/grouping";
import type { DocsIndexItem, GroupingMode, ReaderBundle, ReaderCitation } from "./lib/types";

// ... (保留原有的 buildCitationLookup 和 useEffect 逻辑)

export default function App() {
  const [documents, setDocuments] = useState<DocsIndexItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [bundlesById, setBundlesById] = useState<Record<string, ReaderBundle>>({});
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [groupingMode, setGroupingMode] = useState<GroupingMode>('time');  // 新增
  const [isIndexLoading, setIsIndexLoading] = useState(true);
  const [isBundleLoading, setIsBundleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ... (保留原有的 useEffect 逻辑)

  // 新增：根据 groupingMode 生成分组
  const documentGroups = useMemo(() => {
    if (groupingMode === 'time') {
      return groupByTime(documents);
    } else {
      return groupByIndustry(documents);
    }
  }, [documents, groupingMode]);

  const selectedDocument = documents.find(
    (document) => document.doc_id === selectedDocumentId
  );
  const bundle = selectedDocumentId ? bundlesById[selectedDocumentId] ?? null : null;

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
        <h1>IPO 招股书研报</h1>  {/* 修改标题 */}
      </header>

      {error ? <p className="app-status">{error}</p> : null}
      {isLoading ? <p className="app-status">正在加载本地文档包...</p> : null}
      {!isLoading && documents.length === 0 ? (
        <p className="app-status">当前没有可阅读的本地文档包。</p>
      ) : null}

      {!isLoading && documents.length > 0 ? (
        <main className={`workspace is-immersive${citation ? " has-drawer" : ""}`}>
          <div className="sidebar">  {/* 修改：从 main-column 改为 sidebar */}
            <GroupingTabs mode={groupingMode} onModeChange={setGroupingMode} />
            <DocumentTree
              groups={documentGroups}
              selectedDocumentId={selectedDocumentId}
              onSelect={handleDocumentSelect}
            />
          </div>

          {selectedDocument && bundle ? (
            <div className="main-column">
              <ReportReader
                title={bundle.report_title}
                sections={bundle.sections}
                selectedCitationId={selectedCitationId}
                citationLookup={citationLookup}
                onCitationSelect={setSelectedCitationId}
              />
            </div>
          ) : null}

          {citation ? (
            <CitationDrawer citation={citation} onClose={() => setSelectedCitationId(null)} />
          ) : null}
        </main>
      ) : null}
    </div>
  );
}
```
