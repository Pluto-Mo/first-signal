from __future__ import annotations

import json
import re
from typing import Any

from ipo_evidence.llm_caller import call_llm_for_skill
from ipo_evidence.models import (
    EvidenceItem,
    EvidencePacket,
    QualityStatus,
    SkillInterpretation,
)
from ipo_evidence.report_runtime import load_skill_configs


_SKILL_DEFINITIONS = {
    "business_goal_decompose": {
        "gap": "业务目标相关证据不足",
        "impact": "无法完整拆解业务模式、产品、客户和收入问题。",
        "keywords": ("主营业务", "主要产品", "产品", "收入", "销售", "场景"),
        "sections": ("about_company", "business_and_product", "financials"),
    },
    "capability_match": {
        "gap": "能力匹配相关证据不足",
        "impact": "无法判断产品、研发、客户和交付能力是否支撑商业叙事。",
        "keywords": ("产品", "研发", "客户", "交付", "技术", "销售", "风险", "现金流", "亏损", "毛利率"),
        "sections": ("business_and_product", "financials", "risks"),
    },
    "reader_value_translate": {
        "gap": "读者价值相关证据不足",
        "impact": "无法把披露事实转换成个人读者可继续追问的问题。",
        "keywords": ("产品", "收入", "研发", "客户", "风险", "现金流", "技术", "市场"),
        "sections": ("about_company", "business_and_product", "financials", "risks"),
    },
    "tension_expand": {
        "gap": "矛盾张力相关证据不足",
        "impact": "无法解释增长、投入、现金流和风险之间的张力。",
        "keywords": ("增长", "收入", "研发", "现金流", "亏损", "风险", "费用"),
        "sections": ("business_and_product", "financials", "risks"),
    },
    "disclosure_gap_scan": {
        "gap": "披露缺口证据不足",
        "impact": "无法识别当前证据无法支撑的判断。",
        "keywords": ("未披露", "风险", "无法", "不足", "客户", "收入"),
        "sections": (
            "about_company",
            "business_and_product",
            "financials",
            "risks",
            "use_of_proceeds",
            "governance",
            "related_party",
        ),
    },
}


