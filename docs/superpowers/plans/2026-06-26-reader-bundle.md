# Reader Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real document-package powered reader flow so the web reader loads `data/docs/index.json` and per-document `reader_bundle.json` instead of hard-coded demo samples.

**Architecture:** Keep the existing pipeline output contract as the source of truth. Add a backend reader-bundle builder that converts `report.md` citations plus document metadata into a frontend-ready JSON file, then switch the React app to fetch the docs index and bundle files asynchronously while preserving the current reading layout.

**Tech Stack:** Python, Pydantic, pytest, React, TypeScript, Vite, Vitest

---

### Task 1: Backend Reader Bundle Contract

**Files:**
- Create: `src/ipo_evidence/reader_bundle.py`
- Modify: `src/ipo_evidence/models.py`
- Test: `tests/test_reader_bundle.py`

- [x] **Step 1: Write the failing backend contract test**

```python
def test_build_reader_bundle_maps_report_and_citations():
    ...
    bundle = build_reader_bundle(...)
    assert bundle["report_title"] == "测试股份有限公司招股书长篇阅读"
    assert bundle["sections"][0]["blocks"][0]["citation_ids"] == ["C-001"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reader_bundle.py -v`
Expected: FAIL because `build_reader_bundle` does not exist yet.

- [x] **Step 3: Implement minimal reader bundle models and builder**

```python
class ReaderBundle(BaseModel):
    doc_id: str
    company_name: str
    report_title: str
    ...

def build_reader_bundle(...):
    return ReaderBundle(...)
```

- [x] **Step 4: Run backend bundle tests**

Run: `pytest tests/test_reader_bundle.py -v`
Expected: PASS

### Task 2: Pipeline and Docs Index Wiring

**Files:**
- Modify: `src/ipo_evidence/pipeline.py`
- Modify: `src/ipo_evidence/web_index.py`
- Modify: `tests/test_pipeline.py`

- [x] **Step 1: Write the failing pipeline expectations**

```python
assert (package / "reader_bundle.json").exists()
assert docs_index[0]["reader_bundle_path"] == f"{doc_id}/reader_bundle.json"
```

- [x] **Step 2: Run pipeline tests to verify they fail**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL because the pipeline does not write `reader_bundle.json`.

- [x] **Step 3: Add reader bundle writing to report artifact generation**

```python
reader_bundle = build_reader_bundle(...)
write_json(package_dir / "reader_bundle.json", reader_bundle)
```

- [x] **Step 4: Refresh docs index with bundle path metadata**

```python
class WebIndex(BaseModel):
    reader_bundle_path: str = "reader_bundle.json"
```

- [x] **Step 5: Re-run focused pipeline tests**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS

### Task 3: Frontend Real Data Loading

**Files:**
- Modify: `web/src/App.tsx`
- Create: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/components/DocumentList.tsx`
- Modify: `web/src/components/SourceView.tsx`
- Test: `web/src/__tests__/reader.test.tsx`

- [x] **Step 1: Write the failing frontend async loading test**

```tsx
vi.stubGlobal("fetch", ...)
render(<App />)
await screen.findByText("测试股份有限公司")
expect(screen.getByText("引用 C-001")).toBeInTheDocument()
```

- [x] **Step 2: Run the reader test to verify it fails**

Run: `npm run test -- src/__tests__/reader.test.tsx`
Expected: FAIL because the app still reads hard-coded `documents`.

- [x] **Step 3: Implement docs-index and reader-bundle fetch helpers**

```ts
export async function loadDocsIndex(): Promise<DocsIndexItem[]> { ... }
export async function loadReaderBundle(docId: string): Promise<ReaderBundle> { ... }
```

- [x] **Step 4: Switch the app to async loading with loading and error states**

```tsx
useEffect(() => {
  void loadDocsIndex().then(...)
}, [])
```

- [x] **Step 5: Update document list metadata and source-path rendering**

```tsx
{document.parse_status} · {document.quality_status}
{citation.location.section_path.join(" / ")}
```

- [x] **Step 6: Re-run the focused frontend test**

Run: `npm run test -- src/__tests__/reader.test.tsx`
Expected: PASS

### Task 4: End-to-End Verification

**Files:**
- No code changes expected

- [x] **Step 1: Run backend verification**

Run: `pytest tests/test_reader_bundle.py tests/test_pipeline.py -v`
Expected: PASS

- [x] **Step 2: Run frontend verification**

Run: `npm run test`
Expected: PASS

- [x] **Step 3: Run production build verification**

## Completion Notes

- 已接入 `reader_bundle.json` 产物，前端从 `/index.json` 和每个文档包的 bundle 异步加载数据。
- 阅读器已脱离硬编码 demo，改为真实文档包驱动。
- 前后端验证已完成，最终以 `pytest`、`npm run test` 和 `npm run build` 为准。

Run: `npm run build`
Expected: PASS
