# Narrative-Driven Report Generation Architecture

> **Status:** Architecture proposal for review
>
> **Goal:** 从"模块化拼接"升级到"叙事整体生成"，让最终报告成为一篇流畅、自然、无脚本感的完整文章。

**Core Insight:** 分析应该是模块化的（Skills 可插拔、可组合），写作应该是整体的（一气呵成，不是拼接）。

**Architecture Shift:**
- 当前：Skills 生成文字片段 → stitcher 拼接 → report.md
- 目标：Skills 生成结构化结论 → narrative engine 统一编织 → report.md

**Tech Stack:** Python 3.11+, Pydantic, PyYAML, pytest

---

## 1. Problem Statement

### 当前架构的局限

现有的 `report_generator.py` 是规则脚本，用关键词匹配和硬编码逻辑生成报告：

```python
KEYWORDS = {
    "identity": ["国内领先", "专注", "主营业务"],
    "product": ["产品", "智慧出行", "智慧办公"],
    ...
}
```

即使引入 Skills 和 section-by-section 生成，如果每个 section 独立生成再拼接，最终报告仍会有：

1. **分段感强**：每个 section 是独立的"块"，段落之间缺乏过渡
2. **脚本感重**：像产品说明书，不像人写的文章
3. **逻辑割裂**：结论之间的因果、递进、对比关系被 section 边界打断
4. **citation 突兀**：citation 按 section 分布，而不是按叙事需要分布

### 目标：一篇真正的文章

不是"6 个模块的报告"，而是"一篇完整的文章"：

- 结论之间有逻辑关系（因果、递进、对比）
- 段落过渡自然，不突然跳转
- 证据和数据融入叙事，不单独成段
- 读起来像分析师写的，不像脚本生成的

---

## 2. New Architecture: Three-Layer Separation

```text
┌────────────────────────────────────────────────────────────┐
│  解读层（Interpretation Layer）                              │
│  - Skills 执行深度分析                                        │
│  - 输出：结构化结论 + 证据链 + 推理过程                         │
│  - NOT：文字片段                                             │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  叙事层（Narrative Layer）                                   │
│  - Narrative Engine 把所有结论编织成完整文章                   │
│  - 输入：所有 Skills 的结论                                   │
│  - 输出：流畅、自然、有逻辑的 report.md                        │
│  - 核心：找结论间的关系，决定叙事顺序，统一写作                 │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  引用层（Citation Layer）                                    │
│  - 给叙事中的事实附上 citation                                │
│  - 保持 citation 编号与 evidence_packet 一致                  │
└────────────────────────────────────────────────────────────┘
```

### 2.1 核心变化

**Before:**
```text
Section 1 (产品定位) → draft 1 → 产品定位段落
Section 2 (客户结构) → draft 2 → 客户结构段落
Section 3 (财务表现) → draft 3 → 财务表现段落
Stitcher → 拼接 → report.md
```

**After:**
```text
Skill 1 (business_goal_decompose) → 结论 A、B、C
Skill 2 (capability_match) → 结论 D、E
Skill 3 (disclosure_gap_scan) → 缺口 F、G
...
Narrative Engine → 找关系 → 决定顺序 → 统一编织 → report.md
```

### 2.2 Skills 的新职责

Skills 不再生成文字，只生成**结构化结论**：

```json
{
  "skill_key": "business_goal_decompose",
  "conclusions": [
    {
      "claim_id": "C1-001",
      "claim": "公司产品定位于高端智能硬件市场",
      "claim_type": "fact",
      "evidence_chain": ["E-001", "E-003"],
      "confidence": "high",
      "reasoning": "招股书第 15 页明确提到'面向高端市场的智能硬件产品'，且客户主要为华为、小米等大厂",
      "related_claims": []
    },
    {
      "claim_id": "C1-002",
      "claim": "客户集中度较高，前五大客户占比超过 60%",
      "claim_type": "fact",
      "evidence_chain": ["T-005"],
      "confidence": "high",
      "reasoning": "表格 T-005 显示前五大客户占比为 62.3%",
      "related_claims": ["C1-001"]
    }
  ],
  "gaps": [
    {
      "gap_id": "G1-001",
      "question": "各产品线的收入和毛利率拆分未披露",
      "impact": "无法评估产品多元化程度和单品盈利能力"
    }
  ]
}
```

