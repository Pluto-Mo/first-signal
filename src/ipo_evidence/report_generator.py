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
    "identity": ["国内领先", "专注", "主营业务", "对话式", "端侧", "智能终端", "全栈"],
    "product": ["产品", "智慧出行", "智慧办公", "智慧物联", "AI软件", "AI硬件", "交付模式"],
    "scenario": ["上车", "车载", "智能吸顶麦", "会议", "教育", "智能家居", "机器人", "穿戴"],
    "industry": ["市场规模", "年均复合增长率", "灼识咨询", "产业链", "市占率", "行业", "竞争"],
    "technology": ["研发", "算法", "模型", "大模型", "芯片", "核心技术", "智能体", "端侧算法"],
    "financial": ["营业收入", "收入", "毛利率", "利润", "亏损", "现金流", "研发费用", "报告期"],
    "customer": ["客户", "前五", "比亚迪", "奔驰", "华为", "阿里", "美的", "科沃斯", "销售比例"],
    "proceeds": ["募集资金", "募投", "投资项目", "研发升级", "DUI中台", "资金运用"],
    "risk": ["风险", "亏损", "现金流量净额", "应收账款", "存货", "价格上涨", "坏账", "不利影响", "供应商"],
    "governance": ["治理", "董事会", "股东", "控制", "承诺", "内控", "关联交易"],
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
    "平台运营与销售",
    "董事、监事/",
    "主营业务成本",
    "合并利润表",
    "主要财务指标显示：覆盖项目",
    "按2024 年度高于",
]

BROKEN_ENDINGS = ("在", "提", "所处", "境外", "销售", "客户", "和", "及", "以及", "、")


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
    return "；".join(f"{key}：{value}" for key, value in fields.items())


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

        first = item.fields.get("第一项")
        second = item.fields.get("第二项")
        gap = item.fields.get("差额")
        metric = item.fields.get("比较指标")
        if first and second and gap and metric:
            return f"{first}按{metric}高于{second}，差额为 {_readable_value(gap)}。[{citation_id}]"

        return f"{item.table_title or '产品收入结构表'}显示：{_format_fields(item.fields)}。[{citation_id}]"
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


def _rank_value(ref: dict[str, Any]) -> int:
    rank = ref.get("rank", 99)
    if type(rank) is int and rank >= 0:
        return rank
    return 99


def _items_for_input_group(
    group: dict[str, Any],
    item_index: dict[str, tuple[int, EvidenceItem]],
) -> list[tuple[int, EvidenceItem]]:
    refs = group.get("evidence_refs", [])
    if not isinstance(refs, list):
        return []
    items: list[tuple[int, EvidenceItem]] = []
    seen_evidence_ids: set[str] = set()
    for ref in sorted(refs, key=lambda ref: _rank_value(ref) if isinstance(ref, dict) else 99):
        if not isinstance(ref, dict):
            continue
        evidence_id = ref.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id in item_index:
            if evidence_id in seen_evidence_ids:
                continue
            seen_evidence_ids.add(evidence_id)
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


