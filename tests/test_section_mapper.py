from ipo_evidence.models import Block
from ipo_evidence.section_mapper import build_source_ast, map_canonical_sections


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
