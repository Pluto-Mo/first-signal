# Report Generation Config Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `report_inputs` declared `skill_refs`, `prompt_slot`, and report profile configs become real runtime inputs for section writing and report assembly, instead of passive metadata.

**Architecture:** Add a small config runtime layer that loads and validates prompt, skill, and profile YAML files into typed internal objects. Keep deterministic local generation, but make its behavior driven by loaded configs and report profile metadata. Preserve the existing evidence/citation contract: no new facts, no citation renumbering, no opening-time generation.

**Tech Stack:** Python 3, Pydantic project models, PyYAML via `ipo_evidence.config.load_yaml`, pytest, Vite React build verification.

---

## Current State

Facts from the current workspace:

- `configs/skills/*.yaml`, `configs/prompts/*.yaml`, and `configs/report_profiles/*.yaml` exist and are loadable.
- `report_inputs.py` writes `skill_refs`, `prompt_slot`, `evidence_policy`, `output_contract`, and `section_role` into each section group.
- `section_generator.py` passes `skill_refs` and `prompt_slot` into `section_writer.write_section(...)`.
- `section_writer.py` currently interprets skills with hard-coded string checks such as `"business_goal_decompose" in skill_refs`.
- `prompt_slot` is accepted by `write_section(...)`, but no prompt YAML is loaded or enforced there.
- `report_assembler.py` assembles included drafts and validates citation ids, but does not load `stitch_writer.yaml` or perform meaningful global cleanup.
- `report_generation_architecture.md` describes profile selection as step 1, but current `build_report_inputs(...)` does not select or expose a report profile.

This PR should close the runtime gap without attempting the later `external_fact`, `disclosure_gap`, or full industry-methodology expansion.

## File Structure

- Create `src/ipo_evidence/report_runtime.py`
  - Load prompt, skill, and report profile YAML.
  - Return typed config objects with conservative defaults.
  - Validate unknown `skill_refs` and `prompt_slot` with explicit warnings instead of silent fallback.

- Create `src/ipo_evidence/report_profiles.py`
  - Select a profile key from company name and evidence packet text.
  - Load profile config and expose `profile_key`, `title`, `attention_fields`, and inherited base fields.
  - Keep selection deterministic and conservative.

- Modify `src/ipo_evidence/report_inputs.py`
  - Add top-level `profile_key`, `profile_title`, and `attention_fields`.
  - Keep each section group lightweight; do not copy evidence bodies into `report_inputs`.

- Modify `src/ipo_evidence/section_writer.py`
  - Load prompt config from `prompt_slot`.
  - Load skill configs from `skill_refs`.
  - Generate intro/interpretation from loaded skill config fields, with local deterministic phrasing.
  - Enforce prompt rules through code-level checks: citation limit, forbidden internal terms, paragraph length warning.

- Modify `src/ipo_evidence/section_generator.py`
  - Pass runtime warnings from `write_section(...)` into `InternalTrace.readability_warnings`.
  - Keep trace fields aligned with actually selected evidence.

- Modify `src/ipo_evidence/report_assembler.py`
  - Load `stitch_writer.yaml`.
  - Apply minimal global cleanup: remove duplicated adjacent paragraphs, remove internal system terms, keep citation validation before output.
  - Do not add facts or alter citation ids.

- Add tests:
  - `tests/test_report_runtime.py`
  - `tests/test_report_profiles.py`
  - Extend `tests/test_report_inputs.py`
  - Extend `tests/test_section_writer.py`
  - Extend `tests/test_report_assembler.py`

## Out Of Scope

- Do not implement `external_fact`.
- Do not add database storage.
- Do not change parser, evidence extraction, citation generation, or web reader routing.
- Do not rewrite `report_generator.py` beyond what is required to keep the pipeline passing.
- Do not make LLM calls; this PR keeps deterministic generation.

## Precondition Before Execution

The current workspace already contains uncommitted PR2.5 changes. Before implementing this plan, run:

```powershell
git status --short
```

Expected: PR2.5 files are visible. Either commit PR2.5 first or deliberately continue in the same local diff. Do not run `git push` without explicit user confirmation because project `AGENTS.md` marks `git push` as a redline.

---

### Task 1: Add Runtime Config Loader