def _score(item: EvidenceItem, keywords: list[str]) -> int:
    text = item.claim_summary + " " + (item.quote or "") + " " + " ".join(item.section_path)
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
        key=lambda pair: (-_score(pair[1], keywords), abs(len(pair[1].claim_summary) - 120), pair[0]),
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
    about = grouped.get("about_company", [])
    business = grouped.get("business_and_product", [])
    financials = grouped.get("financials", [])
    proceeds = grouped.get("use_of_proceeds", [])
    risks = grouped.get("risks", [])
    governance = grouped.get("governance", [])
    related_party = grouped.get("related_party", [])

    input_groups = _input_group_map(report_inputs)
    company_view = _merge_unique(
        _items_for_input_group(input_groups.get("company_and_industry", {}), item_index),
        about,
        business,
        financials,
    )
    investment_view = _merge_unique(
        _items_for_input_group(input_groups.get("personal_investment", {}), item_index),
        business,
        financials,
        proceeds,
        risks,
        governance,
    )
    worldview = _merge_unique(
        _items_for_input_group(input_groups.get("cognitive_worldview", {}), item_index),
        about,
        business,
        financials,
        proceeds,
        risks,
    )

    used_ids: set[str] = set()
    identity = _fact(
        _merge_unique(about, business),
        KEYWORDS["identity"] + KEYWORDS["product"],
        "材料中暂未抽出可引用的主营业务描述。",
        used_ids=used_ids,
    )
    product = _facts(
        business,
        KEYWORDS["product"],
        "材料中暂未抽出可引用的产品体系。",
        count=2,
        used_ids=used_ids,
    )
    scenarios = _facts(
        business,
        KEYWORDS["scenario"],
        "材料中暂未抽出可引用的具体应用场景。",
        count=3,
        used_ids=used_ids,
    )
    industry = _facts(
        company_view,
        KEYWORDS["industry"],
        "材料中暂未抽出可引用的行业规模或行业格局。",
        count=3,
        used_ids=used_ids,
    )
    technology = _facts(
        _merge_unique(about, business),
        KEYWORDS["technology"],
        "材料中暂未抽出可引用的技术体系。",
        count=2,
        used_ids=used_ids,
    )
    personal_product = _facts(
        _text_only(business),
        KEYWORDS["scenario"] + ["自主品牌", "客户", "海外", "量产车型", "头部品牌"],
        "材料中暂未抽出可引用的产品落地证据。",
        count=3,
    )
    revenue = _facts(
        _text_only(financials),
        KEYWORDS["financial"],
        "材料中暂未抽出可引用的收入和盈利信息。",
        count=2,
        used_ids=used_ids,
    )
    rd = _facts(
        _merge_unique(financials, about, business),
        ["研发投入", "研发费用", "研发人员", "核心技术", "费用化"],
        "材料中暂未抽出可引用的研发投入。",
        count=2,
        used_ids=used_ids,
    )
    sales = _fact(
        financials,
        ["销售费用率", "销售费用", "同行业可比", "期间费用率", "优化"],
        "材料中暂未抽出可引用的销售费用。",
    )
    customers = _facts(
        _text_only(_merge_unique(business, about, governance)),
        KEYWORDS["customer"],
        "材料中暂未抽出可引用的客户结构。",
        count=2,
        used_ids=used_ids,
    )
    cashflow = _facts(
        _text_only(_merge_unique(risks, financials)),
        ["现金流量净额", "销售回款", "持续为负", "研发投入", "人员支出"],
        "材料中暂未抽出可引用的现金流信息。",
        count=2,
        used_ids=used_ids,
    )
    risk = _facts(
        risks,
        KEYWORDS["risk"],
        "材料中暂未抽出可引用的风险因素。",
        count=3,
        used_ids=used_ids,
    )
    proceeds_fact = _facts(
        proceeds,
        KEYWORDS["proceeds"],
        "材料中暂未抽出可引用的募投方向。",
        count=2,
        used_ids=used_ids,
    )
    governance_fact = _facts(
        _merge_unique(governance, related_party),
        KEYWORDS["governance"],
        "材料中暂未抽出可引用的治理和关联交易材料。",
        count=2,
        used_ids=used_ids,
    )
    worldview_product = _facts(
        _text_only(business),
        KEYWORDS["product"] + KEYWORDS["scenario"] + ["入口", "终端", "场景", "交付"],
        "材料中暂未抽出可引用的产品入口。",
        count=2,
    )
    worldview_competition = _facts(
        _text_only(_merge_unique(business, about)),
        KEYWORDS["technology"] + KEYWORDS["customer"],
        "材料中暂未抽出可引用的竞争力证明。",
        count=3,
    )
    worldview_growth = _facts(
        _text_only(_merge_unique(financials, risks)),
        KEYWORDS["financial"] + ["应收账款", "存货", "资金"],
        "材料中暂未抽出可引用的增长压力。",
        count=3,
    )
    worldview_risk = _facts(
        risks,
        KEYWORDS["risk"],
        "材料中暂未抽出可引用的风险和治理材料。",
        count=3,
    )

    lines = [
        _report_title(company_name),
        "",
        (
            "读这份招股书，最有价值的入口不是先给出一个估值判断，而是把一个“对话式人工智能”公司拆成几个能被验证的问题："
            "它到底卖什么，进入了哪些终端场景，收入增长靠什么支撑，研发投入有没有变成产品壁垒，以及风险是否足以改变前面的叙事。"
            f"{identity}"
        ),
        "",
        f"## 一、{_view_title('company_and_industry', '公司介绍与行业概况')}",
        "",
        (
            "先看业务边界。"
            f"{identity} "
            "这个定位把阅读范围收得很窄：重点不是泛泛讨论大模型，也不是把 AI 当成一个概念标签，而是看对话式 AI、端侧智能和智能终端之间能否形成可交付、可复制、可收费的产品体系。"
        ),
        "",
        (
            "产品体系是理解它的第一把钥匙。"
            f"{product} "
            "这意味着招股书里的“AI”不是单一算法能力，而是软件、芯片、模组、终端和定制交付共同组成的产品网络。读到这里，问题已经从“技术是否先进”转成了“产品是否能进入足够多、足够稳定的真实场景”。"
        ),
        "",
        (
            "这些真实场景主要落在智慧出行、智慧办公和智慧物联。"
            f"{scenarios} "
            "三个场景的商业含义并不相同：车载语音更看重前装导入和整车厂合作，会议办公更接近自主品牌硬件和渠道能力，智能家居、机器人、穿戴设备则考验多品类适配和供应链协同。"
        ),
        "",
        (
            "行业概况部分的高价值信息，在于它给了一个从“技术热词”回到“市场空间”的桥。"
            f"{industry} "
            "这些数据不应该被直接读成乐观结论，但它们说明对话式 AI 的增长不是只发生在聊天机器人里，而是在家居、机器人、车载、办公和其他终端入口里被重新分配。"
        ),
        "",
        (
            "产业链位置也值得单独看。"
            f"{_facts(company_view, ['产业链', '系统级公司', '软硬件适配', '部署实施', '场景化解决方案'], '材料中暂未抽出可引用的产业链定位。', count=2)} "
            "如果一家企业只是提供单点模型能力，它更容易被上游大模型或下游集成商挤压；如果它能把模型、芯片、终端、场景和交付串起来，价值位置就更接近系统级解决方案提供者。"
        ),
        "",
        (
            "技术能力在这里不是孤立装饰，而是商业化的前置条件。"
            f"{technology} "
            "端侧部署、离线可用、低时延、隐私保护、多芯片适配这些能力，只有和客户场景绑定后才有商业意义。换句话说，技术壁垒不是写在技术名词里，而是写在客户迁移成本和交付稳定性里。"
        ),
        "",
        f"## 二、{_view_title('personal_investment', '个人投资视角')}",
        "",
        (
            "从个人投资者或产品使用者的角度，第一件事不是问“AI 赛道能不能涨”，而是问产品是否值得信任。"
            f"{personal_product} "
            "这些证据至少说明产品已经进入汽车、办公、家居、机器人等具体终端，而不是只停留在概念展示。对个人读者来说，这会提高继续研究的价值。"
        ),
        "",
        (
            "第二件事是判断它更像重研发的技术公司，还是重营销的概念公司。"
            f"{rd} {sales} "
            "研发投入高并不自动等于好公司，因为它也会压低利润和现金流；销售费用上升也不自动等于坏事，因为自主品牌产品放量阶段本来需要市场投入。真正要看的，是研发和销售费用最后有没有变成可复用产品、客户粘性和收入质量。"
        ),
        "",
        (
            "收入增长提供了一个正向线索，但这个线索必须和亏损、现金流一起读。"
            f"{revenue} {cashflow} "
            "如果只看收入，会觉得业务正在扩张；如果把经营现金流和亏损放进来，就会看到另一面：增长仍然需要研发、人员和市场投入持续支撑，短期内未必能自然转化为舒服的利润和现金流。"
        ),
        "",
        (
            "客户结构决定了这种增长的含金量。"
            f"{customers} "
            "客户名单能证明产品被真实场景采用，但客户集中度、账期、回款方式和议价能力会影响收入质量。个人读者不需要像机构一样建复杂模型，但至少要形成一个朴素判断：好客户可以证明产品，过度依赖客户也可能反过来限制公司。"
        ),
        "",
        (
            "募投项目可以看作管理层对未来产品路线的押注。"
            f"{proceeds_fact} "
            "如果募投资金继续围绕智慧出行、智慧办公、智慧物联和 DUI 中台展开，它和主营业务的连接是清楚的；但投资者仍要继续追问项目建设期费用、产能消化、研发成果转化和收入承接。"
        ),
        "",
        (
            "个人投资视角下，最需要提前放在桌面上的不是乐观故事，而是风险会怎样改变故事。"
            f"{risk} "
            "这些风险让这份材料不能被读成单纯的 AI 成长叙事。更合理的阶段性判断是：产品和行业线索值得继续跟踪，但盈利质量、现金流改善、客户分散度和研发转化效率还需要后续持续验证。"
        ),
        "",
        f"## 三、{_view_title('cognitive_worldview', '认知世界的方式')}",
        "",
        (
            "这份招股书真正有意思的地方，是它示范了一个行业如何被拆开。第一步不是问“人工智能是不是未来”，而是问技术通过什么入口进入物理世界。"
            f"{worldview_product} "
            "一旦把入口落到车、会议室、教室、家居、机器人和穿戴设备，抽象技术就变成了具体产业问题。"
        ),
        "",
        (
            "第二步，是看企业怎样证明竞争力。"
            f"{worldview_competition} "
            "招股书里的竞争力证明通常不是单一维度：技术要有体系，产品要能交付，客户要能验证，收入要能持续，风险要能解释。任何一个环节单独漂亮，都不足以支撑完整判断。"
        ),
        "",
        (
            "第三步，是把增长和压力放在同一张图里。"
            f"{worldview_growth} "
            "商业世界里，增长常常不是免费的。收入扩大可能伴随存货、应收账款、人员、研发、营销和供应链压力；技术公司尤其如此。读招股书的价值，就是训练自己不要只看增长曲线，也要看增长背后的资金占用和组织成本。"
        ),
        "",
        (
            "第四步，是理解风险不是附录，而是理解商业模式的一部分。"
            f"{worldview_risk} {governance_fact} "
            "风险因素、治理安排和关联交易承诺，不能替代经营事实，但能告诉读者哪些地方最容易出问题：现金流、客户集中、供应链价格、市场竞争、内部控制和利益输送空间。"
        ),
        "",
        (
            "把这套方法迁移到其他公司，可以形成一个很实用的阅读顺序：先找产品入口，再找行业空间，再看客户验证，然后检查收入质量、研发效率、现金流和风险暴露。"
            "这比直接问“是不是好公司”更稳，因为它把一个模糊判断拆成了可以反复回到原文核查的问题。"
        ),
        "",
        (
            "所以，这篇阅读的结论不是一个买卖建议，而是一种更清醒的观察方式："
            "思必驰的材料已经能支撑一条“端侧智能进入多类终端场景”的主线，行业空间、客户场景和研发投入给了继续研究的理由；"
            "亏损、现金流、销售投入、客户结构和竞争压力则提醒读者，这条主线还没有自然变成确定性。"
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
