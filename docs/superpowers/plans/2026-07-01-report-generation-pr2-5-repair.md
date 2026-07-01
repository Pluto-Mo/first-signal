# Report Generation PR2.5 Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the half-switched report generation architecture so `section_drafts` become readable interpretation drafts before they enter final `report.md`.

**Architecture:** Keep the current `report_inputs -> section_generator -> quality_gate -> assembler` contract, but replace the current claim-concatenation draft body with a deterministic section writer. The writer selects a bounded set of core evidence, formats table facts into natural language, applies configured skill refs as concrete interpretation moves, and produces short paragraphs that the assembler can safely stitch. Quality gate gains readability checks so future regressions cannot ship unreadable evidence dumps.

**Tech Stack:** Python, Pydantic models, local YAML config, pytest, existing JSON document package artifacts.

---

## File Structure

- Modify: `src/ipo_evidence/section_generator.py`
  - Continue owning `SectionDraft` construction and `InternalTrace`.
  - Delegate body writing and selected evidence tracking to the new section writer.
- Create: `src/ipo_evidence/section_writer.py`
  - Select bounded evidence per section.
  - Format text and table evidence into readable cited sentences.
  - Execute current deterministic skill actions from `skill_refs`.
  - Return `SectionWriteResult` with body, selected items, citation ids, and readability metrics.
- Modify: `src/ipo_evidence/quality_gate.py`
  - Add readability checks for body length, citation density, and forbidden raw-data text.
  - Reject or defer unreadable section drafts before assembler sees them.
- Modify: `src/ipo_evidence/models.py`
  - Add optional `readability_warnings` to `InternalTrace`.
- Modify: `tests/test_section_generator.py`
  - Update expectations from raw `claim_summary` concatenation to readable bounded paragraphs.
- Create: `tests/test_section_writer.py`
  - Focused tests for evidence selection, table formatting, and skill execution.
- Modify: `tests/test_quality_gate.py`
  - Add tests for readability rejection.
- Modify: `tests/test_pipeline.py`
  - Add regression checks that final `report.md` is not an evidence dump.
- Optional modify: `docs/product/report_generation.md`
  - Update implementation note after behavior changes.

---

### Task 1: Add Section Writer Regression Tests

**Files:**
- Create: `tests/test_section_writer.py`

- [ ] **Step 1: Write failing tests for bounded readable section writing**

Create `tests/test_section_writer.py`:

```python
from ipo_evidence.models import EvidenceItem, QualityStatus
from ipo_evidence.section_writer import write_section


def _text_item(evidence_id: str, summary: str, section: str = "business_and_product") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        canonical_section=section,
        claim_summary=summary,
        source_type="text_quote",
        source_file="sample.pdf",
        page_number=2,
        block_id=f"B-{evidence_id}",
        section_path=["业务和技术"],
        quote=summary,
        quality_status=QualityStatus.safe_to_use,
    )


def _table_item(evidence_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        canonical_section="financials",
        claim_summary="发行人主要财务数据及财务指标中，营业收入（万元）对应数据为：{'项目': '营业收入（万元）', '2025年度': '68,771.52', '2024年度': '60,077.16'}。",
        source_type="table_fact",
        source_file="sample.pdf",
        page_number=11,
        table_id="T-001",
        table_title="主要财务数据及财务指标",
        section_path=["财务会计信息"],
        fields={
            "项目": "营业收入（万元）",
            "2025年度": "68,771.52",
            "2024年度": "60,077.16",
        },
        quality_status=QualityStatus.safe_to_use,
    )


def test_write_section_limits_evidence_and_adds_interpretation():
    items = [
        (index, _text_item(f"E-{index:03d}", f"公司在智慧出行、智慧办公和智慧物联场景形成产品化交付能力，样本 {index}。"))
        for index in range(1, 31)
    ]

    result = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["business_goal_decompose", "capability_match", "reader_value_translate"],
        prompt_slot="narrative_section",
        indexed_items=items,
    )

    assert len(result.selected_items) <= 12
    assert 2 <= len([part for part in result.body.split("\n\n") if part.strip()]) <= 6
    assert result.body.count("[C-") <= 12
    assert "阅读这一节" in result.body
    assert "不是把 AI 当成概念标签" in result.body
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_formats_table_fields_without_raw_dict_literals():
    result = write_section(
        section_key="personal_investment",
        title="个人投资视角",
        skill_refs=["business_goal_decompose", "tension_expand"],
        prompt_slot="narrative_section",
        indexed_items=[(7, _table_item("E-007"))],
    )

    assert "营业收入（万元）" in result.body
    assert "2025年度为 68,771.52" in result.body
    assert "2024年度为 60,077.16" in result.body
    assert "[C-007]" in result.body
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_executes_tension_skill_when_requested():
    items = [
        (1, _text_item("E-001", "报告期内，公司营业收入持续增长。", "financials")),
        (2, _text_item("E-002", "报告期内，公司经营活动现金流量净额持续为负。", "financials")),
    ]

    result = write_section(
        section_key="cognitive_worldview",
        title="认知世界的方式",
        skill_refs=["tension_expand"],
        prompt_slot="narrative_section",
        indexed_items=items,
    )

    assert "张力" in result.body
    assert "增长" in result.body
    assert "现金流" in result.body
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_writer.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ipo_evidence.section_writer'`.

