from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block, QualityStatus, TableObject


def test_build_evidence_packet_uses_text_and_table_sources():
    blocks = [
        Block(
            block_id="B-000002",
            page_number=2,
            text="公司主要从事智能硬件产品的研发、生产和销售。",
            section_path=["发行人基本情况"],
        )
    ]
    tables = [
        TableObject(
            table_id="T-001",
            title="产品收入结构表",
            source_file="测试股份有限公司招股说明书.pdf",
            page_number=3,
            section_path=["业务和技术"],
            columns=["产品", "2023年收入", "占比"],
            rows=[["智能控制器", "12000万元", "45.2%"]],
            quality_score=0.9,
        )
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=tables,
    )

    assert len(packet.items) == 2
    assert packet.items[0].quality_status == QualityStatus.safe_to_use
    assert packet.items[1].table_id == "T-001"
