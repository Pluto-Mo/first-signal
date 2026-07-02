from __future__ import annotations

from dataclasses import dataclass

from ipo_evidence.models import EvidenceItem, QualityStatus
from ipo_evidence.report_runtime import (
    PromptConfig,
    SkillConfig,
    load_prompt_config,
    load_skill_configs,
)


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
    "主营业务未发生重大变化",
    "公司结合自身战略",
    "综上",
    "通过本项目",
    "有助于公司形成",
    "平台运营与销售",
    "董事、监事/",
    "主营业务成本",
    "合并利润表",
    "主要财务指标显示：覆盖项目",
    "按2024 年度高于",
    "上游基础设施",
]

BROKEN_ENDINGS = ("在", "提", "所处", "境外", "销售", "客户", "和", "及", "以及", "、")

FORBIDDEN_RAW_TEXT = ["{'", "对应数据为"]


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
    if "{'" in text:
        text = text.split("{'", 1)[0].rstrip("：:。；;，,")
    text = text.replace("对应数据为：", "为 ").replace("对应数据为", "为")
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


def _normalize_table_text(value: str) -> str:
    return " ".join(value.replace("\\n", " ").replace("\n", " ").split())


def _score(item: EvidenceItem, section_key: str) -> int:
    text = " ".join([item.claim_summary, item.quote or "", " ".join(item.section_path)])
    summary = _clean_text(item.claim_summary)
    score = 0
    for keyword in KEYWORDS_BY_SECTION.get(section_key, []):
        if keyword in text:
            score += 4

    if item.source_type == "table_fact" and item.fields:
        score += 8
        if any(value and value != "-" for value in item.fields.values()):
            score += 4
        if item.table_title:
            score += 2
        return score

    if item.source_type == "text_quote":
        score += 3
    if item.source_type == "table_fact":
        score += 5
    if 35 <= len(item.claim_summary) <= 260:
        score += 2
    for snippet in LOW_VALUE_SNIPPETS:
        if snippet in text:
            score -= 8
    if summary.endswith(BROKEN_ENDINGS):
        score -= 6
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
    scored = [
        (score, pair)
        for pair in indexed_items
        if pair[1].quality_status != QualityStatus.do_not_use
        for score in [_score(pair[1], section_key)]
        if score > 0
    ]
    ranked = sorted(scored, key=lambda scored_pair: (-scored_pair[0], scored_pair[1][0]))
    selected: list[tuple[int, EvidenceItem]] = []
    seen: set[str] = set()
    for _, pair in ranked:
        key = _dedupe_key(pair[1])
        if not key or key in seen:
            continue
        selected.append(pair)
        seen.add(key)
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda pair: pair[0])


def _format_table_sentence(item: EvidenceItem, citation_id: str) -> str:
    fields = {
        _normalize_table_text(key): _normalize_table_text(value)
        for key, value in item.fields.items()
        if value and value != "-"
    }
    metric = fields.get("项目") or fields.get("指标") or _normalize_table_text(item.table_title or "") or "表格项目"
    values = [
        f"{key}为 {_readable_value(value)}"
        for key, value in fields.items()
        if key not in {"项目", "指标"}
    ]
    if values:
        return f"{metric}显示，{'，'.join(values[:4])}。[{citation_id}]"
    table_title = _normalize_table_text(item.table_title or "") or "表格"
    return f"{table_title}披露了{metric}相关数据。[{citation_id}]"


def _format_sentence(index: int, item: EvidenceItem) -> str:
    citation_id = _citation_id(index)
    if item.source_type == "table_fact" and item.fields:
        return _format_table_sentence(item, citation_id)
    return f"{_clean_text(item.claim_summary)}。[{citation_id}]"


def _sentences(items: list[tuple[int, EvidenceItem]], limit: int) -> str:
    return " ".join(_format_sentence(index, item) for index, item in items[:limit])


def _skill_keys(skills: list[SkillConfig]) -> set[str]:
    return {skill.skill_key for skill in skills}


def _skill_actions(skills: list[SkillConfig]) -> str:
    actions = [skill.action.rstrip("。") for skill in skills if skill.action]
    if not actions:
        return ""
    return "这一节先把披露事实转成可核查问题：" + "；".join(actions[:3]) + "。"


def _prompt_forbids_internal_terms(prompt: PromptConfig) -> bool:
    return "不写内部系统词。" in prompt.rules


def _clean_internal_terms(text: str) -> str:
    cleaned = text
    replacements = {
        "本节调用的解读动作是：": "",
        "本节调用的解读动作是": "",
        "prompt_slot": "",
        "skill_refs": "",
        "section draft": "",
        "internal trace": "",
    }
    for internal_term, replacement in replacements.items():
        cleaned = cleaned.replace(internal_term, replacement)
    return cleaned


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


def _skill_interpretation(section_key: str, skills: list[SkillConfig]) -> str:
    keys = _skill_keys(skills)
    parts: list[str] = []
    if "capability_match" in keys:
        parts.append(
            "这些证据需要放在能力匹配框架下读：不是把 AI 当成概念标签，而是看技术、产品、客户和交付是否互相支撑，单一亮点不足以构成完整商业判断。"
        )
    if "tension_expand" in keys:
        parts.append(
            "更重要的是看张力：增长、研发投入、亏损、现金流和风险如果不能互相解释，叙事就还没有闭合。"
        )
    if "reader_value_translate" in keys and section_key == "cognitive_worldview":
        parts.append(
            "把这套方法迁移到其他公司时，可以先找产品入口，再看客户验证，最后检查收入质量和风险暴露。"
        )
    return " ".join(parts)


def _build_paragraphs(
    section_key: str,
    title: str,
    skills: list[SkillConfig],
    prompt: PromptConfig,
    selected_items: list[tuple[int, EvidenceItem]],
) -> list[str]:
    _ = title
    if not selected_items:
        return []
    intro = _skill_intro(section_key, skills)
    first = _sentences(selected_items, 3)
    second = _sentences(selected_items[3:], 4)
    third = _sentences(selected_items[7:], 5)
    interpretation = _skill_interpretation(section_key, skills)
    paragraphs = [f"{intro}{first}"]
    if second:
        paragraphs.append(f"第二层看证据之间是否互相支持。{second}")
    if third:
        paragraphs.append(f"再往后看边界条件。{third}")
    if interpretation:
        paragraphs.append(interpretation)
    if _prompt_forbids_internal_terms(prompt):
        paragraphs = [_clean_internal_terms(paragraph) for paragraph in paragraphs]
    return paragraphs


def _readability_warnings(body: str, prompt: PromptConfig) -> list[str]:
    warnings: list[str] = []
    if any(token in body for token in FORBIDDEN_RAW_TEXT):
        warnings.append("contains_raw_data_literal")
    paragraphs = [paragraph for paragraph in body.split("\n\n") if paragraph.strip()]
    if any(len(paragraph) > 900 for paragraph in paragraphs):
        warnings.append("paragraph_too_long")
    citation_count = body.count("[C-")
    if citation_count > 14:
        warnings.append("too_many_citations")
    if "事实句必须带 citation id。" in prompt.rules and body and citation_count == 0:
        warnings.append("missing_citations")
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
        readability_warnings=_readability_warnings(body, prompt),
    )