---

### Task 2: Implement Deterministic Section Writer

**Files:**
- Create: `src/ipo_evidence/section_writer.py`

- [ ] **Step 1: Create the section writer module**

Create `src/ipo_evidence/section_writer.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import re

from ipo_evidence.models import EvidenceItem


MAX_ITEMS_BY_SECTION = {
    "company_and_industry": 12,
    "personal_investment": 12,
    "cognitive_worldview": 10,
}

KEYWORDS_BY_SECTION = {
    "company_and_industry": [
        "主营业务",
        "产品",
        "智慧出行",
        "智慧办公",
        "智慧物联",
        "行业",
        "市场",
        "技术",
        "客户",
    ],
    "personal_investment": [
        "营业收入",
        "净利润",
        "亏损",
        "现金流",
        "研发",
        "客户",
        "募集资金",
        "风险",
    ],
    "cognitive_worldview": [
        "终端",
        "入口",
        "增长",
        "现金流",
        "风险",
        "竞争",
        "研发",
        "客户",
    ],
}

LOW_VALUE_SNIPPETS = [
    "参见",
    "请参见",
    "详见",
    "本招股说明书",
    "释义",
    "目录",
    "发行人声明",
    "对应数据为",
]

FORBIDDEN_RAW_TEXT = ["{'", '对应数据为']


@dataclass(frozen=True)
class SectionWriteResult:
    body: str
    selected_items: list[tuple[int, EvidenceItem]]
    citation_ids: list[str]
    readability_warnings: list[str]


def _citation_id(index: int) -> str:
    return f"C-{index:03d}"


def _clean_text(value: str, limit: int = 160) -> str:
    text = " ".join(value.replace("\u3000", " ").split()).rstrip("。；;，,")
    for raw in FORBIDDEN_RAW_TEXT:
        if raw in text:
            text = text.split(raw, 1)[0].rstrip("。；;，,")
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for marker in ["。", "；", "，", "、"]:
        pos = cut.rfind(marker)
        if pos >= 48:
            return cut[:pos].rstrip("。；;，,")
    return cut.rstrip("。；;，,") + "..."


def _readable_value(value: str) -> str:
    return (
        value.replace("万元", " 万元")
        .replace("亿元", " 亿元")
        .replace("个百分点", " 个百分点")
    )


def _score(item: EvidenceItem, section_key: str) -> int:
    text = " ".join([item.claim_summary, item.quote or "", " ".join(item.section_path)])
    score = 0
    for keyword in KEYWORDS_BY_SECTION.get(section_key, []):
        if keyword in text:
            score += 4
    if item.source_type == "text_quote":
        score += 3
    if item.source_type == "table_fact":
        score += 1
    if 35 <= len(item.claim_summary) <= 260:
        score += 2
    for snippet in LOW_VALUE_SNIPPETS:
        if snippet in text:
            score -= 4
    if len(item.claim_summary) < 18:
        score -= 4
    return score


def _dedupe_key(item: EvidenceItem) -> str:
    source = item.quote or item.claim_summary
    return _clean_text(source, 72)


def _select_items(
    section_key: str,
    indexed_items: list[tuple[int, EvidenceItem]],
) -> list[tuple[int, EvidenceItem]]:
    limit = MAX_ITEMS_BY_SECTION.get(section_key, 10)
    ranked = sorted(
        indexed_items,
        key=lambda pair: (-_score(pair[1], section_key), pair[0]),
    )
    selected: list[tuple[int, EvidenceItem]] = []
    seen: set[str] = set()
    for pair in ranked:
        key = _dedupe_key(pair[1])
        if not key or key in seen:
            continue
        selected.append(pair)
        seen.add(key)
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda pair: pair[0])


def _format_table_sentence(item: EvidenceItem, citation_id: str) -> str:
    fields = {key: value for key, value in item.fields.items() if value and value != "-"}
    metric = fields.get("项目") or fields.get("指标") or item.table_title or "表格项目"
    values = [
        f"{key}为 {_readable_value(value)}"
        for key, value in fields.items()
        if key not in {"项目", "指标"}
    ]
    if values:
        return f"{metric}显示，{'，'.join(values[:4])}。[{citation_id}]"
    return f"{item.table_title or '表格'}披露了{metric}相关数据。[{citation_id}]"


def _format_sentence(index: int, item: EvidenceItem) -> str:
    citation_id = _citation_id(index)
    if item.source_type == "table_fact" and item.fields:
        return _format_table_sentence(item, citation_id)
    return f"{_clean_text(item.claim_summary)}。[{citation_id}]"


def _sentences(items: list[tuple[int, EvidenceItem]], limit: int) -> str:
    return " ".join(_format_sentence(index, item) for index, item in items[:limit])


def _skill_intro(section_key: str, skill_refs: list[str]) -> str:
    if "business_goal_decompose" in skill_refs:
        if section_key == "company_and_industry":
            return "阅读这一节，先把公司叙事拆成三个问题：它卖什么、进入哪些终端场景、这些场景是否能形成可复制交付。"
        if section_key == "personal_investment":
            return "个人投资视角下，重点不是先判断贵不贵，而是先拆收入质量、研发转化、现金流和风险承受力。"
    if "reader_value_translate" in skill_refs:
        return "这一节的价值，是把招股书披露翻译成几个可以继续核查的问题。"
    return "这一节先从已抽取证据中挑出最能支撑判断的部分。"


def _skill_interpretation(section_key: str, skill_refs: list[str]) -> str:
    parts: list[str] = []
    if "capability_match" in skill_refs:
        parts.append(
            "这些证据需要放在能力匹配框架下读：技术、产品、客户和交付必须互相支撑，单一亮点不足以构成完整商业判断。"
        )
    if "tension_expand" in skill_refs:
        parts.append(
            "更重要的是看张力：增长、研发投入、亏损、现金流和风险如果不能互相解释，叙事就还没有闭合。"
        )
    if "reader_value_translate" in skill_refs and section_key == "cognitive_worldview":
        parts.append(
            "把这套方法迁移到其他公司时，可以先找产品入口，再看客户验证，最后检查收入质量和风险暴露。"
        )
    return " ".join(parts)


def _build_paragraphs(
    section_key: str,
    title: str,
    skill_refs: list[str],
    selected_items: list[tuple[int, EvidenceItem]],
) -> list[str]:
    if not selected_items:
        return []
    intro = _skill_intro(section_key, skill_refs)
    first = _sentences(selected_items, 3)
    second = _sentences(selected_items[3:], 4)
    third = _sentences(selected_items[7:], 4)
    interpretation = _skill_interpretation(section_key, skill_refs)
    paragraphs = [f"{intro}{first}"]
    if second:
        paragraphs.append(f"第二层看证据之间是否互相支持。{second}")
    if third:
        paragraphs.append(f"再往后看边界条件。{third}")
    if interpretation:
        paragraphs.append(interpretation)
    return paragraphs


def _readability_warnings(body: str) -> list[str]:
    warnings: list[str] = []
    if any(token in body for token in FORBIDDEN_RAW_TEXT):
        warnings.append("contains_raw_data_literal")
    paragraphs = [paragraph for paragraph in body.split("\n\n") if paragraph.strip()]
    if any(len(paragraph) > 900 for paragraph in paragraphs):
        warnings.append("paragraph_too_long")
    citation_count = body.count("[C-")
    if citation_count > 14:
        warnings.append("too_many_citations")
    if len(body) > 6500:
        warnings.append("section_too_long")
    return warnings


def write_section(
    *,
    section_key: str,
    title: str,
    skill_refs: list[str],
    prompt_slot: str,
    indexed_items: list[tuple[int, EvidenceItem]],
) -> SectionWriteResult:
    selected_items = _select_items(section_key, indexed_items)
    paragraphs = _build_paragraphs(section_key, title, skill_refs, selected_items)
    body = "\n\n".join(paragraphs).strip()
    citation_ids = [_citation_id(index) for index, _ in selected_items]
    return SectionWriteResult(
        body=body,
        selected_items=selected_items,
        citation_ids=citation_ids,
        readability_warnings=_readability_warnings(body),
    )
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_writer.py -q
```

