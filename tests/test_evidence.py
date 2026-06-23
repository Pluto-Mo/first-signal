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


def test_build_evidence_packet_excludes_directory_and_heading_only_blocks():
    blocks = [
        Block(
            block_id="B-000001",
            page_number=1,
            text="第四节 发行人基本情况 ..... 39  第五节 业务与技术 ..... 121",
            section_path=["目录"],
        ),
        Block(
            block_id="B-000002",
            page_number=2,
            text="## 一、公司的主营业务、主要产品或服务情况",
            section_path=["业务与技术", "公司的主营业务、主要产品或服务情况"],
        ),
        Block(
            block_id="B-000003",
            page_number=3,
            text="报告期内，公司经销模式销售的主要产品为 AI 芯片及智慧办公领域的 AI 硬件产品。",
            section_path=["业务与技术", "公司的主营业务、主要产品或服务情况", "主要产品或服务情况"],
        ),
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=[],
    )

    assert len(packet.items) == 1
    assert packet.items[0].block_id == "B-000003"


def test_build_evidence_packet_excludes_html_table_blocks_and_non_body_sections():
    blocks = [
        Block(
            block_id="B-000010",
            page_number=1,
            text="本公司的发行申请尚需经上海证券交易所和中国证监会履行相应程序。投资者应当以正式公告的招股说明书作为投资决定的依据。",
            section_path=["首次公开发行股票并在科创板上市 招股说明书 （申报稿）", "发行人声明"],
        ),
        Block(
            block_id="B-000056",
            page_number=4,
            text="<table border=1><tr><td>比亚迪汽车</td><td>指</td><td>公司客户，包括西安比亚迪电子有限公司集贤分公司</td></tr></table>",
            section_path=["释义", "专业术语"],
        ),
        Block(
            block_id="B-002717",
            page_number=77,
            text="<table border=1><tr><td>293</td><td>思必驰</td><td>报告期内该专利对应产品收入增长</td></tr></table>",
            section_path=["附件", "附件二：发行人及其子公司拥有的专利"],
        ),
        Block(
            block_id="B-000200",
            page_number=12,
            text="报告期内，公司收入规模持续增长，同时毛利率保持较高水平。",
            section_path=["风险因素", "与发行人相关的风险", "公司存在累计未弥补亏损及持续亏损的风险"],
        ),
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=[],
    )

    assert len(packet.items) == 1
    assert packet.items[0].block_id == "B-000200"


def test_build_evidence_packet_excludes_low_signal_reference_sentences():
    blocks = [
        Block(
            block_id="B-000300",
            page_number=20,
            text="主要客户参见本招股说明书“第五节 业务与技术”之“三、公司销售情况和主要客户”。",
            section_path=["业务与技术", "公司销售情况和主要客户"],
        ),
        Block(
            block_id="B-000301",
            page_number=20,
            text="报告期内，公司主要客户包括比亚迪、上汽集团、梅赛德斯-奔驰等头部企业。",
            section_path=["业务与技术", "公司销售情况和主要客户"],
        ),
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=[],
    )

    assert len(packet.items) == 1
    assert packet.items[0].block_id == "B-000301"


def test_build_evidence_packet_keeps_high_information_text_without_numbers():
    blocks = [
        Block(
            block_id="B-000400",
            page_number=30,
            text="公司构建了覆盖软件、芯片、模组和终端的产品服务体系，并已在智慧出行、智慧办公和智慧物联领域实现规模化应用。",
            section_path=["业务与技术", "公司的主营业务、主要产品或服务情况"],
        )
    ]

    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=blocks,
        tables=[],
    )

    assert len(packet.items) == 1
    assert packet.items[0].block_id == "B-000400"


def test_build_evidence_packet_excludes_low_quality_tables():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[
            TableObject(
                table_id="T-002",
                title="低质量表格",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                section_path=["业务和技术"],
                columns=["产品", "收入"],
                rows=[["智能控制器", "12000万元"]],
                quality_score=0.7,
            )
        ],
    )

    assert packet.items == []


def test_build_evidence_packet_excludes_tables_without_fields():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[
            TableObject(
                table_id="T-003",
                title="空字段表格",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=5,
                section_path=["业务和技术"],
                columns=[],
                rows=[[]],
                quality_score=0.9,
            )
        ],
    )

    assert packet.items == []


def test_build_evidence_packet_uses_section_fallback_for_table_sources():
    packet = build_evidence_packet(
        doc_id="doc_test",
        source_file="测试股份有限公司招股说明书.pdf",
        blocks=[],
        tables=[
            TableObject(
                table_id="T-004",
                title="产品收入结构表",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=6,
                section_path=[],
                columns=["产品", "2023年收入"],
                rows=[["智能控制器", "12000万元"]],
                quality_score=0.9,
            )
        ],
    )

    assert packet.items[0].section_path == ["未识别章节"]
