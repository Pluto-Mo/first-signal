# Report Inputs Architecture Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first deployable slice of `docs/report_generation_architecture.md` without breaking the existing deterministic report pipeline.

**Architecture:** Keep `evidence_packet -> citation.json` unchanged. Extend `report_inputs.json` into a richer dispatch contract, add profile/skill/prompt config files, introduce deterministic section drafts, quality gate decisions, and `analysis_log.json`, then let the current report generator continue producing `report.md` until a later stitcher PR replaces it.

**Tech Stack:** Python 3.11, Pydantic, PyYAML, pytest, local JSON/JSONL filesystem assets.

---

## Scope

This plan implements the first safe phase from `docs/report_generation_architecture.md`:

- Extend `report_inputs.section_groups[]` with `skill_refs`, `evidence_policy`, `output_contract`, and `section_role`.
- Add config folders under `configs/report_profiles/`, `configs/skills/`, and `configs/prompts/`.
- Add deterministic `section_generator`, `quality_gate`, and `analysis_log` modules.
- Write `analysis_log.json` during `run_one()` and `regenerate_report()`.
- Preserve current `report.md`, `citation.json`, `reader_bundle.json`, and citation numbering behavior.

This plan does not implement external evidence types, LLM calls, or full report stitching. Those remain later phases.

## File Structure

- Modify `configs/report_prompt.yaml`
  - Add default `skill_refs`, `evidence_policy`, `output_contract`, and `section_role` to current views.
- Create `configs/report_profiles/base.yaml`
  - Store shared attention fields and default report profile metadata.
- Create `configs/report_profiles/technology_company.yaml`
  - Store the current AI/technology company attention fields.
- Create `configs/report_profiles/consumer_product.yaml`
  - Store consumer product attention fields from the architecture proposal.
- Create `configs/report_profiles/cyclical_industry.yaml`
  - Store cyclical industry attention fields from the architecture proposal.
- Create `configs/skills/business_goal_decompose.yaml`
- Create `configs/skills/capability_match.yaml`
- Create `configs/skills/disclosure_gap_scan.yaml`
- Create `configs/skills/reader_value_translate.yaml`
- Create `configs/skills/tension_expand.yaml`
  - Each file declares a small, stable reading action.
- Create `configs/prompts/section_writer.yaml`
- Create `configs/prompts/stitch_writer.yaml`
- Create `configs/prompts/citation_checker.yaml`
  - Prompt config exists for dispatch only in this phase.
- Modify `src/ipo_evidence/models.py`
  - Add `SectionDraft`, `InternalTrace`, `QualityGateDecision`, `AnalysisLogEntry`, and `AnalysisLog`.
- Modify `src/ipo_evidence/report_inputs.py`
  - Emit the richer dispatch contract while preserving current fields.
- Create `src/ipo_evidence/section_generator.py`
  - Build deterministic section drafts from `report_inputs` and `evidence_packet`.
- Create `src/ipo_evidence/quality_gate.py`
  - Classify drafts as `include`, `merge`, or `log_only` using `evidence_policy`.
- Create `src/ipo_evidence/analysis_log.py`
  - Convert quality gate decisions into `analysis_log.json`.
- Modify `src/ipo_evidence/pipeline.py`
  - Write `analysis_log.json` alongside existing report artifacts.
- Modify tests:
  - `tests/test_report_inputs.py`
  - `tests/test_section_generator.py`
  - `tests/test_quality_gate.py`
  - `tests/test_analysis_log.py`
  - `tests/test_pipeline.py`

---

### Task 1: Extend Report Input Contract Tests

**Files:**
- Modify: `tests/test_report_inputs.py`
- Modify later: `src/ipo_evidence/report_inputs.py`
- Modify later: `configs/report_prompt.yaml`

- [ ] **Step 1: Add failing test for extended dispatch fields**

Append this test to `tests/test_report_inputs.py`:

