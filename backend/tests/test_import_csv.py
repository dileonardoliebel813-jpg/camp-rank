from app.ingestion.import_service import import_from_csv_folder
from app.models.product import Product, ProductPrice
from app.models.review import Comment


def test_import_from_csv_folder(tmp_path, db_session):
    (tmp_path / "canonical_products.csv").write_text(
        "external_group_id,normalized_name,brand,model_name,capacity,use_case,main_image_url,source\n"
        "csv-group-1,CSV Tent 1,CSVBrand,Model 1,2 person,newbie,,test\n",
        encoding="utf-8",
    )
    (tmp_path / "platform_products.csv").write_text(
        "external_group_id,platform,platform_product_id,title,shop_name,shop_type,product_url,image_url,sales_volume,rating_count,positive_rate\n"
        "csv-group-1,JD,CSV-JD-1,CSV Tent JD,CSV Shop,official,,,10,5,96\n",
        encoding="utf-8",
    )
    (tmp_path / "product_prices.csv").write_text(
        "platform_product_id,original_price,current_price,shop_coupon_amount,platform_coupon_amount,member_coupon_amount,limited_coupon_amount,red_packet_amount,discount_amount,shipping_fee,coupon_text,promotion_text,price_update_time\n"
        "CSV-JD-1,399,359,20,10,0,0,0,0,0,store coupon,,2026-04-20\n",
        encoding="utf-8",
    )
    (tmp_path / "comments.csv").write_text(
        "platform_product_id,platform,comment_text,rating,comment_type,has_image,is_follow_up,comment_time,seller_reply\n"
        "CSV-JD-1,JD,CSV import comment with actual setup details,4.5,positive,true,false,2026-04-21,\n",
        encoding="utf-8",
    )

    report = import_from_csv_folder(db_session, str(tmp_path), source_name="test_csv")

    assert report.imported_platform_products == 1
    assert db_session.query(Product).filter(Product.platform_product_id == "CSV-JD-1").first()
    assert db_session.query(ProductPrice).filter(ProductPrice.current_price == 359).first()
    assert db_session.query(Comment).filter(Comment.comment_text.contains("CSV import")).first()

