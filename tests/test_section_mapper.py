from ipo_evidence.models import Block
from ipo_evidence.section_mapper import (
    assign_section_paths,
    build_source_ast,
    map_canonical_sections,
)


def test_build_source_ast_detects_a_share_headings():
    blocks = [
        Block(block_id="B-000001", page_number=1, text="## 第一节 发行人基本情况"),
        Block(block_id="B-000002", page_number=2, text="公司主要从事智能硬件产品。"),
        Block(block_id="B-000003", page_number=3, text="## 第二节 业务和技术"),
    ]

    ast = build_source_ast(blocks)

    assert [node.title for node in ast] == ["发行人基本情况", "业务和技术"]
    assert ast[0].block_ids == ["B-000001", "B-000002"]


def test_map_canonical_sections_maps_business_section():
    ast = build_source_ast(
        [
            Block(block_id="B-000001", page_number=1, text="## 第二节 业务和技术"),
            Block(block_id="B-000002", page_number=2, text="公司的主要产品包括智能控制器。"),
        ]
    )

    canonical = map_canonical_sections(ast)

    assert canonical["business_and_product"]["title"] == "业务与产品"
    assert canonical["business_and_product"]["source_sections"] == ["业务和技术"]


def test_build_source_ast_creates_markdown_like_hierarchy_from_chinese_levels():
    blocks = [
        Block(block_id="B-000001", page_number=1, text="# 第四节 发行人基本情况"),
        Block(block_id="B-000002", page_number=1, text="## 一、发行人基本情况"),
        Block(block_id="B-000003", page_number=1, text="### （一）公司设立情况"),
        Block(block_id="B-000004", page_number=1, text="公司系整体变更设立。"),
    ]

    ast = build_source_ast(blocks)

    assert [node.title for node in ast] == ["发行人基本情况", "发行人基本情况", "公司设立情况"]
    assert [node.level for node in ast] == [1, 2, 3]
    assert ast[2].section_path == ["发行人基本情况", "发行人基本情况", "公司设立情况"]


def test_assign_section_paths_uses_latest_heading_hierarchy():
    blocks = [
        Block(block_id="B-000001", page_number=1, text="# 第五节 业务与技术"),
        Block(block_id="B-000002", page_number=1, text="## 一、公司的主营业务、主要产品或服务情况"),
        Block(block_id="B-000003", page_number=1, text="### （三）主要产品或服务情况"),
        Block(block_id="B-000004", page_number=1, text="公司主要产品包括智能吸顶麦和办公本。"),
    ]

    assigned = assign_section_paths(blocks)

    assert assigned[3].section_path == [
        "业务与技术",
        "公司的主营业务、主要产品或服务情况",
        "主要产品或服务情况",
    ]


def test_build_source_ast_supports_numeric_heading_hierarchy():
    blocks = [
        Block(block_id="B-000001", page_number=1, text="# 第六节 财务会计信息"),
        Block(block_id="B-000002", page_number=1, text="## 1.1 主要会计数据"),
        Block(block_id="B-000003", page_number=1, text="公司最近三年营业收入持续增长。"),
    ]

    ast = build_source_ast(blocks)

    assert [node.title for node in ast] == ["财务会计信息", "主要会计数据"]
    assert [node.level for node in ast] == [1, 2]
    assert ast[1].section_path == ["财务会计信息", "主要会计数据"]
