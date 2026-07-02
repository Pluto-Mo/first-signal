# Narrative-Driven Report Generation with Pluggable Interpretation Skills

> **Status:** Architecture proposal for review
>
> **Goal:** 从"规则脚本"升级到"方法包 + 叙事引擎"架构，让报告生成既有深度解读，又有文章感。

**Core Insight:** 
- **解读方法应该是可插拔的**（现在用"招股书解读方法包"，以后可以换）
- **叙事引擎应该是稳定的**（负责把解读结果编织成文章）
- **Skills 负责深度分析**（业务目标拆解、能力匹配、披露缺口、矛盾张力、读者价值）
- **Narrative Engine 负责自然表达**（把分析结果写成流畅文章，不是拼接）

**Architecture Shift:**
- 当前：硬编码规则脚本（`KEYWORDS` 匹配 + 模板拼接）→ report.md
- 目标：可插拔 Skills（招股书解读方法包）→ Narrative Engine（统一编织）→ report.md

**Tech Stack:** Python 3.11+, Pydantic, PyYAML, pytest

---

## 1. Problem Statement

### 1.1 当前架构的问题

`report_generator.py` 是硬编码的规则脚本：

```python
KEYWORDS = {
    "identity": ["国内领先", "专注", "主营业务"],
    "product": ["产品", "智慧出行", "智慧办公"],
    ...
}
```

这种方式：
- ❌ 解读逻辑和代码混在一起，无法替换
- ❌ 生成的报告像产品说明书，不像文章
- ❌ 无法支持不同的解读视角（投资人、从业者、消费者）
- ❌ 新增分析维度需要改代码

### 1.2 目标架构

```text
┌──────────────────────────────────────────────────────────┐
│  Skills Package（可插拔的解读方法包）                       │
│  - 当前：招股书解读方法包                                   │
│  - 以后：可以换成其他方法包                                 │
├──────────────────────────────────────────────────────────┤
│  Skill 1: 业务目标拆解                                     │
│    输出：公司想做什么？产品是什么？服务谁？                  │
│  Skill 2: 能力匹配                                        │
│    输出：资源配置能不能支撑目标？哪里强？哪里弱？             │
│  Skill 3: 披露缺口识别                                    │
│    输出：关键信息哪些没讲透？为什么？                        │
│  Skill 4: 矛盾张力展开                                    │
│    输出：强项和弱项如何同时存在？张力在哪？                  │
│  Skill 5: 读者价值翻译                                    │
│    输出：对技术人/投资人/从业者/消费者分别意味着什么？        │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│  Narrative Engine（叙事引擎，稳定不变）                     │
│  - 输入：所有 Skills 的解读结果                            │
│  - 输出：一篇流畅、自然、有逻辑的文章                       │
│  - 核心：找解读之间的关系，决定叙事顺序，统一写作           │
└──────────────────────────────────────────────────────────┘
                           ↓
                      report.md
```

### 1.3 Skills 是什么

**Skills = 招股书解读方法包**

不是"提取事实"，而是**深度分析**：

| Skill | 它回答什么问题 | 输出示例 |
|-------|--------------|---------|
| 业务目标拆解 | 公司想做什么？产品是什么？服务谁？ | "这家公司想把 AI 能力装进消费硬件，在车载、会议、家居场景提供对话式交互入口。" |
| 能力匹配 | 资源配置能不能支撑目标？哪里强？哪里弱？ | "研发投入占比高，但毛利率偏低，说明硬件成本和供应链管理压缩了利润空间。" |
| 披露缺口识别 | 关键信息哪些没讲透？为什么？ | "各产品线的收入和毛利率没拆分，无法判断单品盈利能力。" |
| 矛盾张力展开 | 强项和弱项如何同时存在？张力在哪？ | "客户集中度高既是优势（能快速放量），也是风险（议价能力弱）。" |
| 读者价值翻译 | 对不同读者分别意味着什么？ | "技术人：看研发方向；投资人：看盈利能力；从业者：看行业趋势。" |

Skills 的输出不是"事实罗列"，而是**深度判断**。

### 1.4 Narrative Engine 是什么

**把 Skills 的解读结果编织成一篇自然文章**

不是：
```markdown
## 业务目标
公司想做 XXX。

## 能力匹配
资源配置 YYY。

## 披露缺口
关键信息 ZZZ。
```

而是：
```markdown
这是一家把 AI 能力装进消费硬件的公司。它的产品不是简单的智能音箱，而是试图在车载、会议、家居等场景里提供对话式交互入口。这个定位决定了它的客户结构——前五大客户占比超过 60%，主要是华为、小米这样有生态需求的大厂。

这种集中度既是优势（能快速放量），也是风险（议价能力弱）。从数据看，2023 年营收增长 45%，但毛利率只有 38.5%。这背后的逻辑是：它不是纯软件公司，硬件成本会压缩利润空间。招股书中没有详细拆分各产品线的毛利率，但从客户集中度和定价能力看，议价空间不大。

真正值得关注的是...
```

**核心差异：**
- 结论之间有逻辑关系（因果、递进、对比）
- 段落过渡自然，不突然跳转
- 读起来像人写的，不像脚本生成的

---

## 2. Architecture Design

### 2.1 Overall Flow

```text
evidence_packet.json
  ↓
report_inputs.json (调度层：声明哪些 Skills 可以用哪些证据)
  ↓
┌─────────────────────────────────────────────────────────┐
│ Skill Executor 逐个执行 Skills                           │
├─────────────────────────────────────────────────────────┤
│ Skill 1: 业务目标拆解                                     │
│   输入: evidence_refs (business_and_product, financials) │
│   输出: {                                                │
│     "business_goal": "把 AI 能力装进消费硬件",            │
│     "target_scenario": ["车载", "会议", "家居"],         │
│     "evidence_chain": ["E-001", "E-002"],               │
│     "confidence": "high"                                │
│   }                                                     │
│                                                         │
│ Skill 2: 能力匹配                                        │
│   输入: evidence_refs (financials, risks)               │
│   输出: {                                                │
│     "strength": ["研发投入占比高"],                       │
│     "weakness": ["毛利率偏低", "客户集中"],              │
│     "tension": "快速放量 vs 议价能力弱",                  │
│     "evidence_chain": ["T-005", "E-012"],               │
│     "confidence": "high"                                │
│   }                                                     │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
  ↓
all_skill_outputs (所有 Skills 的解读结果)
  ↓
┌─────────────────────────────────────────────────────────┐
│ Narrative Engine 编织成文章                              │
├─────────────────────────────────────────────────────────┤
│ 1. 收集所有解读结果                                       │
│ 2. 找到结论之间的逻辑关系（因果、递进、对比）              │
│ 3. 决定叙事顺序                                          │
│ 4. 用自然语言编织成完整文章                               │
│ 5. 附上 citation                                        │
└─────────────────────────────────────────────────────────┘
  ↓
report.md (一篇流畅的文章)
```

