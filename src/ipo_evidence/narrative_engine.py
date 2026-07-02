from __future__ import annotations

import json
import re
from typing import Any

from ipo_evidence.llm_caller import call_agent_for_narrative
from ipo_evidence.models import EvidencePacket, SkillInterpretation
from ipo_evidence.report_runtime import load_prompt_config


def generate_narrative(
    all_skill_outputs: list[SkillInterpretation],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
    narrative_style: str = "analytical",
) -> tuple[str, dict[str, Any]]:
    del evidence_packet, narrative_style

    narrative_materials = _prepare_narrative_materials(all_skill_outputs)
    evidence_map = _build_evidence_map(all_skill_outputs, citation_index)
    skill_citations = _build_skill_citations(all_skill_outputs, citation_index)
    prompt_config = load_prompt_config("narrative_writer")
    report_md, llm_used, fallback_used = _call_narrative_writer(
        narrative_materials,
        evidence_map,
        skill_citations,
        prompt_config,
    )
    trace = {
        "skills_used": [output.skill_key for output in all_skill_outputs],
        "total_evidence": len(evidence_map),
        "confidence_distribution": _count_confidence(all_skill_outputs),
        "llm_used": llm_used,
        "fallback_used": fallback_used,
    }
    return report_md, trace


def _prepare_narrative_materials(outputs: list[SkillInterpretation]) -> dict[str, dict[str, Any]]:
    materials: dict[str, dict[str, Any]] = {}
    for output in outputs:
        if output.confidence in {"high", "medium"} and output.interpretation:
            materials[output.skill_key] = output.interpretation
    return materials


def _build_evidence_map(
    outputs: list[SkillInterpretation],
    citation_index: dict[str, str],
) -> dict[str, str]:
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
) -> tuple[str, bool, bool]:
    del evidence_map
    if not narrative_materials:
        return "当前证据不足以生成高置信度叙事。", False, False

    system_prompt = _build_system_prompt(prompt_config)
    user_prompt = _build_user_prompt(narrative_materials, skill_citations)
    try:
        report_md = call_agent_for_narrative(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=7000,
            timeout=240,
        )
        cleaned = _clean_llm_output(report_md)
        retry_prompt = _build_retry_prompt_if_needed(cleaned, user_prompt, narrative_materials)
        if retry_prompt:
            cleaned = _clean_llm_output(
                call_agent_for_narrative(
                    user_prompt=retry_prompt,
                    system_prompt=system_prompt,
                    max_tokens=7000,
                    timeout=240,
                )
            )
        return cleaned, True, False
    except (RuntimeError, TimeoutError):
        return _fallback_narrative(narrative_materials, skill_citations), False, True


def _fallback_narrative(
    narrative_materials: dict[str, dict[str, Any]],
    skill_citations: dict[str, list[str]],
) -> str:

    opening_citation = _first_citation(skill_citations, "business_goal_decompose")
    support_citation = _first_citation(skill_citations, "capability_match")
    tension_citation = _first_citation(skill_citations, "tension_expand")
    reader_citation = _first_citation(skill_citations, "reader_value_translate")
    business = narrative_materials.get("business_goal_decompose", {})
    capability = narrative_materials.get("capability_match", {})
    tension = narrative_materials.get("tension_expand", {})
    reader = narrative_materials.get("reader_value_translate", {})
    gap = narrative_materials.get("disclosure_gap_scan", {})

    opening = _business_sentence(business)
    if opening and opening_citation:
        opening = f"{opening}{opening_citation}"

    first_paragraph = [opening] if opening else []
    second_paragraph: list[str] = []
    third_paragraph: list[str] = []
    if capability:
        strengths = _join_points(capability.get("strengths", [])[:2])
        weakness = _join_points(capability.get("weaknesses", [])[:2])
        if strengths and weakness:
            second_paragraph.append(f"能力上，它的正面线索是{strengths}，但约束也很直接：{weakness}。{support_citation}")
        if capability.get("tension"):
            second_paragraph.append(f"真正需要读进去的是{capability['tension']}。")
    if tension:
        tradeoff = str(tension.get("tradeoff_logic", "")).rstrip("。")
        if tradeoff:
            second_paragraph.append(f"{tradeoff}。{tension_citation}")
    if gap.get("critical_gaps"):
        third_paragraph.append(f"披露缺口也不能跳过：{str(gap['critical_gaps'][0]).rstrip('。；;，,')}。")
    if reader.get("for_investors"):
        third_paragraph.append(str(reader["for_investors"]).rstrip("。") + f"。{reader_citation}")

    paragraphs = [
        "".join(sentence for sentence in paragraph if sentence)
        for paragraph in (first_paragraph, second_paragraph, third_paragraph)
    ]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _build_system_prompt(prompt_config) -> str:
    rules_text = "\n".join(f"- {rule}" for rule in prompt_config.rules)
    return f"""你是招股书分析专家，负责把结构化解读结果编织成有章节、有深度、可核查的中文研究报告。

核心任务：
{prompt_config.purpose}

写作规则：
{rules_text}

硬性约束：
- 外层生成器会提供一级标题，你只输出正文，不要输出一级标题。
- 正文必须是 4 个二级标题（##）和 3 个三级标题（###）。
- 避免模板短语：“根据招股书披露”“数据显示”“可以看出”“能力上，它的正面线索是”“真正需要读进去的是”。
- Citation 必须使用 [C-XXX] 格式，并紧跟事实陈述。
- 总字数不设硬性上限或下限，以论证充分、结构完整为准。
- 直接输出 Markdown 正文，不要输出解释、代码块或元信息。"""


