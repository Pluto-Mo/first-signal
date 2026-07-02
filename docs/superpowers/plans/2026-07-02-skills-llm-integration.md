# Skills LLM Integration - Phase 2

> **Status:** Ready for execution (Phase 1 completed successfully)
>
> **Goal:** 把 Skills 从"关键词匹配 + 原文拼接"升级到"LLM 深度分析"，让解读结果从招股书原文变成提炼后的核心判断。

**Current Problem:**
- Skills 输出的 `interpretation` 是招股书原文的拼接
- `business_goal` 输出 200+ 字的原文段落，不是简洁概括
- `capability_match` 输出 144 条 strengths / 108 条 weaknesses（关键词匹配，未筛选）
- 没有真正的"分析"，只是"搬运原文"

**Target:**
- Skills 输出简洁、提炼的核心判断
- `business_goal`: 50 字内概括
- `capability_match`: 3-5 条核心强项/弱项
- `tension_expand`: 展开张力的权衡逻辑
- 每个判断都有 LLM 的深度分析

**Tech Stack:** 
- Python 3.11+
- 复用 Phase 1 的 `llm_caller.py`
- 修改 `skill_executor.py`

---

## 1. Current Problem Analysis

### Phase 1 验证结果

✅ Narrative Engine 已经接入 LLM
✅ 生成 1,431 字自然文章（vs 之前 8 行）
✅ 无模板短语，有逻辑过渡

❌ 但内容深度不够，因为 Skills 输出质量差

### 具体问题

**问题 1: `business_goal_decompose` 输出原文**

当前输出：
```json
{
  "business_goal": "新研发了全栈对话式 AI 和端侧智能技术，积累了端云协同、软硬结合的全系统优化能力以及多芯片、多场景适配经验。在此基础上，公司实现了端侧大小模型多领域的轻量化部署与大规模应用，支持离线低延迟、高隐私保护的本地化智能交互，构建了面向各类终端场景的标准化产品服务体系。"
}
```

→ 这是招股书原文，不是"业务目标"的简洁概括

期望输出：
```json
{
  "business_goal": "把 AI 能力装进消费硬件，在车载/会议/家居等场景提供对话式交互入口",
  "product_entry": ["智能音箱", "车载设备", "会议设备"],
  "target_scenario": ["车载", "会议", "家居"],
  "customer_type": "B2B（大厂生态合作）",
  "revenue_structure": "硬件销售为主，软件收入占比低"
}
```

**问题 2: `capability_match` 证据过多**

当前抓了 144 条 strengths，108 条 weaknesses，都是关键词匹配的原文片段。

期望输出：
```json
{
  "strengths": [
    "研发投入占比 25%，高于行业平均",
    "前五大客户均为行业龙头（华为、小米、阿里）",
    "产品覆盖多场景，应用广度大"
  ],
  "weaknesses": [
    "毛利率 38.5%，低于纯软件公司",
    "客户集中度 62.3%，议价能力受限",
    "报告期内持续亏损（-1.29 亿、-1.75 亿、-0.84 亿）"
  ],
  "tension": "快速放量能力（大客户背书）vs 利润压缩风险（议价能力弱 + 硬件成本高）"
}
```

**问题 3: `tension_expand` 缺乏深度**

当前只是简单罗列正反面，没有展开权衡逻辑。

期望输出：
```json
{
  "tension_point": "客户集中度 62.3%",
  "positive_side": "能快速放量，客户质量高（华为、小米、阿里），有大厂背书",
  "negative_side": "议价能力弱，一旦失去核心客户会严重影响收入",
  "tradeoff_logic": "创业期选择大客户战略可以快速验证产品，但长期需要拓展客户结构来降低风险",
  "future_path": [
    "继续深耕大客户生态，成为平台级供应商",
    "横向拓展中小客户，分散集中度风险"
  ]
}
```

---

## 2. Solution Design

### 核心思路

在 `skill_executor.py` 中，每个 skill 改成：

1. **证据筛选**（保留现有的关键词匹配，但加强过滤）
2. **调用 LLM** 做深度分析（用 Phase 1 的 `llm_caller.py`）
3. **解析 JSON** 结果
4. **返回 SkillInterpretation**

### 架构不变