**Files:**
- Create: `src/ipo_evidence/report_runtime.py`
- Test: `tests/test_report_runtime.py`

- [ ] **Step 1: Write failing tests for prompt and skill loading**

Create `tests/test_report_runtime.py` with:

```python
import pytest

from ipo_evidence.report_runtime import (
    load_prompt_config,
    load_skill_configs,
)


def test_load_prompt_config_by_prompt_slot():
    prompt = load_prompt_config("narrative_section")

    assert prompt.prompt_slot == "narrative_section"
    assert prompt.purpose == "把一个 section draft 写成自然正文。"
    assert "事实句必须带 citation id。" in prompt.rules


def test_load_skill_configs_keeps_request_order():
    skills = load_skill_configs(["capability_match", "business_goal_decompose"])

    assert [skill.skill_key for skill in skills] == [
        "capability_match",
        "business_goal_decompose",
    ]
    assert skills[0].title == "能力匹配"
    assert skills[1].produces == ["business_question"]


def test_load_skill_configs_rejects_unknown_skill():
    with pytest.raises(ValueError, match="unknown skill_ref: missing_skill"):
        load_skill_configs(["missing_skill"])


def test_load_prompt_config_rejects_unknown_prompt_slot():
    with pytest.raises(ValueError, match="unknown prompt_slot: missing_prompt"):
        load_prompt_config("missing_prompt")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_runtime.py -q
```

Expected: FAIL because `ipo_evidence.report_runtime` does not exist.

- [ ] **Step 3: Implement runtime config loader**

Create `src/ipo_evidence/report_runtime.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ipo_evidence.config import load_yaml
from ipo_evidence.paths import repo_root


@dataclass(frozen=True)
class PromptConfig:
    prompt_slot: str
    purpose: str
    rules: list[str]


@dataclass(frozen=True)
class SkillConfig:
    skill_key: str
    title: str
    action: str
    requires: list[str]
    produces: list[str]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _yaml_files(relative_dir: str) -> list[Path]:
    directory = repo_root() / relative_dir
    return sorted(directory.glob("*.yaml"))


@lru_cache(maxsize=1)
def _prompt_index() -> dict[str, PromptConfig]:
    prompts: dict[str, PromptConfig] = {}
    for path in _yaml_files("configs/prompts"):
        config = load_yaml(str(path.relative_to(repo_root()).as_posix()))
        prompt_slot = config.get("prompt_slot")
        if not isinstance(prompt_slot, str) or not prompt_slot:
            continue
        prompts[prompt_slot] = PromptConfig(
            prompt_slot=prompt_slot,
            purpose=config.get("purpose", ""),
            rules=_string_list(config.get("rules")),
        )
    return prompts


@lru_cache(maxsize=1)
def _skill_index() -> dict[str, SkillConfig]:
    skills: dict[str, SkillConfig] = {}
    for path in _yaml_files("configs/skills"):
        config = load_yaml(str(path.relative_to(repo_root()).as_posix()))
        skill_key = config.get("skill_key")
        if not isinstance(skill_key, str) or not skill_key:
            continue
        skills[skill_key] = SkillConfig(
            skill_key=skill_key,
            title=config.get("title", skill_key),
            action=config.get("action", ""),
            requires=_string_list(config.get("requires")),
            produces=_string_list(config.get("produces")),
        )
    return skills


def load_prompt_config(prompt_slot: str) -> PromptConfig:
    prompt = _prompt_index().get(prompt_slot)
    if prompt is None:
        raise ValueError(f"unknown prompt_slot: {prompt_slot}")
    return prompt


def load_skill_configs(skill_refs: list[str]) -> list[SkillConfig]:
    index = _skill_index()
    skills: list[SkillConfig] = []
    for skill_ref in skill_refs:
        skill = index.get(skill_ref)
        if skill is None:
            raise ValueError(f"unknown skill_ref: {skill_ref}")
        skills.append(skill)
    return skills
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_runtime.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/ipo_evidence/report_runtime.py tests/test_report_runtime.py
git commit -m "feat: load report generation runtime configs"
```

Expected: commit succeeds.

---

### Task 2: Add Conservative Report Profile Selection

