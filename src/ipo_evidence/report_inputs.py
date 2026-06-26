from __future__ import annotations

VIEW_TEMPLATES = {
    "company_and_industry": {
        "title": "公司介绍与行业概况",
        "prompt_slot": "company_and_industry",
        "focus_points": ["主营业务", "产品体系", "商业模式", "行业规模", "产业链位置", "增长驱动"],
        "constraints": ["事实必须来自 evidence_refs", "优先使用行业规模、格局、产业链和咨询机构证据"],
        "output_order": 1,
        "token_budget": 2200,
        "source_sections": {"about_company", "business_and_product", "financials", "use_of_proceeds"},
    },
    "personal_investment": {
        "title": "个人投资视角",
        "prompt_slot": "personal_investment",
        "focus_points": ["产品可信度", "研发投入", "销售费用", "增长质量", "客户结构", "现金流风险"],
        "constraints": ["可以写日常判断，但事实必须可 citation", "不写估值和荐股结论", "没有外部风评证据时不编造外部评价"],
        "output_order": 2,
        "token_budget": 2200,
        "source_sections": {"business_and_product", "financials", "use_of_proceeds", "risks", "governance"},
    },
    "cognitive_worldview": {
        "title": "认知世界的方式",
        "prompt_slot": "cognitive_worldview",
        "focus_points": ["如何拆解行业", "企业如何证明竞争力", "产品渠道研发客户风险如何互相影响", "证据如何限制判断"],
        "constraints": ["写认知收获，不写系统评估", "所有例子必须能回到 evidence_refs"],
        "output_order": 3,
        "token_budget": 2200,
        "source_sections": {"about_company", "business_and_product", "financials", "use_of_proceeds", "risks"},
    },
}


def _build_evidence_ref(evidence_id: str, section_path: list[str], rank: int) -> dict:
    return {
        "evidence_id": evidence_id,
        "role": "primary" if rank == 1 else "supporting",
        "rank": rank,
        "label": section_path[-1] if section_path else None,
    }


def build_report_inputs(doc_id: str, company_name: str, packet) -> dict:
    section_groups: list[dict] = []
    for section_key, template in VIEW_TEMPLATES.items():
        refs = []
        for item in packet.items:
            if item.canonical_section not in template["source_sections"]:
                continue
            refs.append(
                _build_evidence_ref(item.evidence_id, item.section_path, len(refs) + 1)
            )
        section_groups.append(
            {
                "section_key": section_key,
                "title": template["title"],
                "prompt_slot": template["prompt_slot"],
                "focus_points": template["focus_points"],
                "constraints": template["constraints"],
                "output_order": template["output_order"],
                "token_budget": template["token_budget"],
                "evidence_refs": refs,
            }
        )

    return {
        "doc_id": doc_id,
        "company_name": company_name,
        "outline": [group["section_key"] for group in section_groups],
        "section_groups": section_groups,
    }
