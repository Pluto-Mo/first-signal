# IPO Evidence MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local A-share prospectus evidence loop that scans `data/inbox/*.pdf`, creates document packages, generates evidence-backed reports, and serves them in a clean local reader.

**Architecture:** Use a Python file-based pipeline for ingest, parsing, section mapping, table extraction, evidence packet construction, report/citation generation, and web index creation. Use a Vite React reader that consumes generated JSON/Markdown files through a small local API layer or static fixtures during MVP development.

**Tech Stack:** Python 3.11+, pytest, pydantic, PyYAML, python-dotenv, Vite React, TypeScript, Vitest, React Testing Library.

---

## Scope Check

This plan implements the confirmed first-stage vertical slice from the design document:

```text
local PDF folder -> doc package -> parser interface -> AST -> tables -> evidence packet -> report/citation -> web reader
```

It intentionally does not implement automatic official-source discovery, PDF downloading, Hong Kong listing documents, graph extraction, database storage, authentication, deployment, or public publishing.

## File Structure

### Root

- Create: `pyproject.toml` — Python package metadata, runtime dependencies, pytest config.
- Create: `package.json` — root commands delegating to `web/`.
- Create: `README.md` — local setup, pipeline commands, Web commands.
- Modify: `.gitignore` — keep generated/local data out of git while preserving directory placeholders.

### Configs

- Create: `configs/parser.yaml` — parser provider selection and output rules.
- Create: `configs/section_mapper.yaml` — A-share source section to canonical section mapping.
- Create: `configs/scoring_rules.yaml` — quality thresholds for parse, section, table, and citation checks.

### Data Placeholders

- Create: `data/inbox/.gitkeep` — user-owned local PDFs live here and are not committed.
- Create: `data/docs/.gitkeep` — generated document packages live here and are not committed.
- Create: `data/tmp/.gitkeep` — temporary parser artifacts live here and are not committed.
- Create: `runs/logs/.gitkeep` — run logs live here and are not committed.
- Create: `runs/evals/.gitkeep` — evaluation artifacts live here and are not committed.

### Python Pipeline

- Create: `src/ipo_evidence/__init__.py` — package marker and version.
- Create: `src/ipo_evidence/models.py` — pydantic models for manifest, blocks, AST nodes, tables, evidence, citations, reports, and web index.
- Create: `src/ipo_evidence/paths.py` — repository-relative path helpers.
- Create: `src/ipo_evidence/io.py` — JSON, JSONL, Markdown, and CSV read/write helpers.
- Create: `src/ipo_evidence/config.py` — YAML config loader.
- Create: `src/ipo_evidence/ingest.py` — scan inbox and create doc packages.
- Create: `src/ipo_evidence/parser/base.py` — parser protocol and normalized parser output.
- Create: `src/ipo_evidence/parser/api_stub.py` — deterministic local API-shaped parser stub for tests and offline development.
- Create: `src/ipo_evidence/section_mapper.py` — source AST detection and canonical mapping.
- Create: `src/ipo_evidence/table_extractor.py` — normalized table extraction from parser output.
- Create: `src/ipo_evidence/evidence.py` — evidence packet builder.
- Create: `src/ipo_evidence/report_generator.py` — deterministic MVP report generator from evidence packet.
- Create: `src/ipo_evidence/citation_layer.py` — citation collection and report citation validation.
- Create: `src/ipo_evidence/web_index.py` — `web_index.json` generation.
- Create: `src/ipo_evidence/pipeline.py` — orchestrates one or more docs.
- Create: `src/ipo_evidence/cli.py` — command-line entrypoints.

### Python Tests

- Create: `tests/fixtures/sample_prospectus.txt` — parser-stub source text representing a small A-share prospectus.
- Create: `tests/test_models.py`
- Create: `tests/test_ingest.py`
- Create: `tests/test_section_mapper.py`
- Create: `tests/test_table_extractor.py`
- Create: `tests/test_evidence.py`
- Create: `tests/test_report_and_citation.py`
- Create: `tests/test_pipeline.py`

### Web

- Create: `web/package.json` — Vite React scripts and dependencies.
- Create: `web/index.html`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/data.ts`
- Create: `web/src/components/DocumentList.tsx`
- Create: `web/src/components/ReportReader.tsx`
- Create: `web/src/components/CitationPanel.tsx`
- Create: `web/src/components/SourceView.tsx`
- Create: `web/src/styles.css`
- Create: `web/src/__tests__/reader.test.tsx`

---

## Task 1: Project Scaffolding And Config

**Files:**
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `README.md`
- Modify: `.gitignore`
- Create: `configs/parser.yaml`
- Create: `configs/section_mapper.yaml`
- Create: `configs/scoring_rules.yaml`
- Create: `data/inbox/.gitkeep`
- Create: `data/docs/.gitkeep`
- Create: `data/tmp/.gitkeep`
- Create: `runs/logs/.gitkeep`
- Create: `runs/evals/.gitkeep`

- [ ] **Step 1: Write project metadata**

Create `pyproject.toml` with this content:

```toml
[project]
name = "ipo-evidence-intelligence"
version = "0.1.0"
description = "Local A-share prospectus evidence loop"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7",
  "PyYAML>=6.0",
  "python-dotenv>=1.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-cov>=5.0",
  "ruff>=0.5"
]

[project.scripts]
ipo-evidence = "ipo_evidence.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Write root package commands**

Create `package.json` with this content:

```json
{
  "scripts": {
    "web:dev": "npm --prefix web run dev",
    "web:build": "npm --prefix web run build",
    "web:test": "npm --prefix web run test"
  }
}
```

- [ ] **Step 3: Write setup documentation**

Create `README.md` with this content:

~~~~markdown
# IPO Evidence Intelligence

Personal A-share prospectus evidence reader.

## First-stage scope

The MVP reads local PDFs from `data/inbox/`, creates long-term document packages under `data/docs/`, generates evidence-backed reports, and serves them in a local Web reader.

## Local pipeline