```text
report_inputs.json (调度层)
  ↓
skill_executor.py (解读层 - 改这里)
  ├─ 证据筛选（关键词 + 去重）
  ├─ 调用 LLM 分析（新增）
  └─ 返回结构化结论
  ↓
narrative_engine.py (叙事层 - 已完成)
  ↓
report.md
```

---

## 3. Implementation Plan

### Step 1: Add Evidence Filtering Helpers

在 `skill_executor.py` 开头添加证据去重和限制逻辑：

```python
def _deduplicate_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """去重证据（基于 claim_summary 相似度）"""
    seen_claims: set[str] = set()
    deduped: list[EvidenceItem] = []
    
    for item in items:
        # 简化版：取前 50 字作为指纹
        fingerprint = item.claim_summary[:50].strip()
        if fingerprint not in seen_claims:
            seen_claims.add(fingerprint)
            deduped.append(item)
    
    return deduped


def _limit_evidence(items: list[EvidenceItem], max_count: int = 10) -> list[EvidenceItem]:
    """限制证据数量，优先保留高质量证据"""
    # 按质量分数排序
    sorted_items = sorted(items, key=lambda x: x.quality_score, reverse=True)
    return sorted_items[:max_count]
```

### Step 2: Refactor `_execute_business_goal_decompose`

替换 `skill_executor.py` 中的 `_execute_business_goal_decompose`：

```python
def _execute_business_goal_decompose(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """
    业务目标拆解（LLM 版）
    
    从招股书原文中提炼：
    - 核心业务目标（50 字内）
    - 产品入口（3-5 个）
    - 目标场景（3-5 个）
    - 客户类型
    - 收入结构特征
    """
    from ipo_evidence.llm_caller import call_claude_for_skill
    
    # 1. 证据筛选和去重
    relevant = [
        item for item in evidence_items
        if any(kw in item.text for kw in ["主营业务", "主要产品", "产品", "收入", "销售", "场景"])
    ]
    relevant = _deduplicate_evidence(relevant)
    relevant = _limit_evidence(relevant, max_count=10)
    
    if len(relevant) < 2:
        return SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={},
            evidence_chain=[],
            confidence="low",
            gaps=[{"gap": "业务目标相关证据不足", "impact": "无法完整拆解业务模式"}]
        )
    
    # 2. 构建证据文本
    evidence_text = "\n\n".join([
        f"[{citation_index.get(item.evidence_id, '?')}] {item.claim_summary[:200]}"
        for item in relevant
    ])
    
    # 3. 构建 prompt
    instruction = """你是招股书分析专家。根据以下证据，回答：

1. 公司的核心业务目标是什么？（用一句话概括，不超过 50 字，不要照搬原文）
2. 产品入口有哪些？（列出 3-5 个关键产品）
3. 目标场景是什么？（列出 3-5 个应用场景）
4. 客户类型是 B2B 还是 B2C？（简短回答）
5. 收入结构特征是什么？（用一句话概括）

要求：
- 提炼核心信息，不要照搬原文
- 用简洁语言概括
- 只输出 JSON，格式：
{
  "business_goal": "简洁概括（50字内）",
  "product_entry": ["产品1", "产品2", ...],
  "target_scenario": ["场景1", "场景2", ...],
  "customer_type": "B2B/B2C/混合",
  "revenue_structure": "简洁描述"
}

不要输出任何解释，只输出 JSON。"""
    
    # 4. 调用 LLM
    try:
        response = call_claude_for_skill(
            skill_name="business_goal_decompose",
            evidence_text=evidence_text,
            instruction=instruction,
            max_tokens=1000,
        )
        
        # 5. 解析 JSON
        interpretation = json.loads(response)
        
        return SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation=interpretation,
            evidence_chain=[item.evidence_id for item in relevant],
            confidence="high",
            gaps=[],
        )
    except (json.JSONDecodeError, RuntimeError) as e:
        # LLM 调用失败，回退到规则版本
        return _execute_business_goal_decompose_fallback(relevant, citation_index)


def _execute_business_goal_decompose_fallback(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """回退版本（保留原有规则逻辑）"""
    # 保留原有的规则实现
    interpretation = {
        "business_goal": _clean_claim(evidence_items[0].claim_summary)[:100],
        "product_entry": _extract_terms(evidence_items, ("AI 芯片", "智能硬件", "产品")),
        "target_scenario": _extract_terms(evidence_items, ("智慧出行", "会议", "家居", "车载", "办公")),
        "customer_type": "B2B" if _has_any(evidence_items, ("客户", "销售")) else "未充分披露",
        "revenue_structure": "收入结构仍需继续核查",
    }
    
    return SkillInterpretation(
        skill_key="business_goal_decompose",
        interpretation=interpretation,
        evidence_chain=[item.evidence_id for item in evidence_items[:5]],
        confidence="medium",
        gaps=[],
    )
```

