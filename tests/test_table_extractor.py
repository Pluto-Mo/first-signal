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


def test_extract_tables_normalizes_negative_page_number_to_one():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "异常页码表",
                "page_number": -1,
                "columns": ["项目"],
                "rows": [["收入"]],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].page_number == 1


def test_extract_tables_normalizes_zero_page_number_to_one():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "零页码表",
                "page_number": 0,
                "columns": ["项目"],
                "rows": [["收入"]],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].page_number == 1


def test_extract_tables_normalizes_bad_page_number_to_one():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "坏页码表",
                "page_number": "bad",
                "columns": ["项目"],
                "rows": [["收入"]],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].page_number == 1


def test_extract_tables_uses_fallback_title_and_medium_quality_without_title():
    tables = extract_tables(
        raw_tables=[
            {
                "columns": ["项目"],
                "rows": [["收入"]],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].title == "未命名表格 1"
    assert tables[0].quality_score == 0.75


def test_extract_tables_scores_low_quality_when_rows_missing():
    tables = extract_tables(
        raw_tables=[
            {
                "title": "缺少行数据表",
                "columns": ["项目"],
            }
        ],
        source_file="测试股份有限公司招股说明书.pdf",
        section_path=["业务和技术"],
    )

    assert tables[0].quality_score == 0.4