```powershell
python -m pip install -e ".[dev]"
python -m ipo_evidence.cli scan-inbox
python -m ipo_evidence.cli run --limit 3
python -m ipo_evidence.cli generate-report --doc-id <doc_id>
```

## Web reader

```powershell
npm install --prefix web
npm run web:dev
npm run web:build
```

## Data policy

`data/inbox/` contains user-owned PDF inputs. The system must not delete files in that directory.
Generated document packages under `data/docs/` are local artifacts and are not committed.
```
~~~~

- [ ] **Step 4: Update `.gitignore` to keep placeholders**

Modify `.gitignore` so these generated directories remain ignored but `.gitkeep` files can be committed:

```gitignore
data/inbox/*
!data/inbox/.gitkeep
data/tmp/*
!data/tmp/.gitkeep
data/docs/*
!data/docs/.gitkeep
runs/logs/*
!runs/logs/.gitkeep
runs/evals/*
!runs/evals/.gitkeep
```

- [ ] **Step 5: Create config files**

Create `configs/parser.yaml`:

```yaml
provider: api_stub
input_type: local_pdf
preserve_source_pdf: true
outputs:
  markdown: document.md
  blocks: blocks.jsonl
  raw_tables: raw_tables.json
  parse_report: parse_report.json
```

Create `configs/section_mapper.yaml`:

```yaml
canonical_sections:
  about_company:
    title: 关于公司
    source_patterns:
      - 发行人基本情况
      - 发行人概况
  business_and_product:
    title: 业务与产品
    source_patterns:
      - 业务和技术
      - 主营业务
  customers_and_suppliers:
    title: 客户与供应商
    source_patterns:
      - 主要客户
      - 主要供应商
  r_and_d_and_talent:
    title: 研发与人才
    source_patterns:
      - 研发
      - 核心技术人员
  financials:
    title: 财务与经营数据
    source_patterns:
      - 财务会计信息
      - 管理层讨论与分析
  use_of_proceeds:
    title: 募集资金用途
    source_patterns:
      - 募集资金运用
      - 募集资金用途
  risks:
    title: 风险因素
    source_patterns:
      - 风险因素
```

Create `configs/scoring_rules.yaml`:

```yaml
parse_quality:
  max_garbled_ratio: 0.05
  min_non_empty_pages: 3
section_quality:
  min_required_major_sections: 3
table_quality:
  min_quality_score_for_evidence: 0.75
citation_quality:
  required_fields:
    - source_file
    - page_number
    - section_path
```

- [ ] **Step 6: Create data placeholders**

Create empty placeholder files:

```text
data/inbox/.gitkeep
data/docs/.gitkeep
data/tmp/.gitkeep
runs/logs/.gitkeep
runs/evals/.gitkeep
```

- [ ] **Step 7: Verify scaffolding**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
git status --short
```

Expected:

```text
no tests ran
```

and `git status --short` shows the new scaffolding files.

- [ ] **Step 8: Commit**

```powershell
git add pyproject.toml package.json README.md .gitignore configs data runs
git commit -m "chore: scaffold project configuration"
```

---

## Task 2: Domain Models And File IO

**Files:**
- Create: `src/ipo_evidence/__init__.py`
- Create: `src/ipo_evidence/models.py`
- Create: `src/ipo_evidence/paths.py`
- Create: `src/ipo_evidence/io.py`
- Create: `src/ipo_evidence/config.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/test_models.py`:

```python
from ipo_evidence.models import Citation, Manifest, QualityStatus


def test_manifest_defaults_to_local_pdf_input():
    manifest = Manifest(
        doc_id="doc_abc123",
        company_name="测试股份有限公司",
        source_file="测试股份有限公司招股说明书.pdf",
    )

    assert manifest.input_type == "local_pdf"
    assert manifest.market == "a_share"
    assert manifest.quality_status == QualityStatus.manual_review


def test_citation_requires_local_locator_when_url_is_missing():
    citation = Citation(
        citation_id="C-001",
        type="text_quote",
        source_file="测试股份有限公司招股说明书.pdf",
        source_url=None,
        page_number=18,
        block_id="B-000018",
        section_path=["发行人基本情况", "主营业务"],
        quote="公司主要从事智能硬件产品的研发、生产和销售。",
        summary="公司主营业务为智能硬件。",
    )

    assert citation.source_url is None
    assert citation.page_number == 18
    assert citation.block_id == "B-000018"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ipo_evidence'`.

- [ ] **Step 3: Create package marker**

Create `src/ipo_evidence/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Implement domain models**

Create `src/ipo_evidence/models.py`:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class QualityStatus(StrEnum):
    safe_to_use = "safe_to_use"
    manual_review = "manual_review"
    do_not_use = "do_not_use"


class Manifest(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    source_url: str | None = None
    market: Literal["a_share"] = "a_share"
    document_type: str = "招股说明书"
    input_type: Literal["local_pdf"] = "local_pdf"
    parse_status: str = "discovered"
    report_status: str = "not_started"
    quality_status: QualityStatus = QualityStatus.manual_review
    tags: list[str] = Field(default_factory=list)


class Block(BaseModel):
    block_id: str
    page_number: int
    text: str
    section_path: list[str] = Field(default_factory=list)


class AstNode(BaseModel):
    title: str
    level: int
    section_path: list[str]
    block_ids: list[str] = Field(default_factory=list)
    children: list["AstNode"] = Field(default_factory=list)


class TableObject(BaseModel):
    table_id: str
    title: str
    source_file: str
    page_number: int
    section_path: list[str]
    columns: list[str]
    rows: list[list[str]]
    notes: list[str] = Field(default_factory=list)
    quality_score: float = 0.0


class EvidenceItem(BaseModel):
    evidence_id: str
    canonical_section: str
    claim_summary: str
    source_type: Literal["text_quote", "table_fact"]
    source_file: str
    page_number: int
    block_id: str | None = None
    table_id: str | None = None
    section_path: list[str]
    quote: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    quality_status: QualityStatus = QualityStatus.manual_review


class EvidencePacket(BaseModel):
    doc_id: str
    items: list[EvidenceItem]


class Citation(BaseModel):
    citation_id: str
    type: Literal["text_quote", "table_fact"]
    source_file: str
    source_url: str | None = None
    page_number: int
    block_id: str | None = None
    table_id: str | None = None
    section_path: list[str]
    quote: str | None = None
    table_title: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    summary: str


class WebIndex(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    quality_status: QualityStatus
    parse_status: str
    report_status: str
    tags: list[str] = Field(default_factory=list)
    report_path: str = "report.md"
    citation_path: str = "citation.json"


JsonDict = dict[str, Any]
```

- [ ] **Step 5: Implement path helpers**

Create `src/ipo_evidence/paths.py`:

```python
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return repo_root() / "data"


def inbox_dir() -> Path:
    return data_dir() / "inbox"


def docs_dir() -> Path:
    return data_dir() / "docs"


def doc_dir(doc_id: str) -> Path:
    return docs_dir() / doc_id
```

- [ ] **Step 6: Implement IO helpers**

Create `src/ipo_evidence/io.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, value: BaseModel | dict | list) -> None:
    ensure_dir(path.parent)
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    else:
        payload = value
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[BaseModel | dict]) -> None:
    ensure_dir(path.parent)
    lines: list[str] = []
    for row in rows:
        payload = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
        lines.append(json.dumps(payload, ensure_ascii=False))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
```

- [ ] **Step 7: Implement config loader**

Create `src/ipo_evidence/config.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

from ipo_evidence.paths import repo_root


def load_yaml(relative_path: str) -> dict:
    path = repo_root() / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
```

- [ ] **Step 8: Run model tests**

Run:

```powershell
python -m pytest tests/test_models.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 9: Commit**

```powershell
git add src/ipo_evidence tests/test_models.py
git commit -m "feat: add domain models and IO helpers"
```

---

## Task 3: Inbox Ingest And Document Package Creation

**Files:**
- Create: `src/ipo_evidence/ingest.py`
- Create: `tests/test_ingest.py`

- [ ] **Step 1: Write ingest tests**

Create `tests/test_ingest.py`:

```python
from pathlib import Path

from ipo_evidence.ingest import scan_inbox


def test_scan_inbox_creates_manifest_for_pdf(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "测试股份有限公司招股说明书.pdf").write_bytes(b"%PDF-1.4\nsample")

    created = scan_inbox(inbox, docs)

    assert len(created) == 1
    manifest_path = docs / created[0].doc_id / "manifest.json"
    assert manifest_path.exists()
    assert created[0].company_name == "测试股份有限公司"
    assert created[0].source_file == "测试股份有限公司招股说明书.pdf"


def test_scan_inbox_is_idempotent(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    (inbox / "测试股份有限公司招股说明书.pdf").write_bytes(b"%PDF-1.4\nsample")

    first = scan_inbox(inbox, docs)
    second = scan_inbox(inbox, docs)

    assert [doc.doc_id for doc in first] == [doc.doc_id for doc in second]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_ingest.py -q
```

Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'scan_inbox'`.

- [ ] **Step 3: Implement ingest**

Create `src/ipo_evidence/ingest.py`:

```python
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ipo_evidence.io import write_json
from ipo_evidence.models import Manifest


def doc_id_for_file(path: Path) -> str:
    digest = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


def company_name_from_filename(path: Path) -> str:
    stem = path.stem
    match = re.search(r"(.+?)(?:招股说明书|首次公开发行|招股书)", stem)
    if match:
        return match.group(1).strip(" _-")
    return "unknown_company"


def scan_inbox(inbox: Path, docs: Path) -> list[Manifest]:
    manifests: list[Manifest] = []
    docs.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(inbox.glob("*.pdf")):
        manifest = Manifest(
            doc_id=doc_id_for_file(pdf_path),
            company_name=company_name_from_filename(pdf_path),
            source_file=pdf_path.name,
        )
        package_dir = docs / manifest.doc_id
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = package_dir / "manifest.json"
        if not manifest_path.exists():
            write_json(manifest_path, manifest)
        manifests.append(manifest)

    return manifests
```

- [ ] **Step 4: Run ingest tests**

Run:

```powershell
python -m pytest tests/test_ingest.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git add src/ipo_evidence/ingest.py tests/test_ingest.py
git commit -m "feat: scan local PDF inbox"
```

---

## Task 4: Parser Interface And Deterministic API Stub

**Files:**
- Create: `src/ipo_evidence/parser/__init__.py`
- Create: `src/ipo_evidence/parser/base.py`
- Create: `src/ipo_evidence/parser/api_stub.py`
- Create: `tests/fixtures/sample_prospectus.txt`
- Create: `tests/test_parser_stub.py`

- [ ] **Step 1: Write parser fixture**

Create `tests/fixtures/sample_prospectus.txt`:

```text
# 测试股份有限公司招股说明书

## 第一节 发行人基本情况
公司主要从事智能硬件产品的研发、生产和销售。

## 第二节 业务和技术
公司的主要产品包括智能控制器和消费级智能终端。

| 产品 | 2023年收入 | 占比 |
| --- | ---: | ---: |
| 智能控制器 | 12000万元 | 45.2% |
| 智能终端 | 9800万元 | 36.9% |

## 第三节 财务会计信息
报告期内公司营业收入持续增长。

## 第四节 募集资金运用
募集资金拟用于智能制造基地建设项目。

## 第五节 风险因素
公司存在客户集中度较高的风险。
```

- [ ] **Step 2: Write parser tests**

Create `tests/test_parser_stub.py`:

```python
from pathlib import Path

from ipo_evidence.parser.api_stub import ApiStubParser


def test_api_stub_parser_creates_normalized_output(tmp_path: Path):
    source = Path("tests/fixtures/sample_prospectus.txt")
    pdf = tmp_path / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")

    output = ApiStubParser(fixture_path=source).parse(pdf)

    assert output.markdown.startswith("# 测试股份有限公司招股说明书")
    assert output.blocks[0].block_id == "B-000001"
    assert output.blocks[0].page_number == 1
    assert output.raw_tables[0]["title"] == "产品收入结构表"
    assert output.parse_report["quality_status"] == "safe_to_use"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_parser_stub.py -q
```

Expected: FAIL with `No module named 'ipo_evidence.parser'`.

- [ ] **Step 4: Implement parser base**

Create `src/ipo_evidence/parser/__init__.py`:

```python
from ipo_evidence.parser.api_stub import ApiStubParser

__all__ = ["ApiStubParser"]
```

Create `src/ipo_evidence/parser/base.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from ipo_evidence.models import Block


class ParserOutput(BaseModel):
    markdown: str
    blocks: list[Block]
    raw_tables: list[dict] = Field(default_factory=list)
    parse_report: dict


class Parser(Protocol):
    def parse(self, pdf_path: Path) -> ParserOutput:
        raise NotImplementedError
```

- [ ] **Step 5: Implement API stub parser**

Create `src/ipo_evidence/parser/api_stub.py`:

```python
from __future__ import annotations

from pathlib import Path

from ipo_evidence.models import Block
from ipo_evidence.parser.base import ParserOutput


class ApiStubParser:
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path

    def parse(self, pdf_path: Path) -> ParserOutput:
        markdown = self.fixture_path.read_text(encoding="utf-8")
        blocks: list[Block] = []
        block_number = 1
        current_page = 1
        for paragraph in [part.strip() for part in markdown.split("\n\n") if part.strip()]:
            blocks.append(
                Block(
                    block_id=f"B-{block_number:06d}",
                    page_number=current_page,
                    text=paragraph,
                    section_path=[],
                )
            )
            block_number += 1
            current_page += 1

        raw_tables = [
            {
                "title": "产品收入结构表",
                "page_number": 3,
                "columns": ["产品", "2023年收入", "占比"],
                "rows": [
                    ["智能控制器", "12000万元", "45.2%"],
                    ["智能终端", "9800万元", "36.9%"],
                ],
                "notes": [],
            }
        ]

        parse_report = {
            "source_file": pdf_path.name,
            "quality_status": "safe_to_use",
            "page_count": len(blocks),
            "garbled_ratio": 0.0,
            "raw_table_count": len(raw_tables),
        }
        return ParserOutput(
            markdown=markdown,
            blocks=blocks,
            raw_tables=raw_tables,
            parse_report=parse_report,
        )
```

- [ ] **Step 6: Run parser tests**

Run:

```powershell
python -m pytest tests/test_parser_stub.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit**

```powershell
git add src/ipo_evidence/parser tests/fixtures/sample_prospectus.txt tests/test_parser_stub.py
git commit -m "feat: add parser interface and API stub"
```

---

## Task 5: Section Mapping And Table Extraction

**Files:**
- Create: `src/ipo_evidence/section_mapper.py`
- Create: `src/ipo_evidence/table_extractor.py`
- Create: `tests/test_section_mapper.py`
- Create: `tests/test_table_extractor.py`

- [ ] **Step 1: Write section mapper tests**

Create `tests/test_section_mapper.py`:

```python
from ipo_evidence.models import Block
from ipo_evidence.section_mapper import build_source_ast, map_canonical_sections


def test_build_source_ast_detects_a_share_headings():
    blocks = [
        Block(block_id="B-000001", page_number=1, text="## 第一节 发行人基本情况"),
        Block(block_id="B-000002", page_number=2, text="公司主要从事智能硬件产品。"),
        Block(block_id="B-000003", page_number=3, text="## 第二节 业务和技术"),
    ]

    ast = build_source_ast(blocks)

    assert [node.title for node in ast] == ["发行人基本情况", "业务和技术"]
    assert ast[0].block_ids == ["B-000001", "B-000002"]


def test_map_canonical_sections_maps_business_section():
    ast = build_source_ast([
        Block(block_id="B-000001", page_number=1, text="## 第二节 业务和技术"),
        Block(block_id="B-000002", page_number=2, text="公司的主要产品包括智能控制器。"),
    ])

    canonical = map_canonical_sections(ast)

    assert canonical["business_and_product"]["title"] == "业务与产品"
    assert canonical["business_and_product"]["source_sections"] == ["业务和技术"]
```

- [ ] **Step 2: Write table extractor tests**

Create `tests/test_table_extractor.py`:

```python
from ipo_evidence.table_extractor import extract_tables


def test_extract_tables_normalizes_raw_tables():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "产品收入结构表",
                "page_number": 3,
                "columns": ["产品", "2023年收入", "占比"],
                "rows": [["智能控制器", "12000万元", "45.2%"]],
                "notes": [],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].table_id == "T-001"
    assert tables[0].quality_score == 0.9
    assert tables[0].columns == ["产品", "2023年收入", "占比"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_section_mapper.py tests/test_table_extractor.py -q
```

Expected: FAIL with missing module or missing functions.

- [ ] **Step 4: Implement section mapper**

Create `src/ipo_evidence/section_mapper.py`:

```python
from __future__ import annotations

import re

from ipo_evidence.models import AstNode, Block


CANONICAL_RULES = {
    "about_company": ("关于公司", ["发行人基本情况", "发行人概况"]),
    "business_and_product": ("业务与产品", ["业务和技术", "主营业务"]),
    "financials": ("财务与经营数据", ["财务会计信息", "管理层讨论与分析"]),
    "use_of_proceeds": ("募集资金用途", ["募集资金运用", "募集资金用途"]),
    "risks": ("风险因素", ["风险因素"]),
}


def normalize_heading(text: str) -> str | None:
    stripped = text.strip().lstrip("#").strip()
    match = re.match(r"第[一二三四五六七八九十]+节\s+(.+)", stripped)
    if match:
        return match.group(1).strip()
    return None


def build_source_ast(blocks: list[Block]) -> list[AstNode]:
    nodes: list[AstNode] = []
    current: AstNode | None = None
    for block in blocks:
        heading = normalize_heading(block.text)
        if heading:
            current = AstNode(
                title=heading,
                level=1,
                section_path=[heading],
                block_ids=[block.block_id],
            )
            nodes.append(current)
        elif current is not None:
            current.block_ids.append(block.block_id)
    return nodes


def map_canonical_sections(source_ast: list[AstNode]) -> dict:
    canonical: dict[str, dict] = {}
    for key, (title, patterns) in CANONICAL_RULES.items():
        matched = [
            node.title
            for node in source_ast
            if any(pattern in node.title for pattern in patterns)
        ]
        if matched:
            canonical[key] = {"title": title, "source_sections": matched}
    return canonical
```

- [ ] **Step 5: Implement table extractor**

Create `src/ipo_evidence/table_extractor.py`:

```python
from __future__ import annotations

from ipo_evidence.models import TableObject


def score_table(raw_table: dict) -> float:
    has_title = bool(raw_table.get("title"))
    has_columns = bool(raw_table.get("columns"))
    has_rows = bool(raw_table.get("rows"))
    if has_title and has_columns and has_rows:
        return 0.9
    if has_columns and has_rows:
        return 0.75
    return 0.4


def extract_tables(
    raw_tables: list[dict],
    source_file: str,
    section_path: list[str],
) -> list[TableObject]:
    tables: list[TableObject] = []
    for index, raw_table in enumerate(raw_tables, start=1):
        tables.append(
            TableObject(
                table_id=f"T-{index:03d}",
                title=raw_table.get("title") or f"未命名表格 {index}",
                source_file=source_file,
                page_number=int(raw_table.get("page_number") or 1),
                section_path=section_path,
                columns=list(raw_table.get("columns") or []),
                rows=list(raw_table.get("rows") or []),
                notes=list(raw_table.get("notes") or []),
                quality_score=score_table(raw_table),
            )
        )
    return tables
```

- [ ] **Step 6: Run section and table tests**

Run:

```powershell
python -m pytest tests/test_section_mapper.py tests/test_table_extractor.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 7: Commit**

```powershell
git add src/ipo_evidence/section_mapper.py src/ipo_evidence/table_extractor.py tests/test_section_mapper.py tests/test_table_extractor.py
git commit -m "feat: map sections and extract tables"
```

---

## Task 6: Evidence Packet, Report, And Citation Layer

**Files:**
- Create: `src/ipo_evidence/evidence.py`
- Create: `src/ipo_evidence/report_generator.py`
- Create: `src/ipo_evidence/citation_layer.py`
- Create: `tests/test_evidence.py`
- Create: `tests/test_report_and_citation.py`

- [ ] **Step 1: Write evidence tests**

Create `tests/test_evidence.py`:

```python
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block, QualityStatus, TableObject


def test_build_evidence_packet_uses_text_and_table_sources():
    blocks = [
        Block(
            block_id="B-000002",
            page_number=2,
            text="公司主要从事智能硬件产品的研发、生产和销售。",
            section_path=["发行人基本情况"],
        )
    ]
    tables = [
        TableObject(
            table_id="T-001",
            title="产品收入结构表",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=3,
            section_path=["业务和技术"],
            columns=["产品", "2023年收入", "占比"],
            rows=[["智能控制器", "12000万元", "45.2%"]],
            quality_score=0.9,
        )
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=tables,
    )

    assert len(packet.items) == 2
    assert packet.items[0].quality_status == QualityStatus.safe_to_use
    assert packet.items[1].table_id == "T-001"
```

- [ ] **Step 2: Write report and citation tests**

Create `tests/test_report_and_citation.py`:

```python
from ipo_evidence.citation_layer import build_citations
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block
from ipo_evidence.report_generator import generate_report


def test_report_contains_citation_markers_and_citation_json():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司主要从事智能硬件产品的研发、生产和销售。",
                section_path=["发行人基本情况"],
            )
        ],
        tables=[],
    )

    draft = generate_report("测试股份有限公司", packet)
    citations = build_citations(packet)

    assert "[C-001]" in draft
    assert citations[0].citation_id == "C-001"
    assert citations[0].block_id == "B-000002"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_evidence.py tests/test_report_and_citation.py -q
```

Expected: FAIL with missing modules or missing functions.

- [ ] **Step 4: Implement evidence builder**

Create `src/ipo_evidence/evidence.py`:

```python
from __future__ import annotations

from ipo_evidence.models import Block, EvidenceItem, EvidencePacket, QualityStatus, TableObject


def build_evidence_packet(
    doc_id: str,
    source_file: str,
    blocks: list[Block],
    tables: list[TableObject],
) -> EvidencePacket:
    items: list[EvidenceItem] = []
    next_id = 1
    for block in blocks:
        if "公司主要从事" in block.text or "主要产品" in block.text:
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section="about_company",
                    claim_summary=block.text.rstrip("。") + "。",
                    source_type="text_quote",
                    source_file=source_file,
                    page_number=block.page_number,
                    block_id=block.block_id,
                    section_path=block.section_path or ["未识别章节"],
                    quote=block.text,
                    quality_status=QualityStatus.safe_to_use,
                )
            )
            next_id += 1
    for table in tables:
        if table.quality_score >= 0.75 and table.rows:
            fields = {
                table.columns[index]: table.rows[0][index]
                for index in range(min(len(table.columns), len(table.rows[0])))
            }
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section="business_and_product",
                    claim_summary=f"{table.title}显示：{fields}",
                    source_type="table_fact",
                    source_file=source_file,
                    page_number=table.page_number,
                    table_id=table.table_id,
                    section_path=table.section_path,
                    fields=fields,
                    quality_status=QualityStatus.safe_to_use,
                )
            )
            next_id += 1
    return EvidencePacket(doc_id=doc_id, items=items)
```

- [ ] **Step 5: Implement report generator**

Create `src/ipo_evidence/report_generator.py`:

```python
from __future__ import annotations

from ipo_evidence.models import EvidencePacket


def generate_report(company_name: str, packet: EvidencePacket) -> str:
    lines = [
        f"# {company_name}招股书解读",
        "",
        "## 1. 处理结论",
        "",
        "当前报告由本地证据包生成，适合进行第一轮人工复核。",
        "",
        "## 2. 关于公司",
        "",
    ]
    for index, item in enumerate(packet.items, start=1):
        citation_id = f"C-{index:03d}"
        lines.append(f"- {item.claim_summary}[{citation_id}]")
    lines.extend(
        [
            "",
            "## 3. 后续跟踪问题",
            "",
            "- 需要继续核查客户集中度、募投项目合理性和风险因素。",
        ]
    )
    return "\n".join(lines) + "\n"
```

- [ ] **Step 6: Implement citation layer**

Create `src/ipo_evidence/citation_layer.py`:

```python
from __future__ import annotations

from ipo_evidence.models import Citation, EvidencePacket


def build_citations(packet: EvidencePacket) -> list[Citation]:
    citations: list[Citation] = []
    for index, item in enumerate(packet.items, start=1):
        citation_id = f"C-{index:03d}"
        citations.append(
            Citation(
                citation_id=citation_id,
                type=item.source_type,
                source_file=item.source_file,
                source_url=None,
                page_number=item.page_number,
                block_id=item.block_id,
                table_id=item.table_id,
                section_path=item.section_path,
                quote=item.quote,
                fields=item.fields,
                summary=item.claim_summary,
            )
        )
    return citations
```

- [ ] **Step 7: Run evidence/report/citation tests**

Run:

```powershell
python -m pytest tests/test_evidence.py tests/test_report_and_citation.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 8: Commit**

```powershell
git add src/ipo_evidence/evidence.py src/ipo_evidence/report_generator.py src/ipo_evidence/citation_layer.py tests/test_evidence.py tests/test_report_and_citation.py
git commit -m "feat: generate evidence reports with citations"
```

---

## Task 7: Pipeline Orchestration And CLI

**Files:**
- Create: `src/ipo_evidence/web_index.py`
- Create: `src/ipo_evidence/pipeline.py`
- Create: `src/ipo_evidence/cli.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write pipeline test**

Create `tests/test_pipeline.py`:

```python
from pathlib import Path

from ipo_evidence.pipeline import run_one


def test_run_one_creates_document_package(tmp_path: Path):
    inbox = tmp_path / "inbox"
    docs = tmp_path / "docs"
    inbox.mkdir()
    pdf = inbox / "测试股份有限公司招股说明书.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsample")

    doc_id = run_one(
        pdf_path=pdf,
        docs_dir=docs,
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    package = docs / doc_id
    assert (package / "manifest.json").exists()
    assert (package / "document.md").exists()
    assert (package / "blocks.jsonl").exists()
    assert (package / "source_ast.json").exists()
    assert (package / "canonical_ast.json").exists()
    assert (package / "tables" / "T-001.json").exists()
    assert (package / "evidence_packet.json").exists()
    assert (package / "report.md").exists()
    assert (package / "citation.json").exists()
    assert (package / "web_index.json").exists()
```

- [ ] **Step 2: Run pipeline test to verify it fails**

Run:

```powershell
python -m pytest tests/test_pipeline.py -q
```

Expected: FAIL with missing `ipo_evidence.pipeline`.

- [ ] **Step 3: Implement web index**

Create `src/ipo_evidence/web_index.py`:

```python
from __future__ import annotations

from ipo_evidence.models import Manifest, WebIndex


def build_web_index(manifest: Manifest) -> WebIndex:
    return WebIndex(
        doc_id=manifest.doc_id,
        company_name=manifest.company_name,
        source_file=manifest.source_file,
        quality_status=manifest.quality_status,
        parse_status=manifest.parse_status,
        report_status=manifest.report_status,
        tags=manifest.tags,
    )
```

- [ ] **Step 4: Implement pipeline orchestration**

Create `src/ipo_evidence/pipeline.py`:

```python
from __future__ import annotations

from pathlib import Path

from ipo_evidence.citation_layer import build_citations
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.ingest import company_name_from_filename, doc_id_for_file
from ipo_evidence.io import ensure_dir, write_json, write_jsonl, write_text
from ipo_evidence.models import Manifest, QualityStatus
from ipo_evidence.parser.api_stub import ApiStubParser
from ipo_evidence.report_generator import generate_report
from ipo_evidence.section_mapper import build_source_ast, map_canonical_sections
from ipo_evidence.table_extractor import extract_tables
from ipo_evidence.web_index import build_web_index


def run_one(pdf_path: Path, docs_dir: Path, fixture_path: Path) -> str:
    doc_id = doc_id_for_file(pdf_path)
    package_dir = ensure_dir(docs_dir / doc_id)
    source_file = pdf_path.name
    company_name = company_name_from_filename(pdf_path)
    manifest = Manifest(
        doc_id=doc_id,
        company_name=company_name,
        source_file=source_file,
        parse_status="parsed",
        report_status="reported",
        quality_status=QualityStatus.safe_to_use,
    )

    parser = ApiStubParser(fixture_path=fixture_path)
    parsed = parser.parse(pdf_path)
    source_ast = build_source_ast(parsed.blocks)
    canonical_ast = map_canonical_sections(source_ast)
    tables = extract_tables(parsed.raw_tables, source_file, ["业务和技术"])
    packet = build_evidence_packet(doc_id, source_file, parsed.blocks, tables)
    report = generate_report(company_name, packet)
    citations = build_citations(packet)
    web_index = build_web_index(manifest)

    write_json(package_dir / "manifest.json", manifest)
    write_text(package_dir / "document.md", parsed.markdown)
    write_jsonl(package_dir / "blocks.jsonl", parsed.blocks)
    write_json(package_dir / "source_ast.json", [node.model_dump(mode="json") for node in source_ast])
    write_json(package_dir / "canonical_ast.json", canonical_ast)
    tables_dir = ensure_dir(package_dir / "tables")
    for table in tables:
        write_json(tables_dir / f"{table.table_id}.json", table)
    write_json(package_dir / "evidence_packet.json", packet)
    write_text(package_dir / "report.md", report)
    write_json(package_dir / "citation.json", [citation.model_dump(mode="json") for citation in citations])
    write_json(package_dir / "parse_report.json", parsed.parse_report)
    write_json(package_dir / "web_index.json", web_index)
    return doc_id
```

- [ ] **Step 5: Implement CLI**

Create `src/ipo_evidence/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from ipo_evidence.ingest import scan_inbox
from ipo_evidence.paths import docs_dir, inbox_dir, repo_root
from ipo_evidence.pipeline import run_one


def main() -> None:
    parser = argparse.ArgumentParser(prog="ipo-evidence")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("scan-inbox")
    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("--limit", type=int, default=3)
    report_parser = subcommands.add_parser("generate-report")
    report_parser.add_argument("--doc-id", required=True)
    args = parser.parse_args()

    if args.command == "scan-inbox":
        manifests = scan_inbox(inbox_dir(), docs_dir())
        print(f"scanned={len(manifests)}")
        return

    if args.command == "run":
        fixture = repo_root() / "tests" / "fixtures" / "sample_prospectus.txt"
        pdfs = sorted(inbox_dir().glob("*.pdf"))[: args.limit]
        for pdf in pdfs:
            doc_id = run_one(pdf, docs_dir(), fixture)
            print(f"processed={doc_id}")
        return

    if args.command == "generate-report":
        print(f"report generation is included in pipeline for doc_id={args.doc_id}")
        return


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run pipeline tests**

Run:

```powershell
python -m pytest tests/test_pipeline.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Run all Python tests**

Run:

```powershell
python -m pytest -q
```

Expected all tests pass.

- [ ] **Step 8: Commit**

```powershell
git add src/ipo_evidence/web_index.py src/ipo_evidence/pipeline.py src/ipo_evidence/cli.py tests/test_pipeline.py
git commit -m "feat: orchestrate local evidence pipeline"
```

---

## Task 8: Web Reader

**Files:**
- Create: `web/package.json`
- Create: `web/index.html`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/data.ts`
- Create: `web/src/components/DocumentList.tsx`
- Create: `web/src/components/ReportReader.tsx`
- Create: `web/src/components/CitationPanel.tsx`
- Create: `web/src/components/SourceView.tsx`
- Create: `web/src/styles.css`
- Create: `web/src/__tests__/reader.test.tsx`

- [ ] **Step 1: Write Web package files**

Create `web/package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.3.0",
    "typescript": "^5.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^15.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "vitest": "^1.6.0",
    "jsdom": "^24.1.0"
  }
}
```

Create `web/index.html`:

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

Create `web/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom"
  }
});
```

Create `web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

- [ ] **Step 2: Write Web test**

Create `web/src/__tests__/reader.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import App from "../App";

test("renders document list and clean reader", () => {
  render(<App />);
  expect(screen.getByText("IPO Evidence Reader")).toBeInTheDocument();
  expect(screen.getByText("测试股份有限公司")).toBeInTheDocument();
  expect(screen.getByText("公司主要从事智能硬件产品")).toBeInTheDocument();
  expect(screen.getByText("Citation")).toBeInTheDocument();
});
```

- [ ] **Step 3: Run Web test to verify it fails**

Run:

```powershell
npm install --prefix web
npm --prefix web run test
```

Expected: FAIL with missing `../App`.

- [ ] **Step 4: Implement Web types and fixture data**

Create `web/src/lib/types.ts`:

```ts
export type QualityStatus = "safe_to_use" | "manual_review" | "do_not_use";

export type DocumentIndex = {
  doc_id: string;
  company_name: string;
  source_file: string;
  quality_status: QualityStatus;
  parse_status: string;
  report_status: string;
  tags: string[];
};

export type Citation = {
  citation_id: string;
  type: "text_quote" | "table_fact";
  source_file: string;
  page_number: number;
  block_id?: string | null;
  section_path: string[];
  quote?: string | null;
  summary: string;
};
```

Create `web/src/lib/data.ts`:

```ts
import type { Citation, DocumentIndex } from "./types";

export const documents: DocumentIndex[] = [
  {
    doc_id: "doc_test",
    company_name: "测试股份有限公司",
    source_file: "测试股份有限公司招股说明书.pdf",
    quality_status: "safe_to_use",
    parse_status: "parsed",
    report_status: "reported",
    tags: ["A股", "招股说明书"]
  }
];

export const reportMarkdown = `# 测试股份有限公司招股书解读

## 1. 处理结论

公司主要从事智能硬件产品。[C-001]
`;

export const citations: Citation[] = [
  {
    citation_id: "C-001",
    type: "text_quote",
    source_file: "测试股份有限公司招股说明书.pdf",
    page_number: 2,
    block_id: "B-000002",
    section_path: ["发行人基本情况"],
    quote: "公司主要从事智能硬件产品的研发、生产和销售。",
    summary: "公司主要从事智能硬件产品"
  }
];
```

- [ ] **Step 5: Implement React components**

Create `web/src/components/DocumentList.tsx`:

```tsx
import type { DocumentIndex } from "../lib/types";

export function DocumentList({ documents }: { documents: DocumentIndex[] }) {
  return (
    <section className="document-list">
      <h1>IPO Evidence Reader</h1>
      {documents.map((doc) => (
        <article className="document-card" key={doc.doc_id}>
          <h2>{doc.company_name}</h2>
          <p>{doc.source_file}</p>
          <span>{doc.quality_status}</span>
        </article>
      ))}
    </section>
  );
}
```

Create `web/src/components/ReportReader.tsx`:

```tsx
export function ReportReader({ markdown }: { markdown: string }) {
  const html = markdown
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/\[C-(\d{3})\]/g, '<button class="citation-token">C-$1</button>')
    .replace(/\n\n/g, "</p><p>");

  return (
    <article
      className="report-reader"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
    />
  );
}
```

Create `web/src/components/CitationPanel.tsx`:

```tsx
import type { Citation } from "../lib/types";

export function CitationPanel({ citation }: { citation: Citation }) {
  return (
    <aside className="citation-panel">
      <h2>Citation</h2>
      <strong>{citation.citation_id}</strong>
      <p>{citation.summary}</p>
      <dl>
        <dt>来源文件</dt>
        <dd>{citation.source_file}</dd>
        <dt>页码</dt>
        <dd>{citation.page_number}</dd>
        <dt>章节</dt>
        <dd>{citation.section_path.join(" / ")}</dd>
      </dl>
      {citation.quote ? <blockquote>{citation.quote}</blockquote> : null}
    </aside>
  );
}
```

Create `web/src/components/SourceView.tsx`:

```tsx
export function SourceView() {
  return <section className="source-view">Markdown 原文页将在接入真实文档包后读取 document.md。</section>;
}
```

- [ ] **Step 6: Implement App and styles**

Create `web/src/App.tsx`:

```tsx
import { CitationPanel } from "./components/CitationPanel";
import { DocumentList } from "./components/DocumentList";
import { ReportReader } from "./components/ReportReader";
import { citations, documents, reportMarkdown } from "./lib/data";
import "./styles.css";

export default function App() {
  return (
    <main className="app-shell">
      <DocumentList documents={documents} />
      <section className="reader-layout">
        <ReportReader markdown={reportMarkdown} />
        <CitationPanel citation={citations[0]} />
      </section>
    </main>
  );
}
```

Create `web/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `web/src/styles.css`:

```css
:root {
  color: #1f2933;
  background: #f7f8f8;
  font-family: Inter, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

.app-shell {
  min-height: 100vh;
}

.document-list {
  border-bottom: 1px solid #d9dfdf;
  padding: 20px 32px;
}

.document-card {
  background: #ffffff;
  border: 1px solid #d9dfdf;
  border-radius: 8px;
  padding: 14px 16px;
  max-width: 720px;
}

.reader-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 28px;
  padding: 32px;
}

.report-reader {
  background: #ffffff;
  border: 1px solid #d9dfdf;
  border-radius: 8px;
  line-height: 1.8;
  margin: 0 auto;
  max-width: 760px;
  padding: 32px;
}

.citation-token {
  border: 1px solid #3b7f6e;
  background: #edf7f4;
  border-radius: 4px;
  color: #235b4d;
  cursor: pointer;
  margin-left: 4px;
}

.citation-panel {
  background: #ffffff;
  border: 1px solid #d9dfdf;
  border-radius: 8px;
  min-height: 320px;
  padding: 20px;
  position: sticky;
  top: 24px;
}

blockquote {
  border-left: 3px solid #3b7f6e;
  margin-left: 0;
  padding-left: 12px;
}

@media (max-width: 900px) {
  .reader-layout {
    grid-template-columns: 1fr;
  }

  .citation-panel {
    position: static;
  }
}
```

- [ ] **Step 7: Run Web tests and build**

Run:

```powershell
npm --prefix web run test
npm --prefix web run build
```

Expected: both commands pass.

- [ ] **Step 8: Commit**

```powershell
git add web package.json
git commit -m "feat: add clean web evidence reader"
```

---

## Task 9: End-To-End Verification And Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-06-23-ipo-evidence-mvp-design.md` only if implementation revealed a design correction.

- [ ] **Step 1: Run Python verification**

Run:

```powershell
python -m pytest -q
```

Expected: all Python tests pass.

- [ ] **Step 2: Run Web verification**

Run:

```powershell
npm --prefix web run test
npm --prefix web run build
```

Expected: Web tests and production build pass.

- [ ] **Step 3: Run local sample pipeline**

Create a tiny sample PDF placeholder in `data/inbox/` only for local smoke testing:

```powershell
Set-Content -Path "data/inbox/测试股份有限公司招股说明书.pdf" -Value "%PDF-1.4 sample"
python -m ipo_evidence.cli run --limit 1
```

Expected:

```text
processed=doc_<12 hex chars>
```

and one package appears under `data/docs/`.

- [ ] **Step 4: Verify generated package**

Run:

```powershell
Get-ChildItem -Recurse data/docs | Select-Object FullName
```

Expected package contains:

```text
manifest.json
document.md
blocks.jsonl
source_ast.json
canonical_ast.json
tables/T-001.json
evidence_packet.json
report.md
citation.json
parse_report.json
web_index.json
```

- [ ] **Step 5: Clean local smoke artifacts**

Because deleting files is a user redline in this project, ask the user before removing `data/inbox/测试股份有限公司招股说明书.pdf` and generated `data/docs/doc_*` artifacts. If the user declines cleanup, leave them in place; `.gitignore` prevents committing them.

- [ ] **Step 6: Update README with verified commands**

Modify `README.md` so the commands exactly match the implementation:

~~~~markdown
## Verified MVP commands

```powershell
python -m pytest -q
npm --prefix web run test
npm --prefix web run build
python -m ipo_evidence.cli run --limit 1
```
~~~~

- [ ] **Step 7: Final status check**

Run:

```powershell
git status --short
```

Expected: only intentional README or design updates are shown.

- [ ] **Step 8: Commit**

```powershell
git add README.md docs/superpowers/specs/2026-06-23-ipo-evidence-mvp-design.md
git commit -m "docs: document verified MVP workflow"
```

If only generated ignored artifacts changed, skip the commit and report that no tracked documentation changed.

---

## Self-Review

### Spec Coverage

- Local PDF folder input: Tasks 1, 3, 7, and 9.
- API-first parser with fallback boundary: Task 4 defines the parser interface and API-shaped stub.
- Markdown, blocks, source AST, canonical AST: Tasks 4, 5, and 7.
- Tables: Tasks 5 and 7.
- Evidence packet: Task 6.
- Report and citation: Task 6.
- Web reader with pure report layout and citation panel: Task 8.
- Quality and failure state foundation: Tasks 2, 6, and 7 include quality statuses; deeper quality scoring can be extended after this vertical slice passes.
- No automatic discovery/download/HK/graphs/database: excluded from file structure and tasks.

### Placeholder Scan

The plan contains no banned placeholder terms or empty implementation instructions. Each task includes exact files, test commands, expected results, and commit commands.

### Type Consistency

The model names used across tasks are consistent: `Manifest`, `Block`, `AstNode`, `TableObject`, `EvidenceItem`, `EvidencePacket`, `Citation`, and `WebIndex`. The pipeline writes the filenames required by the design document.