### Step 3: Refactor `_execute_capability_match`

替换 `skill_executor.py` 中的 `_execute_capability_match`：

```python
def _execute_capability_match(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """
    能力匹配（LLM 版）
    
    从招股书中分析：
    - 能力强项（3-5 条核心判断）
    - 能力弱项（3-5 条核心判断）
    - 核心张力
    - 资源配置特征
    """
    from ipo_evidence.llm_caller import call_claude_for_skill
    
    # 1. 证据筛选和去重
    relevant = [
        item for item in evidence_items
        if any(kw in item.text for kw in ["产品", "研发", "客户", "技术", "销售", "风险", "现金流", "毛利率"])
    ]
    relevant = _deduplicate_evidence(relevant)
    relevant = _limit_evidence(relevant, max_count=15)
    
    if len(relevant) < 3:
        return SkillInterpretation(
            skill_key="capability_match",
            interpretation={},
            evidence_chain=[],
            confidence="low",
            gaps=[{"gap": "能力匹配相关证据不足", "impact": "无法判断产品、研发、客户和交付能力"}]
        )
    
    # 2. 构建证据文本
    evidence_text = "\n\n".join([
        f"[{citation_index.get(item.evidence_id, '?')}] {item.claim_summary[:150]}"
        for item in relevant
    ])
    
    # 3. 构建 prompt
    instruction = """你是招股书分析专家。根据以下证据，分析公司的能力匹配情况：

1. 能力强项有哪些？（列出 3-5 条核心判断，每条不超过 30 字）
2. 能力弱项有哪些？（列出 3-5 条核心判断，每条不超过 30 字）
3. 核心张力是什么？（用一句话概括强项和弱项的矛盾点）
4. 资源配置特征是什么？（用一句话概括研发、销售、生产的配置）

要求：
- 提炼核心判断，不要照搬原文
- 强项和弱项各不超过 5 条
- 用数据支撑判断（如"研发投入占比 25%"）
- 只输出 JSON，格式：
{
  "strengths": ["强项1", "强项2", "强项3"],
  "weaknesses": ["弱项1", "弱项2", "弱项3"],
  "tension": "核心张力概括",
  "resource_allocation": "资源配置特征"
}

不要输出任何解释，只输出 JSON。"""
    
    # 4. 调用 LLM
    try:
        response = call_claude_for_skill(
            skill_name="capability_match",
            evidence_text=evidence_text,
            instruction=instruction,
            max_tokens=1500,
        )
        
        # 5. 解析 JSON
        interpretation = json.loads(response)
        
        return SkillInterpretation(
            skill_key="capability_match",
            interpretation=interpretation,
            evidence_chain=[item.evidence_id for item in relevant],
            confidence="high",
            gaps=[],
        )
    except (json.JSONDecodeError, RuntimeError) as e:
        # LLM 调用失败，回退到规则版本
        return _execute_capability_match_fallback(relevant, citation_index)
```

### Step 4: Refactor `_execute_tension_expand`

替换 `skill_executor.py` 中的 `_execute_tension_expand`：

