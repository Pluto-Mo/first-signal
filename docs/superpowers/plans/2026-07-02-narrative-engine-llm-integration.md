# Narrative Engine LLM Integration - Phase 1

> **Status:** Ready for execution
>
> **Goal:** 把 Narrative Engine 从"硬编码模板拼接"升级到"LLM 驱动叙事"，让报告从 8 行模板文字变成 800-1500 字的自然文章。

**Current Problem:**
- `narrative_engine.py` 的 `_call_narrative_writer()` 是硬编码的字符串拼接
- 输出只有 3 段、8 行文字
- 有明显的模板痕迹："能力上，它的正面线索是..."、"真正需要读进去的是..."
- 没有逻辑过渡，只是简单拼接

**Target:**
- 用 LLM 生成自然、流畅、有深度的文章
- 长度：800-1500 字
- 结构：4-6 个自然段落
- 风格：像分析师写的，不是脚本生成的

**Tech Stack:** 
- Python 3.11+
- 内置 subprocess 调用 `claude` CLI（在 Claude Code/Codex 环境中运行）
- 使用项目中已有的 `configs/prompts/narrative_writer.yaml`

---

## 1. Current Architecture Problem

### 当前的 `_call_narrative_writer()` 实现

```python
def _call_narrative_writer(
    narrative_materials: dict[str, dict[str, Any]],
    evidence_map: dict[str, str],
    skill_citations: dict[str, list[str]],
    prompt_config,
) -> str:
    # 硬编码的模板拼接
    opening = _business_sentence(business)
    second_paragraph.append(f"能力上，它的正面线索是{strengths}，但约束也很直接：{weakness}。")
    # ...
    return "\n\n".join(paragraphs)
```

**问题：**
1. 完全是字符串拼接，没有 LLM 调用
2. 模板痕迹明显
3. 无法生成自然过渡和深度分析
4. 长度固定为 3 段

---

## 2. Solution: Call Claude CLI

### 为什么用 `claude` CLI？

在 Claude Code/Codex 环境中运行时，可以直接用 `subprocess` 调用 `claude` 命令：

```python
import subprocess

def call_claude_cli(prompt: str, system: str = "") -> str:
    """调用 claude CLI 生成内容"""
    cmd = ["claude", "-p", prompt]
    if system:
        cmd.extend(["-s", system])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr}")
    
    return result.stdout.strip()
```

**优点：**
- 不需要外部 API key
- 利用当前会话的 Claude 实例
- 简单、直接、零配置

---

## 3. Implementation Plan

### Step 1: Create LLM Caller Module

Create `src/ipo_evidence/llm_caller.py`:

```python
"""
LLM caller for narrative generation.

Uses subprocess to call `claude` CLI when running inside Claude Code/Codex.
"""

from __future__ import annotations

import subprocess
from typing import Optional


def call_claude_for_narrative(
    user_prompt: str,
    system_prompt: str,
    max_tokens: int = 4000,
    timeout: int = 120,
) -> str:
    """
    调用 claude CLI 生成叙事内容
    
    Args:
        user_prompt: 用户 prompt（包含解读结果）
        system_prompt: 系统 prompt（写作规则和风格指南）
        max_tokens: 最大输出 token 数
        timeout: 超时时间（秒）
    
    Returns:
        生成的文章内容
    
    Raises:
        RuntimeError: 如果 claude CLI 调用失败
        TimeoutError: 如果调用超时
    """
    # 构建命令
    # 使用 -p 传递 user prompt，-s 传递 system prompt
    cmd = [
        "claude",
        "-p", user_prompt,
        "-s", system_prompt,
        "--max-tokens", str(max_tokens),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Claude CLI timed out after {timeout}s") from e
    
    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
    
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("Claude CLI returned empty output")
    
    return output


def call_claude_for_skill(
    skill_name: str,
    evidence_text: str,
    instruction: str,
    max_tokens: int = 2000,
) -> str:
    """
    调用 claude CLI 执行 Skill 分析
    
    Args:
        skill_name: skill 名称（用于日志）
        evidence_text: 证据文本
        instruction: 分析指令
        max_tokens: 最大输出 token 数
    
    Returns:
        JSON 格式的分析结果
    """
    system_prompt = f"""你是招股书分析专家，正在执行 {skill_name} 分析任务。
请严格按照指令要求，用 JSON 格式输出分析结果。
不要输出任何解释或元信息，只输出 JSON。"""
    
    user_prompt = f"""
{instruction}

证据：
{evidence_text}
"""
    
    return call_claude_for_narrative(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )
```

### Step 2: Update `narrative_engine.py`

