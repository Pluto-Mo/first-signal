from ipo_evidence.table_extractor import extract_tables


def test_extract_tables_normalizes_raw_tables():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "产品收入结构表",
                "page_number": 3,
                "columns": ["产品", "2023年收入", "占比"],
                "rows": [["智能控制器", "12000万元", "45.2%"]],
                "notes": [],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].table_id == "T-001"
    assert tables[0].quality_score == 0.9
    assert tables[0].columns == ["产品", "2023年收入", "占比"]