**Files:**
- Create: `src/ipo_evidence/report_profiles.py`
- Modify: `src/ipo_evidence/report_inputs.py`
- Test: `tests/test_report_profiles.py`
- Test: `tests/test_report_inputs.py`

- [ ] **Step 1: Write failing profile tests**

Create `tests/test_report_profiles.py`:

```python
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block
from ipo_evidence.report_profiles import load_report_profile, select_report_profile


def _packet(text: str):
    return build_evidence_packet(
        doc_id="doc_test",
        source_file="sample.pdf",
        blocks=[
            Block(
                block_id="B-001",
                page_number=1,
                text=text,
                section_path=["业务与技术"],
            )
        ],
        tables=[],
    )


def test_load_report_profile_merges_base_attention_fields():
    profile = load_report_profile("consumer_product")

    assert profile.profile_key == "consumer_product"
    assert profile.title == "消费产品公司解读"
    assert "产品定位" in profile.attention_fields


def test_select_report_profile_defaults_to_base():
    profile_key = select_report_profile("测试股份有限公司", _packet("公司主营业务为软件销售。"))

    assert profile_key == "base"


def test_select_report_profile_detects_technology_company():
    profile_key = select_report_profile(
        "测试股份有限公司",
        _packet("公司核心技术包括 AI 芯片、算法、研发平台和专利。"),
    )

    assert profile_key == "technology_company"
```

Extend `tests/test_report_inputs.py` with:

```python
def test_build_report_inputs_exposes_selected_profile_metadata():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[
            Block(
                block_id="B-000002",
                page_number=2,
                text="公司核心技术包括 AI 芯片、算法、研发平台和专利。",
                section_path=["业务与技术"],
            )
        ],
        tables=[],
    )

    report_inputs = build_report_inputs("doc_test", "测试股份有限公司", packet)

    assert report_inputs["profile_key"] == "technology_company"
    assert report_inputs["profile_title"] == "技术公司解读"
    assert "核心技术" in report_inputs["attention_fields"]
    assert "quote" not in str(report_inputs["attention_fields"])
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_profiles.py tests/test_report_inputs.py -q
```

Expected: FAIL because `report_profiles.py` and report input profile fields do not exist.

- [ ] **Step 3: Implement report profile loader and selector**

Create `src/ipo_evidence/report_profiles.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ipo_evidence.config import load_yaml
from ipo_evidence.models import EvidencePacket


@dataclass(frozen=True)
class ReportProfile:
    profile_key: str
    title: str
    attention_fields: list[str]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _load_profile_yaml(profile_key: str) -> dict:
    return load_yaml(f"configs/report_profiles/{profile_key}.yaml")


def load_report_profile(profile_key: str) -> ReportProfile:
    config = _load_profile_yaml(profile_key)
    if not config:
        raise ValueError(f"unknown report profile: {profile_key}")

    attention_fields: list[str] = []
    extends = config.get("extends")
    if isinstance(extends, str) and extends:
        parent = load_report_profile(extends)
        attention_fields.extend(parent.attention_fields)

    for field in _string_list(config.get("attention_fields")):
        if field not in attention_fields:
            attention_fields.append(field)

    return ReportProfile(
        profile_key=config.get("profile_key", profile_key),
        title=config.get("title", profile_key),
        attention_fields=attention_fields,
    )


def _packet_text(packet: EvidencePacket) -> str:
    parts: list[str] = []
    for item in packet.items:
        parts.append(item.claim_summary)
        parts.extend(item.section_path)
        if item.quote:
            parts.append(item.quote)
        if item.table_title:
            parts.append(item.table_title)
    return " ".join(parts)


def select_report_profile(company_name: str, packet: EvidencePacket) -> str:
    text = f"{company_name} {_packet_text(packet)}"
    technology_keywords = ["AI", "芯片", "算法", "核心技术", "研发", "专利", "产品化"]
    consumer_keywords = ["消费", "渠道", "电商", "零售", "售后", "价格带", "供应链"]
    cyclical_keywords = ["产能", "原材料", "库存", "资本开支", "价格周期", "供需"]

    keyword_groups = [
        ("technology_company", technology_keywords),
        ("consumer_product", consumer_keywords),
        ("cyclical_industry", cyclical_keywords),
    ]
    for profile_key, keywords in keyword_groups:
        if sum(1 for keyword in keywords if keyword in text) >= 2:
            return profile_key
    return "base"
```