```python
def _execute_tension_expand(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    """
    矛盾张力展开（LLM 版）
    
    识别并展开强项和弱项如何同时存在，分析权衡逻辑。
    """
    from ipo_evidence.llm_caller import call_claude_for_skill
    
    # 1. 证据筛选
    relevant = [
        item for item in evidence_items
        if any(kw in item.text for kw in ["增长", "收入", "研发", "现金流", "亏损", "风险", "费用"])
    ]
    relevant = _deduplicate_evidence(relevant)
    relevant = _limit_evidence(relevant, max_count=10)
    
    if len(relevant) < 2:
        return SkillInterpretation(
            skill_key="tension_expand",
            interpretation={},
            evidence_chain=[],
            confidence="low",
            gaps=[{"gap": "矛盾张力相关证据不足", "impact": "无法解释增长、投入与风险的张力"}]
        )
    
    # 2. 构建证据文本
    evidence_text = "\n\n".join([
        f"[{citation_index.get(item.evidence_id, '?')}] {item.claim_summary[:150]}"
        for item in relevant
    ])
    
    # 3. 构建 prompt
    instruction = """你是招股书分析专家。根据以下证据，分析公司的矛盾张力：

1. 核心张力点是什么？（用一句话点出主要矛盾）
2. 正面因素是什么？（优势、机会）
3. 负面因素是什么？（风险、约束）
4. 权衡逻辑是什么？（为什么这两者会同时存在？）
5. 可能的演化路径有哪些？（列出 2-3 条）

要求：
- 找到真正的张力点（不是简单罗列优缺点）
- 解释为什么这个张力存在
- 只输出 JSON，格式：
{
  "tension_point": "核心张力点",
  "positive_side": "正面因素",
  "negative_side": "负面因素",
  "tradeoff_logic": "权衡逻辑",
  "future_path": ["路径1", "路径2"]
}

不要输出任何解释，只输出 JSON。"""
    
    # 4. 调用 LLM
    try:
        response = call_claude_for_skill(
            skill_name="tension_expand",
            evidence_text=evidence_text,
            instruction=instruction,
            max_tokens=1200,
        )
        
        interpretation = json.loads(response)
        
        return SkillInterpretation(
            skill_key="tension_expand",
            interpretation=interpretation,
            evidence_chain=[item.evidence_id for item in relevant],
            confidence="high",
            gaps=[],
        )
    except (json.JSONDecodeError, RuntimeError) as e:
        return _execute_tension_expand_fallback(relevant, citation_index)
```

### Step 5: Update `llm_caller.py`

检查 `llm_caller.py` 中的 `call_claude_for_skill` 是否已实现，如果没有则添加：

```python
def call_claude_for_skill(
    skill_name: str,
    evidence_text: str,
    instruction: str,
    max_tokens: int = 2000,
) -> str:
    """
    调用 LLM 执行 Skill 分析
    
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
不要输出任何解释、注释或元信息，只输出 JSON。
确保 JSON 格式正确，可以被 json.loads() 解析。"""
    
    user_prompt = f"""{instruction}

证据：
{evidence_text}
"""
    
    return call_agent_for_narrative(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )
```

### Step 6: Test with Real Document

```bash
# 重新生成报告
python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3

# 检查输出
cat data/docs/doc_beaac21be4b3/report.md

# 检查 narrative_trace
cat data/docs/doc_beaac21be4b3/narrative_trace.json
```

**Expected Changes:**

1. **report.md 质量提升**
   - 更有洞察力的判断
   - 更精准的数据引用
   - 更深入的分析

2. **business_goal 变简洁**
   - Before: 200+ 字原文
   - After: 50 字简洁概括

3. **capability_match 更聚焦**
   - Before: 144 条 strengths
   - After: 3-5 条核心强项

### Step 7: Commit