def _build_user_prompt(
    narrative_materials: dict[str, dict[str, Any]],
    skill_citations: dict[str, list[str]],
) -> str:
    sections: list[str] = []
    business = narrative_materials.get("business_goal_decompose")
    if business:
        sections.append(f"""
【业务定位素材】
核心业务目标: {_clip(business.get('business_goal'), 180)}
产品入口: {_join_list(business.get('product_entry'), limit=6, item_limit=80)}
目标场景: {_join_list(business.get('target_scenario'), limit=6, item_limit=80)}
客户类型: {_clip(business.get('customer_type'), 120)}
收入结构: {_clip(business.get('revenue_structure'), 180)}
可用 citation: {', '.join(skill_citations.get('business_goal_decompose', [])[:8])}

写作要求：
- 写一个自然表达的二级标题（##），不要出现“第一章”“一、业务定位”。
- 2-3 段，400-500 字。
- 说明公司做什么、产品进入哪些场景、客户是谁。
- 解释为什么这条路径需要系统能力，融入背景知识但不要写科普。
""")

    capability = narrative_materials.get("capability_match")
    if capability:
        sections.append(f"""
【能力分析素材】
能力强项: {_join_list(capability.get('strengths'), limit=5, item_limit=100)}
能力弱项: {_join_list(capability.get('weaknesses'), limit=5, item_limit=100)}
核心张力: {_clip(capability.get('tension'), 180)}
资源配置: {_clip(capability.get('resource_allocation'), 220)}
可用 citation: {', '.join(skill_citations.get('capability_match', [])[:10])}

写作要求：
- 写一个自然表达的二级标题（##），标题应概括能力和约束。
- 3-4 段，600-800 字。
- 展开技术能力、为什么需要全栈或系统能力、规模验证、短板约束。
- 标题下写自然段落，不要写列表。
""")

    tension = narrative_materials.get("tension_expand")
    if tension:
        sections.append(f"""
【财务张力素材】
张力点: {_clip(tension.get('tension_point'), 220)}
正面因素: {_clip(tension.get('positive_side'), 260)}
负面因素: {_clip(tension.get('negative_side'), 260)}
权衡逻辑: {_clip(tension.get('tradeoff_logic'), 320)}
未来路径: {_join_list(tension.get('future_path'), limit=3, item_limit=120)}
可用 citation: {', '.join(skill_citations.get('tension_expand', [])[:8])}

写作要求：
- 写一个自然表达的二级标题（##），标题应概括商业或财务张力。
- 2-3 段，400-500 字。
- 展开财务数据、为什么会形成这种张力、风险和机会如何同时存在。
""")

    gap = narrative_materials.get("disclosure_gap_scan")
    if gap:
        sections.append(
            "\n".join(
                [
                    "## 披露缺口",
                    f"- 关键缺口：{_join_list(gap.get('critical_gaps'), limit=2, item_limit=100)}",
                ]
            )
        )

    reader = narrative_materials.get("reader_value_translate")
    if reader:
        sections.append(f"""
【读者价值素材】
从业者价值: {_clip(reader.get('for_practitioners'), 600)}
消费者价值: {_clip(reader.get('for_consumers'), 600)}
技术演进位置: {_clip(reader.get('trend_tech_position'), 800)}
产业链影响: {_clip(reader.get('trend_industry_impact'), 900)}
个人影响: {_clip(reader.get('trend_personal_impact'), 700)}
更大图景: {_clip(reader.get('trend_big_picture'), 900)}
可用 citation: {', '.join(skill_citations.get('reader_value_translate', [])[:10])}

写作要求：
- 写一个自然表达的二级标题（##），例如“这份招股书能告诉你什么”。
- 这一章必须包含以下 3 个三级标题，文字完全保留：
  ### 如果你是该行业的从业者
  ### 如果你是消费者
  ### 这份招股书揭示的趋势
- 从业者部分 2-3 段，300-400 字，给出具体机会窗口和行动建议。
- 消费者部分 2-3 段，300-400 字，给出具体购买或观望建议。
- 趋势分析部分严格 6 段，1,400-1,800 字；低于 1,400 或高于 1,800 字都不合格。
- 趋势分析每段都要展开具体逻辑，不要用一句话带过；必须完整覆盖技术演进位置、产业链影响、个人影响、更大图景四层。
""")

    return f"""请根据以下结构化解读结果，生成一份结构化研究报告正文。

{chr(10).join(sections)}

整体要求：
1. 不要输出一级标题（#），外层系统会自动添加一级标题。
2. 正文必须包含 4 个二级标题（##），二级标题要自然表达，不要用“一、二、三”或“第一章”。
3. 读者价值章节必须包含 3 个三级标题（###）：如果你是该行业的从业者、如果你是消费者、这份招股书揭示的趋势。
4. 总字数不设硬性上限或下限；趋势分析部分严格 6 段、1,400-1,800 字，低于 1,400 或高于 1,800 字都不合格。
5. 标题下写自然段落，不要用列表、加粗标签或目录式提纲。
6. 融入背景知识和类比，但不要编造公司事实。
7. 只能使用上面给出的 citation 编号，不要编造新的编号。
8. Citation 自然嵌入事实句，格式：[C-XXX]。"""