```python
def test_build_report_inputs_adds_architecture_dispatch_contract():
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

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)
    section = report_inputs["section_groups"][0]

    assert section["skill_refs"] == [
        "business_goal_decompose",
        "capability_match",
        "reader_value_translate",
    ]
    assert section["evidence_policy"] == {
        "min_fact_count": 2,
        "min_strength": "medium",
        "weak_evidence": "merge_into_related_section",
        "no_evidence": "log_only",
    }
    assert section["output_contract"] == {
        "shape": "narrative_section",
        "requires": ["core_claim", "evidence_chain", "reader_value"],
    }
    assert section["section_role"] == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_report_inputs.py::test_build_report_inputs_adds_architecture_dispatch_contract -q
```

Expected: FAIL with `KeyError: 'skill_refs'`.

- [ ] **Step 3: Add config fields to `configs/report_prompt.yaml`**

For each current `input_views.*` entry, add:

```yaml
    skill_refs:
      - "business_goal_decompose"
      - "capability_match"
      - "reader_value_translate"
    evidence_policy:
      min_fact_count: 2
      min_strength: "medium"
      weak_evidence: "merge_into_related_section"
      no_evidence: "log_only"
    output_contract:
      shape: "narrative_section"
      requires:
        - "core_claim"
        - "evidence_chain"
        - "reader_value"
    section_role: "main"
```

For `cognitive_worldview`, use:

```yaml
    skill_refs:
      - "reader_value_translate"
      - "tension_expand"
```

- [ ] **Step 4: Update `src/ipo_evidence/report_inputs.py`**

Add these helpers above `build_report_inputs()`:

```python
DEFAULT_EVIDENCE_POLICY = {
    "min_fact_count": 2,
    "min_strength": "medium",
    "weak_evidence": "merge_into_related_section",
    "no_evidence": "log_only",
}

DEFAULT_OUTPUT_CONTRACT = {
    "shape": "narrative_section",
    "requires": ["core_claim", "evidence_chain", "reader_value"],
}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dict_value(value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return fallback.copy()
```

Then add these fields to each `section_groups.append({...})` payload:

```python
"skill_refs": _string_list(template.get("skill_refs")),
"evidence_policy": _dict_value(template.get("evidence_policy"), DEFAULT_EVIDENCE_POLICY),
"output_contract": _dict_value(template.get("output_contract"), DEFAULT_OUTPUT_CONTRACT),
"section_role": template.get("section_role", "main"),
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_report_inputs.py -q
```

Expected: all `test_report_inputs.py` tests pass.

- [ ] **Step 6: Commit**

```powershell
git add configs/report_prompt.yaml src/ipo_evidence/report_inputs.py tests/test_report_inputs.py
git commit -m "feat: extend report input dispatch contract"
```

---

### Task 2: Add Profile, Skill, and Prompt Config Files

**Files:**
- Create: `configs/report_profiles/base.yaml`
- Create: `configs/report_profiles/technology_company.yaml`
- Create: `configs/report_profiles/consumer_product.yaml`
- Create: `configs/report_profiles/cyclical_industry.yaml`
- Create: `configs/skills/business_goal_decompose.yaml`
- Create: `configs/skills/capability_match.yaml`
- Create: `configs/skills/disclosure_gap_scan.yaml`
- Create: `configs/skills/reader_value_translate.yaml`
- Create: `configs/skills/tension_expand.yaml`
- Create: `configs/prompts/section_writer.yaml`
- Create: `configs/prompts/stitch_writer.yaml`
- Create: `configs/prompts/citation_checker.yaml`
- Test: `tests/test_report_inputs.py`

- [ ] **Step 1: Add failing config existence test**

Append to `tests/test_report_inputs.py`:

```python
from ipo_evidence.config import load_yaml


def test_architecture_config_files_are_loadable():
    paths = [
        "configs/report_profiles/base.yaml",
        "configs/report_profiles/technology_company.yaml",
        "configs/report_profiles/consumer_product.yaml",
        "configs/report_profiles/cyclical_industry.yaml",
        "configs/skills/business_goal_decompose.yaml",
        "configs/skills/capability_match.yaml",
        "configs/skills/disclosure_gap_scan.yaml",
        "configs/skills/reader_value_translate.yaml",
        "configs/skills/tension_expand.yaml",
        "configs/prompts/section_writer.yaml",
        "configs/prompts/stitch_writer.yaml",
        "configs/prompts/citation_checker.yaml",
    ]

    for path in paths:
        config = load_yaml(path)
        assert isinstance(config, dict)
        assert config
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_report_inputs.py::test_architecture_config_files_are_loadable -q
```

