import json

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import CanonicalProduct, Product
from app.scoring.explanation_generator import generate_platform_explanation
from app.services.spec_analysis_service import build_parameter_analysis
from app.utils.urls import public_product_url


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else [str(value)]
    except json.JSONDecodeError:
        return [tag.strip() for tag in raw.split(",") if tag.strip()]


def list_canonical_products(
    db: Session,
    brand: str | None = None,
    use_case: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    platform: str | None = None,
) -> list[dict]:
    query = db.query(CanonicalProduct).options(
        joinedload(CanonicalProduct.products).joinedload(Product.prices),
        joinedload(CanonicalProduct.products).joinedload(Product.platform_offer_analysis),
        joinedload(CanonicalProduct.product_score),
    )
    if brand:
        query = query.filter(CanonicalProduct.brand == brand)
    if use_case:
        query = query.filter(CanonicalProduct.use_case == use_case)

    results = []
    for canonical in query.all():
        products = canonical.products
        if platform:
            products = [product for product in products if product.platform == platform]
        prices = [price.stable_final_price for product in products for price in product.prices]
        if not prices:
            continue
        if min_price is not None and max(prices) < min_price:
            continue
        if max_price is not None and min(prices) > max_price:
            continue
        recommended = next(
            (p for p in products if p.platform_offer_analysis and p.platform_offer_analysis.is_recommended_platform),
            None,
        )
        lowest = min(products, key=lambda p: p.prices[-1].stable_final_price)
        risk_tags = []
        for product in products:
            if product.platform_offer_analysis:
                risk_tags.extend(parse_tags(product.platform_offer_analysis.warning_tags))
        results.append(
            {
                "id": canonical.id,
                "normalized_name": canonical.normalized_name,
                "brand": canonical.brand,
                "model_name": canonical.model_name,
                "capacity": canonical.capacity,
                "use_case": canonical.use_case,
                "final_score": canonical.product_score.final_score if canonical.product_score else None,
                "data_confidence_score": canonical.data_confidence_score,
                "min_stable_final_price": min(prices),
                "max_stable_final_price": max(prices),
                "recommended_platform": recommended.platform if recommended else None,
                "lowest_price_platform": lowest.platform if lowest else None,
                "main_risk_tags": sorted(set(risk_tags))[:5],
            }
        )
    return results


def get_product_detail(db: Session, canonical_product_id: int) -> dict:
    canonical = (
        db.query(CanonicalProduct)
        .options(
            joinedload(CanonicalProduct.products).joinedload(Product.spec),
            joinedload(CanonicalProduct.products).joinedload(Product.prices),
            joinedload(CanonicalProduct.products).joinedload(Product.benefit),
            joinedload(CanonicalProduct.products).joinedload(Product.return_policy),
            joinedload(CanonicalProduct.products).joinedload(Product.comments),
            joinedload(CanonicalProduct.products).joinedload(Product.platform_offer_analysis),
            joinedload(CanonicalProduct.redbook_notes),
            joinedload(CanonicalProduct.product_score),
        )
        .filter(CanonicalProduct.id == canonical_product_id)
        .first()
    )
    if not canonical:
        raise HTTPException(status_code=404, detail="Canonical product not found")

    comments = [comment for product in canonical.products for comment in product.comments]
    parameter_analyses = [
        {
            "product_id": product.id,
            "platform_product_id": product.platform_product_id,
            "title": product.title,
            "analysis": build_parameter_analysis(product.spec),
        }
        for product in canonical.products
    ]
    return {
        "canonical_product": _model_dict(canonical, exclude={"products", "redbook_notes", "product_score"}),
        "products": [_model_dict(product, exclude={"canonical_product"}) for product in canonical.products],
        "specs": [_model_dict(product.spec, exclude={"product"}) for product in canonical.products if product.spec],
        "parameter_analysis": parameter_analyses,
        "prices": [_model_dict(price, exclude={"product"}) for product in canonical.products for price in product.prices],
        "benefits": [_model_dict(product.benefit, exclude={"product"}) for product in canonical.products if product.benefit],
        "return_policy": [
            _model_dict(product.return_policy, exclude={"product"})
            for product in canonical.products
            if product.return_policy
        ],
        "comments": [_model_dict(comment, exclude={"product", "quality_analysis", "negative_analysis"}) for comment in comments],
        "comment_quality_analysis": [
            _model_dict(comment.quality_analysis, exclude={"comment"})
            for comment in comments
            if comment.quality_analysis
        ],
        "negative_review_analysis": [
            _model_dict(comment.negative_analysis, exclude={"comment"})
            for comment in comments
            if comment.negative_analysis
        ],
        "redbook_notes": [_model_dict(note, exclude={"canonical_product"}) for note in canonical.redbook_notes],
        "platform_offer_analysis": [
            _model_dict(product.platform_offer_analysis, exclude={"product"})
            for product in canonical.products
            if product.platform_offer_analysis
        ],
        "product_score": _model_dict(canonical.product_score, exclude={"canonical_product"}) if canonical.product_score else None,
    }