```bash
git add src/ipo_evidence/skill_executor.py src/ipo_evidence/llm_caller.py
git commit -m "feat: integrate LLM into skills for deep analysis

- Add evidence deduplication and limiting helpers
- Refactor business_goal_decompose to use LLM for concise extraction
- Refactor capability_match to use LLM for focused analysis
- Refactor tension_expand to use LLM for tradeoff logic
- Add fallback mechanisms for LLM failures
- Expected: skills output concise judgments instead of raw text

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## 4. Implementation Priority

### Priority 1 (必须改): 

1. ✅ `business_goal_decompose` — 影响最大，开头段落的质量
2. ✅ `capability_match` — 当前问题最严重（144 条 strengths）

### Priority 2 (推荐改):

3. ✅ `tension_expand` — 提升张力分析的深度

### Priority 3 (可选):

4. `disclosure_gap_scan` — 当前规则版本尚可
5. `reader_value_translate` — 当前规则版本尚可

**建议：先改 Priority 1，测试效果后再决定是否继续**

---

## 5. Validation Checklist

After implementation, verify:

- [ ] `python -m ipo_evidence.cli generate-report --doc-id doc_beaac21be4b3` succeeds
- [ ] `business_goal` 字数 < 100（vs 之前 200+）
- [ ] `capability_match` strengths ≤ 5 条（vs 之前 144 条）
- [ ] Report 质量提升（更有洞察力）
- [ ] LLM 调用成功率 > 80%（检查 narrative_trace.json）
- [ ] Fallback 机制工作正常（手动测试 LLM 失败场景）

---

## 6. Troubleshooting

### Issue: LLM 返回的不是有效 JSON

**Cause:** LLM 输出了解释文字或格式错误

**Solution:**
- 在 system prompt 中强调"只输出 JSON，不要任何解释"
- 添加 JSON 解析错误处理，回退到规则版本

### Issue: LLM 调用超时

**Cause:** 证据文本太长

**Solution:**
- 减少 `max_count`（从 15 降到 10）
- 截断每条证据的长度（`:150` 改为 `:100`）

### Issue: Skills 质量下降

**Cause:** Prompt 不够精确

**Solution:**
- 添加更多示例
- 明确输出格式要求
- 调整 evidence_text 的构建方式

---

## 7. Expected Improvements

### Before (规则版 Skills)

```json
{
  "business_goal": "新研发了全栈对话式 AI 和端侧智能技术，积累了端云协同、软硬结合的全系统优化能力以及多芯片、多场景适配经验...",
  "strengths": [
    "公司本次募集资金投资项目紧密围绕主营业务与核心技术开展...",
    "公司是国内领先的对话式人工智能企业...",
    // ... 142 more items
  ]
}
```

### After (LLM 版 Skills)

```json
{
  "business_goal": "把 AI 能力装进消费硬件，在车载/会议/家居等场景提供对话式交互入口",
  "product_entry": ["智能音箱", "车载设备", "会议设备"],
  "target_scenario": ["车载", "会议", "家居"],
  "customer_type": "B2B（大厂生态合作）",
  "revenue_structure": "硬件销售为主，软件收入占比低"
}
```

```json
{
  "strengths": [
    "研发投入占比 25%，高于行业平均",
    "前五大客户均为行业龙头（华为、小米、阿里）",
    "产品覆盖多场景，在智慧出行装机量位列第二"
  ],
  "weaknesses": [
    "毛利率 38.5%，低于纯软件公司",
    "客户集中度 62.3%，议价能力受限",
    "报告期内持续亏损，2025 年亏损 0.84 亿元"
  ],
  "tension": "快速放量能力（大客户背书）vs 利润压缩风险（议价能力弱 + 硬件成本高）"
}
```

### Report Quality Improvement

**开头段落（Before）:**
```markdown
新研发了全栈对话式 AI 和端侧智能技术，积累了端云协同、软硬结合的全系统优化能力...核心场景包括智慧出行、会议、家居、车载、办公。
```

**开头段落（After）:**
```markdown
这是一家把 AI 能力装进消费硬件的公司。它试图在车载、会议、家居等场景提供对话式交互入口，客户主要是华为、小米这样的大厂。这个定位决定了它的业务特征：重研发（25% 投入占比）、强交付（前五大客户占比 62%）、低毛利（38.5%，受硬件成本约束）。
```

→ 更简洁、更有分析视角、数据更精准

---

## 8. Success Criteria

This PR is successful when:

1. ✅ Skills 调用 LLM 成功（检查 narrative_trace.json 有 `llm_used: true`）
2. ✅ `business_goal` 简洁（< 100 字）
3. ✅ `capability_match` 聚焦（strengths/weaknesses 各 ≤ 5 条）
4. ✅ Report 质量提升（有洞察力，数据精准）
5. ✅ Fallback 机制正常（LLM 失败时不崩溃）
6. ✅ 所有测试通过

---

## 9. Next Steps (Out of Scope)

After this PR, consider:

1. **优化 Prompt** — 根据生成质量调整 instruction
2. **添加更多 Skills** — 如财务质量分析、行业对标
3. **多轮分析** — Skills 可以相互引用结果
4. **缓存机制** — 避免重复调用 LLM