**Key fields:**
- `claim_type`: `fact`（直接事实）、`inference`（推断结论）、`risk`（风险判断）
- `confidence`: `high/medium/low`
- `related_claims`: 声明结论之间的依赖关系（供 narrative engine 使用）
- `reasoning`: 内部推理过程（不进入最终报告，仅供调试）

### 2.3 Narrative Engine 的职责

**核心任务：把结构化结论编织成自然文章**

```python
def generate_narrative(
    all_skill_outputs: list[dict],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
    narrative_style: str = "analytical"
) -> str:
    # 1. 收集所有高置信度结论
    high_conf_claims = extract_high_confidence_claims(all_skill_outputs)
    
    # 2. 构建结论依赖图
    narrative_graph = build_narrative_dependencies(high_conf_claims)
    
    # 3. 决定叙事主线和顺序
    narrative_arc = decide_narrative_arc(narrative_graph, narrative_style)
    
    # 4. 用 LLM 把结论编织成自然段落
    report_md = weave_narrative(
        narrative_arc,
        high_conf_claims,
        citation_index,
        narrative_style
    )
    
    return report_md
```

**关键点：**
- 不是"一个结论 = 一段话"
- 而是"多个相关结论 = 一个自然段落"
- 结论之间有因果、递进、对比等逻辑关系
- 段落过渡自然，用叙事手法串联

---

## 3. Detailed Implementation Plan

### 3.1 File Structure

**New files:**
- `src/ipo_evidence/narrative_engine.py` — 叙事引擎核心
- `src/ipo_evidence/skill_executor.py` — Skills 执行引擎
- `configs/prompts/narrative_writer.yaml` — 叙事层 prompt
- `tests/test_narrative_engine.py` — 叙事引擎测试
- `tests/test_skill_executor.py` — Skills 执行测试

**Modified files:**
- `src/ipo_evidence/report_generator.py` — 改造为编排器
- `src/ipo_evidence/report_assembler.py` — 简化或移除（功能并入 narrative_engine）
- `configs/skills/*.yaml` — 扩展 skill schema

**Deprecated files:**
- `src/ipo_evidence/report_generator.py` 中的 `KEYWORDS`、`LOW_VALUE_SNIPPETS` 等硬编码逻辑

### 3.2 Phase 1: Skill Output Schema

**Goal:** 定义 Skills 的输出格式

**Step 1: Extend skill config schema**

Modify `configs/skills/business_goal_decompose.yaml`:

```yaml
skill_key: "business_goal_decompose"
title: "业务目标拆解"
action: "把披露事实拆成产品、客户、收入和资源配置问题"
requires:
  - "core_claim"
produces:
  - "business_question"
  - "structured_conclusion"

output_schema:
  conclusions:
    - claim_id: string
      claim: string
      claim_type: fact | inference | risk
      evidence_chain: list[string]
      confidence: high | medium | low
      reasoning: string
      related_claims: list[string]
  gaps:
    - gap_id: string
      question: string
      impact: string
```

**Step 2: Create SkillOutput model**

Create `src/ipo_evidence/models.py` (extend existing):

```python
@dataclass
class SkillConclusion:
    claim_id: str
    claim: str
    claim_type: str  # fact, inference, risk
    evidence_chain: list[str]
    confidence: str  # high, medium, low
    reasoning: str
    related_claims: list[str] = field(default_factory=list)

@dataclass
class SkillGap:
    gap_id: str
    question: str
    impact: str

@dataclass
class SkillOutput:
    skill_key: str
    conclusions: list[SkillConclusion]
    gaps: list[SkillGap]
```

**Step 3: Write tests**

Create `tests/test_skill_output.py`:

```python
def test_skill_conclusion_schema():
    conclusion = SkillConclusion(
        claim_id="C1-001",
        claim="公司产品定位于高端智能硬件市场",
        claim_type="fact",
        evidence_chain=["E-001", "E-003"],
        confidence="high",
        reasoning="招股书第 15 页明确提到...",
    )
    assert conclusion.confidence in ["high", "medium", "low"]
    assert conclusion.claim_type in ["fact", "inference", "risk"]
```

### 3.3 Phase 2: Skill Executor

**Goal:** 实现 Skills 执行引擎

**Step 1: Create skill_executor.py**