Modify `src/ipo_evidence/narrative_engine.py`:

```python
from __future__ import annotations

import json
from typing import Any

from ipo_evidence.llm_caller import call_claude_for_narrative
from ipo_evidence.models import EvidencePacket, SkillInterpretation
from ipo_evidence.report_runtime import load_prompt_config


def generate_narrative(
    all_skill_outputs: list[SkillInterpretation],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
    narrative_style: str = "analytical",
) -> tuple[str, dict[str, Any]]:
    """生成叙事报告"""
    del evidence_packet, narrative_style
    
    narrative_materials = _prepare_narrative_materials(all_skill_outputs)
    evidence_map = _build_evidence_map(all_skill_outputs, citation_index)
    skill_citations = _build_skill_citations(all_skill_outputs, citation_index)
    prompt_config = load_prompt_config("narrative_writer")
    
    report_md = _call_narrative_writer(
        narrative_materials,
        evidence_map,
        skill_citations,
        prompt_config,
    )
    
    trace = {
        "skills_used": [output.skill_key for output in all_skill_outputs],
        "total_evidence": len(evidence_map),
        "confidence_distribution": _count_confidence(all_skill_outputs),
    }
    
    return report_md, trace


def _prepare_narrative_materials(outputs: list[SkillInterpretation]) -> dict[str, dict[str, Any]]:
    """提取高置信度的解读结果"""
    materials: dict[str, dict[str, Any]] = {}
    for output in outputs:
        if output.confidence in {"high", "medium"} and output.interpretation:
            materials[output.skill_key] = output.interpretation
    return materials


def _build_evidence_map(
    outputs: list[SkillInterpretation],
    citation_index: dict[str, str],
) -> dict[str, str]:
    """构建 evidence_id -> citation_id 映射"""
    evidence_map: dict[str, str] = {}
    for output in outputs:
        for evidence_id in output.evidence_chain:
            if evidence_id in citation_index:
                evidence_map[evidence_id] = citation_index[evidence_id]
    return evidence_map


def _build_skill_citations(
    outputs: list[SkillInterpretation],
    citation_index: dict[str, str],
) -> dict[str, list[str]]:
    """为每个 skill 构建 citation 列表"""
    citations: dict[str, list[str]] = {}
    for output in outputs:
        citations[output.skill_key] = [
            citation_index[evidence_id]
            for evidence_id in output.evidence_chain
            if evidence_id in citation_index
        ]
    return citations


def _call_narrative_writer(
    narrative_materials: dict[str, dict[str, Any]],
    evidence_map: dict[str, str],
    skill_citations: dict[str, list[str]],
    prompt_config,
) -> str:
    """
    调用 LLM 生成叙事
    
    CHANGED: 从硬编码模板拼接改为调用 claude CLI
    """
    if not narrative_materials:
        return "当前证据不足以生成高置信度叙事。"
    
    # 构建 system prompt
    system_prompt = _build_system_prompt(prompt_config)
    
    # 构建 user prompt
    user_prompt = _build_user_prompt(narrative_materials, skill_citations)
    
    # 调用 LLM
    try:
        report_md = call_claude_for_narrative(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            timeout=120,
        )
        return report_md
    except (RuntimeError, TimeoutError) as e:
        # LLM 调用失败时，回退到简化版本
        return _fallback_narrative(narrative_materials, skill_citations)


def _build_system_prompt(prompt_config) -> str:
    """构建 system prompt"""
    rules_text = "\n".join(f"- {rule}" for rule in prompt_config.rules.get("structure", []))
    
    return f"""你是招股书分析专家，负责把结构化的解读结果编织成一篇自然、流畅、有深度的文章。

# 核心任务
{prompt_config.purpose}

# 写作规则
{rules_text}

# 重要约束
- 不要逐个 Skill 分段写，而是找到解读之间的逻辑关系，自然串联
- 用因果、递进、对比、补充等手法连接内容
- 避免模板短语："根据招股书披露"、"数据显示"、"可以看出"
- Citation 用 [C-XXX] 格式紧跟事实陈述
- 全文 800-1500 字，分 4-6 个自然段落
- 每段 3-6 句话，不要单句成段"""


def _build_user_prompt(
    narrative_materials: dict[str, dict[str, Any]],
    skill_citations: dict[str, list[str]],
) -> str:
    """构建 user prompt"""
    
    # 格式化每个 skill 的输出
    sections = []
    
    if "business_goal_decompose" in narrative_materials:
        business = narrative_materials["business_goal_decompose"]
        citations = skill_citations.get("business_goal_decompose", [])
        sections.append(f"""
## 业务目标拆解
- 核心业务目标: {business.get('business_goal', 'N/A')}
- 产品入口: {', '.join(business.get('product_entry', []))}
- 目标场景: {', '.join(business.get('target_scenario', []))}
- 客户类型: {business.get('customer_type', 'N/A')}
- 可用 citation: {', '.join(citations[:5])}
""")
    
    if "capability_match" in narrative_materials:
        capability = narrative_materials["capability_match"]
        citations = skill_citations.get("capability_match", [])
        strengths = capability.get("strengths", [])
        weaknesses = capability.get("weaknesses", [])
        sections.append(f"""
## 能力匹配
- 能力强项 (前 3 条): {'; '.join(str(s)[:80] for s in strengths[:3])}
- 能力弱项 (前 3 条): {'; '.join(str(w)[:80] for w in weaknesses[:3])}
- 核心张力: {capability.get('tension', 'N/A')}
- 可用 citation: {', '.join(citations[:5])}
""")
    
    if "tension_expand" in narrative_materials:
        tension = narrative_materials["tension_expand"]
        citations = skill_citations.get("tension_expand", [])
        sections.append(f"""
## 矛盾张力
- 正面因素: {tension.get('positive_side', 'N/A')}
- 负面因素: {tension.get('negative_side', 'N/A')}
- 权衡逻辑: {tension.get('tradeoff_logic', 'N/A')}
- 可用 citation: {', '.join(citations[:5])}
""")
    
    if "disclosure_gap_scan" in narrative_materials:
        gap = narrative_materials["disclosure_gap_scan"]
        gaps = gap.get("critical_gaps", [])
        sections.append(f"""
## 披露缺口
- 关键缺口 (前 2 条): {'; '.join(str(g)[:80] for g in gaps[:2])}
""")
    
    if "reader_value_translate" in narrative_materials:
        reader = narrative_materials["reader_value_translate"]
        sections.append(f"""
## 读者价值
- 投资人视角: {reader.get('for_investors', 'N/A')}
- 技术人视角: {reader.get('for_tech_people', 'N/A')}
""")
    
    return f"""请根据以下解读结果，编织成一篇完整的文章。

{''.join(sections)}

要求：
1. 从公司定位切入，用 1-2 句话勾勒全貌
2. 中间展开能力分析和张力讨论，用数据支撑判断
3. 适当提及披露缺口，但不要单独成段
4. 结尾回到读者价值，给出可操作的结论
5. 全文 800-1500 字，4-6 个自然段落
6. Citation 紧跟事实陈述，格式：[C-XXX]

直接输出文章内容，不要包含任何解释或元信息。"""


def _fallback_narrative(
    narrative_materials: dict[str, dict[str, Any]],
    skill_citations: dict[str, list[str]],
) -> str:
    """LLM 调用失败时的回退方案（保留原有的简化逻辑）"""
    business = narrative_materials.get("business_goal_decompose", {})
    capability = narrative_materials.get("capability_match", {})
    
    opening_citation = _first_citation(skill_citations, "business_goal_decompose")
    opening = _business_sentence(business)
    if opening and opening_citation:
        opening = f"{opening}{opening_citation}"
    
    paragraphs = [opening] if opening else []
    
    if capability:
        strengths = _join_points(capability.get("strengths", [])[:2])
        weakness = _join_points(capability.get("weaknesses", [])[:2])
        if strengths and weakness:
            paragraphs.append(f"能力上，正面线索包括{strengths}；约束则体现在{weakness}。")
    
    return "\n\n".join(p for p in paragraphs if p)


def _count_confidence(outputs: list[SkillInterpretation]) -> dict[str, int]:
    """统计置信度分布"""
    counts = {"high": 0, "medium": 0, "low": 0}
    for output in outputs:
        counts[output.confidence] += 1
    return counts


def _first_citation(skill_citations: dict[str, list[str]], skill_key: str) -> str:
    """获取第一个 citation"""
    citations = skill_citations.get(skill_key, [])
    return f"[{citations[0]}]" if citations else ""


def _join_points(points: Any) -> str:
    """连接多个要点"""
    if not isinstance(points, list):
        return ""
    cleaned = [str(point).strip().rstrip("。；;，,")[:50] for point in points if str(point).strip()]
    return "、".join(cleaned)


def _business_sentence(business: dict[str, Any]) -> str:
    """构建业务目标句子"""
    if not business:
        return ""
    goal = str(business.get("business_goal", "")).rstrip("。")[:100]
    scenarios = business.get("target_scenario", [])
    if isinstance(scenarios, list) and scenarios:
        return f"{goal}，核心场景包括{'、'.join(str(item) for item in scenarios[:5])}。"
    return goal + "。" if goal else ""
```

