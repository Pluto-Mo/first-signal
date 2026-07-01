# Profile-Driven Report Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the selected report profile actively shape `report_inputs.section_groups`, instead of only appearing as top-level metadata.

**Architecture:** Extend report profile YAML with per-section focus fields, load them through `ReportProfile`, and merge those fields into each generated section group as `profile_focus_points` plus profile-enriched `focus_points`. Keep this PR in the dispatch layer only: no parser/evidence/citation changes, no LLM calls, and no rewrite of section generation behavior. During `regenerate_report`, refresh profile-derived section metadata while preserving user-edited evidence refs and evidence policies.

**Tech Stack:** Python 3, PyYAML via existing `load_yaml`, dataclasses, pytest.

---

## Scope

This PR addresses the remaining architecture gap:

```text
1. 根据 company_profile 选择 report profile
2. report_inputs 根据 profile 生成 section_groups
```

Already implemented before this PR:

- profile selection and top-level `profile_key/profile_title/attention_fields`
- skill/prompt runtime loading
- section generation from `skill_refs` and `prompt_slot`
- quality gate and analysis log
- stitch cleanup

Out of scope for this PR:

- Weak evidence true merge into neighboring sections
- `citation_checker.yaml` as a separate runtime
- `quality_notes.md`
- `external_fact`, `calculated_metric`, `cross_doc_fact`, `visual_fact`
- Changing final report wording

## File Structure

- Modify `configs/report_profiles/base.yaml`
  - Add `section_focus` defaults for existing section keys.

- Modify `configs/report_profiles/consumer_product.yaml`
  - Add consumer-product section focus fields.

- Modify `configs/report_profiles/technology_company.yaml`
  - Add technology section focus fields.

- Modify `configs/report_profiles/cyclical_industry.yaml`
  - Add cyclical section focus fields.

- Modify `src/ipo_evidence/report_profiles.py`
  - Add `section_focus: dict[str, list[str]]` to `ReportProfile`.
  - Merge inherited `section_focus` by section key with dedupe.

- Modify `src/ipo_evidence/report_inputs.py`
  - Load profile before building groups.
  - Add `profile_key` and `profile_focus_points` to each section group.
  - Merge template `focus_points` with profile-specific focus points.

- Modify `src/ipo_evidence/pipeline.py`
  - Refresh profile-derived section group metadata during `regenerate_report`.
  - Preserve user-edited `evidence_refs`, `evidence_policy`, and `output_contract`.

- Modify tests:
  - `tests/test_report_profiles.py`
  - `tests/test_report_inputs.py`
  - `tests/test_pipeline.py`

---

### Task 1: Load Per-Section Focus From Profiles

**Files:**
- Modify: `configs/report_profiles/base.yaml`
- Modify: `configs/report_profiles/consumer_product.yaml`
- Modify: `configs/report_profiles/technology_company.yaml`
- Modify: `configs/report_profiles/cyclical_industry.yaml`
- Modify: `src/ipo_evidence/report_profiles.py`
- Test: `tests/test_report_profiles.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_report_profiles.py`:

```python
def test_load_report_profile_merges_section_focus_from_parent():
    profile = load_report_profile("technology_company")

    assert "产品入口" in profile.section_focus["company_and_industry"]
    assert "核心技术" in profile.section_focus["company_and_industry"]
    assert profile.section_focus["company_and_industry"].count("客户验证") == 1


def test_load_report_profile_exposes_consumer_section_focus():
    profile = load_report_profile("consumer_product")

    assert "渠道结构" in profile.section_focus["company_and_industry"]
    assert "平台依赖" in profile.section_focus["personal_investment"]
    assert "用户口碑" in profile.section_focus["cognitive_worldview"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_profiles.py -q
```

Expected: FAIL because `ReportProfile.section_focus` does not exist.

- [ ] **Step 3: Add YAML `section_focus` fields**

Append to `configs/report_profiles/base.yaml`:

```yaml
section_focus:
  company_and_industry:
    - "产品入口"
    - "行业空间"
    - "客户验证"
  personal_investment:
    - "收入质量"
    - "研发效率"
    - "现金流"
    - "风险暴露"
  cognitive_worldview:
    - "业务模式"
    - "产品入口"
    - "证据边界"
```

Append to `configs/report_profiles/consumer_product.yaml`:

```yaml
section_focus:
  company_and_industry:
    - "产品定位"
    - "渠道结构"
    - "供应链"
  personal_investment:
    - "价格带"
    - "平台依赖"
    - "销售费用"
    - "售后服务"
  cognitive_worldview:
    - "用户口碑"
    - "渠道结构"
    - "供应链"
```

Append to `configs/report_profiles/technology_company.yaml`:

```yaml
section_focus:
  company_and_industry:
    - "核心技术"
    - "产品化进度"
    - "客户验证"
  personal_investment:
    - "研发人员"
    - "专利"
    - "替代风险"
  cognitive_worldview:
    - "核心技术"
    - "客户验证"
    - "替代风险"
```

Append to `configs/report_profiles/cyclical_industry.yaml`:

```yaml
section_focus:
  company_and_industry:
    - "行业供需"
    - "产能"
    - "价格周期"
  personal_investment:
    - "原材料成本"
    - "库存"
    - "资本开支"
  cognitive_worldview:
    - "价格周期"
    - "行业供需"
    - "风险暴露"
```

- [ ] **Step 4: Extend `ReportProfile`**

Modify `src/ipo_evidence/report_profiles.py`:

```python
@dataclass(frozen=True)
class ReportProfile:
    profile_key: str
    title: str
    attention_fields: list[str]
    section_focus: dict[str, list[str]]
```

Add helpers:

```python
def _section_focus(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    focus: dict[str, list[str]] = {}
    for section_key, fields in value.items():
        if isinstance(section_key, str):
            focus[section_key] = _string_list(fields)
    return focus


def _merge_section_focus(
    parent: dict[str, list[str]],
    child: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged = {key: list(values) for key, values in parent.items()}
    for section_key, fields in child.items():
        merged[section_key] = _dedupe_preserving_order(
            merged.get(section_key, []) + fields
        )
    return merged
```

Update `load_report_profile(...)`:

```python
    section_focus: dict[str, list[str]] = {}
    parent_key = config.get("extends")
    if isinstance(parent_key, str) and parent_key:
        parent = load_report_profile(parent_key)
        attention_fields.extend(parent.attention_fields)
        section_focus = _merge_section_focus(section_focus, parent.section_focus)
    attention_fields.extend(_string_list(config.get("attention_fields")))
    section_focus = _merge_section_focus(
        section_focus,
        _section_focus(config.get("section_focus")),
    )

    return ReportProfile(
        profile_key=config.get("profile_key", profile_key),
        title=config.get("title", profile_key),
        attention_fields=_dedupe_preserving_order(attention_fields),
        section_focus=section_focus,
    )
```

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_profiles.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add configs/report_profiles src/ipo_evidence/report_profiles.py tests/test_report_profiles.py
git commit -m "feat: load profile section focus"
```

Expected: commit succeeds.

---

### Task 2: Make Section Groups Profile-Driven

**Files:**
- Modify: `src/ipo_evidence/report_inputs.py`
- Test: `tests/test_report_inputs.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_report_inputs.py`:

```python
def test_build_report_inputs_adds_profile_focus_to_section_groups():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司核心技术包括 AI 芯片、算法、研发平台和专利，主要产品已实现销售。",
                section_path=["业务与技术"],
            )
        ],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)
    first_section = report_inputs["section_groups"][0]

    assert report_inputs["profile_key"] == "technology_company"
    assert first_section["profile_key"] == "technology_company"
    assert "核心技术" in first_section["profile_focus_points"]
    assert "核心技术" in first_section["focus_points"]
    assert first_section["focus_points"].count("客户验证") == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_inputs.py -q