Expected: PASS.

---

### Task 3: Wire Section Writer Into Section Generator

**Files:**
- Modify: `src/ipo_evidence/models.py`
- Modify: `src/ipo_evidence/section_generator.py`
- Modify: `tests/test_section_generator.py`

- [ ] **Step 1: Add trace readability warnings**

In `src/ipo_evidence/models.py`, update `InternalTrace`:

```python
class InternalTrace(BaseModel):
    section_key: str
    skill_refs: list[str] = Field(default_factory=list)
    prompt_slot: str
    evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    evidence_quality_statuses: list[QualityStatus] = Field(default_factory=list)
    fact_count: int = 0
    missing_contract_fields: list[str] = Field(default_factory=list)
    readability_warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Replace raw body construction**

In `src/ipo_evidence/section_generator.py`, remove `_body_for_items()` and import the writer:

```python
from ipo_evidence.section_writer import write_section
```

Then inside `generate_section_drafts()`, after `items` is collected and before `InternalTrace`, use:

```python
        skill_refs = _string_list(group.get("skill_refs"))
        prompt_slot = group.get("prompt_slot", "narrative_section")
        section_role = group.get("section_role", "main")
        normalized_prompt_slot = (
            prompt_slot if isinstance(prompt_slot, str) else "narrative_section"
        )
        write_result = write_section(
            section_key=section_key,
            title=title,
            skill_refs=skill_refs,
            prompt_slot=normalized_prompt_slot,
            indexed_items=items,
        )