Expected: FAIL with `FileNotFoundError` for `configs/report_profiles/base.yaml`.

- [ ] **Step 3: Create report profile configs**

Create `configs/report_profiles/base.yaml`:

```yaml
profile_key: "base"
title: "通用招股书解读"
attention_fields:
  - "产品入口"
  - "行业空间"
  - "客户验证"
  - "收入质量"
  - "研发效率"
  - "现金流"
  - "风险暴露"
default_skill_refs:
  - "business_goal_decompose"
  - "capability_match"
  - "reader_value_translate"
```

Create `configs/report_profiles/technology_company.yaml`:

```yaml
profile_key: "technology_company"
title: "技术公司解读"
extends: "base"
attention_fields:
  - "研发人员"
  - "核心技术"
  - "专利"
  - "产品化进度"
  - "客户验证"
  - "替代风险"
```

Create `configs/report_profiles/consumer_product.yaml`:

```yaml
profile_key: "consumer_product"
title: "消费产品公司解读"
extends: "base"
attention_fields:
  - "产品定位"
  - "价格带"
  - "渠道结构"
  - "平台依赖"
  - "销售费用"
  - "用户口碑"
  - "售后服务"
  - "供应链"
```

Create `configs/report_profiles/cyclical_industry.yaml`:

```yaml
profile_key: "cyclical_industry"
title: "周期行业公司解读"
extends: "base"
attention_fields:
  - "产能"
  - "价格周期"
  - "原材料成本"
  - "库存"
  - "资本开支"
  - "行业供需"
```

- [ ] **Step 4: Create skill configs**

Create `configs/skills/business_goal_decompose.yaml`:

```yaml
skill_key: "business_goal_decompose"
title: "业务目标拆解"
action: "把披露事实拆成产品、客户、收入和资源配置问题。"
requires:
  - "core_claim"
produces:
  - "business_question"
```

Create `configs/skills/capability_match.yaml`:

```yaml
skill_key: "capability_match"
title: "能力匹配"
action: "检查产品、研发、客户和交付能力是否支撑披露中的商业叙事。"
requires:
  - "evidence_chain"
produces:
  - "capability_judgment"
```

Create `configs/skills/disclosure_gap_scan.yaml`:

```yaml
skill_key: "disclosure_gap_scan"
title: "披露缺口识别"
action: "识别当前证据无法支撑的判断，并记录需要补充的证据。"
requires:
  - "evidence_chain"
produces:
  - "gap_note"
```

Create `configs/skills/reader_value_translate.yaml`:

```yaml
skill_key: "reader_value_translate"
title: "读者价值翻译"
action: "把事实和判断转成个人读者能继续研究的问题。"
requires:
  - "core_claim"
produces:
  - "reader_value"
```

Create `configs/skills/tension_expand.yaml`:

```yaml
skill_key: "tension_expand"
title: "矛盾张力展开"
action: "把增长、投入、现金流、风险之间的张力讲清楚。"
requires:
  - "core_claim"
  - "evidence_chain"
produces:
  - "tension_summary"
```

- [ ] **Step 5: Create prompt configs**

Create `configs/prompts/section_writer.yaml`:

```yaml
prompt_slot: "narrative_section"
purpose: "把一个 section draft 写成自然正文。"
rules:
  - "只使用 evidence_refs 对应证据。"
  - "事实句必须带 citation id。"
  - "不写内部系统词。"
```

Create `configs/prompts/stitch_writer.yaml`:

```yaml
prompt_slot: "stitch_writer"
purpose: "整合合格 section drafts，处理排序、去重和过渡。"
rules:
  - "不新增事实。"
  - "不改变 citation id。"
  - "删除低完成度内容。"
```

Create `configs/prompts/citation_checker.yaml`:

```yaml
prompt_slot: "citation_checker"
purpose: "检查报告引用是否能回到 citation.json。"
rules:
  - "报告中的 citation id 必须存在。"
  - "citation 必须保留本地定位字段。"
```

- [ ] **Step 6: Run focused test**

Run:

```powershell
python -m pytest tests/test_report_inputs.py::test_architecture_config_files_are_loadable -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add configs/report_profiles configs/skills configs/prompts tests/test_report_inputs.py
git commit -m "feat: add report architecture configs"
```

---

### Task 3: Add Section Draft Models and Generator

**Files:**
- Modify: `src/ipo_evidence/models.py`
- Create: `src/ipo_evidence/section_generator.py`
- Test: `tests/test_section_generator.py`

- [ ] **Step 1: Write failing generator test**

Create `tests/test_section_generator.py`:

```python
from ipo_evidence.models import EvidenceItem, EvidencePacket, QualityStatus
from ipo_evidence.section_generator import generate_section_drafts


def test_generate_section_drafts_uses_section_evidence_refs_and_trace():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="about_company",
                claim_summary="公司主要从事智能硬件产品的研发、生产和销售。",
                source_type="text_quote",
                source_file="sample.pdf",
                page_number=2,
                block_id="B-001",
                section_path=["发行人基本情况"],
                quote="公司主要从事智能硬件产品的研发、生产和销售。",
                quality_status=QualityStatus.safe_to_use,
            )
        ],
    )
    report_inputs = {
        "doc_id": "doc_test",
        "company_name": "测试股份有限公司",
        "section_groups": [
            {
                "section_key": "company_and_industry",
                "title": "公司介绍与行业概况",
                "prompt_slot": "narrative_section",
                "skill_refs": ["business_goal_decompose"],
                "evidence_refs": [{"evidence_id": "E-001", "rank": 1}],
                "evidence_policy": {"min_fact_count": 1, "no_evidence": "log_only"},
                "output_contract": {
                    "shape": "narrative_section",
                    "requires": ["core_claim", "evidence_chain", "reader_value"],
                },
                "section_role": "main",
            }
        ],
    }

    drafts = generate_section_drafts(packet, report_inputs)

    assert len(drafts) == 1
    assert drafts[0].section_key == "company_and_industry"
    assert drafts[0].title == "公司介绍与行业概况"
    assert drafts[0].body == "公司主要从事智能硬件产品的研发、生产和销售。[C-001]"
    assert drafts[0].citation_ids == ["C-001"]
    assert drafts[0].internal_trace.skill_refs == ["business_goal_decompose"]
    assert drafts[0].internal_trace.evidence_ids == ["E-001"]
    assert drafts[0].internal_trace.fact_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_section_generator.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ipo_evidence.section_generator'`.

- [ ] **Step 3: Add models**

Append to `src/ipo_evidence/models.py` before `JsonDict`:

```python
class InternalTrace(BaseModel):
    section_key: str
    skill_refs: list[str] = Field(default_factory=list)
    prompt_slot: str
    evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    fact_count: int = 0
    missing_contract_fields: list[str] = Field(default_factory=list)


class SectionDraft(BaseModel):
    section_key: str
    title: str
    section_role: str = "main"
    body: str
    citation_ids: list[str] = Field(default_factory=list)
    internal_trace: InternalTrace
```

- [ ] **Step 4: Create generator**

Create `src/ipo_evidence/section_generator.py`:

```python
from __future__ import annotations

from typing import Any

from ipo_evidence.models import EvidenceItem, EvidencePacket, InternalTrace, SectionDraft


def _citation_id(index: int) -> str:
    return f"C-{index:03d}"


def _item_index(packet: EvidencePacket) -> dict[str, tuple[int, EvidenceItem]]:
    return {item.evidence_id: (index, item) for index, item in enumerate(packet.items, start=1)}


def _section_groups(report_inputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report_inputs:
        return []
    groups = report_inputs.get("section_groups", [])
    if not isinstance(groups, list):
        return []
    return [group for group in groups if isinstance(group, dict)]


def _clean_sentence(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split()).rstrip("。；;，,") + "。"


def _body_for_items(items: list[tuple[int, EvidenceItem]]) -> tuple[str, list[str]]:
    sentences: list[str] = []
    citation_ids: list[str] = []
    for index, item in items:
        citation_id = _citation_id(index)
        citation_ids.append(citation_id)
        sentences.append(f"{_clean_sentence(item.claim_summary)}[{citation_id}]")
    return " ".join(sentences), citation_ids


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def generate_section_drafts(
    packet: EvidencePacket,
    report_inputs: dict[str, Any] | None,
) -> list[SectionDraft]:
    indexed = _item_index(packet)
    drafts: list[SectionDraft] = []
    for group in _section_groups(report_inputs):
        section_key = group.get("section_key")
        title = group.get("title")
        if not isinstance(section_key, str) or not isinstance(title, str):
            continue

        refs = group.get("evidence_refs", [])
        items: list[tuple[int, EvidenceItem]] = []
        if isinstance(refs, list):
            for ref in sorted(refs, key=lambda ref: ref.get("rank", 99) if isinstance(ref, dict) else 99):
                if not isinstance(ref, dict):
                    continue
                evidence_id = ref.get("evidence_id")
                if isinstance(evidence_id, str) and evidence_id in indexed:
                    items.append(indexed[evidence_id])

        body, citation_ids = _body_for_items(items)
        required = _string_list(group.get("output_contract", {}).get("requires") if isinstance(group.get("output_contract"), dict) else [])
        missing = [field for field in required if field not in {"core_claim", "evidence_chain", "reader_value"}]
        trace = InternalTrace(
            section_key=section_key,
            skill_refs=_string_list(group.get("skill_refs")),
            prompt_slot=group.get("prompt_slot", "narrative_section"),
            evidence_ids=[item.evidence_id for _, item in items],
            citation_ids=citation_ids,
            fact_count=len(items),
            missing_contract_fields=missing,
        )
        drafts.append(
            SectionDraft(
                section_key=section_key,
                title=title,
                section_role=group.get("section_role", "main"),
                body=body,
                citation_ids=citation_ids,
                internal_trace=trace,
            )
        )
    return drafts
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_section_generator.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/ipo_evidence/models.py src/ipo_evidence/section_generator.py tests/test_section_generator.py
git commit -m "feat: generate section drafts with trace"
```

---

### Task 4: Add Quality Gate and Analysis Log

**Files:**
- Modify: `src/ipo_evidence/models.py`
- Create: `src/ipo_evidence/quality_gate.py`
- Create: `src/ipo_evidence/analysis_log.py`
- Test: `tests/test_quality_gate.py`
- Test: `tests/test_analysis_log.py`

- [ ] **Step 1: Write failing quality gate test**

Create `tests/test_quality_gate.py`:

```python
from ipo_evidence.models import InternalTrace, SectionDraft
from ipo_evidence.quality_gate import apply_quality_gate


def test_quality_gate_logs_empty_required_section():
    draft = SectionDraft(
        section_key="platform_dependency",
        title="平台依赖",
        section_role="main",
        body="",
        citation_ids=[],
        internal_trace=InternalTrace(
            section_key="platform_dependency",
            skill_refs=["disclosure_gap_scan"],
            prompt_slot="narrative_section",
            evidence_ids=[],
            citation_ids=[],
            fact_count=0,
        ),
    )
    policies = {
        "platform_dependency": {
            "min_fact_count": 2,
            "weak_evidence": "merge_into_related_section",
            "no_evidence": "log_only",
        }
    }

    decisions = apply_quality_gate([draft], policies)

    assert decisions[0].section_key == "platform_dependency"
    assert decisions[0].action == "log_only"
    assert decisions[0].reason == "证据数量 0 低于最低要求 2。"
```

- [ ] **Step 2: Write failing analysis log test**

Create `tests/test_analysis_log.py`:

```python
from ipo_evidence.analysis_log import build_analysis_log
from ipo_evidence.models import QualityGateDecision


def test_build_analysis_log_records_log_only_decisions():
    decisions = [
        QualityGateDecision(
            section_key="platform_dependency",
            action="log_only",
            reason="证据数量 0 低于最低要求 2。",
            needed_evidence=["补充 platform_dependency 的可引用证据"],
            suggested_next_step="补充证据后重新生成该 section。",
        )
    ]

    log = build_analysis_log("doc_test", decisions)

    assert log.doc_id == "doc_test"
    assert len(log.skipped_or_merged) == 1
    assert log.skipped_or_merged[0].section_key == "platform_dependency"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_quality_gate.py tests/test_analysis_log.py -q
```

Expected: FAIL because modules or models do not exist.

- [ ] **Step 4: Add models**

Append to `src/ipo_evidence/models.py` after `SectionDraft`:

```python
class QualityGateDecision(BaseModel):
    section_key: str
    action: Literal["include", "merge", "log_only"]
    reason: str
    needed_evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class AnalysisLogEntry(BaseModel):
    section_key: str
    reason: str
    needed_evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class AnalysisLog(BaseModel):
    doc_id: str
    skipped_or_merged: list[AnalysisLogEntry] = Field(default_factory=list)
```

- [ ] **Step 5: Create `src/ipo_evidence/quality_gate.py`**

```python
from __future__ import annotations

from typing import Any

from ipo_evidence.models import QualityGateDecision, SectionDraft


def _min_fact_count(policy: dict[str, Any]) -> int:
    value = policy.get("min_fact_count", 1)
    return value if isinstance(value, int) and value >= 0 else 1


def _action_for_weak(policy: dict[str, Any]) -> str:
    value = policy.get("weak_evidence", "merge_into_related_section")
    if value == "merge_into_related_section":
        return "merge"
    return "log_only"


def apply_quality_gate(
    drafts: list[SectionDraft],
    policies_by_section: dict[str, dict[str, Any]],
) -> list[QualityGateDecision]:
    decisions: list[QualityGateDecision] = []
    for draft in drafts:
        policy = policies_by_section.get(draft.section_key, {})
        min_fact_count = _min_fact_count(policy)
        fact_count = draft.internal_trace.fact_count

        if fact_count == 0:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action="log_only",
                    reason=f"证据数量 {fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的可引用证据"],
                    suggested_next_step="补充证据后重新生成该 section。",
                )
            )
            continue

        if fact_count < min_fact_count:
            decisions.append(
                QualityGateDecision(
                    section_key=draft.section_key,
                    action=_action_for_weak(policy),
                    reason=f"证据数量 {fact_count} 低于最低要求 {min_fact_count}。",
                    needed_evidence=[f"补充 {draft.section_key} 的 supporting evidence"],
                    suggested_next_step="合并到相关段落，或补足证据后独立成段。",
                )
            )
            continue

        decisions.append(
            QualityGateDecision(
                section_key=draft.section_key,
                action="include",
                reason=f"证据数量 {fact_count} 达到最低要求 {min_fact_count}。",
            )
        )
    return decisions
```

- [ ] **Step 6: Create `src/ipo_evidence/analysis_log.py`**

```python
from __future__ import annotations

from ipo_evidence.models import AnalysisLog, AnalysisLogEntry, QualityGateDecision


def build_analysis_log(doc_id: str, decisions: list[QualityGateDecision]) -> AnalysisLog:
    entries = [
        AnalysisLogEntry(
            section_key=decision.section_key,
            reason=decision.reason,
            needed_evidence=decision.needed_evidence,
            suggested_next_step=decision.suggested_next_step,
        )
        for decision in decisions
        if decision.action in {"merge", "log_only"}
    ]
    return AnalysisLog(doc_id=doc_id, skipped_or_merged=entries)
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
python -m pytest tests/test_quality_gate.py tests/test_analysis_log.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add src/ipo_evidence/models.py src/ipo_evidence/quality_gate.py src/ipo_evidence/analysis_log.py tests/test_quality_gate.py tests/test_analysis_log.py
git commit -m "feat: add report quality gate and analysis log"
```

---

### Task 5: Write Analysis Log in Pipeline