### 2.2 Skills Output Schema

每个 Skill 输出一个**解读结果**（不是文字片段）：

```python
@dataclass
class SkillInterpretation:
    skill_key: str
    
    # 核心解读（自由格式，由 Skill 决定）
    interpretation: dict[str, Any]
    
    # 证据链（必须）
    evidence_chain: list[str]
    
    # 置信度（必须）
    confidence: str  # high, medium, low
    
    # 信息缺口（可选）
    gaps: list[dict[str, str]]
```

**示例 1: 业务目标拆解**

```json
{
  "skill_key": "business_goal_decompose",
  "interpretation": {
    "business_goal": "把 AI 能力装进消费硬件",
    "product_entry": ["智能音箱", "车载设备", "会议设备"],
    "target_scenario": ["车载", "会议", "家居"],
    "customer_type": "B2B（大厂生态合作）"
  },
  "evidence_chain": ["E-001", "E-002", "T-003"],
  "confidence": "high",
  "gaps": []
}
```

**示例 2: 能力匹配**

```json
{
  "skill_key": "capability_match",
  "interpretation": {
    "strengths": [
      "研发投入占比 25%，高于同行",
      "前五大客户均为行业龙头"
    ],
    "weaknesses": [
      "毛利率 38.5%，低于纯软件公司",
      "客户集中度 62.3%，议价能力弱"
    ],
    "tension": "快速放量能力 vs 利润压缩风险",
    "resource_allocation": "研发和销售投入高，但受硬件成本约束"
  },
  "evidence_chain": ["T-005", "E-012", "E-015"],
  "confidence": "high",
  "gaps": [
    {
      "gap": "各产品线的毛利率未披露",
      "impact": "无法判断单品盈利能力"
    }
  ]
}
```

**示例 3: 披露缺口识别**

```json
{
  "skill_key": "disclosure_gap_scan",
  "interpretation": {
    "critical_gaps": [
      "各产品线收入和毛利率拆分缺失",
      "前五大客户的具体合作模式未详述",
      "研发费用的细分方向未披露"
    ],
    "possible_reasons": [
      "产品线尚未成熟，拆分无意义",
      "客户合同保密条款约束",
      "研发方向涉及商业机密"
    ]
  },
  "evidence_chain": ["E-020", "E-025"],
  "confidence": "medium",
  "gaps": []
}
```

**关键点：**
- `interpretation` 字段是自由格式，由 Skill 自己定义结构
- 不同 Skill 的 `interpretation` 结构可以完全不同
- 必须有 `evidence_chain`（口出有凭）
- 必须有 `confidence`（质量控制）

### 2.3 Five Core Skills Definition

#### Skill 1: 业务目标拆解 (business_goal_decompose)

**What it does:**
把披露事实拆成产品、客户、收入和资源配置问题。

**Input:**
- evidence_refs from: `business_and_product`, `about_company`, `financials`

**Output structure:**
```python
{
  "business_goal": str,           # 公司想做什么
  "product_entry": list[str],     # 产品入口
  "target_scenario": list[str],   # 目标场景
  "customer_type": str,           # 客户类型（B2B/B2C/混合）
  "revenue_structure": str,       # 收入结构特征
}
```

**Example output:**
```json
{
  "skill_key": "business_goal_decompose",
  "interpretation": {
    "business_goal": "把 AI 能力装进消费硬件，在多场景提供对话式交互",
    "product_entry": ["智能音箱", "车载设备", "会议设备", "智能家居"],
    "target_scenario": ["车载", "会议", "教育", "家居"],
    "customer_type": "B2B（生态合作为主）",
    "revenue_structure": "硬件销售为主，软件收入占比低"
  },
  "evidence_chain": ["E-001", "E-002", "T-003"],
  "confidence": "high",
  "gaps": []
}
```

#### Skill 2: 能力匹配 (capability_match)

**What it does:**
评估资源配置是否能支撑业务目标，找出强项和弱项。

**Input:**
- evidence_refs from: `financials`, `business_and_product`, `risks`

**Output structure:**
```python
{
  "strengths": list[str],        # 能力强项
  "weaknesses": list[str],       # 能力弱项
  "tension": str,                # 核心张力点
  "resource_allocation": str,    # 资源配置特征
}
```

**Example output:**
```json
{
  "skill_key": "capability_match",
  "interpretation": {
    "strengths": [
      "研发投入占比 25%，高于行业平均",
      "前五大客户均为行业龙头，客户质量高",
      "产品覆盖多场景，应用广度大"
    ],
    "weaknesses": [
      "毛利率 38.5%，低于纯软件公司",
      "客户集中度 62.3%，议价能力受限",
      "硬件成本占比高，利润空间被压缩"
    ],
    "tension": "快速放量能力（大客户背书）vs 利润压缩风险（议价能力弱 + 硬件成本高）",
    "resource_allocation": "重研发 + 重销售，但受硬件成本结构约束"
  },
  "evidence_chain": ["T-005", "E-012", "E-015", "T-008"],
  "confidence": "high",
  "gaps": [
    {
      "gap": "各产品线的毛利率未拆分",
      "impact": "无法判断单品盈利能力和未来利润改善空间"
    }
  ]
}
```

#### Skill 3: 披露缺口识别 (disclosure_gap_scan)

**What it does:**
识别招股书中关键信息的缺失，推断可能的原因。

**Input:**
- evidence_refs from: all sections

**Output structure:**
```python
{
  "critical_gaps": list[str],      # 关键信息缺口
  "possible_reasons": list[str],   # 可能的原因
  "workarounds": list[str],        # 可以用什么方式推断
}
```