- [ ] **Step 4: Wire profile metadata into report inputs**

Modify `src/ipo_evidence/report_inputs.py` imports:

```python
from ipo_evidence.report_profiles import load_report_profile, select_report_profile
```

Modify the end of `build_report_inputs(...)`:

```python
    profile_key = select_report_profile(company_name, packet)
    profile = load_report_profile(profile_key)

    return {
        "doc_id": doc_id,
        "company_name": company_name,
        "profile_key": profile.profile_key,
        "profile_title": profile.title,
        "attention_fields": profile.attention_fields,
        "outline": [group["section_key"] for group in section_groups],
        "section_groups": section_groups,
    }
```

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_profiles.py tests/test_report_inputs.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/ipo_evidence/report_profiles.py src/ipo_evidence/report_inputs.py tests/test_report_profiles.py tests/test_report_inputs.py
git commit -m "feat: select report profile for report inputs"
```

Expected: commit succeeds.

---

### Task 3: Make Section Writer Consume Prompt and Skill Configs

**Files:**
- Modify: `src/ipo_evidence/section_writer.py`
- Test: `tests/test_section_writer.py`

- [ ] **Step 1: Add failing tests for config-driven writer behavior**

Append to `tests/test_section_writer.py`:

```python
def test_write_section_loads_skill_config_action_text():
    result = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["capability_match"],
        prompt_slot="narrative_section",
        indexed_items=[
            (
                1,
                _text_item(
                    "E-001",
                    "公司产品覆盖智慧出行和智慧办公场景，并形成客户交付记录。",
                ),
            )
        ],
    )

    assert "检查产品、研发、客户和交付能力" in result.body
    assert "[C-001]" in result.body


def test_write_section_rejects_unknown_prompt_slot():
    try:
        write_section(
            section_key="company_and_industry",
            title="公司介绍与行业概况",
            skill_refs=[],
            prompt_slot="missing_prompt",
            indexed_items=[],
        )
    except ValueError as exc:
        assert "unknown prompt_slot: missing_prompt" in str(exc)
    else:
        raise AssertionError("write_section should reject unknown prompt_slot")


def test_write_section_rejects_unknown_skill_ref():
    try:
        write_section(
            section_key="company_and_industry",
            title="公司介绍与行业概况",
            skill_refs=["missing_skill"],
            prompt_slot="narrative_section",
            indexed_items=[],
        )
    except ValueError as exc:
        assert "unknown skill_ref: missing_skill" in str(exc)
    else:
        raise AssertionError("write_section should reject unknown skill_ref")
```

- [ ] **Step 2: Run writer tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_writer.py -q
```

Expected: FAIL because writer does not yet load configs and does not include action text.

- [ ] **Step 3: Modify imports and helper signatures**

In `src/ipo_evidence/section_writer.py`, add:

```python
from ipo_evidence.report_runtime import PromptConfig, SkillConfig, load_prompt_config, load_skill_configs
```

Change helper signatures:

```python
def _skill_intro(section_key: str, skills: list[SkillConfig]) -> str:
```

```python
def _skill_interpretation(section_key: str, skills: list[SkillConfig]) -> str:
```

```python
def _build_paragraphs(
    section_key: str,
    title: str,
    skills: list[SkillConfig],
    prompt: PromptConfig,
    selected_items: list[tuple[int, EvidenceItem]],
) -> list[str]:
```

- [ ] **Step 4: Replace string-only skill checks with loaded configs**

Use these helpers in `src/ipo_evidence/section_writer.py`:

```python
def _skill_keys(skills: list[SkillConfig]) -> set[str]:
    return {skill.skill_key for skill in skills}


def _skill_actions(skills: list[SkillConfig]) -> str:
    actions = [skill.action.rstrip("。") for skill in skills if skill.action]
    if not actions:
        return ""
    return "本节调用的解读动作是：" + "；".join(actions[:3]) + "。"
```

Update `_skill_intro(...)` so config action is visible:

```python
def _skill_intro(section_key: str, skills: list[SkillConfig]) -> str:
    keys = _skill_keys(skills)
    action_text = _skill_actions(skills)
    if "business_goal_decompose" in keys:
        if section_key == "company_and_industry":
            return f"{action_text}阅读这一节，先把公司叙事拆成三个问题：它卖什么、进入哪些终端场景、这些场景是否能形成可复制交付。"
        if section_key == "personal_investment":
            return f"{action_text}个人投资视角下，重点不是先判断贵不贵，而是先拆收入质量、研发转化、现金流和风险承受力。"
    if "reader_value_translate" in keys:
        return f"{action_text}这一节的价值，是把招股书披露翻译成几个可以继续核查的问题。"
    if action_text:
        return action_text
    return "这一节先从已抽取证据中挑出最能支撑判断的部分。"
```

Update `_skill_interpretation(...)` to use `keys = _skill_keys(skills)`.

- [ ] **Step 5: Load configs in `write_section(...)`**

Modify `write_section(...)`:

```python
def write_section(
    *,
    section_key: str,
    title: str,
    skill_refs: list[str],
    prompt_slot: str,
    indexed_items: list[tuple[int, EvidenceItem]],
) -> SectionWriteResult:
    prompt = load_prompt_config(prompt_slot)
    skills = load_skill_configs(skill_refs)
    selected_items = _select_items(section_key, indexed_items)
    paragraphs = _build_paragraphs(section_key, title, skills, prompt, selected_items)
    body = "\n\n".join(paragraphs).strip()
    citation_ids = [_citation_id(index) for index, _ in selected_items]
    return SectionWriteResult(
        body=body,
        selected_items=selected_items,
        citation_ids=citation_ids,
        readability_warnings=_readability_warnings(body),
    )
```

Use `prompt` inside `_build_paragraphs(...)` by enforcing prompt rule warnings through existing `_readability_warnings(...)`; do not put prompt metadata into final body.

- [ ] **Step 6: Run section writer tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_writer.py -q
```

Expected: PASS.

- [ ] **Step 7: Run generator and gate tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_section_generator.py tests/test_quality_gate.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src/ipo_evidence/section_writer.py tests/test_section_writer.py
git commit -m "feat: drive section writing from runtime configs"
```

Expected: commit succeeds.

---

### Task 4: Add Minimal Config-Driven Stitch Cleanup

**Files:**
- Modify: `src/ipo_evidence/report_assembler.py`
- Test: `tests/test_report_assembler.py`

- [ ] **Step 1: Add failing assembler tests**

Append to `tests/test_report_assembler.py`:

```python
def test_assemble_report_removes_duplicate_adjacent_paragraphs():
    duplicated = "同一段判断。[C-001]\n\n同一段判断。[C-001]"

    report = assemble_report(
        "测试股份有限公司",
        [_draft("first", "第一节", duplicated)],
        [_decision("first", "include")],
        valid_citation_ids={"C-001"},
    )

    assert report.count("同一段判断。[C-001]") == 1


def test_assemble_report_removes_internal_system_terms():
    report = assemble_report(
        "测试股份有限公司",
        [_draft("first", "第一节", "该段来自 section draft 和 internal trace。[C-001]")],
        [_decision("first", "include")],
        valid_citation_ids={"C-001"},
    )

    assert "section draft" not in report
    assert "internal trace" not in report
    assert "[C-001]" in report
```

- [ ] **Step 2: Run assembler tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_assembler.py -q
```

Expected: FAIL because duplicate cleanup and internal term cleanup do not exist.

- [ ] **Step 3: Load stitch prompt config and add cleanup helpers**

Modify `src/ipo_evidence/report_assembler.py` imports:

```python
from ipo_evidence.report_runtime import load_prompt_config
```

Add constants and helpers:

```python
INTERNAL_TERMS = [
    "section draft",
    "internal trace",
    "analysis_log",
    "quality gate",
    "evidence_refs",
]


def _remove_internal_terms(text: str) -> str:
    cleaned = text
    for term in INTERNAL_TERMS:
        cleaned = cleaned.replace(term, "")
    return re.sub(r" {2,}", " ", cleaned)


