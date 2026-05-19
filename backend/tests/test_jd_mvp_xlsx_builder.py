from pathlib import Path

from scripts import build_jd_mvp_from_xlsx as builder


def test_same_cell_reference_in_shop_name_and_after_sale_is_resolved(monkeypatch):
    headers = [
        "SKU",
        "pid",
        "wareAttribute",
        "商家回复",
        "图片地址",
        "图片数量",
        "得分类型",
        "昵称",
        "点赞数",
        "视频地址",
        "视频数量",
        "评论id",
        "评论内容",
        "评论得分",
        "评论数",
        "评论时间",
        "购买次数",
        "追评",
        "追评时间",
        "当前价格",
        "商品链接",
        "",
        "",
        "",
        "售后服务",
        "店铺名称",
    ]
    full_name = "探险者（TAN XIAN ZHE）帐篷户外露营防雨过夜3人-4人速开便捷天幕二合一黑胶防晒帐篷"
    after_sale = "支持7天无理由退货，退换货可享免费上门取件"
    workbook_rows = [
        headers,
        ["已购A", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c1", "很好", 5, 1, "2026-01-01", 1, "", "", 168, "https://item.jd.com/1001.html", "", "", "", after_sale, full_name],
        ["已购B", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c2", "不错", 5, 1, "2026-01-02", 1, "", "", 168, "https://item.jd.com/1001.html", "", "", "", "同Y2", "同Z2"],
    ]
    monkeypatch.setattr(builder, "_load_workbook_rows", lambda _path, _sheet: workbook_rows)

    rows = builder._load_rows(Path("unused.xlsx"), "data")

    assert rows[0]["shop_name"] == full_name
    assert rows[1]["shop_name"] == full_name
    assert rows[0]["after_sale"] == after_sale
    assert rows[1]["after_sale"] == after_sale


def test_same_cell_reference_supports_chained_reference():
    full_name = "探险者完整名称"
    workbook_rows = [
        [""] * 26,
        [""] * 25 + [full_name],
        [""] * 25 + ["同Z2"],
    ]

    assert builder._resolve_same_cell_reference("同Z3", workbook_rows) == full_name


def test_title_falls_back_to_shop_name_when_product_name_is_missing(monkeypatch):
    headers = [
        "SKU",
        "pid",
        "wareAttribute",
        "商家回复",
        "图片地址",
        "图片数量",
        "得分类型",
        "昵称",
        "点赞数",
        "视频地址",
        "视频数量",
        "评论id",
        "评论内容",
        "评论得分",
        "评论数",
        "评论时间",
        "购买次数",
        "追评",
        "追评时间",
        "当前价格",
        "商品链接",
        "",
        "",
        "",
        "售后服务",
        "店铺名称",
    ]
    shop_name = "真实商品显示名"
    workbook_rows = [
        headers,
        ["已购A", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c1", "很好", 5, 1, "2026-01-01", 1, "", "", 168, "https://item.jd.com/1001.html", "", "", "", "同Y2", shop_name],
    ]
    monkeypatch.setattr(builder, "_load_workbook_rows", lambda _path, _sheet: workbook_rows)

    payload = builder.build_payload(Path("unused.xlsx"), "data")

    assert payload["canonical_products"][0]["normalized_name"] == shop_name
    assert payload["platform_products"][0]["title"] == shop_name


def test_products_with_same_price_are_grouped_by_product_url(monkeypatch):
    headers = [
        "SKU",
        "pid",
        "wareAttribute",
        "商家回复",
        "图片地址",
        "图片数量",
        "得分类型",
        "昵称",
        "点赞数",
        "视频地址",
        "视频数量",
        "评论id",
        "评论内容",
        "评论得分",
        "评论数",
        "评论时间",
        "购买次数",
        "追评",
        "追评时间",
        "当前价格",
        "商品链接",
        "",
        "",
        "",
        "售后服务",
        "店铺名称",
    ]
    workbook_rows = [
        headers,
        ["已购A", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c1", "很好", 5, 1, "2026-01-01", 1, "", "", 229, "https://item.jd.com/1001.html", "", "", "", "支持7天无理由", "商品A"],
        ["已购B", "2001", "", "", "", 0, "好评", "", 0, "", 0, "c2", "不错", 5, 1, "2026-01-02", 1, "", "", 229, "https://item.jd.com/2001.html", "", "", "", "支持7天无理由", "商品B"],
    ]
    monkeypatch.setattr(builder, "_load_workbook_rows", lambda _path, _sheet: workbook_rows)

    payload = builder.build_payload(Path("unused.xlsx"), "data")

    assert len(payload["platform_products"]) == 2
    assert {item["title"] for item in payload["platform_products"]} == {"商品A", "商品B"}


def test_self_referential_same_cell_shop_name_uses_previous_value(monkeypatch):
    headers = [
        "SKU",
        "pid",
        "wareAttribute",
        "商家回复",
        "图片地址",
        "图片数量",
        "得分类型",
        "昵称",
        "点赞数",
        "视频地址",
        "视频数量",
        "评论id",
        "评论内容",
        "评论得分",
        "评论数",
        "评论时间",
        "购买次数",
        "追评",
        "追评时间",
        "当前价格",
        "商品链接",
        "",
        "",
        "",
        "售后服务",
        "店铺名称",
    ]
    workbook_rows = [
        headers,
        ["已购A", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c1", "很好", 5, 1, "2026-01-01", 1, "", "", 229, "https://item.jd.com/1001.html", "", "", "", "支持7天无理由", "真实商品名"],
        ["已购B", "1002", "", "", "", 0, "好评", "", 0, "", 0, "c2", "不错", 5, 1, "2026-01-02", 1, "", "", 229, "https://item.jd.com/1001.html", "", "", "", "同Y3", "同Z3"],
    ]
    monkeypatch.setattr(builder, "_load_workbook_rows", lambda _path, _sheet: workbook_rows)

    rows = builder._load_rows(Path("unused.xlsx"), "data")
    payload = builder.build_payload(Path("unused.xlsx"), "data")

    assert rows[1]["shop_name"] == "真实商品名"
    assert rows[1]["after_sale"] == "支持7天无理由"
    assert payload["platform_products"][0]["title"] == "真实商品名"


def test_same_product_name_groups_multiple_variant_urls(monkeypatch):
    headers = [
        "SKU",
        "pid",
        "wareAttribute",
        "商家回复",
        "图片地址",
        "图片数量",
        "得分类型",
        "昵称",
        "点赞数",
        "视频地址",
        "视频数量",
        "评论id",
        "评论内容",
        "评论得分",
        "评论数",
        "评论时间",
        "购买次数",
        "追评",
        "追评时间",
        "当前价格",
        "商品链接",
        "",
        "",
        "",
        "售后服务",
        "店铺名称",
    ]
    workbook_rows = [
        headers,
        ["已购A", "1001", "", "", "", 0, "好评", "", 0, "", 0, "c1", "很好", 5, 1, "2026-01-01", 1, "", "", 221, "https://item.jd.com/1001.html", "", "", "", "支持7天无理由", "同一个商品"],
        ["已购B", "1002", "", "", "", 0, "好评", "", 0, "", 0, "c2", "不错", 5, 1, "2026-01-02", 1, "", "", 221, "https://item.jd.com/1002.html", "", "", "", "支持7天无理由", "同一个商品"],
    ]
    monkeypatch.setattr(builder, "_load_workbook_rows", lambda _path, _sheet: workbook_rows)

    payload = builder.build_payload(Path("unused.xlsx"), "data")

    assert len(payload["platform_products"]) == 1
    assert payload["platform_products"][0]["rating_count"] == 2