**Example output:**
```json
{
  "skill_key": "disclosure_gap_scan",
  "interpretation": {
    "critical_gaps": [
      "各产品线收入和毛利率拆分缺失",
      "前五大客户的具体合作模式未详述",
      "研发费用按技术方向的细分未披露",
      "平台类客户（华为、小米）的依赖度风险未量化"
    ],
    "possible_reasons": [
      "产品线尚未成熟，拆分意义不大",
      "客户合同有保密条款",
      "研发方向涉及商业机密",
      "平台依赖问题敏感，避免详述"
    ],
    "workarounds": [
      "从客户结构和收入集中度反推产品线分布",
      "从研发人员配置推断技术方向",
      "从毛利率变化趋势推断产品结构调整"
    ]
  },
  "evidence_chain": ["E-020", "E-025", "T-010"],
  "confidence": "medium",
  "gaps": []
}
```

#### Skill 4: 矛盾张力展开 (tension_expand)

**What it does:**
识别强项和弱项如何同时存在，展开其中的张力和权衡。

**Input:**
- evidence_refs from: `financials`, `risks`, `business_and_product`
- context from: `capability_match` output

**Output structure:**
```python
{
  "tension_point": str,           # 核心张力点
  "positive_side": str,           # 正面因素
  "negative_side": str,           # 负面因素
  "tradeoff_logic": str,          # 权衡逻辑
  "future_path": list[str],       # 可能的演化路径
}
```

**Example output:**
```json
{
  "skill_key": "tension_expand",
  "interpretation": {
    "tension_point": "客户集中度 62.3%",
    "positive_side": "能快速放量，客户质量高（华为、小米、阿里），有大厂背书",
    "negative_side": "议价能力弱，一旦失去核心客户会严重影响收入",
    "tradeoff_logic": "创业期选择大客户战略可以快速验证产品，但长期需要拓展客户结构来降低风险",
    "future_path": [
      "继续深耕大客户生态，成为平台级供应商",
      "横向拓展中小客户，分散集中度风险",
      "纵向延伸产业链，提升议价能力"
    ]
  },
  "evidence_chain": ["T-005", "E-012", "E-018"],
  "confidence": "high",
  "gaps": []
}
```

#### Skill 5: 读者价值翻译 (reader_value_translate)

**What it does:**
把分析结果翻译成不同读者关心的语言。

**Input:**
- All previous skill outputs

**Output structure:**
```python
{
  "for_tech_people": str,         # 技术人关心什么
  "for_investors": str,           # 投资人关心什么
  "for_practitioners": str,       # 从业者关心什么
  "for_consumers": str,           # 消费者关心什么（如果相关）
}
```

**Example output:**
```json
{
  "skill_key": "reader_value_translate",
  "interpretation": {
    "for_tech_people": "值得关注的是它的技术方向：端侧 AI + 对话式交互。研发投入占比 25%，重点在算法和芯片适配。如果你在做类似方向，可以参考它的场景选择。",
    "for_investors": "收入增长快（45%），但毛利率偏低（38.5%）且客户集中（62.3%）。盈利能力受硬件成本约束，议价空间有限。关键看未来能否拓展客户结构或提升产品附加值。",
    "for_practitioners": "它选择了 B2B 生态合作路线，而不是直接 2C。这意味着产品设计、渠道策略、定价模式都围绕大客户需求。如果你在相关行业，可以观察它的客户拓展节奏。",
    "for_consumers": "这家公司的产品你可能在华为、小米的设备里见过，但不会直接买到它的品牌产品。它是幕后供应商，不是面向消费者的品牌。"
  },
  "evidence_chain": ["E-001", "T-005", "E-012", "E-015"],
  "confidence": "high",
  "gaps": []
}
```

### 2.4 Skills 的可插拔性

**当前：招股书解读方法包**
```yaml
# configs/skill_packages/ipo_prospectus_analysis.yaml
package_key: "ipo_prospectus_analysis"
title: "招股书解读方法包"
skills:
  - business_goal_decompose
  - capability_match
  - disclosure_gap_scan
  - tension_expand
  - reader_value_translate
```

**未来：可以换成其他方法包**
```yaml
# configs/skill_packages/financial_quality_audit.yaml
package_key: "financial_quality_audit"
title: "财务质量审查包"
skills:
  - revenue_quality_check
  - cash_flow_analysis
  - asset_quality_scan
  - earnings_manipulation_detect
```

**关键点：**
- Skills Package 是可配置的
- Narrative Engine 不关心用哪个 Package
- 只要 Skills 输出符合 `SkillInterpretation` schema，就能编织成文章

---

## 3. Narrative Engine Design

### 3.1 核心职责

**把 Skills 的解读结果编织成一篇自然文章**

输入：
```python
[
  SkillInterpretation(business_goal_decompose),
  SkillInterpretation(capability_match),
  SkillInterpretation(disclosure_gap_scan),
  SkillInterpretation(tension_expand),
  SkillInterpretation(reader_value_translate),
]
```

输出：
```markdown
这是一家把 AI 能力装进消费硬件的公司。[C-001] 它的产品不是简单的智能音箱...

（一篇完整的文章）
```

### 3.2 Narrative Engine 的工作流程

```python
def generate_narrative(
    all_skill_outputs: list[SkillInterpretation],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> tuple[str, dict]:
    # 1. 提取所有解读结果
    interpretations = [s.interpretation for s in all_skill_outputs]
    
    # 2. 构建叙事素材包
    narrative_materials = {
        "business_goal": interpretations[0],
        "capability": interpretations[1],
        "gaps": interpretations[2],
        "tension": interpretations[3],
        "reader_value": interpretations[4],
    }
    
    # 3. 构建证据映射
    evidence_map = {}
    for skill_output in all_skill_outputs:
        for eid in skill_output.evidence_chain:
            if eid in citation_index:
                evidence_map[eid] = citation_index[eid]
    
    # 4. 调用 Narrative Writer Prompt
    report_md = _call_narrative_writer(
        narrative_materials,
        evidence_map,
    )
    
    # 5. 生成叙事追踪
    narrative_trace = {
        "skills_used": [s.skill_key for s in all_skill_outputs],
        "total_evidence": len(evidence_map),
        "confidence_distribution": _count_confidence(all_skill_outputs),
    }
    
    return report_md, narrative_trace
```