Create `src/ipo_evidence/skill_executor.py`:

```python
from ipo_evidence.models import EvidencePacket, SkillOutput, SkillConclusion
from ipo_evidence.report_runtime import load_skill_configs

def execute_skill(
    skill_key: str,
    evidence_refs: list[dict],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> SkillOutput:
    """
    执行单个 skill，返回结构化结论
    
    Args:
        skill_key: skill 标识
        evidence_refs: 本 skill 可用的证据引用
        evidence_packet: 只读证据包
        citation_index: evidence_id -> citation_id 映射
    
    Returns:
        SkillOutput: 结构化结论和缺口
    """
    skill_config = load_skill_configs([skill_key])[0]
    
    # 收集可用证据
    available_evidence = [
        evidence_packet.get_item(ref["evidence_id"])
        for ref in evidence_refs
        if evidence_packet.get_item(ref["evidence_id"])
    ]
    
    # 根据 skill_key 分发到具体执行逻辑
    if skill_key == "business_goal_decompose":
        return _execute_business_goal_decompose(
            available_evidence, citation_index
        )
    elif skill_key == "capability_match":
        return _execute_capability_match(
            available_evidence, citation_index
        )
    # ... 其他 skills
    
    raise ValueError(f"Unknown skill: {skill_key}")


def _execute_business_goal_decompose(
    evidence_items: list,
    citation_index: dict[str, str],
) -> SkillOutput:
    """
    业务目标拆解逻辑
    """
    conclusions = []
    gaps = []
    
    # 筛选与业务目标相关的证据
    relevant = [
        item for item in evidence_items
        if any(kw in item.text for kw in ["主营业务", "产品", "收入"])
    ]
    
    if len(relevant) < 2:
        gaps.append(SkillGap(
            gap_id="G-BG-001",
            question="业务目标相关证据不足",
            impact="无法完整拆解业务模式"
        ))
        return SkillOutput(
            skill_key="business_goal_decompose",
            conclusions=[],
            gaps=gaps
        )
    
    # 提取结论（这里可以调 LLM 或用规则）
    for idx, item in enumerate(relevant[:3]):
        conclusions.append(SkillConclusion(
            claim_id=f"C-BG-{idx:03d}",
            claim=f"从 {item.text[:50]} 提取的业务判断",
            claim_type="fact",
            evidence_chain=[item.evidence_id],
            confidence="high" if item.quality_score > 0.7 else "medium",
            reasoning=f"基于证据 {item.evidence_id} 的直接陈述",
        ))
    
    return SkillOutput(
        skill_key="business_goal_decompose",
        conclusions=conclusions,
        gaps=gaps
    )
```

**Step 2: Write tests**

Create `tests/test_skill_executor.py`:

```python
def test_execute_skill_returns_structured_output():
    packet = build_evidence_packet(...)
    citation_index = {"E-001": "C-001"}
    
    output = execute_skill(
        skill_key="business_goal_decompose",
        evidence_refs=[{"evidence_id": "E-001", "rank": 1}],
        evidence_packet=packet,
        citation_index=citation_index,
    )
    
    assert output.skill_key == "business_goal_decompose"
    assert isinstance(output.conclusions, list)
    assert all(isinstance(c, SkillConclusion) for c in output.conclusions)
```

### 3.4 Phase 3: Narrative Engine Core

**Goal:** 实现叙事引擎

**Step 1: Create narrative_engine.py**

Create `src/ipo_evidence/narrative_engine.py`:

```python
from ipo_evidence.models import SkillOutput, SkillConclusion, EvidencePacket

def generate_narrative(
    all_skill_outputs: list[SkillOutput],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
    narrative_style: str = "analytical",
) -> tuple[str, dict]:
    """
    把所有 Skills 的结构化结论编织成完整文章
    
    Returns:
        (report_md, narrative_trace)
    """
    # 1. 收集所有高置信度结论
    high_conf_claims = _collect_high_confidence_claims(all_skill_outputs)
    
    # 2. 构建结论依赖图
    narrative_graph = _build_narrative_graph(high_conf_claims)
    
    # 3. 决定叙事顺序
    narrative_arc = _decide_narrative_arc(narrative_graph, narrative_style)
    
    # 4. 编织成文章
    report_md = _weave_narrative(
        narrative_arc,
        high_conf_claims,
        citation_index,
        narrative_style,
    )
    
    # 5. 生成叙事追踪（供调试和质量评估）
    narrative_trace = {
        "total_claims": len(high_conf_claims),
        "used_claims": len(narrative_arc),
        "narrative_order": [c.claim_id for c in narrative_arc],
    }
    
    return report_md, narrative_trace


def _collect_high_confidence_claims(
    outputs: list[SkillOutput]
) -> list[SkillConclusion]:
    """收集高置信度结论"""
    claims = []
    for output in outputs:
        for conclusion in output.conclusions:
            if conclusion.confidence in ["high", "medium"]:
                claims.append(conclusion)
    return claims


def _build_narrative_graph(
    claims: list[SkillConclusion]
) -> dict[str, list[str]]:
    """构建结论依赖图"""
    graph = {claim.claim_id: claim.related_claims for claim in claims}
    return graph


def _decide_narrative_arc(
    graph: dict[str, list[str]],
    narrative_style: str,
) -> list[SkillConclusion]:
    """
    决定叙事顺序
    
    策略：
    1. 拓扑排序（保证依赖关系）
    2. 按 claim_type 分组（fact -> inference -> risk）
    3. 按 narrative_style 调整顺序
    """
    # 简化实现：先按 claim_type 排序
    # 实际应该用拓扑排序 + 启发式调整
    sorted_claims = sorted(
        claims,
        key=lambda c: {"fact": 0, "inference": 1, "risk": 2}.get(c.claim_type, 3)
    )
    return sorted_claims


def _weave_narrative(
    narrative_arc: list[SkillConclusion],
    all_claims: list[SkillConclusion],
    citation_index: dict[str, str],
    narrative_style: str,
) -> str:
    """
    把结论编织成自然文章
    
    核心逻辑：
    1. 按叙事顺序遍历结论
    2. 找到相关的结论组（related_claims）
    3. 把相关结论合并成一个自然段落
    4. 添加过渡句
    """
    # 这里应该调用 LLM，传入：
    # - narrative_arc（结论顺序）
    # - citation_index（证据映射）
    # - narrative_style（写作风格）
    # 
    # Prompt 参考 configs/prompts/narrative_writer.yaml
    
    # 简化实现：先拼接
    paragraphs = []
    for claim in narrative_arc:
        citations = [citation_index[eid] for eid in claim.evidence_chain if eid in citation_index]
        citation_str = "".join(f"[{cid}]" for cid in citations)
        paragraphs.append(f"{claim.claim}{citation_str}")
    
    return "\n\n".join(paragraphs)
```

**Step 2: Write tests**

Create `tests/test_narrative_engine.py`:

```python
def test_generate_narrative_returns_markdown():
    skill_outputs = [
        SkillOutput(
            skill_key="business_goal_decompose",
            conclusions=[
                SkillConclusion(
                    claim_id="C1-001",
                    claim="公司产品定位于高端智能硬件市场",
                    claim_type="fact",
                    evidence_chain=["E-001"],
                    confidence="high",
                    reasoning="...",
                )
            ],
            gaps=[],
        )
    ]
    
    report_md, trace = generate_narrative(
        all_skill_outputs=skill_outputs,
        evidence_packet=...,
        citation_index={"E-001": "C-001"},
        narrative_style="analytical",
    )
    
    assert isinstance(report_md, str)
    assert "[C-001]" in report_md
    assert trace["total_claims"] == 1
```

### 3.5 Phase 4: Narrative Writer Prompt

**Goal:** 定义叙事层的 Prompt

Create `configs/prompts/narrative_writer.yaml`:

```yaml
prompt_slot: "narrative_writer"
purpose: "把结构化的解读结论编织成一篇自然、流畅、有文章感的报告"

context: |
  你会收到多个 Skills 生成的结构化结论，每个结论包含：
  - claim: 核心判断
  - evidence_chain: 支撑证据的 ID
  - confidence: 置信度
  - related_claims: 相关结论的 ID
  
  你的任务是把这些结论编织成一篇完整的文章，而不是逐条罗列。

rules:
  - "找到结论之间的逻辑关系（因果、递进、对比、补充）"
  - "相关的结论应该合并到同一段落，而不是分开写"
  - "用自然语言串联，避免'首先'、'其次'、'最后'这类列举词"
  - "段落之间要有自然过渡，不要突然跳转话题"
  - "数据和事实要融入叙事，不要单独成段罗列"
  - "citation 要自然嵌入，紧跟事实陈述，不要堆在句尾"
  - "避免'根据招股书'、'数据显示'、'可以看出'这类脚本感表达"
  - "用具体描述代替抽象总结，用动词代替名词"
  - "证据不足时可以说'招股书未详细披露'，但不要留空段或占位符"
  
narrative_patterns:
  opening:
    - "从公司的核心定位切入，用 1-2 句话勾勒业务全貌"
    - "不要用'XX公司成立于XX年'这样的官腔开头"
    - "例：'这是一家把 AI 能力装进消费硬件的公司'"
  
  body:
    - "按'是什么 -> 为什么 -> 有什么问题'的逻辑展开"
    - "用因果关系串联：'这个定位决定了它的客户结构'"
    - "用对比突出张力：'收入增长很快，但毛利率并不算高'"
    - "用递进深化分析：'不仅如此，招股书中还透露...'"
  
  transition:
    - "段落之间用逻辑连接，而不是硬切"
    - "例：'这种集中度既是优势，也是风险'"
    - "例：'真正值得关注的是...'"
    - "例：'但这背后的逻辑是...'"
  
  evidence_integration:
    - "数据紧跟判断，形成证据链"
    - "例：'前五大客户占比超过 60%，[C-001] 主要是华为、小米这样的大厂。[C-002]'"
    - "不要写成：'客户集中度较高。[C-001] 前五大客户占比为 62.3%。'"
  
  closing:
    - "回到对读者的价值，而不是简单总结"
    - "例：'对于关注这家公司的人来说，值得追问的是...'"
    - "不要写：'综上所述，公司具有以下特点...'"

style_constraints:
  tone: "分析性，不是营销性或学术性"
  perspective: "第三人称，客观陈述，不用'我们认为'"
  sentence_length: "长短结合，平均 15-25 字，避免超长句"
  paragraph_length: "每段 3-6 句话，不要单句成段"
  terminology: "用行业通用术语，不生造概念"

anti_patterns:
  avoid_list_style:
    - "❌ 公司主要有以下三个特点：1. ... 2. ... 3. ..."
    - "✓ 这家公司有三个特点。第一个是...，这决定了...。更重要的是..."
  
  avoid_template_phrases:
    - "❌ 根据招股书披露"
    - "✓ 招股书中提到"
    - "❌ 数据显示"
    - "✓ 2023 年营收 5.2 亿元"
    - "❌ 可以看出"
    - "✓ （直接写结论）"
  
  avoid_abrupt_jumps:
    - "❌ 公司产品定位高端。客户集中度较高。"
    - "✓ 公司产品定位高端，这决定了它的客户结构——前五大客户占比超过 60%。"

output_format:
  structure: "连续的自然段落，不要加小标题或分节"
  citation: "紧跟事实陈述，用 [C-XXX] 格式"
  length: "根据结论数量自然展开，不强求字数"
```

### 3.6 Phase 5: Integrate into Report Generator

**Goal:** 改造 `report_generator.py` 为编排器

Modify `src/ipo_evidence/report_generator.py`:

```python
from ipo_evidence.skill_executor import execute_skill
from ipo_evidence.narrative_engine import generate_narrative
from ipo_evidence.report_inputs import build_report_inputs

def generate_report(
    doc_id: str,
    company_name: str,
    evidence_packet: EvidencePacket,
) -> tuple[str, dict, dict]:
    """
    新的报告生成流程
    
    Returns:
        (report_md, citation_dict, narrative_trace)
    """
    # 1. 构建 report_inputs（调度层）
    report_inputs = build_report_inputs(doc_id, company_name, evidence_packet)
    
    # 2. 构建 citation index
    citation_index = {
        item.evidence_id: _citation_id(idx + 1)
        for idx, item in enumerate(evidence_packet.items)
    }
    
    # 3. 执行所有 Skills（解读层）
    all_skill_outputs = []
    for section_group in report_inputs["section_groups"]:
        for skill_ref in section_group["skill_refs"]:
            skill_output = execute_skill(
                skill_key=skill_ref,
                evidence_refs=section_group["evidence_refs"],
                evidence_packet=evidence_packet,
                citation_index=citation_index,
            )
            all_skill_outputs.append(skill_output)
    
    # 4. 生成叙事（叙事层）
    report_md, narrative_trace = generate_narrative(
        all_skill_outputs=all_skill_outputs,
        evidence_packet=evidence_packet,
        citation_index=citation_index,
        narrative_style="analytical",
    )
    
    # 5. 构建 citation.json
    citation_dict = _build_citation_dict(evidence_packet, citation_index)
    
    return report_md, citation_dict, narrative_trace
```