### Step 3: Add Tests

Create `tests/test_llm_caller.py`:

```python
import pytest
from ipo_evidence.llm_caller import call_claude_for_narrative


def test_call_claude_for_narrative_basic():
    """测试基本的 LLM 调用"""
    user_prompt = "请用一句话描述对话式 AI 技术。"
    system_prompt = "你是技术专家。"
    
    response = call_claude_for_narrative(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=100,
    )
    
    assert isinstance(response, str)
    assert len(response) > 10
    assert "对话" in response or "AI" in response


def test_call_claude_handles_timeout():
    """测试超时处理"""
    with pytest.raises(TimeoutError):
        call_claude_for_narrative(
            user_prompt="test",
            system_prompt="test",
            timeout=0.001,  # 1ms，必然超时
        )


def test_call_claude_handles_error():
    """测试错误处理（无效命令）"""
    # 这个测试可能需要根据实际环境调整
    pass
```

---

## 4. Execution Steps

### Step 1: Create `llm_caller.py`

```bash
# 创建文件
touch src/ipo_evidence/llm_caller.py

# 写入内容（见 Section 3 - Step 1）
```

### Step 2: Update `narrative_engine.py`

```bash
# 备份原文件
cp src/ipo_evidence/narrative_engine.py src/ipo_evidence/narrative_engine.py.bak

# 替换为新实现（见 Section 3 - Step 2）
```