### 3.3 Narrative Writer Prompt (核心)

Create `configs/prompts/narrative_writer.yaml`:

```yaml
prompt_slot: "narrative_writer"
purpose: "把招股书解读方法包的输出编织成一篇自然、流畅、有深度的文章"

input_structure: |
  你会收到 5 个 Skills 的解读结果：
  
  1. business_goal_decompose: 公司想做什么、产品是什么、服务谁
  2. capability_match: 资源配置能不能支撑、哪里强、哪里弱
  3. disclosure_gap_scan: 关键信息哪些没讲透、为什么
  4. tension_expand: 强项和弱项如何同时存在、张力在哪
  5. reader_value_translate: 对不同读者分别意味着什么
  
  每个解读结果包含：
  - interpretation: 核心判断（结构化数据）
  - evidence_chain: 证据 ID 列表
  - confidence: 置信度
  
  你还会收到 evidence_map: {evidence_id: citation_id} 的映射。

task: |
  把这些解读结果编织成一篇完整的文章。
  
  核心要求：
  1. 不要逐个 Skill 分段写，而是找到解读之间的逻辑关系，自然串联
  2. 用因果、递进、对比、补充等手法连接内容
  3. 在合适的位置附上 citation [C-XXX]
  4. 读起来像人写的分析文章，不像脚本生成的

writing_rules:
  structure:
    - "不要用小标题分段，写成连续的自然段落"
    - "开头从公司定位切入（business_goal），用 1-2 句话勾勒全貌"
    - "中间展开能力分析（capability + tension），用数据支撑判断"
    - "适当提及披露缺口（gaps），但不要单独成段"
    - "结尾回到读者价值（reader_value），给出可操作的结论"
  
  logic_flow:
    - "用因果关系串联：'这个定位决定了它的客户结构'"
    - "用对比突出张力：'收入增长很快，但毛利率并不算高'"
    - "用递进深化分析：'不仅如此，招股书中还透露...'"
    - "用补充完善信息：'值得注意的是...'"
  
  citation_style:
    - "citation 紧跟事实陈述：'前五大客户占比超过 60%，[C-015]'"
    - "不要堆在句尾：'❌ 客户集中度较高。[C-015][C-016][C-017]'"
    - "多个相关 citation 可以连续出现：'营收 5.2 亿元，[C-023] 同比增长 45%。[C-024]'"
  
  language_style:
    - "用具体描述代替抽象总结：'✓ 前五大客户占比 62.3%' not '❌ 客户集中度较高'"
    - "用动词代替名词：'✓ 压缩利润空间' not '❌ 利润空间的压缩'"
    - "用自然表达代替模板句：'✓ 招股书中提到' not '❌ 根据招股书披露'"
  
  paragraph_style:
    - "每段 3-6 句话，不要单句成段"
    - "段落之间用逻辑连接词过渡，不要硬切"
    - "长短句结合，平均 15-25 字"

anti_patterns:
  avoid_section_headers:
    - "❌ ## 业务目标"
    - "❌ ## 能力分析"
    - "✓ （用自然段落过渡，不加标题）"
  
  avoid_list_enumeration:
    - "❌ 公司主要有以下三个特点：1. ... 2. ... 3. ..."
    - "✓ 这家公司有三个特点。第一个是...，这决定了...。更重要的是..."
  
  avoid_template_phrases:
    - "❌ 根据招股书披露 → ✓ 招股书中提到"
    - "❌ 数据显示 → ✓ （直接写数据）"
    - "❌ 可以看出 → ✓ （直接写结论）"
    - "❌ 综上所述 → ✓ （不用总结词，自然收尾）"
  
  avoid_gap_placeholders:
    - "❌ 关键信息缺失，无法判断"
    - "✓ 招股书未详细拆分各产品线的毛利率，但从客户集中度看..."

narrative_patterns:
  opening_paragraph:
    template: |
      从 business_goal 切入，用 1-2 句话勾勒公司定位和产品入口。
      不要用"XX公司成立于XX年"这样的官腔开头。
    
    example: |
      这是一家把 AI 能力装进消费硬件的公司。[C-001] 它的产品不是简单的智能音箱，
      而是试图在车载、会议、家居等场景里提供对话式交互入口。[C-002]
  
  capability_paragraph:
    template: |
      展开 capability_match 的分析，用"这个定位决定了..."连接到客户结构。
      用对比手法展示 strengths 和 weaknesses，引出 tension。
    
    example: |
      这个定位决定了它的客户结构：前五大客户占比超过 60%，[C-015] 主要是华为、小米
      这样有生态需求的大厂。[C-016] 这种集中度既是优势（能快速放量），也是风险（议价能力弱）。
  
  financial_paragraph:
    template: |
      从收入增长切入，用"但"转折引出毛利率问题，展开 tension_expand 的分析。
      适当提及 disclosure_gap，但用"招股书未详细披露..."这样的自然表达。
    
    example: |
      收入增长很快——2023 年 5.2 亿，比上一年多了 45%，[C-023] 但毛利率 38.5% 并不算特别高。[C-024]
      这背后的逻辑是：它不是纯软件公司，硬件成本、供应链管理都会压缩利润空间。
      招股书中没有详细拆分各产品线的毛利率，但从客户集中度和定价能力看，议价空间不大。
  
  closing_paragraph:
    template: |
      回到 reader_value_translate，用"对于...来说"的句式给出不同读者的可操作结论。
      不要用"综上所述"，自然收尾。
    
    example: |
      对于关注这家公司的人来说，值得追问的是：未来能否拓展客户结构来降低集中度风险，
      或者提升产品附加值来改善利润空间。技术人可以关注它的研发方向，投资人需要跟踪
      毛利率变化，从业者可以观察它的客户拓展节奏。

output_format:
  - "连续的自然段落，不要加小标题"
  - "Citation 用 [C-XXX] 格式紧跟事实"
  - "全文 800-1500 字，根据解读内容自然展开"
  - "分 4-6 个段落，每段 3-6 句话"
```

### 3.4 Example: What Narrative Engine Produces