**Files:**
- Modify: `src/ipo_evidence/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing pipeline test assertion**

In `tests/test_pipeline.py::test_run_one_creates_document_package`, add:

```python
assert (package / "analysis_log.json").exists()
```

After reading `docs_index`, add:

```python
analysis_log = read_json(package / "analysis_log.json")
assert analysis_log["doc_id"] == doc_id
assert "skipped_or_merged" in analysis_log
```

In `test_regenerate_report_rewrites_report_and_citations`, add:

```python
analysis_log_path = package / "analysis_log.json"
analysis_log_path.write_text('{"doc_id":"broken","skipped_or_merged":[{"section_key":"old","reason":"old"}]}\n', encoding="utf-8")
```

After reading `web_index`, add:

```python
analysis_log = read_json(analysis_log_path)
assert analysis_log["doc_id"] == doc_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_pipeline.py::test_run_one_creates_document_package tests/test_pipeline.py::test_regenerate_report_rewrites_report_and_citations -q
```

Expected: FAIL because `analysis_log.json` is missing.

- [ ] **Step 3: Update pipeline imports**

In `src/ipo_evidence/pipeline.py`, add:

```python
from ipo_evidence.analysis_log import build_analysis_log
from ipo_evidence.quality_gate import apply_quality_gate
from ipo_evidence.section_generator import generate_section_drafts
```

- [ ] **Step 4: Add helper to extract policies**

Add above `_write_report_artifacts()`:

```python
def _evidence_policies(report_inputs: dict | None) -> dict[str, dict]:
    if not report_inputs:
        return {}
    groups = report_inputs.get("section_groups", [])
    if not isinstance(groups, list):
        return {}
    policies: dict[str, dict] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        section_key = group.get("section_key")
        policy = group.get("evidence_policy")
        if isinstance(section_key, str) and isinstance(policy, dict):
            policies[section_key] = policy
    return policies
```

- [ ] **Step 5: Write `analysis_log.json` in `_write_report_artifacts()`**

Inside `_write_report_artifacts()`, after `citations = build_citations(packet)`, add:

```python
    section_drafts = generate_section_drafts(packet, report_inputs)
    quality_decisions = apply_quality_gate(section_drafts, _evidence_policies(report_inputs))
    analysis_log = build_analysis_log(packet.doc_id, quality_decisions)
```

Before writing `reader_bundle.json`, add:

```python
    write_json(package_dir / "analysis_log.json", analysis_log)
```

- [ ] **Step 6: Run focused pipeline tests**

Run:

```powershell
python -m pytest tests/test_pipeline.py::test_run_one_creates_document_package tests/test_pipeline.py::test_regenerate_report_rewrites_report_and_citations -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/ipo_evidence/pipeline.py tests/test_pipeline.py
git commit -m "feat: write report analysis log"
```

---

### Task 6: Full Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run full Python test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run git diff check**

Run:

```powershell
git diff --check
```

Expected: exit code 0.

- [ ] **Step 3: Check worktree**

Run:

```powershell
git status --short
```

Expected: no unstaged changes after all commits.

- [ ] **Step 4: Optional web validation**

Run only if `web/vite.config.ts` or reader files changed during execution:

```powershell
npm --prefix web run test
npm --prefix web run build
```

Expected: both commands exit code 0.

---

## Self-Review

- Spec coverage:
  - `report_inputs` dispatch contract: Task 1.
  - profiles, skills, prompts: Task 2.
  - section draft and internal trace: Task 3.
  - quality gate and analysis log: Task 4.
  - pipeline artifact writing: Task 5.
  - citation generated from evidence packet: preserved by not modifying `citation_layer.py`.
  - stitcher and full report rewrite: intentionally deferred to Phase 2 to avoid replacing the existing long-form generator in the same PR.
- Placeholder scan:
  - No placeholder markers or open-ended implementation instructions.
  - Deferred items are explicitly out of Phase 1 scope.
- Type consistency:
  - `SectionDraft`, `InternalTrace`, `QualityGateDecision`, `AnalysisLogEntry`, and `AnalysisLog` are defined before use.
  - `apply_quality_gate()` and `build_analysis_log()` signatures match tests and pipeline usage.
