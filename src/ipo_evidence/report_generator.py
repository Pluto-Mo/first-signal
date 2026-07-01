from __future__ import annotations

from collections import defaultdict
from typing import Any

from ipo_evidence.models import EvidenceItem, EvidencePacket
from ipo_evidence.report_inputs import load_report_prompt_config


SECTION_ORDER = [
    "about_company",
    "business_and_product",
    "financials",
    "use_of_proceeds",
    "risks",
    "governance",
    "related_party",
]

KEYWORDS = {
    "identity": [
        "公司主要从事",
        "主营业务",
        "主要业务",
        "专注",
        "定位",
        "发行人",
        "产品服务",
    ],
    "product": [
        "产品",
        "服务",
        "解决方案",
        "产品体系",
        "业务模式",
        "硬件",
        "软件",
        "系统",
    ],
    "scenario": [
        "应用场景",
        "场景",
        "客户需求",
        "行业应用",
        "终端",
        "渠道",
        "交付",
        "使用",
    ],
    "industry": [
        "市场规模",
        "年均复合增长率",
        "产业链",
        "市占率",
        "市场份额",
        "行业",
        "竞争",
        "趋势",
        "渗透率",
    ],
    "technology": [
        "研发",
        "研发投入",
        "研发费用",
        "核心技术",
        "技术体系",
        "专利",
        "软件",
        "硬件",
        "算法",
        "平台",
    ],
    "talent": [
        "研发人员",
        "核心技术人员",
        "技术骨干",
        "员工",
        "人才",
        "团队",
        "信息化",
        "结构设计",
        "制造",
    ],
    "channel": [
        "销售模式",
        "渠道",
        "经销",
        "直销",
        "线上",
        "线下",
        "电商",
        "平台",
        "客户",
        "供应商",
    ],
    "financial": [
        "营业收入",
        "收入",
        "毛利率",
        "利润",
        "亏损",
        "现金流",
        "研发费用",
        "销售费用",
        "报告期",
    ],
    "customer": [
        "客户",
        "前五",
        "销售比例",
        "集中度",
        "主要客户",
        "合作",
        "订单",
        "终端客户",
    ],
    "proceeds": [
        "募集资金",
        "募投",
        "投资项目",
        "研发升级",
        "建设项目",
        "资金运用",
        "产能",
    ],
    "risk": [
        "风险",
        "亏损",
        "现金流量净额",
        "应收账款",
        "存货",
        "价格上涨",
        "坏账",
        "不利影响",
        "供应商",
        "客户集中",
    ],
    "governance": [
        "治理",
        "董事会",
        "股东",
        "控制",
        "承诺",
        "内控",
        "关联交易",
        "关联方",
    ],
    "disclosure_gap": [
        "未披露",
        "未提及",
        "缺少",
        "无法",
        "平台",
        "渠道",
        "客户",
        "店铺",
        "第三方",
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
    "主营业务未发生重大变化",
    "公司结合自身战略",
    "综上",
    "通过本项目",
    "有助于公司形成",
    "董事、监事/",
    "合并利润表",
]

BROKEN_ENDINGS = ("在", "提", "所处", "境外", "销售", "客户", "和", "与", "或", "及", "以及", "、")
SUBJECT_FIELD_KEYS = (
    "产品",
    "项目",
    "业务指标",
    "应用领域",
    "公司名称",
    "客户名称",
    "供应商名称",
    "类别",
    "名称",
)
IMPORTANT_FIELD_KEYWORDS = (
    "收入",
    "占比",
    "毛利率",
    "研发",
    "销售费用",
    "现金流",
    "应收账款",
    "存货",
    "募集资金",
    "投资",
    "金额",
    "数量",
    "比例",
    "报告期",
)


def _citation_id(index: int) -> str:
    return f"C-{index:03d}"


def _clean_text(value: str, limit: int = 185) -> str:
    text = " ".join(value.replace("\u3000", " ").split()).rstrip("。；;，,")
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


def _format_fields(fields: dict[str, str]) -> str:
    return "；".join(f"{key}：{_readable_value(value)}" for key, value in fields.items())


def _table_subject(fields: dict[str, str]) -> str | None:
    for key in SUBJECT_FIELD_KEYS:
        value = fields.get(key)
        if value:
            return value
    for key, value in fields.items():
        if value and not any(keyword in key for keyword in IMPORTANT_FIELD_KEYWORDS):
            return value
    return None


def _important_fields(fields: dict[str, str], limit: int = 5) -> dict[str, str]:
    selected: dict[str, str] = {}
    for key, value in fields.items():
        if key in SUBJECT_FIELD_KEYS:
            continue
        if any(keyword in key for keyword in IMPORTANT_FIELD_KEYWORDS):
            selected[key] = value
        if len(selected) >= limit:
            break
    if selected:
        return selected
    for key, value in fields.items():
        if key not in SUBJECT_FIELD_KEYS:
            selected[key] = value
        if len(selected) >= limit:
            break
    return selected or fields


def _sentence(item: EvidenceItem, citation_id: str, limit: int = 185) -> str:
    if item.source_type == "table_fact" and item.fields:
        product = item.fields.get("产品")
        revenue = item.fields.get("2023年收入")
        ratio = item.fields.get("占比")
        if product and revenue and ratio:
            return f"{product} 2023 年收入为 {_readable_value(revenue)}，占比 {ratio}。[{citation_id}]"

        covered = item.fields.get("覆盖项目")
        total_ratio = item.fields.get("占比合计")
        concentration = item.fields.get("集中度判断")
        if covered and total_ratio and concentration:
            return f"{covered}合计收入占比为 {total_ratio}，{concentration}。[{citation_id}]"

        subject = _table_subject(item.fields)
        table_title = item.table_title or "表格"
        fields = _important_fields(item.fields)
        formatted = _format_fields(fields)
        if subject:
            return f"{table_title}显示，{subject}的关键字段为：{formatted}。[{citation_id}]"
        return f"{table_title}显示：{formatted}。[{citation_id}]"

    return f"{_clean_text(item.claim_summary, limit)}。[{citation_id}]"


def _group_items(packet: EvidencePacket) -> dict[str, list[tuple[int, EvidenceItem]]]:
    grouped: dict[str, list[tuple[int, EvidenceItem]]] = defaultdict(list)
    for index, item in enumerate(packet.items, start=1):
        grouped[item.canonical_section].append((index, item))
    return grouped


def _index_items(packet: EvidencePacket) -> dict[str, tuple[int, EvidenceItem]]:
    return {item.evidence_id: (index, item) for index, item in enumerate(packet.items, start=1)}


def _section_groups_from_inputs(report_inputs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report_inputs:
        return []
    groups = report_inputs.get("section_groups", [])
    if not isinstance(groups, list):
        return []
    return [group for group in groups if isinstance(group, dict)]


def _input_group_map(report_inputs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        group["section_key"]: group
        for group in _section_groups_from_inputs(report_inputs)
        if isinstance(group.get("section_key"), str)
    }


def _prompt_config() -> dict[str, Any]:
    return load_report_prompt_config()


def _report_title(company_name: str) -> str:
    suffix = _prompt_config().get("report_title_suffix", "招股书长篇阅读")
    return f"# {company_name}{suffix}"


def _view_title(section_key: str, fallback: str) -> str:
    views = _prompt_config().get("input_views", {})
    if not isinstance(views, dict):
        return fallback
    view = views.get(section_key, {})
    if not isinstance(view, dict):
        return fallback
    title = view.get("title")
    return title if isinstance(title, str) and title else fallback


def _items_for_input_group(
    group: dict[str, Any],
    item_index: dict[str, tuple[int, EvidenceItem]],
) -> list[tuple[int, EvidenceItem]]:
    refs = group.get("evidence_refs", [])
    if not isinstance(refs, list):
        return []
    items: list[tuple[int, EvidenceItem]] = []
    for ref in sorted(refs, key=lambda ref: ref.get("rank", 99) if isinstance(ref, dict) else 99):
        if not isinstance(ref, dict):
            continue
        evidence_id = ref.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id in item_index:
            items.append(item_index[evidence_id])
    return items


def _merge_unique(*groups: list[tuple[int, EvidenceItem]]) -> list[tuple[int, EvidenceItem]]:
    seen: set[str] = set()
    merged: list[tuple[int, EvidenceItem]] = []
    for group in groups:
        for pair in group:
            _, item = pair
            if item.evidence_id in seen:
                continue
            merged.append(pair)
            seen.add(item.evidence_id)
    return sorted(merged, key=lambda pair: pair[0])


def _text_only(items: list[tuple[int, EvidenceItem]]) -> list[tuple[int, EvidenceItem]]:
    return [pair for pair in items if pair[1].source_type == "text_quote"]


def _section_items(
    grouped: dict[str, list[tuple[int, EvidenceItem]]],
    section_keys: list[str],
) -> list[tuple[int, EvidenceItem]]:
    return _merge_unique(*(grouped.get(section_key, []) for section_key in section_keys))


def _view_items(
    view_key: str,
    fallback_sections: list[str],
    grouped: dict[str, list[tuple[int, EvidenceItem]]],
    input_groups: dict[str, dict[str, Any]],
    item_index: dict[str, tuple[int, EvidenceItem]],
) -> list[tuple[int, EvidenceItem]]:
    configured = _items_for_input_group(input_groups.get(view_key, {}), item_index)
    fallback = _section_items(grouped, fallback_sections)
    return _merge_unique(configured, fallback)


def _score(item: EvidenceItem, keywords: list[str]) -> int:
    field_text = _format_fields(item.fields) if item.fields else ""
    text = " ".join(
        [
            item.claim_summary,
            item.quote or "",
            item.table_title or "",
            field_text,
            " ".join(item.section_path),
        ]
    )
    summary = item.claim_summary.strip().rstrip("。；;，,")
    score = 0
    for keyword in keywords:
        if keyword in text:
            score += 3
    if item.source_type == "table_fact":
        score += 1
    if 35 <= len(item.claim_summary) <= 260:
        score += 2
    if item.quality_status == "safe_to_use":
        score += 1
    for snippet in LOW_VALUE_SNIPPETS:
        if snippet in text:
            score -= 4
    if len(item.claim_summary) < 18:
        score -= 4
    if summary.endswith(BROKEN_ENDINGS):
        score -= 5
    return score


def _select(
    items: list[tuple[int, EvidenceItem]],
    keywords: list[str],
    limit: int,
    *,
    exclude_ids: set[str] | None = None,
) -> list[tuple[int, EvidenceItem]]:
    exclude_ids = exclude_ids or set()
    candidates = [pair for pair in items if pair[1].evidence_id not in exclude_ids]
    if not candidates:
        candidates = items
    ranked = sorted(
        candidates,
        key=lambda pair: (
            -_score(pair[1], keywords),
            abs(len(pair[1].claim_summary) - 120),
            pair[0],
        ),
    )
    selected: list[tuple[int, EvidenceItem]] = []
    selected_keys: set[str] = set()
    for pair in ranked:
        if _score(pair[1], keywords) <= 0:
            continue
        text_key = _clean_text(pair[1].claim_summary, 72)
        if text_key in selected_keys:
            continue
        selected.append(pair)
        selected_keys.add(text_key)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for pair in ranked:
            text_key = _clean_text(pair[1].claim_summary, 72)
            if pair not in selected and text_key not in selected_keys:
                selected.append(pair)
                selected_keys.add(text_key)
            if len(selected) >= limit:
                break
    return sorted(selected, key=lambda pair: pair[0])


def _fact(
    items: list[tuple[int, EvidenceItem]],
    keywords: list[str],
    fallback: str,
    *,
    limit: int = 185,
    used_ids: set[str] | None = None,
) -> str:
    selected = _select(items, keywords, 1, exclude_ids=used_ids)
    if not selected:
        return fallback
    index, item = selected[0]
    if used_ids is not None:
        used_ids.add(item.evidence_id)
    return _sentence(item, _citation_id(index), limit)


def _facts(
    items: list[tuple[int, EvidenceItem]],
    keywords: list[str],
    fallback: str,
    *,
    count: int = 2,
    limit: int = 185,
    used_ids: set[str] | None = None,
) -> str:
    selected = _select(items, keywords, count, exclude_ids=used_ids)
    if not selected:
        return fallback
    if used_ids is not None:
        used_ids.update(item.evidence_id for _, item in selected)
    return " ".join(_sentence(item, _citation_id(index), limit) for index, item in selected)


def _report_body(
    company_name: str,
    grouped: dict[str, list[tuple[int, EvidenceItem]]],
    report_inputs: dict[str, Any] | None,
    item_index: dict[str, tuple[int, EvidenceItem]],
) -> list[str]:
    input_groups = _input_group_map(report_inputs)

    about = grouped.get("about_company", [])
    business = grouped.get("business_and_product", [])
    financials = grouped.get("financials", [])
    proceeds = grouped.get("use_of_proceeds", [])
    risks = grouped.get("risks", [])
    governance = grouped.get("governance", [])
    related_party = grouped.get("related_party", [])

    signal_view = _view_items(
        "signal_and_question",
        ["about_company", "business_and_product", "financials", "risks"],
        grouped,
        input_groups,
        item_index,
    )
    capability_view = _view_items(
        "business_capability_chain",
        ["about_company", "business_and_product", "financials", "use_of_proceeds", "governance"],
        grouped,
        input_groups,
        item_index,
    )
    disclosure_view = _view_items(
        "disclosure_gap_and_risk",
        ["financials", "risks", "governance", "related_party", "business_and_product"],
        grouped,
        input_groups,
        item_index,
    )
    reader_view = _view_items(
        "reader_action_map",
        [
            "about_company",
            "business_and_product",
            "financials",
            "use_of_proceeds",
            "risks",
            "governance",
        ],
        grouped,
        input_groups,
        item_index,
    )

    used_ids: set[str] = set()
    identity = _fact(
        _merge_unique(about, business, signal_view),
        KEYWORDS["identity"] + KEYWORDS["product"],
        "材料中暂未抽出可引用的主营业务描述。",
        used_ids=used_ids,
    )
    product = _facts(
        _merge_unique(business, signal_view),
        KEYWORDS["product"] + KEYWORDS["scenario"],
        "材料中暂未抽出可引用的产品或应用场景。",
        count=3,
        used_ids=used_ids,
    )
    industry = _facts(
        signal_view,
        KEYWORDS["industry"],
        "材料中暂未抽出可引用的行业规模、趋势或竞争格局。",
        count=2,
        used_ids=used_ids,
    )
    technology = _facts(
        _merge_unique(capability_view, business, about),
        KEYWORDS["technology"],
        "材料中暂未抽出可引用的研发或技术储备。",
        count=2,
        used_ids=used_ids,
    )
    talent = _facts(
        _text_only(_merge_unique(capability_view, about, business, governance)),
        KEYWORDS["talent"],
        "材料中暂未抽出可引用的人员或组织能力描述。",
        count=2,
        used_ids=used_ids,
    )
    channel_customer = _facts(
        _text_only(_merge_unique(capability_view, business, about, governance)),
        KEYWORDS["channel"] + KEYWORDS["customer"],
        "材料中暂未抽出可引用的客户或渠道验证。",
        count=3,
        used_ids=used_ids,
    )
    revenue = _facts(
        _merge_unique(financials, capability_view, reader_view),
        KEYWORDS["financial"],
        "材料中暂未抽出可引用的收入、利润或费用信息。",
        count=2,
        used_ids=used_ids,
    )
    cashflow = _facts(
        _merge_unique(financials, risks, disclosure_view),
        ["现金流量净额", "经营活动", "应收账款", "存货", "回款", "亏损"],
        "材料中暂未抽出可引用的现金流、回款或资金占用信息。",
        count=2,
        used_ids=used_ids,
    )
    proceeds_fact = _facts(
        _merge_unique(proceeds, capability_view),
        KEYWORDS["proceeds"] + KEYWORDS["technology"],
        "材料中暂未抽出可引用的募投方向。",
        count=2,
        used_ids=used_ids,
    )
    risk = _facts(
        _merge_unique(risks, disclosure_view),
        KEYWORDS["risk"],
        "材料中暂未抽出可引用的风险因素。",
        count=3,
        used_ids=used_ids,
    )
    governance_fact = _facts(
        _merge_unique(governance, related_party, disclosure_view),
        KEYWORDS["governance"],
        "材料中暂未抽出可引用的治理或关联交易信息。",
        count=2,
        used_ids=used_ids,
    )
    disclosure_signal = _facts(
        disclosure_view,
        KEYWORDS["disclosure_gap"] + KEYWORDS["channel"],
        "当前证据包未直接抽出渠道缺口或披露空白；这一项保留为后续核查任务。",
        count=2,
        used_ids=used_ids,
    )
    reader_evidence = _facts(
        reader_view,
        KEYWORDS["product"] + KEYWORDS["customer"] + KEYWORDS["financial"] + KEYWORDS["risk"],
        "材料中暂未抽出足够支撑读者分层结论的证据。",
        count=3,
    )

    lines = [
        _report_title(company_name),
        "",
        (
            "这份招股书的读法，可以从一个第一信号进入。第一信号指产品表现、"
            "渠道动作、增长叙事或披露空白中出现的不协调现象；它会把问题收束为："
            "业务目标需要哪些能力，招股书披露的资源是否支撑这些能力。"
            f"{identity}"
        ),
        "",
        f"## 一、{_view_title('signal_and_question', '现象入口与核心问题')}",
        "",
        (
            "先把阅读对象压缩成一个可验证问题。"
            f"{identity} "
            "这条主营业务线索决定了后续阅读顺序：先看产品进入哪些真实场景，再看"
            "这些场景需要哪些技术、渠道、供应链、服务和组织能力。"
        ),
        "",
        (
            "产品和场景提供第一组证据。"
            f"{product} "
            "产品描述的价值在于限定能力要求；一个产品越依赖持续运营、客户适配和"
            "售后服务，越需要继续检查团队经验、研发投入和渠道质量。"
        ),
        "",
        (
            "行业趋势只能提供问题入口。"
            f"{industry} "
            "趋势成立会放大研究价值，传导到单家公司仍然需要产品可信度、客户验证、"
            "费用效率和交付稳定性共同支撑。"
        ),
        "",
        f"## 二、{_view_title('business_capability_chain', '业务、能力与资源匹配')}",
        "",
        (
            "能力链的核心是把产品目标追到资源配置。"
            f"{technology} {talent} "
            "研发、人员和技术名称只有进入产品、客户和交付环节后，才会变成可验证的"
            "竞争力。"
        ),
        "",
        (
            "客户和渠道负责验证能力是否落地。"
            f"{channel_customer} "
            "客户名单、销售模式和渠道结构能够说明产品是否被真实采用，也会影响账期、"
            "回款、议价能力和收入质量。"
        ),
        "",
        (
            "财务数据说明能力链消耗了多少资源。"
            f"{revenue} {cashflow} "
            "收入增长需要和费用、现金流、应收账款、存货一起读，原因是增长会占用资金、"
            "组织和交付资源。"
        ),
        "",
        (
            "募投项目体现管理层想补足的能力。"
            f"{proceeds_fact} "
            "募投方向和主营业务连接越清晰，越值得继续跟踪项目建设、研发成果转化和"
            "收入承接。"
        ),
        "",
        f"## 三、{_view_title('disclosure_gap_and_risk', '披露空白与风险约束')}",
        "",
        (
            "风险因素决定结论强度。"
            f"{risk} "
            "风险的读法是追问它影响哪一段能力链：产品可靠性、客户关系、供应链、"
            "现金流、费用效率或治理稳定性。"
        ),
        "",
        (
            "披露空白也有阅读价值。"
            f"{disclosure_signal} "
            "重要渠道、平台、客户或产品线缺席时，安全写法是把它标记为核查任务，"
            "再用公告、店铺数据、产品评价或行业资料补证。"
        ),
        "",
        (
            "治理和关联交易提供另一组边界。"
            f"{governance_fact} "
            "这类信息会影响利益分配、内部控制和长期经营稳定性，也会限制单纯从"
            "产品或行业趋势推出强结论。"
        ),
        "",
        f"## 四、{_view_title('reader_action_map', '不同读者的可用结论')}",
        "",
        (
            "同一份招股书，对不同读者的价值来自同一组证据的再翻译。"
            f"{reader_evidence} "
            "投资人关注增长叙事能否被现金流和风险承接；行业从业者关注渠道、客户、"
            "费用和产品数据；技术或产品人关注能力缺口和组织储备；消费者关注产品"
            "可信度和交付风险。"
        ),
        "",
        (
            f"对 {company_name} 的阶段性结论是：先用第一信号提出问题，再用主营业务、"
            "产品场景、能力储备、客户渠道、财务质量、募投方向和风险因素逐层核查。"
            "这条链路能保留招股书的证据边界，也能把阅读结果转化为继续研究、业务"
            "参照、职业判断和产品判断。"
        ),
        "",
    ]
    return lines


def generate_report(
    company_name: str,
    packet: EvidencePacket,
    report_inputs: dict[str, Any] | None = None,
) -> str:
    grouped = _group_items(packet)
    item_index = _index_items(packet)
    for group in _section_groups_from_inputs(report_inputs):
        section_key = group.get("section_key")
        if isinstance(section_key, str):
            grouped[section_key] = _items_for_input_group(group, item_index)

    lines = _report_body(company_name, grouped, report_inputs, item_index)
    return "\n".join(lines) + "\n"