def execute_skill(
    skill_key: str,
    evidence_refs: list[dict[str, Any]],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> SkillInterpretation:
    load_skill_configs([skill_key])
    definition = _SKILL_DEFINITIONS.get(skill_key)
    if definition is None:
        raise ValueError(f"unknown skill_ref: {skill_key}")

    evidence_items = _available_evidence(evidence_refs, evidence_packet, citation_index)
    relevant_items = [
        item
        for item in evidence_items
        if item.canonical_section in definition["sections"]
        and _matches_keywords(item, definition["keywords"])
        and not _is_low_value_claim(item.claim_summary)
    ]
    if not relevant_items:
        return SkillInterpretation(
            skill_key=skill_key,
            interpretation={},
            evidence_chain=[],
            confidence="low",
            gaps=[{"gap": definition["gap"], "impact": definition["impact"]}],
        )

    if skill_key == "business_goal_decompose":
        return _execute_business_goal_decompose(relevant_items, citation_index)
    if skill_key == "capability_match":
        return _execute_capability_match(relevant_items, citation_index)
    if skill_key == "tension_expand":
        return _execute_tension_expand(relevant_items, citation_index)
    if skill_key == "reader_value_translate":
        return _execute_reader_value_translate(relevant_items, citation_index)

    evidence_chain = [item.evidence_id for item in relevant_items[:5]]
    return SkillInterpretation(
        skill_key=skill_key,
        interpretation=_interpret(skill_key, relevant_items),
        evidence_chain=evidence_chain,
        confidence=_confidence(relevant_items),
        gaps=[],
    )


def _execute_business_goal_decompose(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    relevant = _limit_evidence(_deduplicate_evidence(evidence_items), max_count=10)
    if not relevant:
        return _low_confidence_result(
            "business_goal_decompose",
            "业务目标相关证据不足",
            "无法完整拆解业务模式、产品、客户和收入问题。",
        )

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
  "product_entry": ["产品1", "产品2"],
  "target_scenario": ["场景1", "场景2"],
  "customer_type": "B2B/B2C/混合",
  "revenue_structure": "简洁描述"
}

不要输出任何解释，只输出 JSON。"""
    try:
        response = call_llm_for_skill(
            skill_name="business_goal_decompose",
            evidence_text=_format_evidence_text(relevant, citation_index, limit=200),
            instruction=instruction,
        )
        interpretation = _parse_json_object(response)
        if "business_goal" in interpretation:
            interpretation["business_goal"] = str(interpretation["business_goal"])[:100]
        return _skill_result("business_goal_decompose", interpretation, relevant)
    except (json.JSONDecodeError, RuntimeError, TimeoutError, ValueError):
        return _execute_business_goal_decompose_fallback(relevant, citation_index)


def _execute_capability_match(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    relevant = _limit_evidence(_deduplicate_evidence(evidence_items), max_count=15)
    if not relevant:
        return _low_confidence_result(
            "capability_match",
            "能力匹配相关证据不足",
            "无法判断产品、研发、客户和交付能力是否支撑商业叙事。",
        )

    instruction = """你是招股书分析专家。根据以下证据，分析公司的能力匹配情况：

1. 能力强项有哪些？（列出 3-5 条核心判断，每条不超过 30 字）
2. 能力弱项有哪些？（列出 3-5 条核心判断，每条不超过 30 字）
3. 核心张力是什么？（用一句话概括强项和弱项的矛盾点）
4. 资源配置特征是什么？（用一句话概括研发、销售、生产的配置）

要求：
- 提炼核心判断，不要照搬原文
- 强项和弱项各不超过 5 条
- 尽量用数据支撑判断
- 只输出 JSON，格式：
{
  "strengths": ["强项1", "强项2", "强项3"],
  "weaknesses": ["弱项1", "弱项2", "弱项3"],
  "tension": "核心张力概括",
  "resource_allocation": "资源配置特征"
}

不要输出任何解释，只输出 JSON。"""
    try:
        response = call_llm_for_skill(
            skill_name="capability_match",
            evidence_text=_format_evidence_text(relevant, citation_index, limit=150),
            instruction=instruction,
        )
        interpretation = _parse_json_object(response)
        interpretation["strengths"] = _compact_list(interpretation.get("strengths"), limit=5)
        interpretation["weaknesses"] = _compact_list(interpretation.get("weaknesses"), limit=5)
        return _skill_result("capability_match", interpretation, relevant)
    except (json.JSONDecodeError, RuntimeError, TimeoutError, ValueError):
        return _execute_capability_match_fallback(relevant, citation_index)


def _execute_tension_expand(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    relevant = _limit_evidence(_deduplicate_evidence(evidence_items), max_count=10)
    if not relevant:
        return _low_confidence_result(
            "tension_expand",
            "矛盾张力相关证据不足",
            "无法解释增长、投入、现金流和风险之间的张力。",
        )

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
    try:
        response = call_llm_for_skill(
            skill_name="tension_expand",
            evidence_text=_format_evidence_text(relevant, citation_index, limit=150),
            instruction=instruction,
        )
        interpretation = _parse_json_object(response)
        interpretation["future_path"] = _compact_list(interpretation.get("future_path"), limit=3)
        return _skill_result("tension_expand", interpretation, relevant)
    except (json.JSONDecodeError, RuntimeError, TimeoutError, ValueError):
        return _execute_tension_expand_fallback(relevant, citation_index)


def _execute_reader_value_translate(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    relevant = _limit_evidence(_deduplicate_evidence(evidence_items), max_count=15)
    if len(relevant) < 3:
        return _low_confidence_result(
            "reader_value_translate",
            "读者价值相关证据不足",
            "无法提供从业者、消费者和趋势层面的深度洞察。",
        )

    instruction = """你是招股书分析专家。根据以下证据，为不同读者提供可操作的洞察：

1. 如果你是该行业的从业者（创业者、产品经理）：
- 这家公司占据了什么位置？
- 它的短板在哪里？这可能意味着什么机会窗口？
- 给出 2-3 条具体、可操作的建议。

2. 如果你是消费者：
- 应该如何判断该公司或相关公司的产品？
- 如果买，应该看什么指标或体验？
- 如果不买或观望，原因是什么？

3. 这份招股书揭示的趋势（重点，需要深度分析）：
- 技术演进位置：这个技术在整个人机交互、终端智能或产业升级中的位置。
- 产业链影响：对上游芯片、模组、云服务、硬件厂商和下游应用方的影响。
- 个人影响：对职业选择、产品判断和消费决策的影响。
- 更大图景：AI 能力商品化、端侧化、模块化或产业演化类比。

要求：
- 具体到这家公司的特征，不要泛化。
- 给出可操作建议。
- 融入背景知识，但不要写成科普。
- 趋势部分要有足够信息密度，供最终报告展开 1,400-1,800 字。
- 只输出 JSON，格式：
{
  "for_practitioners": "从业者价值（200-300 字，2-3 条可操作建议）",
  "for_consumers": "消费者价值（200-300 字，具体购买建议）",
  "trend_tech_position": "技术演进位置（200-300 字）",
  "trend_industry_impact": "产业链影响（300-400 字）",
  "trend_personal_impact": "个人影响（200-300 字）",
  "trend_big_picture": "更大图景（300-400 字）"
}

不要输出任何解释，只输出 JSON。"""
    try:
        response = call_llm_for_skill(
            skill_name="reader_value_translate",
            evidence_text=_format_evidence_text(relevant, citation_index, limit=200),
            instruction=instruction,
        )
        interpretation = _parse_json_object(response)
        return _skill_result("reader_value_translate", interpretation, relevant)
    except (json.JSONDecodeError, RuntimeError, TimeoutError, ValueError):
        return _execute_reader_value_translate_fallback(relevant, citation_index)


def _execute_business_goal_decompose_fallback(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    del citation_index
    return _skill_result(
        "business_goal_decompose",
        {
            "business_goal": _clean_claim(evidence_items[0].claim_summary)[:100],
            "product_entry": _extract_terms(evidence_items, ("AI 芯片", "智慧办公硬件", "智能硬件", "产品")),
            "target_scenario": _extract_terms(evidence_items, ("智慧出行", "会议", "家居", "车载", "办公")),
            "customer_type": "B2B" if _has_any(evidence_items, ("客户", "销售", "交付")) else "未充分披露",
            "revenue_structure": _first_matching_claim(evidence_items, ("收入", "销售")) or "收入结构仍需继续核查",
        },
        evidence_items[:5],
    )


def _execute_capability_match_fallback(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    del citation_index
    strengths = _matching_claims(evidence_items, ("研发", "技术", "产品", "交付"))[:5]
    weaknesses = _matching_claims(evidence_items, ("风险", "客户集中", "现金流", "费用", "毛利率", "亏损"))[:5]
    return _skill_result(
        "capability_match",
        {
            "strengths": strengths or [_clean_claim(evidence_items[0].claim_summary)],
            "weaknesses": weaknesses or ["当前证据未充分展开能力弱项"],
            "tension": "增长能力与客户集中风险并存" if weaknesses else "能力强项仍需和风险证据共同验证",
            "resource_allocation": _first_matching_claim(evidence_items, ("研发", "费用", "销售")) or "资源配置仍需结合财务证据核查",
        },
        evidence_items[:5],
    )


def _execute_tension_expand_fallback(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    del citation_index
    positive = _first_matching_claim(evidence_items, ("增长", "收入", "产品", "研发")) or _clean_claim(evidence_items[0].claim_summary)
    negative = _first_matching_claim(evidence_items, ("风险", "现金流", "亏损", "客户集中")) or "负面约束需要更多风险证据验证"
    return _skill_result(
        "tension_expand",
        {
            "tension_point": "增长、投入与风险之间的张力",
            "positive_side": positive,
            "negative_side": negative,
            "tradeoff_logic": "正面业务线索需要和盈利质量、现金流、客户集中度一起读。",
            "future_path": ["继续验证收入质量", "跟踪客户分散度", "观察研发投入转化效率"],
        },
        evidence_items[:5],
    )


def _execute_reader_value_translate_fallback(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
) -> SkillInterpretation:
    del citation_index
    summary = _clean_claim(evidence_items[0].claim_summary)
    product = _first_matching_claim(evidence_items, ("产品", "技术", "研发")) or summary
    risk = _first_matching_claim(evidence_items, ("风险", "现金流", "客户", "亏损")) or "风险约束仍需结合后续证据验证。"
    return _skill_result(
        "reader_value_translate",
        {
            "for_practitioners": f"从业者可从产品入口、客户路线和交付方式寻找机会。当前证据显示：{product}",
            "for_consumers": "消费者不应只看概念标签，应优先验证产品是否进入真实场景、是否有稳定客户和可持续服务能力。",
            "trend_tech_position": f"这类业务处在技术从概念走向终端落地的阶段，关键不是单点能力，而是能否把产品、研发和交付闭合。{product}",
            "trend_industry_impact": "产业链会从单点技术采购转向系统方案协作，上游技术、硬件和下游场景方之间的分工会重新调整。",
            "trend_personal_impact": "个人选择职业或产品时，应关注场景工程、端侧适配、客户交付和商业化效率，而不是只追逐抽象技术名词。",
            "trend_big_picture": f"更大的图景是技术能力被模块化、商品化并嵌入具体终端。与此同时，{risk}",
        },
        evidence_items[:5],
    )


def _interpret(skill_key: str, evidence_items: list[EvidenceItem]) -> dict[str, Any]:
    if skill_key == "business_goal_decompose":
        return {
            "business_goal": _clean_claim(evidence_items[0].claim_summary),
            "product_entry": _extract_terms(evidence_items, ("AI 芯片", "智慧办公硬件", "智能硬件", "产品")),
            "target_scenario": _extract_terms(evidence_items, ("智慧出行", "会议", "家居", "车载", "办公")),
            "customer_type": "B2B" if _has_any(evidence_items, ("客户", "销售", "交付")) else "未充分披露",
            "revenue_structure": _first_matching_claim(evidence_items, ("收入", "销售")) or "收入结构仍需继续核查",
        }
    if skill_key == "capability_match":
        strengths = _matching_claims(evidence_items, ("研发", "技术", "产品", "交付"))
        weaknesses = _matching_claims(evidence_items, ("风险", "客户集中", "现金流", "费用", "毛利率"))
        return {
            "strengths": strengths or [_clean_claim(evidence_items[0].claim_summary)],
            "weaknesses": weaknesses or ["当前证据未充分展开能力弱项"],
            "tension": "增长能力与客户集中风险并存" if weaknesses else "能力强项仍需和风险证据共同验证",
            "resource_allocation": _first_matching_claim(evidence_items, ("研发", "费用", "销售")) or "资源配置仍需结合财务证据核查",
        }
    if skill_key == "disclosure_gap_scan":
        return {
            "critical_gaps": _matching_claims(evidence_items, ("未披露", "无法", "不足")) or ["关键拆分信息仍需人工复核"],
            "possible_reasons": ["可能涉及合同保密、商业敏感或披露粒度限制"],
            "workarounds": ["从客户结构、收入结构和风险披露交叉验证"],
        }
    if skill_key == "tension_expand":
        positive = _first_matching_claim(evidence_items, ("增长", "收入", "产品", "研发")) or _clean_claim(evidence_items[0].claim_summary)
        negative = _first_matching_claim(evidence_items, ("风险", "现金流", "亏损", "客户集中")) or "负面约束需要更多风险证据验证"
        return {
            "tension_point": "增长、投入与风险之间的张力",
            "positive_side": positive,
            "negative_side": negative,
            "tradeoff_logic": "正面业务线索需要和盈利质量、现金流、客户集中度一起读。",
            "future_path": ["继续验证收入质量", "跟踪客户分散度", "观察研发投入转化效率"],
        }
    if skill_key == "reader_value_translate":
        summary = _clean_claim(evidence_items[0].claim_summary)
        return {
            "for_tech_people": f"技术人可以从产品入口和研发方向继续拆解：{summary}",
            "for_investors": "投资人应把收入增长、毛利率、现金流和客户集中度放在同一张图里看。",
            "for_practitioners": "从业者可关注它选择的客户路线、交付方式和场景扩展节奏。",
            "for_consumers": "消费者视角下，它更可能是终端设备背后的能力供应商。",
        }
    return {}


def _available_evidence(
    evidence_refs: list[dict[str, Any]],
    evidence_packet: EvidencePacket,
    citation_index: dict[str, str],
) -> list[EvidenceItem]:
    items_by_id = {item.evidence_id: item for item in evidence_packet.items}
    selected: list[EvidenceItem] = []
    seen: set[str] = set()
    for ref in sorted(evidence_refs, key=_rank_value):
        evidence_id = ref.get("evidence_id") if isinstance(ref, dict) else None
        if not isinstance(evidence_id, str):
            continue
        if evidence_id in seen or evidence_id not in citation_index:
            continue
        item = items_by_id.get(evidence_id)
        if item is None:
            continue
        selected.append(item)
        seen.add(evidence_id)
    return selected


def _rank_value(ref: dict[str, Any]) -> int:
    rank = ref.get("rank", 99) if isinstance(ref, dict) else 99
    if type(rank) is int and rank >= 0:
        return rank
    return 99


def _matches_keywords(item: EvidenceItem, keywords: tuple[str, ...]) -> bool:
    text = _evidence_text(item)
    return any(keyword in text for keyword in keywords)


def _deduplicate_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen_claims: set[str] = set()
    deduped: list[EvidenceItem] = []
    for item in items:
        fingerprint = " ".join(item.claim_summary.split())[:50]
        if fingerprint in seen_claims:
            continue
        seen_claims.add(fingerprint)
        deduped.append(item)
    return deduped


def _limit_evidence(items: list[EvidenceItem], max_count: int = 10) -> list[EvidenceItem]:
    return sorted(items, key=_quality_score, reverse=True)[:max_count]


def _quality_score(item: EvidenceItem) -> int:
    if item.quality_status == QualityStatus.safe_to_use:
        return 3
    if item.quality_status == QualityStatus.manual_review:
        return 2
    return 1


def _format_evidence_text(
    evidence_items: list[EvidenceItem],
    citation_index: dict[str, str],
    *,
    limit: int,
) -> str:
    return "\n\n".join(
        f"[{citation_index.get(item.evidence_id, '?')}] {_clean_for_prompt(_evidence_text(item), limit)}"
        for item in evidence_items
    )


def _evidence_text(item: EvidenceItem) -> str:
    return " ".join(
        [
            item.claim_summary,
            item.quote or "",
            item.table_title or "",
            " ".join(item.section_path),
            " ".join(item.fields.values()),
        ]
    )


def _clean_for_prompt(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("。；;，,") + "..."


def _parse_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("skill LLM response must be a JSON object")
    return parsed


def _compact_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:80] for item in value if str(item).strip()][:limit]


def _skill_result(
    skill_key: str,
    interpretation: dict[str, Any],
    evidence_items: list[EvidenceItem],
) -> SkillInterpretation:
    return SkillInterpretation(
        skill_key=skill_key,
        interpretation=interpretation,
        evidence_chain=[item.evidence_id for item in evidence_items],
        confidence=_confidence(evidence_items),
        gaps=[],
    )


def _low_confidence_result(skill_key: str, gap: str, impact: str) -> SkillInterpretation:
    return SkillInterpretation(
        skill_key=skill_key,
        interpretation={},
        evidence_chain=[],
        confidence="low",
        gaps=[{"gap": gap, "impact": impact}],
    )


def _clean_claim(value: str) -> str:
    text = " ".join(value.replace("\\n", " ").split())
    if "对应数据为：" in text:
        text = text.split("对应数据为：", 1)[0].rstrip("，；;:：") + "。"
    text = text.rstrip("。；;，,")
    if len(text) > 180:
        cut = text[:180]
        for marker in ("。", "；", "，"):
            pos = cut.rfind(marker)
            if pos >= 48:
                text = cut[:pos]
                break
        else:
            text = cut.rstrip("。；;，,") + "..."
    return text.rstrip("。；;，,") + "。"


def _extract_terms(evidence_items: list[EvidenceItem], terms: tuple[str, ...]) -> list[str]:
    text = " ".join(item.claim_summary for item in evidence_items)
    return [term for term in terms if term in text]


def _has_any(evidence_items: list[EvidenceItem], terms: tuple[str, ...]) -> bool:
    text = " ".join(item.claim_summary for item in evidence_items)
    return any(term in text for term in terms)


def _matching_claims(evidence_items: list[EvidenceItem], terms: tuple[str, ...]) -> list[str]:
    return [
        _clean_claim(item.claim_summary)
        for item in evidence_items
        if any(term in item.claim_summary for term in terms)
        and not _is_low_value_claim(item.claim_summary)
    ]


def _first_matching_claim(evidence_items: list[EvidenceItem], terms: tuple[str, ...]) -> str | None:
    matches = _matching_claims(evidence_items, terms)
    return matches[0] if matches else None


def _is_low_value_claim(value: str) -> bool:
    snippets = (
        "具体分析如下",
        "如下：",
        "主要财务指标显示",
        "结合行业特点，公司选取",
        "参见",
        "详见",
        "（万元）",
        "(万元)",
    )
    text = " ".join(value.split())
    return any(snippet in text for snippet in snippets) or len(text.strip("。；;，,：:")) < 12


def _confidence(evidence_items: list[EvidenceItem]) -> str:
    statuses = {item.quality_status for item in evidence_items}
    if QualityStatus.safe_to_use in statuses:
        return "high"
    if statuses == {QualityStatus.do_not_use}:
        return "low"
    return "medium"