**Input (Skills 的解读结果):**
```json
{
  "business_goal_decompose": {
    "business_goal": "把 AI 能力装进消费硬件",
    "target_scenario": ["车载", "会议", "家居"],
    ...
  },
  "capability_match": {
    "strengths": ["研发投入高", "客户质量好"],
    "weaknesses": ["毛利率低", "客户集中"],
    "tension": "快速放量 vs 议价能力弱",
    ...
  },
  ...
}
```

**Output (Narrative Engine 生成的文章):**
```markdown
这是一家把 AI 能力装进消费硬件的公司。[C-001] 它的产品不是简单的智能音箱，而是试图在车载、会议、家居等场景里提供对话式交互入口。[C-002] 这个定位决定了它的客户结构：前五大客户占比超过 60%，[C-015] 主要是华为、小米这样有生态需求的大厂。[C-016] 这种集中度既是优势（能快速放量），也是风险（议价能力弱）。

收入增长很快——2023 年 5.2 亿，比上一年多了 45%，[C-023] 但毛利率 38.5% 并不算特别高。[C-024] 这背后的逻辑是：它不是纯软件公司，硬件成本、供应链管理都会压缩利润空间。招股书中没有详细拆分各产品线的毛利率，但从客户集中度和定价能力看，议价空间不大。

真正值得关注的是它的研发投入结构。研发费用占比 25%，[C-030] 高于行业平均水平，重点在端侧算法和芯片适配。[C-031] 这说明它在押注技术差异化，而不是简单的硬件组装。但这也意味着短期内很难看到利润率的显著改善——研发投入高 + 硬件成本约束，两头挤压之下，盈利能力受限。

招股书中没有详细披露前五大客户的具体合作模式，也没有说明平台依赖度的风险量化。[C-040] 这可能与客户合同的保密条款有关，但对于想深入了解业务稳定性的人来说，这是个信息缺口。从现有数据推断，华为、小米这样的平台型客户既能带来规模，也会要求定制化开发和价格让步。

对于关注这家公司的人来说，值得追问的是：未来能否拓展客户结构来降低集中度风险，或者提升产品附加值来改善利润空间。技术人可以关注它的研发方向——端侧 AI + 对话式交互是个有趣的技术路线。投资人需要跟踪毛利率变化，看硬件成本是否能被软件收入稀释。从业者可以观察它的客户拓展节奏，判断 B2B 生态合作模式的可行性。
```

**特点：**
- ✅ 结论之间有因果、递进、对比关系
- ✅ 段落过渡自然，用逻辑连接词串联
- ✅ Citation 自然嵌入，不突兀
- ✅ 披露缺口融入分析，不单独罗列
- ✅ 读起来像人写的，不像脚本生成的

---

## 4. Implementation Plan

### 4.1 File Structure

**New files:**
```
src/ipo_evidence/
  skill_executor.py              # Skills 执行引擎
  narrative_engine.py            # 叙事引擎
  models.py (extend)             # 添加 SkillInterpretation 模型

configs/
  skill_packages/
    ipo_prospectus_analysis.yaml # 招股书解读方法包配置
  skills/
    business_goal_decompose.yaml # 已存在，扩展 output_schema
    capability_match.yaml        # 已存在，扩展 output_schema
    disclosure_gap_scan.yaml     # 已存在，扩展 output_schema
    tension_expand.yaml          # 已存在，扩展 output_schema
    reader_value_translate.yaml  # 已存在，扩展 output_schema
  prompts/
    narrative_writer.yaml        # 叙事层 Prompt

tests/
  test_skill_executor.py         # Skills 执行测试
  test_narrative_engine.py       # 叙事引擎测试
```

**Modified files:**
```
src/ipo_evidence/
  report_generator.py            # 改造为编排器
  pipeline.py                    # 调用新的 generate_report

configs/
  report_prompt.yaml             # 可能需要调整 section_groups
```

**Deprecated:**
```
src/ipo_evidence/report_generator.py 中的：
  - KEYWORDS
  - LOW_VALUE_SNIPPETS
  - BROKEN_ENDINGS
  - 硬编码的规则逻辑
```

### 4.2 Phase 1: Skill Output Schema & Config (Week 1)

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
  - "structured_interpretation"

output_schema:
  business_goal: string          # 公司想做什么
  product_entry: list[string]    # 产品入口
  target_scenario: list[string]  # 目标场景
  customer_type: string          # 客户类型
  revenue_structure: string      # 收入结构特征
```

Repeat for other 4 skills with their respective schemas.

**Step 2: Create SkillInterpretation model**

Extend `src/ipo_evidence/models.py`:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class SkillInterpretation:
    """Skill 的解读结果（不是文字，是结构化判断）"""
    skill_key: str
    interpretation: dict[str, Any]  # 自由格式，由 Skill 定义
    evidence_chain: list[str]
    confidence: str  # high, medium, low
    gaps: list[dict[str, str]] = field(default_factory=list)
```

**Step 3: Create skill package config**

Create `configs/skill_packages/ipo_prospectus_analysis.yaml`:

```yaml
package_key: "ipo_prospectus_analysis"
title: "招股书解读方法包"
description: |
  一套完整的招股书分析框架：
  - 业务目标拆解：公司想做什么
  - 能力匹配：资源能不能支撑
  - 披露缺口识别：哪些没讲透
  - 矛盾张力展开：强弱如何共存
  - 读者价值翻译：对不同人意味着什么

skills:
  - business_goal_decompose
  - capability_match
  - disclosure_gap_scan
  - tension_expand
  - reader_value_translate

execution_order: sequential  # 按顺序执行（后面的 skill 可以用前面的结果）
```

**Step 4: Write tests**

Create `tests/test_skill_schema.py`:

```python
def test_skill_interpretation_schema():
    interp = SkillInterpretation(
        skill_key="business_goal_decompose",
        interpretation={
            "business_goal": "把 AI 能力装进消费硬件",
            "product_entry": ["智能音箱", "车载设备"],
        },
        evidence_chain=["E-001", "E-002"],
        confidence="high",
        gaps=[],
    )
    assert interp.confidence in ["high", "medium", "low"]
    assert isinstance(interp.interpretation, dict)
```

**Commit:**
```bash
git add configs/skills configs/skill_packages src/ipo_evidence/models.py tests/test_skill_schema.py
git commit -m "feat: define skill interpretation schema and package config"
```