def get_price_compare(db: Session, canonical_product_id: int) -> dict:
    detail = get_product_detail(db, canonical_product_id)
    products = (
        db.query(Product)
        .options(
            joinedload(Product.prices),
            joinedload(Product.benefit),
            joinedload(Product.return_policy),
            joinedload(Product.platform_offer_analysis),
        )
        .filter(Product.canonical_product_id == canonical_product_id)
        .all()
    )
    offers = []
    for product in products:
        price = product.prices[-1]
        analysis = product.platform_offer_analysis
        offers.append(
            {
                "platform": product.platform,
                "shop_name": product.shop_name,
                "stable_final_price": price.stable_final_price,
                "theoretical_lowest_price": price.theoretical_lowest_price,
                "coupon_reliability_score": price.coupon_reliability_score,
                "gift_estimated_value": product.benefit.gift_estimated_value if product.benefit else 0,
                "gift_adjusted_cost": analysis.gift_adjusted_cost,
                "coupon_uncertainty_cost": analysis.coupon_uncertainty_cost,
                "return_protection_score": product.return_policy.return_protection_score,
                "return_risk_score": product.return_policy.return_risk_score,
                "return_risk_cost": product.return_policy.return_risk_cost,
                "risk_adjusted_cost": analysis.risk_adjusted_cost,
                "platform_buy_score": analysis.platform_buy_score,
                "is_lowest_price": analysis.is_lowest_price,
                "is_recommended_platform": analysis.is_recommended_platform,
                "warning_tags": parse_tags(analysis.warning_tags),
                "recommendation_reason": analysis.recommendation_reason,
                "data_confidence_score": product.canonical_product.data_confidence_score,
            }
        )
    lowest = next((offer for offer in offers if offer["is_lowest_price"]), min(offers, key=lambda item: item["stable_final_price"]))
    recommended = next((offer for offer in offers if offer["is_recommended_platform"]), max(offers, key=lambda item: item["platform_buy_score"]))
    price_gap = round(recommended["stable_final_price"] - lowest["stable_final_price"], 2)
    explanation = generate_platform_explanation(lowest, recommended)
    return {
        "canonical_product": detail["canonical_product"],
        "offers": offers,
        "lowest_price_platform": lowest["platform"],
        "recommended_platform": recommended["platform"],
        "price_gap": price_gap,
        "explanation": explanation,
    }


def get_mock_recommendations(db: Session) -> list[dict]:
    products = list_canonical_products(db)
    recommendations = []
    for item in sorted(products, key=lambda product: product["final_score"] or 0, reverse=True)[:8]:
        compare = get_price_compare(db, item["id"])
        recommendations.append(
            {
                "product_name": item["normalized_name"],
                "final_score": item["final_score"] or 0,
                "data_confidence_score": item["data_confidence_score"],
                "recommended_platform": compare["recommended_platform"],
                "lowest_price_platform": compare["lowest_price_platform"],
                "price_gap": compare["price_gap"],
                "reason": compare["explanation"],
                "advantages": ["样例：参数结构完整", "样例：多平台价格覆盖", "样例：保留退货风险字段"],
                "risks": item["main_risk_tags"] or ["样例数据，不代表真实结论"],
                "risk_tags": item["main_risk_tags"],
            }
        )
    return recommendations


def _model_dict(model, exclude: set[str] | None = None) -> dict:
    if model is None:
        return {}
    exclude = exclude or set()
    data = {}
    for column in model.__table__.columns:
        if column.name in exclude:
            continue
        value = getattr(model, column.name)
        if column.name == "product_url":
            value = public_product_url(value)
        data[column.name] = value
    return data