```

Then build `InternalTrace` from selected items:

```python
        trace = InternalTrace(
            section_key=section_key,
            skill_refs=skill_refs,
            prompt_slot=normalized_prompt_slot,
            evidence_ids=[item.evidence_id for _, item in write_result.selected_items],
            citation_ids=write_result.citation_ids,
            evidence_quality_statuses=[
                item.quality_status for _, item in write_result.selected_items
            ],
            fact_count=len(write_result.selected_items),
            missing_contract_fields=missing,
            readability_warnings=write_result.readability_warnings,
        )
```

And set draft body/citation ids from the writer:

```python
        drafts.append(
            SectionDraft(
                section_key=section_key,
                title=title,
                section_role=section_role if isinstance(section_role, str) else "main",
                body=write_result.body,
                citation_ids=write_result.citation_ids,
                internal_trace=trace,
            )
        )
```

- [ ] **Step 3: Update section generator tests**

In `tests/test_section_generator.py`, replace the exact body assertion:

```python
    assert drafts[0].body == "公司主要从事智能硬件产品的研发、生产和销售。[C-001]"
```

with:

```python
    assert "阅读这一节" in drafts[0].body
    assert "公司主要从事智能硬件产品的研发、生产和销售。[C-001]" in drafts[0].body
    assert drafts[0].citation_ids == ["C-001"]