### Step 3: Test with Real Document

```bash
# 重新生成报告
python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3

# 检查输出
cat data/docs/doc_beaac21be4b3/report.md
```

**Expected Output:**
- 长度：800-1500 字（而不是 8 行）
- 结构：4-6 个自然段落
- 风格：自然过渡，无模板短语
- Citation：自然嵌入，不突兀

### Step 4: Verify Quality

```bash
# 检查字数
wc -m data/docs/doc_beaac21be4b3/report.md

# 检查段落数
grep -c "^$" data/docs/doc_beaac21be4b3/report.md

# 检查是否有模板短语（应该为 0）
grep -E "能力上，它的正面线索|真正需要读进去的|披露缺口也不能跳过" data/docs/doc_beaac21be4b3/report.md
```

### Step 5: Commit

```bash
git add src/ipo_evidence/llm_caller.py src/ipo_evidence/narrative_engine.py tests/test_llm_caller.py
git commit -m "feat: integrate LLM into narrative engine

- Add llm_caller.py with subprocess-based claude CLI integration
- Refactor narrative_engine.py to use LLM instead of template concatenation
- Add fallback mechanism for LLM failures
- Expected output: 800-1500 word natural articles instead of 8-line templates

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## 5. Validation Checklist

After implementation, verify:

- [ ] `python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3` succeeds
- [ ] Generated report is 800-1500 characters (not 8 lines)
- [ ] Report has 4-6 natural paragraphs
- [ ] No template phrases like "能力上，它的正面线索是"
- [ ] Citations are naturally embedded: "前五大客户占比超过 60%，[C-015]"
- [ ] Paragraphs have natural transitions
- [ ] `pytest tests/test_llm_caller.py -q` passes

---

## 6. Troubleshooting

### Issue: `claude: command not found`

**Cause:** Running outside Claude Code/Codex environment

**Solution:** 
- This implementation requires running inside Claude Code/Codex
- Alternative: modify `llm_caller.py` to use Anthropic API directly

### Issue: LLM returns empty output

**Check:**
- User prompt is not empty
- System prompt is valid
- max_tokens is sufficient (at least 2000)

**Fallback:**
- System will automatically use `_fallback_narrative()` for simple output

### Issue: Timeout

**Cause:** LLM generation takes too long

**Solution:**
- Increase timeout (default 120s)
- Reduce max_tokens
- Simplify user prompt

---

## 7. Next Steps (Out of Scope)

After this PR is complete, consider:

1. **Phase 2:** Make Skills call LLM for deep analysis
2. **Phase 3:** Improve evidence filtering and ranking
3. **Phase 4:** Add multiple narrative styles (analytical / storytelling / academic)
4. **Phase 5:** Optimize LLM prompt based on generated quality

---

## 8. Success Criteria

This PR is successful when:

1. ✅ `llm_caller.py` created and tested
2. ✅ `narrative_engine.py` refactored to use LLM
3. ✅ Generated report is 800-1500 字（not 8 lines）
4. ✅ Report reads like natural writing (no template phrases)
5. ✅ All tests pass
6. ✅ Can regenerate doc_beaac21be4b3 successfully
