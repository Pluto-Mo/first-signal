from ipo_evidence.models import EvidenceItem, EvidencePacket, QualityStatus
from ipo_evidence.report_generator import generate_report


def _text_item(
    evidence_id: str,
    canonical_section: str,
    text: str,
    page_number: int,
    section_path: list[str],
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        canonical_section=canonical_section,
        claim_summary=text,
        source_type="text_quote",
        source_file="测试股份有限公司招股说明书.pdf",
        page_number=page_number,
        block_id=f"B-{page_number:06d}",
        section_path=section_path,
        quote=text,
        quality_status=QualityStatus.safe_to_use,
    )


def test_generate_report_uses_configured_views_without_company_specific_copy():
    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            _text_item(
                "E-001",
                "about_company",
                "公司主要从事智能硬件产品的研发、生产和销售，主营业务覆盖消费电子领域。",
                2,
                ["发行人基本情况"],
            ),
            _text_item(
                "E-002",
                "business_and_product",
                "主要产品包括存储设备、连接设备和充电设备，应用场景覆盖办公和家庭。",
                12,
                ["业务与技术", "主要产品或服务情况"],
            ),
            _text_item(
                "E-003",
                "financials",
                "报告期内，公司营业收入保持增长，销售费用和研发费用同步增加。",
                88,
                ["管理层讨论与分析"],
            ),
            _text_item(
                "E-004",
                "risks",
                "公司存在客户集中、市场竞争加剧及经营现金流波动风险。",
                122,
                ["风险因素"],
            ),
        ],
    )

    report = generate_report("测试股份有限公司", packet)

    assert "# 测试股份有限公司招股书长篇阅读" in report
    assert "公司介绍与行业概况" in report
    assert "个人投资视角" in report
    assert "认知世界的方式" in report
    assert "思必驰" not in report
    assert "AI 赛道" not in report
    assert "[C-001]" in report