---

## 4. Example: Before vs After

### Before (Section-by-Section 拼接)

```markdown
## 产品定位

公司主要产品为智能硬件，定位高端市场。[C-001] 产品包括智能音箱、智能显示器等。[C-002]

## 客户结构

前五大客户占比为 62.3%，客户集中度较高。[C-015] 主要客户包括华为、小米等。[C-016]

## 财务表现

2023 年营收 5.2 亿元，同比增长 45%。[C-023] 毛利率为 38.5%。[C-024]
```

**问题：**
- 分段感强，像产品说明书
- 结论之间没有逻辑关系
- citation 堆砌，不自然
- 读起来像脚本生成的

### After (Narrative Engine)

```markdown
这是一家把 AI 能力装进消费硬件的公司。[C-001] 它的产品不是简单的智能音箱，而是试图在车载、会议、家居等场景里提供对话式交互入口。[C-002] 这个定位决定了它的客户结构：前五大客户占比超过 60%，[C-015] 主要是华为、小米这样有生态需求的大厂。[C-016] 这种集中度既是优势（能快速放量），也是风险（议价能力弱）。

收入增长很快——2023 年 5.2 亿，比上一年多了 45%，[C-023] 但毛利率 38.5% 并不算特别高。[C-024] 这背后的逻辑是：它不是纯软件公司，硬件成本、供应链管理都会压缩利润空间。招股书中没有详细拆分各产品线的毛利率，但从客户集中度和定价能力看，议价空间不大。

真正值得关注的是它的研发投入结构...
```

**改进：**
- 结论之间有因果、递进、对比关系
- 段落过渡自然，用逻辑连接词串联
- citation 自然嵌入，不突兀
- 读起来像人写的分析文章

---

## 5. Implementation Phases

### Phase 1: Skill Output Schema (Week 1)

**Deliverables:**
- [ ] Extend `configs/skills/*.yaml` with `output_schema`
- [ ] Create `SkillOutput`, `SkillConclusion`, `SkillGap` models
- [ ] Write tests for skill output schema
- [ ] Commit: `feat: define skill output schema`

**Validation:**
- `pytest tests/test_skill_output.py -q` passes

### Phase 2: Skill Executor (Week 1-2)

**Deliverables:**
- [ ] Create `src/ipo_evidence/skill_executor.py`
- [ ] Implement `execute_skill()` dispatcher
- [ ] Implement `_execute_business_goal_decompose()` as first example
- [ ] Implement `_execute_capability_match()` as second example
- [ ] Write tests for skill executor
- [ ] Commit: `feat: implement skill executor`

**Validation:**
- `pytest tests/test_skill_executor.py -q` passes
- Can execute at least 2 skills and get structured output

### Phase 3: Narrative Engine Core (Week 2)

**Deliverables:**
- [ ] Create `src/ipo_evidence/narrative_engine.py`
- [ ] Implement `generate_narrative()` main flow
- [ ] Implement `_collect_high_confidence_claims()`
- [ ] Implement `_build_narrative_graph()`
- [ ] Implement `_decide_narrative_arc()` (simple version)
- [ ] Implement `_weave_narrative()` (simple concatenation first)
- [ ] Write tests for narrative engine
- [ ] Commit: `feat: implement narrative engine core`

**Validation:**
- `pytest tests/test_narrative_engine.py -q` passes
- Can generate markdown from skill outputs (even if simple)

### Phase 4: Narrative Writer Prompt (Week 2-3)

**Deliverables:**
- [ ] Create `configs/prompts/narrative_writer.yaml`
- [ ] Define rules, narrative_patterns, style_constraints
- [ ] Define anti_patterns with examples
- [ ] Update `_weave_narrative()` to use LLM with this prompt
- [ ] Test with real evidence packet
- [ ] Commit: `feat: add narrative writer prompt`