### 4.3 Phase 2: Skill Executor (Week 1-2)

**Step 1: Create skill_executor.py**

Create `src/ipo_evidence/skill_executor.py`:

```python
from ipo_evidence.models import EvidencePacket, SkillInterpretation
from ipo_evidence.report_runtime import load_skill_configs

def execute_skill(
    skill_key: str,
    evidence_refs: list[dict],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """
    执行单个 Skill，返回结构化解读结果
    
    Args:
        skill_key: skill 标识
        evidence_refs: 本 skill 可用的证据引用
        evidence_packet: 只读证据包
        citation_index: evidence_id -> citation_id 映射
    
    Returns:
        SkillInterpretation: 结构化解读结果
    """
    # 收集可用证据
    available_evidence = [
        evidence_packet.get_item(ref["evidence_id"])
        for ref in evidence_refs
        if evidence_packet.get_item(ref["evidence_id"])
    ]
    
    # 根据 skill_key 分发到具体实现
    if skill_key == "business_goal_decompose":
        return _execute_business_goal_decompose(available_evidence, citation_index)
    elif skill_key == "capability_match":
        return _execute_capability_match(available_evidence, citation_index)
    elif skill_key == "disclosure_gap_scan":
        return _execute_disclosure_gap_scan(available_evidence, citation_index)
    elif skill_key == "tension_expand":
        return _execute_tension_expand(available_evidence, citation_index)
    elif skill_key == "reader_value_translate":
        return _execute_reader_value_translate(available_evidence, citation_index)
    
    raise ValueError(f"Unknown skill: {skill_key}")


def _execute_business_goal_decompose(
    evidence_items: list,
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """
    业务目标拆解
    
    核心逻辑：
    1. 从 business_and_product 相关证据中提取业务目标
    2. 识别产品入口和目标场景
    3. 判断客户类型（B2B/B2C）
    4. 分析收入结构
    """
    # 筛选相关证据
    relevant = [
        item for item in evidence_items
        if any(kw in item.text for kw in ["主营业务", "产品", "客户", "收入"])
    ]
    
    if len(relevant) < 2:
        return SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={},
            evidence_chain=[],
            confidence="low",
            gaps=[{
                "gap": "业务目标相关证据不足",
                "impact": "无法完整拆解业务模式"
            }]
        )
    
    # 这里应该调用 LLM 或用更复杂的规则
    # 简化实现：先用规则提取关键信息
    
    business_goal = "（从证据中提取的业务目标）"
    product_entry = []  # 从证据中提取
    target_scenario = []  # 从证据中提取
    
    return SkillInterpretation(
        skill_key="business_goal_decompose",
        interpretation={
            "business_goal": business_goal,
            "product_entry": product_entry,
            "target_scenario": target_scenario,
            "customer_type": "B2B",
            "revenue_structure": "硬件销售为主",
        },
        evidence_chain=[item.evidence_id for item in relevant[:5]],
        confidence="high",
        gaps=[],
    )

# 其他 4 个 skills 的实现...
```

**Step 2: Write tests**

Create `tests/test_skill_executor.py`:

```python
def test_execute_business_goal_decompose():
    packet = build_evidence_packet(...)
    citation_index = {"E-001": "C-001"}
    
    output = execute_skill(
        skill_key="business_goal_decompose",
        evidence_refs=[{"evidence_id": "E-001", "rank": 1}],
        evidence_packet=packet,
        citation_index=citation_index,
    )
    
    assert output.skill_key == "business_goal_decompose"
    assert isinstance(output.interpretation, dict)
    assert "business_goal" in output.interpretation
    assert output.confidence in ["high", "medium", "low"]
```

**Commit:**
```bash
git add src/ipo_evidence/skill_executor.py tests/test_skill_executor.py
git commit -m "feat: implement skill executor with 5 core skills"
```

### 4.4 Phase 3: Narrative Engine (Week 2)

**Step 1: Create narrative_engine.py**

Create `src/ipo_evidence/narrative_engine.py`:

```python
from ipo_evidence.models import SkillInterpretation, EvidencePacket
from ipo_evidence.report_runtime import load_prompt_config

def generate_narrative(
    all_skill_outputs: list[SkillInterpretation],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> tuple[str, dict]:
    """
    把 Skills 的解读结果编织成完整文章
    
    Returns:
        (report_md, narrative_trace)
    """
    # 1. 提取所有解读结果
    narrative_materials = _prepare_narrative_materials(all_skill_outputs)
    
    # 2. 构建证据映射
    evidence_map = _build_evidence_map(all_skill_outputs, citation_index)
    
    # 3. 调用 Narrative Writer
    prompt_config = load_prompt_config("narrative_writer")
    report_md = _call_narrative_writer(
        narrative_materials,
        evidence_map,
        prompt_config,
    )
    
    # 4. 生成叙事追踪
    narrative_trace = {
        "skills_used": [s.skill_key for s in all_skill_outputs],
        "total_evidence": len(evidence_map),
        "confidence_distribution": _count_confidence(all_skill_outputs),
    }
    
    return report_md, narrative_trace


def _prepare_narrative_materials(outputs: list[SkillInterpretation]) -> dict:
    """提取所有解读结果"""
    materials = {}
    for output in outputs:
        materials[output.skill_key] = output.interpretation
    return materials


def _build_evidence_map(
    outputs: list[SkillInterpretation],
    citation_index: dict[str, str],
) -> dict[str, str]:
    """构建 evidence_id -> citation_id 映射"""
    evidence_map = {}
    for output in outputs:
        for eid in output.evidence_chain:
            if eid in citation_index:
                evidence_map[eid] = citation_index[eid]
    return evidence_map


def _call_narrative_writer(
    narrative_materials: dict,
    evidence_map: dict[str, str],
    prompt_config,
) -> str:
    """
    调用 LLM 生成叙事
    
    这里应该构建 prompt，传入：
    - narrative_materials（5 个 Skills 的解读结果）
    - evidence_map（证据映射）
    - prompt_config.rules（写作规则）
    """
    # TODO: 实际调用 LLM
    # 简化实现：先返回模板
    return "（Narrative Writer 生成的文章）"


def _count_confidence(outputs: list[SkillInterpretation]) -> dict:
    """统计置信度分布"""
    counts = {"high": 0, "medium": 0, "low": 0}
    for output in outputs:
        counts[output.confidence] += 1
    return counts
```