```

Expected: FAIL because section groups do not contain `profile_key` or `profile_focus_points`.

- [ ] **Step 3: Update `build_report_inputs(...)`**

In `src/ipo_evidence/report_inputs.py`, add helper:

```python
def _dedupe_list(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped
```

Move profile selection before template iteration:

```python
def build_report_inputs(doc_id: str, company_name: str, packet) -> dict:
    profile_key = select_report_profile(company_name, packet)
    profile = load_report_profile(profile_key)
    section_groups: list[dict] = []
```

Inside the loop, compute profile focus:

```python
        template_focus_points = _string_list(template.get("focus_points"))
        profile_focus_points = profile.section_focus.get(section_key, [])
```

Then set group fields:

```python
                "profile_key": profile.profile_key,
                "profile_focus_points": list(profile_focus_points),
                "focus_points": _dedupe_list(template_focus_points + profile_focus_points),
```

Remove the old direct `"focus_points": template["focus_points"]`.

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_inputs.py tests/test_report_profiles.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/ipo_evidence/report_inputs.py tests/test_report_inputs.py
git commit -m "feat: apply profile focus to report inputs"
```

Expected: commit succeeds.

---

### Task 3: Refresh Profile-Driven Fields During Regeneration

**Files:**
- Modify: `src/ipo_evidence/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Extend `test_regenerate_report_refreshes_profile_metadata_without_overwriting_section_edits` in `tests/test_pipeline.py`:

```python
    first_group.pop("profile_key", None)
    first_group.pop("profile_focus_points", None)
    first_group["focus_points"] = ["stale-focus"]
```

After regeneration, add:

```python
    assert refreshed_first_group["profile_key"] == refreshed["profile_key"]
    assert refreshed_first_group["profile_focus_points"]
    assert refreshed_first_group["focus_points"] != ["stale-focus"]
    assert refreshed_first_group["evidence_policy"]["min_fact_count"] == 123
    assert refreshed_first_group["evidence_refs"] == [{"evidence_id": "E-SENTINEL", "rank": 99}]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_pipeline.py::test_regenerate_report_refreshes_profile_metadata_without_overwriting_section_edits -q
```

Expected: FAIL because section group profile fields are not refreshed.

- [ ] **Step 3: Add group refresh helper**

Modify `src/ipo_evidence/pipeline.py`:

```python
PROFILE_GROUP_REFRESH_KEYS = {
    "profile_key",
    "profile_focus_points",
    "focus_points",
}


def _refresh_section_group_profile_fields(
    existing_groups: list,
    fresh_groups: list,
) -> list:
    fresh_by_key = {
        group.get("section_key"): group
        for group in fresh_groups
        if isinstance(group, dict)
    }
    refreshed: list = []
    for group in existing_groups:
        if not isinstance(group, dict):
            refreshed.append(group)
            continue
        section_key = group.get("section_key")
        fresh = fresh_by_key.get(section_key)
        if not isinstance(fresh, dict):
            refreshed.append(group)
            continue
        next_group = dict(group)
        for key in PROFILE_GROUP_REFRESH_KEYS:
            if key in fresh:
                next_group[key] = fresh[key]
        refreshed.append(next_group)
    return refreshed
```

Update `_refresh_report_inputs(...)` after top-level key refresh:

```python
    if isinstance(refreshed_report_inputs.get("section_groups"), list):
        refreshed_report_inputs["section_groups"] = _refresh_section_group_profile_fields(
            refreshed_report_inputs["section_groups"],
            fresh_report_inputs.get("section_groups", []),
        )
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_pipeline.py tests/test_report_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/ipo_evidence/pipeline.py tests/test_pipeline.py
git commit -m "feat: refresh profile-driven report input groups"
```

Expected: commit succeeds.

---

### Task 4: End-to-End Verification

**Files:**
- Modify only if verification exposes a real issue.

- [ ] **Step 1: Run full Python suite**

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

- [ ] **Step 3: Regenerate real report**

Run:

```powershell
$env:PYTHONPATH='src'; python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3
```

Expected: `reported=doc_beaac21be4b3`.

- [ ] **Step 4: Check report metrics and profile-driven inputs**

Run:

```powershell
@'
from pathlib import Path
import json
import re

base = Path("data/docs/doc_beaac21be4b3")
report = (base / "report.md").read_text(encoding="utf-8")
report_inputs = json.loads((base / "report_inputs.json").read_text(encoding="utf-8"))
paragraphs = [p for p in report.split("\n\n") if p.strip()]
print("chars", len(report))
print("paragraphs", len(paragraphs))
print("max_paragraph", max(len(p) for p in paragraphs) if paragraphs else 0)
print("citations", len(re.findall(r"\[C-\d{3}\]", report)))
print("raw_dict_literals", report.count("{'"))
print("corresponding_data_phrase", report.count("对应数据为"))
print("literal_backslash_n", report.count("\\n"))
print("profile_key", report_inputs.get("profile_key"))
print("first_group_profile_focus", report_inputs["section_groups"][0].get("profile_focus_points"))
'@ | python -
```

Expected:

```text
raw_dict_literals 0
corresponding_data_phrase 0
literal_backslash_n 0
profile_key technology_company
first_group_profile_focus [...]
```

- [ ] **Step 5: Check git status**

Run:

```powershell
git status --short
```

Expected: clean or only intentionally untracked generated artifacts. Do not add `data/docs/...` unless already tracked.

---

## Self-Review

Spec coverage:

- `report_inputs 根据 profile 生成 section_groups`: covered by Tasks 1-3.
- Industry profiles provide focus fields rather than duplicated skill sets: covered by YAML `section_focus`.
- Existing evidence/citation boundaries remain unchanged: no citation, evidence, or writer behavior changes in this PR.
- Regeneration path updates old packages: covered by Task 3.

Known remaining gaps after this PR:

- True weak-evidence merge into neighboring sections.
- `citation_checker.yaml` as an independent runtime.
- `quality_notes.md`.
- External facts and disclosure gap workflows.
- Stitch layer still has only minimal global ordering/cleanup, not full narrative rewrite.

Placeholder scan:

- This plan avoids open-ended implementation placeholders.

Type consistency:

- `ReportProfile.section_focus` is introduced before `report_inputs` consumes it.
- `profile_focus_points` is generated by `report_inputs` before `pipeline` refreshes it.