**Validation:**
- Generated report has natural flow, not list-style
- No template phrases like "根据招股书披露"
- Citation naturally embedded

### Phase 5: Integration (Week 3)

**Deliverables:**
- [ ] Refactor `report_generator.py` to use new architecture
- [ ] Remove old `KEYWORDS`, `LOW_VALUE_SNIPPETS` logic
- [ ] Update `pipeline.py` to call new `generate_report()`
- [ ] Simplify or remove `report_assembler.py`
- [ ] Update all tests
- [ ] Run end-to-end test with real document
- [ ] Commit: `feat: integrate narrative-driven generation`

**Validation:**
- `pytest -q` all passes
- `python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3` succeeds
- Generated report has article feel, not script feel

### Phase 6: Additional Skills (Week 4+)

**Deliverables:**
- [ ] Implement remaining skills:
  - `disclosure_gap_scan`
  - `reader_value_translate`
  - `tension_expand`
- [ ] Test each skill independently
- [ ] Test narrative engine with all skills combined
- [ ] Commit: `feat: implement additional skills`

**Validation:**
- All 5 core skills working
- Narrative engine can handle 10+ conclusions
- Report maintains natural flow with more content

---

## 6. Migration Strategy

### Backward Compatibility

During migration, support both old and new generation paths:

```python
def generate_report(
    doc_id: str,
    company_name: str,
    evidence_packet: EvidencePacket,
    use_narrative_engine: bool = False,  # Feature flag
) -> tuple[str, dict, dict]:
    if use_narrative_engine:
        return _generate_report_narrative(doc_id, company_name, evidence_packet)
    else:
        return _generate_report_legacy(doc_id, company_name, evidence_packet)
```

### Deprecation Path

1. **Phase 1-3:** New architecture coexists with old
2. **Phase 4:** Default to new architecture, keep old as fallback
3. **Phase 5:** Remove old architecture after validation

---

## 7. Quality Metrics

### How to Measure Success

**Objective metrics:**
- Citation coverage: ≥ 90% of facts have citations
- Conclusion confidence: ≥ 70% high-confidence claims used
- Gap tracking: All low-confidence areas logged

**Subjective metrics (human review):**
- Natural flow: Does it read like an article?
- Logical coherence: Are conclusions connected?
- No script feel: Avoid template phrases?
- Smooth transitions: No abrupt jumps?

### Validation Checklist

Run this on generated reports:

```python
def validate_narrative_quality(report_md: str) -> dict:
    return {
        "has_headers": "##" in report_md,  # Should be False
        "template_phrases": count_template_phrases(report_md),  # Should be 0
        "avg_paragraph_length": calculate_avg_paragraph_length(report_md),
        "citation_distribution": check_citation_distribution(report_md),
    }
```

---

## 8. Out of Scope

**Not in this PR:**
- External facts (`external_fact`, web scraping)
- Multi-document comparison (`cross_doc_fact`)
- Visual fact extraction (`visual_fact`)
- Quality notes as separate artifact (`quality_notes.md`)
- Advanced narrative patterns (rhetorical devices, storytelling)

**Why deferred:**
- Focus on core architecture first
- External facts require separate data pipeline
- Advanced patterns need more prompt engineering

---

## 9. Risk Assessment

### High Risk

**Risk:** Narrative engine generates hallucinations
**Mitigation:** 
- All claims must have `evidence_chain`
- LLM prompt explicitly forbids adding facts not in input
- Post-generation validation checks citation coverage

### Medium Risk

**Risk:** Natural flow sacrifices information density
**Mitigation:**
- Keep skill output schema separate from narrative
- All conclusions stored in `narrative_trace` for audit
- Can regenerate with different narrative style

### Low Risk

**Risk:** Performance regression (slower generation)
**Mitigation:**
- Skills run in parallel (future optimization)
- Narrative generation is single LLM call
- Likely faster than current multi-section generation

---

## 10. Success Criteria

This PR is successful when:

1. ✅ All 5 phases completed and tested
2. ✅ Generated report reads like an article, not a script
3. ✅ No template phrases in generated content
4. ✅ Citation coverage ≥ 90%
5. ✅ Human review: "This feels natural"
6. ✅ All existing tests pass
7. ✅ Can regenerate existing documents without regression