def _dedupe_adjacent_paragraphs(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
    deduped: list[str] = []
    previous = None
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if paragraph == previous:
            continue
        deduped.append(paragraph)
        previous = paragraph
    return "\n\n".join(deduped)


def _clean_draft_body(body: str) -> str:
    return _dedupe_adjacent_paragraphs(_remove_internal_terms(body)).strip()
```

- [ ] **Step 4: Apply cleanup inside assembly**

Modify the draft loop in `assemble_report(...)`:

```python
    load_prompt_config("stitch_writer")
    lines = [
        _report_title(company_name),
        "",
        "本文基于招股说明书中已抽取的可引用证据，围绕业务定位、能力配置、商业化验证和风险约束展开阅读。",
    ]
    for draft in included:
        cleaned_body = _clean_draft_body(draft.body)
        if not cleaned_body:
            continue
        lines.extend(["", f"## {draft.title}", "", cleaned_body])
```

Keep `_validate_citations(included, valid_citation_ids)` before cleanup. The cleanup must not change citation ids.

- [ ] **Step 5: Run assembler tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/test_report_assembler.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/ipo_evidence/report_assembler.py tests/test_report_assembler.py
git commit -m "feat: apply stitch writer cleanup"
```

Expected: commit succeeds.

---

### Task 5: End-to-End Regression

**Files:**
- Modify only if tests expose a real integration issue.

- [ ] **Step 1: Run full Python test suite**

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

- [ ] **Step 3: Regenerate the real report used in the current review**

Run the existing pipeline command that was used for `doc_beaac21be4b3`. If the exact command is unknown in the executing session, inspect `src/ipo_evidence/cli.py` and `src/ipo_evidence/pipeline.py`, then run the narrowest command that regenerates that doc's `report.md`, `analysis_log.json`, and reader bundle.

Expected generated report checks:

```text
raw_dict_literals: 0
corresponding_data_phrase: 0
literal_backslash_n: 0
broken_patterns: 0
missing_citations: []
```

- [ ] **Step 4: Run a lightweight report metric script**

Run:

```powershell
@'
from pathlib import Path
import re

report = Path("data/docs/doc_beaac21be4b3/report.md").read_text(encoding="utf-8")
paragraphs = [p for p in report.split("\n\n") if p.strip()]
print("chars", len(report))
print("paragraphs", len(paragraphs))
print("max_paragraph", max(len(p) for p in paragraphs))
print("citations", len(re.findall(r"\[C-\d{3}\]", report)))
print("raw_dict_literals", report.count("{'"))
print("corresponding_data_phrase", report.count("对应数据为"))
print("literal_backslash_n", report.count("\\n"))
'@ | python -
```

Expected: raw-literal counts are `0`, max paragraph stays under the readability gate threshold, citations are present.

- [ ] **Step 5: Check working tree**

Run:

```powershell
git status --short
```

Expected: only intentional generated artifacts or no changes. Data under `data/docs/...` may be untracked by git; do not add it unless the project already tracks that doc asset.

- [ ] **Step 6: Final commit if integration changes were needed**

If Task 5 required code or test fixes, run:

```powershell
git add <changed-files>
git commit -m "test: verify config driven report generation"
```

Expected: commit succeeds. Do not push without explicit user confirmation.

---

## Self-Review

Spec coverage:

- `report_inputs` as dispatch contract: covered by Task 2 and existing tests.
- `skills` as interpretation actions: covered by Task 1 and Task 3.
- `prompt` as section writing rules: covered by Task 1 and Task 3.
- `stitch` only integrates section drafts without new facts: covered by Task 4.
- `profile` selection before report input generation: covered by Task 2.
- citation preservation: covered by existing assembler validation and Task 4 expectations.

Known gaps intentionally left for later:

- `external_fact`, `calculated_metric`, `cross_doc_fact`, and `visual_fact`.
- Mature natural-language rewrite of the whole report by an LLM.
- `quality_notes.md`.
- Full industry-specific section expansion beyond conservative profile metadata.

Placeholder scan:

- This plan contains no open-ended implementation placeholders.
- The one dynamic command in Task 5 is bounded by exact files to inspect and exact expected outputs because the existing CLI surface may differ between branches.

Type consistency:

- `PromptConfig` and `SkillConfig` are defined in Task 1 before use in Task 3.
- `ReportProfile` is defined in Task 2 before use in `report_inputs.py`.
- Function names used by tests match implementation steps.