```

In the invalid rank / duplicate test, keep the selected ids expectations strict:

```python
    assert drafts[0].internal_trace.evidence_ids == ["E-001", "E-002", "E-003"]
    assert drafts[0].internal_trace.fact_count == 3
    assert drafts[0].body.count("[C-") == 3
```

- [ ] **Step 4: Run section generator tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_generator.py tests/test_section_writer.py -q
```

Expected: PASS.

---

### Task 4: Add Readability Gate

**Files:**
- Modify: `src/ipo_evidence/quality_gate.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write failing quality gate tests**

Append to `tests/test_quality_gate.py`:

```python
def test_quality_gate_logs_section_with_raw_dict_literal():
    draft = _draft("company_and_industry", 3, [QualityStatus.safe_to_use] * 3)
    draft.body = "公司符合科创属性要求中，对应数据为：{'项目': '营业收入'}。[C-001]"
    draft.internal_trace.readability_warnings = ["contains_raw_data_literal"]

    decisions = apply_quality_gate(
        [draft],
        {"company_and_industry": {"min_fact_count": 2}},
    )

    assert decisions[0].action == "log_only"
    assert "可读性" in decisions[0].reason
    assert decisions[0].suggested_next_steps == ["重写 section draft，移除原始表格字面量。"]


def test_quality_gate_logs_section_with_too_many_citations():
    draft = _draft("company_and_industry", 20, [QualityStatus.safe_to_use] * 20)
    draft.body = " ".join(f"事实{i}。[C-{i:03d}]" for i in range(1, 21))
    draft.internal_trace.readability_warnings = ["too_many_citations"]

    decisions = apply_quality_gate(
        [draft],
        {"company_and_industry": {"min_fact_count": 2}},
    )

    assert decisions[0].action == "log_only"
    assert "可读性" in decisions[0].reason
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_quality_gate.py -q
```

Expected: FAIL because `apply_quality_gate()` does not inspect `readability_warnings`.

- [ ] **Step 3: Implement readability rejection**

In `src/ipo_evidence/quality_gate.py`, add:

```python
def _readability_reason(warnings: list[str]) -> str | None:
    if not warnings:
        return None
    labels = {
        "contains_raw_data_literal": "包含原始表格字面量",
        "paragraph_too_long": "段落过长",
        "too_many_citations": "引用过密",
        "section_too_long": "section 过长",
    }
    joined = "、".join(labels.get(warning, warning) for warning in warnings)
    return f"section draft 可读性未达标：{joined}。"
```

At the top of the loop in `apply_quality_gate()`, after `policy` is loaded:

```python
        readability_reason = _readability_reason(draft.internal_trace.readability_warnings)
        if readability_reason:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action="log_only",
                    reason=readability_reason,
                    title=draft.title,
                    evidence_count=draft.internal_trace.fact_count,
                    min_fact_count=_min_fact_count(policy),
                    strength=_strongest_strength(draft.internal_trace.evidence_quality_statuses),
                    required_strength=_min_strength(policy),
                    needed_evidence=[],
                    suggested_next_step="重写 section draft，移除不可读内容。",
                    suggested_next_steps=["重写 section draft，移除原始表格字面量。"],
                )
            )
            continue
```

- [ ] **Step 4: Run quality gate tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_quality_gate.py -q
```

Expected: PASS.

---

### Task 5: Add Pipeline-Level Readability Regression

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add final report readability assertions to existing pipeline tests**

In `test_run_one_creates_document_package()`, after `report_text` is read, add:

```python
    paragraphs = [part.strip() for part in report_text.split("\n\n") if part.strip()]
    assert all(len(paragraph) < 1200 for paragraph in paragraphs)
    assert report_text.count("{'") == 0
    assert "对应数据为" not in report_text
    assert report_text.count("[C-") <= 50
```

