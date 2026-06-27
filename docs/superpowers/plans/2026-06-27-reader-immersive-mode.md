# Reader Immersive Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current section-switched reader into a continuous long-form reading experience with an on-demand citation drawer.

**Architecture:** Keep the existing bundle-loading flow and data contract. Replace the report-reader tab interaction with a single continuous article renderer, move citation details into a closable side drawer controlled by the app shell, and tighten the citation chip visual scale so the正文 stays dominant.

**Tech Stack:** React, TypeScript, Vite, Vitest, CSS

---

### Task 1: Lock The New Reading Behavior In Tests

**Files:**
- Modify: `web/src/__tests__/reader.test.tsx`
- Test: `web/src/__tests__/reader.test.tsx`

- [x] **Step 1: Write the failing immersive-reader expectations**

```tsx
expect(screen.queryByRole("tab", { name: "一、业务概况" })).not.toBeInTheDocument();
expect(screen.queryByText("引用 C-001")).not.toBeInTheDocument();
await user.click(screen.getByRole("button", { name: /查看引用 C-002/ }));
expect(screen.getByText("引用 C-002")).toBeInTheDocument();
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/__tests__/reader.test.tsx`
Expected: FAIL because the UI still renders section tabs and a permanent citation panel.

### Task 2: Render One Continuous Article

**Files:**
- Modify: `web/src/components/ReportReader.tsx`
- Modify: `web/src/App.tsx`

- [x] **Step 1: Remove section-tab interaction from the reader**

```tsx
{sections.map((section) => (
  <section key={section.id}>
    <h3>{section.title}</h3>
    ...
  </section>
))}
```

- [x] **Step 2: Simplify app state so citation selection no longer depends on selected section**

```tsx
const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
```

- [x] **Step 3: Re-run focused test**

Run: `npm run test -- src/__tests__/reader.test.tsx`
Expected: still FAIL on drawer behavior until Task 3 is done.

### Task 3: Add Citation Drawer Behavior

**Files:**
- Modify: `web/src/App.tsx`
- Create or Modify: `web/src/components/CitationDrawer.tsx` or existing side panel components
- Modify: `web/src/components/CitationPanel.tsx`
- Modify: `web/src/components/SourceView.tsx`

- [x] **Step 1: Render citation details only when a citation is selected**

```tsx
{citation ? (
  <aside className="citation-drawer">...</aside>
) : null}
```

- [x] **Step 2: Add close action**

```tsx
<button type="button" onClick={() => setSelectedCitationId(null)}>关闭引用</button>
```

- [x] **Step 3: Re-run focused test**

Run: `npm run test -- src/__tests__/reader.test.tsx`
Expected: PASS

### Task 4: Polish Layout And Chip Size

**Files:**
- Modify: `web/src/styles.css`
- Modify: `web/src/components/DocumentList.tsx`

- [x] **Step 1: Expand the article layout and weaken the document list visually**

```css
.workspace.is-immersive { ... }
.document-list { ... }
```

- [x] **Step 2: Shrink citation chips and style the drawer**

```css
.citation-chip { font-size: 12px; padding: 2px 8px; }
.citation-drawer { ... }
```

- [x] **Step 3: Run full frontend verification**

Run: `npm run test`
Expected: PASS

- [x] **Step 4: Run production build verification**

## Completion Notes

- 阅读器已切换到整篇连续长文模式，不再通过 section tab 切换阅读。
- citation 默认收起，点击句尾引用标签后，通过右侧抽屉展示引用摘要与来源定位。
- citation 标签已缩小，并修复了来源字段为空时显示 `null` 的问题。
- 最终验证覆盖了阅读器测试、前端整包测试、生产构建，以及浏览器内实际点开引用抽屉的检查。

Run: `npm run build`
Expected: PASS