**Step 2: Write tests**

Create `tests/test_narrative_engine.py`:

```python
def test_generate_narrative_returns_markdown():
    skill_outputs = [
        SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={"business_goal": "把 AI 能力装进消费硬件"},
            evidence_chain=["E-001"],
            confidence="high",
        )
    ]
    
    report_md, trace = generate_narrative(
        all_skill_outputs=skill_outputs,
        evidence_packet=...,
        citation_index={"E-001": "C-001"},
    )
    
    assert isinstance(report_md, str)
    assert trace["skills_used"] == ["business_goal_decompose"]
    assert trace["confidence_distribution"]["high"] == 1
```

**Commit:**
```bash
git add src/ipo_evidence/narrative_engine.py tests/test_narrative_engine.py
git commit -m "feat: implement narrative engine core"
```

### 4.5 Phase 4: Narrative Writer Prompt (Week 2-3)

**Step 1: Create narrative_writer.yaml**

已经在 Section 3.3 完整定义，直接创建文件：

Create `configs/prompts/narrative_writer.yaml` (见 Section 3.3 的完整内容)

**Step 2: Update narrative_engine.py to use the prompt**

Modify `src/ipo_evidence/narrative_engine.py`:

```python
def _call_narrative_writer(
    narrative_materials: dict,
    evidence_map: dict[str, str],
    prompt_config,
) -> str:
    """
    调用 LLM 生成叙事
    """
    # 构建 prompt
    system_prompt = _build_system_prompt(prompt_config)
    user_prompt = _build_user_prompt(narrative_materials, evidence_map)
    
    # 调用 LLM（这里需要集成实际的 LLM 调用）
    # response = call_llm(system_prompt, user_prompt)
    
    # 临时实现：返回占位符
    return "（等待 LLM 集成）"


def _build_system_prompt(prompt_config) -> str:
    """构建 system prompt"""
    return f"""
{prompt_config.purpose}

{prompt_config.rules}

请严格遵守以下写作规则和反模式指南。
"""


def _build_user_prompt(narrative_materials: dict, evidence_map: dict) -> str:
    """构建 user prompt"""
    return f"""
请根据以下解读结果，编织成一篇自然的文章。

# 解读结果

## 业务目标拆解
{json.dumps(narrative_materials.get("business_goal_decompose", {}), ensure_ascii=False, indent=2)}

## 能力匹配
{json.dumps(narrative_materials.get("capability_match", {}), ensure_ascii=False, indent=2)}

## 披露缺口识别
{json.dumps(narrative_materials.get("disclosure_gap_scan", {}), ensure_ascii=False, indent=2)}

## 矛盾张力展开
{json.dumps(narrative_materials.get("tension_expand", {}), ensure_ascii=False, indent=2)}

## 读者价值翻译
{json.dumps(narrative_materials.get("reader_value_translate", {}), ensure_ascii=False, indent=2)}

# 证据映射
{json.dumps(evidence_map, ensure_ascii=False, indent=2)}

请生成完整文章，不要包含任何解释或元信息。
"""
```

**Step 3: Test with real document**

```bash
python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3
```

**Validation:**
- Generated report has natural flow
- No template phrases like "根据招股书披露"
- Citation naturally embedded
- Reads like human-written article

**Commit:**
```bash
git add configs/prompts/narrative_writer.yaml src/ipo_evidence/narrative_engine.py
git commit -m "feat: add narrative writer prompt and integrate LLM"
```

### 4.6 Phase 5: Integration (Week 3)

**Step 1: Refactor report_generator.py**

Modify `src/ipo_evidence/report_generator.py`:

```python
from ipo_evidence.skill_executor import execute_skill
from ipo_evidence.narrative_engine import generate_narrative
from ipo_evidence.report_inputs import build_report_inputs
from ipo_evidence.config import load_yaml

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
    
    # 2. 加载 skill package
    skill_package = load_yaml("configs/skill_packages/ipo_prospectus_analysis.yaml")
    
    # 3. 构建 citation index
    citation_index = {
        item.evidence_id: _citation_id(idx + 1)
        for idx, item in enumerate(evidence_packet.items)
    }
    
    # 4. 执行所有 Skills（解读层）
    all_skill_outputs = []
    for skill_key in skill_package["skills"]:
        # 找到对应的 section_group
        section_group = _find_section_group_for_skill(
            skill_key, 
            report_inputs["section_groups"]
        )
        
        skill_output = execute_skill(
            skill_key=skill_key,
            evidence_refs=section_group["evidence_refs"],
            evidence_packet=evidence_packet,
            citation_index=citation_index,
        )
        all_skill_outputs.append(skill_output)
    
    # 5. 生成叙事（叙事层）
    report_md, narrative_trace = generate_narrative(
        all_skill_outputs=all_skill_outputs,
        evidence_packet=evidence_packet,
        citation_index=citation_index,
    )
    
    # 6. 构建 citation.json
    citation_dict = _build_citation_dict(evidence_packet, citation_index)
    
    return report_md, citation_dict, narrative_trace


def _find_section_group_for_skill(skill_key: str, section_groups: list) -> dict:
    """找到包含该 skill 的 section_group"""
    for group in section_groups:
        if skill_key in group.get("skill_refs", []):
            return group
    # 如果没找到，返回默认 group（包含所有证据）
    return {"evidence_refs": []}
```

**Step 2: Update pipeline.py**

Modify `src/ipo_evidence/pipeline.py`:

```python
def generate_report_for_doc(doc_id: str) -> dict:
    """生成报告的主入口"""
    # 加载 evidence packet
    evidence_packet = load_evidence_packet(doc_id)
    company_name = _extract_company_name(evidence_packet)
    
    # 调用新的 generate_report
    report_md, citation_dict, narrative_trace = generate_report(
        doc_id=doc_id,
        company_name=company_name,
        evidence_packet=evidence_packet,
    )
    
    # 写入文件
    doc_dir = paths.docs_dir() / doc_id
    (doc_dir / "report.md").write_text(report_md, encoding="utf-8")
    (doc_dir / "citation.json").write_text(
        json.dumps(citation_dict, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (doc_dir / "narrative_trace.json").write_text(
        json.dumps(narrative_trace, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    return {"reported": doc_id}
```