def _business_sentence(business: dict[str, Any]) -> str:
    if not business:
        return ""
    goal = str(business.get("business_goal", "")).rstrip("。")
    scenarios = business.get("target_scenario", [])
    if isinstance(scenarios, list) and scenarios:
        return f"{goal}，核心场景包括{'、'.join(str(item) for item in scenarios)}。"
    return goal + "。" if goal else ""


def _clean_llm_output(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("markdown").strip()
    return text


def _build_retry_prompt_if_needed(
    report_md: str,
    original_prompt: str,
    narrative_materials: dict[str, dict[str, Any]],
) -> str | None:
    if "reader_value_translate" not in narrative_materials:
        return None
    metrics = _structured_report_metrics(report_md)
    problems: list[str] = []
    if metrics["h2_count"] != 4:
        problems.append(f"二级标题数量为 {metrics['h2_count']}，要求 4 个")
    if metrics["h3_count"] != 3:
        problems.append(f"三级标题数量为 {metrics['h3_count']}，要求 3 个")
    trend_chars = metrics["trend_chars"]
    if trend_chars < 1400:
        problems.append(f"趋势分析只有 {trend_chars} 字，低于 1,400 字")
    if trend_chars > 1800:
        problems.append(f"趋势分析有 {trend_chars} 字，高于 1,800 字")
    if not problems:
        return None
    return f"""{original_prompt}

上一次输出没有满足结构化研报要求：
{chr(10).join(f"- {problem}" for problem in problems)}

请重新输出完整正文。要求：
- 仍然不要输出一级标题。
- 保持 4 个二级标题和 3 个指定三级标题。
- “### 这份招股书揭示的趋势”下面严格 1,400-1,800 字。
- 不要压缩趋势分析，也不要超过 1,800 字。
- 只能使用原 prompt 中提供的 citation 编号。"""


def _structured_report_metrics(report_md: str) -> dict[str, int]:
    h2_count = len(re.findall(r"^## ", report_md, flags=re.MULTILINE))
    h3_count = len(re.findall(r"^### ", report_md, flags=re.MULTILINE))
    trend_match = re.search(
        r"^### 这份招股书揭示的趋势\s*(.*)",
        report_md,
        flags=re.MULTILINE | re.DOTALL,
    )
    trend = trend_match.group(1).strip() if trend_match else ""
    next_heading = re.search(r"\n#{1,3} ", trend)
    if next_heading:
        trend = trend[: next_heading.start()].strip()
    return {
        "h2_count": h2_count,
        "h3_count": h3_count,
        "trend_chars": len(trend),
    }


def _clip(value: Any, limit: int = 120) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("。；;，,") + "..."


def _join_list(value: Any, *, limit: int = 5, item_limit: int = 80) -> str:
    if not isinstance(value, list):
        return _clip(value, item_limit)
    return "；".join(_clip(item, item_limit) for item in value[:limit] if str(item).strip())


def _count_confidence(outputs: list[SkillInterpretation]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for output in outputs:
        counts[output.confidence] += 1
    return counts


def _first_citation(skill_citations: dict[str, list[str]], skill_key: str) -> str:
    citations = skill_citations.get(skill_key, [])
    return f"[{citations[0]}]" if citations else ""


def _join_points(points: Any) -> str:
    if not isinstance(points, list):
        return ""
    cleaned = [str(point).strip().rstrip("。；;，,") for point in points if str(point).strip()]
    return "、".join(cleaned)


def _build_debug_prompt(narrative_materials: dict[str, dict[str, Any]], evidence_map: dict[str, str]) -> str:
    return "\n".join(
        [
            "请根据以下解读结果，编织成一篇自然的文章。",
            json.dumps(narrative_materials, ensure_ascii=False, indent=2),
            "证据映射：",
            json.dumps(evidence_map, ensure_ascii=False, indent=2),
        ]
    )