- [ ] **Step 2: Add a focused regenerate regression for large input groups**

Append this test to `tests/test_pipeline.py`:

```python
def test_regenerate_report_does_not_dump_large_report_inputs(tmp_path: Path):
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
    report_inputs = read_json(package / "report_inputs.json")
    first_group = report_inputs["section_groups"][0]
    original_refs = list(first_group["evidence_refs"])
    first_group["evidence_refs"] = original_refs * 20
    (package / "report_inputs.json").write_text(
        json.dumps(report_inputs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    regenerate_report(doc_id, docs)

    report_text = (package / "report.md").read_text(encoding="utf-8")
    paragraphs = [part.strip() for part in report_text.split("\n\n") if part.strip()]
    assert all(len(paragraph) < 1200 for paragraph in paragraphs)
    assert report_text.count("[C-") <= 50
    assert "对应数据为" not in report_text
    assert "{'" not in report_text
```

- [ ] **Step 3: Run pipeline tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_pipeline.py -q
```

Expected: PASS.

---

### Task 6: Regenerate Real Report and Verify Output Quality

**Files:**
- Generated local artifacts under `data/docs/doc_beaac21be4b3/`

- [ ] **Step 1: Regenerate the real report**

Run:

```powershell
$env:PYTHONPATH='src'; @'
from pathlib import Path
from ipo_evidence.pipeline import regenerate_report

regenerate_report("doc_beaac21be4b3", Path("data/docs"))
'@ | python -
```

Expected: command exits with code 0.

- [ ] **Step 2: Check real report readability metrics**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; @'
from pathlib import Path

text = Path("data/docs/doc_beaac21be4b3/report.md").read_text(encoding="utf-8")
paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
print("chars", len(text))
print("lines", text.count("\n") + 1)
print("paragraphs", len(paragraphs))
print("top_para_lengths", sorted([len(part) for part in paragraphs], reverse=True)[:5])
print("citations", text.count("[C-"))
print("raw_dict_literals", text.count("{'"))
print("corresponding_data_phrase", text.count("对应数据为"))
'@ | python -
```

Expected:

```text
raw_dict_literals 0
corresponding_data_phrase 0
```

Also expected:

```text
citations <= 50
max(top_para_lengths) < 1200
```

- [ ] **Step 3: Verify citation coverage**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; @'
import json
import re
from pathlib import Path

pkg = Path("data/docs/doc_beaac21be4b3")
report = (pkg / "report.md").read_text(encoding="utf-8")
citations = json.loads((pkg / "citation.json").read_text(encoding="utf-8"))
valid = {citation["citation_id"] for citation in citations}
used = set(re.findall(r"\[(C-\d{3})\]", report))
print("used", len(used))
print("missing", sorted(used - valid))
'@ | python -
```

Expected:

```text
missing []
```

---

### Task 7: Full Verification

**Files:**
- No direct edits.

- [ ] **Step 1: Run all Python tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run Web build**

Run:

```powershell
npm --prefix web run build
```

Expected: build succeeds.

- [ ] **Step 3: Run Git checks**

Run:

```powershell
git diff --check
git status --short
```

Expected:

- `git diff --check` exits 0.
- `git status --short` shows only intentional source/test/doc changes and regenerated report artifacts if they are tracked.

---

## Self-Review

**Spec coverage:** This plan implements the missing part of `docs/report_generation_architecture.md`: `section_generator` now produces natural section drafts, `skill_refs` become deterministic interpretation moves, `prompt_slot` stays part of the trace, `quality_gate` blocks unreadable drafts, and final `report.md` remains assembled from section drafts.

**Placeholder scan:** No `TBD`, `TODO`, or undefined future behavior remains in the plan. Each implementation task includes exact files, code, commands, and expected results.

**Type consistency:** `SectionWriteResult`, `write_section()`, `InternalTrace.readability_warnings`, and existing `SectionDraft` / `QualityGateDecision` fields are used consistently across tasks.

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-07-01-report-generation-pr2-5-repair.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
