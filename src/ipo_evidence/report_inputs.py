from __future__ import annotations

SECTION_TEMPLATES = {
    "about_company": {
        "title": "关于公司",
        "prompt_slot": "about_company",
        "focus_points": ["公司定位", "产品与服务体系", "核心能力"],
        "constraints": ["仅使用 evidence_refs 对应证据", "避免复述目录式句子"],
        "output_order": 1,
        "token_budget": 1200,
    },
    "business_and_product": {
        "title": "业务与产品",
        "prompt_slot": "business_and_product",
        "focus_points": ["业务结构", "主要产品", "客户与场景"],
        "constraints": ["优先使用正文事实和高质量表格", "避免空泛定义"],
        "output_order": 2,
        "token_budget": 1600,
    },
    "financials": {
        "title": "财务与经营数据",
        "prompt_slot": "financials",
        "focus_points": ["收入利润", "现金流", "关键财务变化"],
        "constraints": ["保留关键数值关系", "没有来源定位的判断不得写入"],
        "output_order": 3,
        "token_budget": 1600,
    },
    "risks": {
        "title": "风险因素",
        "prompt_slot": "risks",
        "focus_points": ["核心风险", "风险触发条件", "影响路径"],
        "constraints": ["聚焦高相关风险", "避免把普通经营描述写成风险"],
        "output_order": 4,
        "token_budget": 1200,
    },
    "use_of_proceeds": {
        "title": "募集资金用途",
        "prompt_slot": "use_of_proceeds",
        "focus_points": ["募投方向", "可行性", "与主业关系"],
        "constraints": ["优先使用募投章节证据", "避免泛化成公司愿景"],
        "output_order": 5,
        "token_budget": 1200,
    },
}

DEFAULT_TEMPLATE = {
    "title": "待分析章节",
    "prompt_slot": "general_section",
    "focus_points": ["章节要点"],
    "constraints": ["仅使用 evidence_refs 对应证据"],
    "output_order": 99,
}


def _build_evidence_ref(evidence_id: str, section_path: list[str], rank: int) -> dict:
    return {
        "evidence_id": evidence_id,
        "role": "primary" if rank == 1 else "supporting",
        "rank": rank,
        "label": section_path[-1] if section_path else None,
    }


def build_report_inputs(doc_id: str, company_name: str, packet) -> dict:
    grouped: dict[str, dict] = {}
    ordered_keys: list[str] = []

    for item in packet.items:
        section_key = item.canonical_section
        if section_key not in grouped:
            template = SECTION_TEMPLATES.get(section_key, DEFAULT_TEMPLATE)
            grouped[section_key] = {
                "section_key": section_key,
                "title": template["title"],
                "prompt_slot": template["prompt_slot"],
                "focus_points": template["focus_points"],
                "constraints": template["constraints"],
                "output_order": template["output_order"],
                **({"token_budget": template["token_budget"]} if "token_budget" in template else {}),
                "evidence_refs": [],
            }
            ordered_keys.append(section_key)

        rank = len(grouped[section_key]["evidence_refs"]) + 1
        grouped[section_key]["evidence_refs"].append(
            _build_evidence_ref(item.evidence_id, item.section_path, rank)
        )

    section_groups = [grouped[key] for key in ordered_keys]
    return {
        "doc_id": doc_id,
        "company_name": company_name,
        "outline": ordered_keys,
        "section_groups": section_groups,
    }