**Step 3: Run full test suite**

```bash
pytest -q
```

**Step 4: End-to-end test with real document**

```bash
python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3
```

**Validation:**
- All tests pass
- Generated report reads like an article
- No hard-coded keywords used
- Citation coverage ≥ 90%

**Commit:**
```bash
git add src/ipo_evidence/report_generator.py src/ipo_evidence/pipeline.py
git commit -m "feat: integrate narrative-driven generation into pipeline"
```

### 4.7 Phase 6: Remove Legacy Code (Week 3-4)

**Step 1: Mark legacy code as deprecated**

Add deprecation comments to old logic:

```python
# DEPRECATED: This will be removed in next PR
KEYWORDS = {
    # ...
}
```

**Step 2: Add feature flag**

```python
def generate_report(
    doc_id: str,
    company_name: str,
    evidence_packet: EvidencePacket,
    use_narrative_engine: bool = True,  # Default to new architecture
) -> tuple[str, dict, dict]:
    if use_narrative_engine:
        return _generate_report_narrative(...)
    else:
        return _generate_report_legacy(...)
```

**Step 3: Test both paths**

Run tests with both feature flags to ensure no regression.

**Step 4: Remove legacy code after validation**

Once new architecture is validated, remove:
- `KEYWORDS`
- `LOW_VALUE_SNIPPETS`
- `BROKEN_ENDINGS`
- Old template-based generation logic

**Commit:**
```bash
git add src/ipo_evidence/report_generator.py
git commit -m "refactor: remove legacy rule-based generation code"
```

---

## 5. Quality Metrics

### 5.1 Objective Metrics

**Citation Coverage:**
```python
def check_citation_coverage(report_md: str, citation_dict: dict) -> float:
    """检查 citation 覆盖率"""
    citations_in_report = set(re.findall(r'\[C-\d{3}\]', report_md))
    total_facts = len([item for item in evidence_packet.items if item.source_type in ["text_quote", "table_fact"]])
    return len(citations_in_report) / total_facts if total_facts > 0 else 0
```

**Target:** ≥ 90%

**Confidence Distribution:**
```python
def check_confidence_distribution(narrative_trace: dict) -> dict:
    """检查 Skills 的置信度分布"""
    return narrative_trace["confidence_distribution"]
```

**Target:** high ≥ 70%

### 5.2 Subjective Metrics (Human Review)

**Natural Flow Checklist:**
- [ ] 没有小标题分段
- [ ] 段落之间有逻辑过渡
- [ ] 不是列举式表达
- [ ] 没有模板短语（"根据招股书披露"、"数据显示"）
- [ ] Citation 自然嵌入，不突兀
- [ ] 读起来像人写的，不像脚本生成的

**Deep Analysis Checklist:**
- [ ] 业务目标拆解到位（产品、客户、场景）
- [ ] 能力匹配有洞察（强项、弱项、张力）
- [ ] 披露缺口识别准确
- [ ] 矛盾张力展开有深度
- [ ] 读者价值翻译实用

---

## 6. Migration Strategy

### 6.1 Backward Compatibility

支持新旧两条路径，用 feature flag 切换：

```python
# configs/feature_flags.yaml
narrative_engine:
  enabled: true
  fallback_to_legacy: true  # 新引擎失败时回退到旧逻辑
```

### 6.2 Rollout Plan

**Week 1-2:** 新架构并行开发，不影响现有流程
**Week 3:** 新架构可用，默认关闭，手动测试
**Week 4:** 新架构默认开启，保留旧架构作为 fallback
**Week 5+:** 移除旧架构

---

## 7. Out of Scope

**Not in this PR:**
- External facts (`external_fact`) — 需要单独的外部数据接入层
- Multi-document comparison (`cross_doc_fact`) — 需要跨文档 diff 能力
- Visual fact extraction (`visual_fact`) — 需要图表 OCR 和理解
- Quality notes as separate artifact (`quality_notes.md`) — 可以后续添加
- Advanced narrative patterns (storytelling, rhetorical devices) — 可以后续优化 prompt

---

## 8. Risk Assessment

### High Risk: Skills 解读偏离用户意图

**Risk:** Skills 的判断不符合用户的分析视角
**Mitigation:**
- Skills 输出结构化数据，不是最终文字，容易调整
- 可以通过修改 skill 逻辑或 prompt 来调整解读方向
- narrative_trace.json 记录所有解读结果，便于审查

### Medium Risk: Narrative Engine 生成脚本感文字

**Risk:** 即使有详细 prompt，LLM 仍可能生成模板化表达
**Mitigation:**
- Anti-patterns 中明确列举禁止表达
- 人工审查生成结果，持续优化 prompt
- 可以添加后处理规则过滤模板短语

### Low Risk: 性能下降

**Risk:** Skills 执行 + LLM 叙事可能比旧逻辑慢
**Mitigation:**
- Skills 可以并行执行（未来优化）
- Narrative Engine 只调用一次 LLM
- 比当前多个 section 分别生成可能更快

---

## 9. Success Criteria

This PR is successful when:

1. ✅ All 5 core skills implemented and tested
2. ✅ Narrative Engine generates natural-flow articles
3. ✅ No template phrases in generated content
4. ✅ Citation coverage ≥ 90%
5. ✅ Human review: "Reads like an analyst wrote it"
6. ✅ All existing tests pass
7. ✅ Can regenerate doc_beaac21be4b3 with new architecture
8. ✅ Skills are truly pluggable (can add new skill package without changing core code)

---

## 10. Next Steps After This PR

**未来可以扩展：**
- 新增 Skill Package：财务质量审查包、行业竞争力评估包
- 优化 Narrative Engine：支持多种 narrative_style（analytical / storytelling / academic）
- 添加 External Facts：从网页、电商、社交媒体补充证据
- Multi-document comparison：对比不同版本招股书
- Reader-specific reports：针对不同读者生成定制化报告

**架构优势：**
- Skills 可插拔 → 新增分析方法不改核心代码
- Narrative Engine 稳定 → 换 Skills 不影响文章质量
- 证据层解耦 → 新增证据类型不影响 Skills 和 Narrative Engine

