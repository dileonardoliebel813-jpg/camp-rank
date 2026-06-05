import json
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import (
    CanonicalProduct,
    Comment,
    CommentQualityAnalysis,
    NegativeReviewAnalysis,
    PlatformOfferAnalysis,
    Product,
    ProductScore,
)
from app.scoring.coupon_reliability import calculate_coupon_reliability_score, normalize_coupon_type
from app.scoring.explanation_generator import generate_platform_explanation
from app.scoring.gift_value import (
    calculate_gift_adjusted_cost,
    calculate_gift_usefulness_score,
    estimate_gift_value,
)
from app.scoring.platform_buy_score import (
    calculate_platform_buy_score,
    calculate_price_advantage_score,
    select_lowest_price_offer,
    select_recommended_offer,
)
from app.scoring.price_calculation import (
    calculate_coupon_uncertainty_cost,
    calculate_stable_final_price,
    calculate_theoretical_lowest_price,
)
from app.scoring.product_scoring import (
    calculate_comment_score_from_negative_rate,
    calculate_data_confidence_score,
    calculate_dimension_score,
    calculate_final_product_score,
    calculate_risk_penalty,
)
from app.scoring.recommendation_ranker import build_recommendations
from app.scoring.review_evidence_score import calculate_review_evidence
from app.scoring.return_risk import (
    calculate_return_protection_score,
    calculate_return_risk_cost,
    calculate_return_risk_score,
    calculate_risk_adjusted_cost,
)
from app.services.sample_data_service import ensure_sample_data


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    except json.JSONDecodeError:
        return [item.strip() for item in raw.split(",") if item.strip()]


def _json_list(items: list[str]) -> str:
    return json.dumps(sorted(set(str(item) for item in items if item)), ensure_ascii=False)


def _latest_price(product: Product):
    return max(product.prices, key=lambda price: price.id) if product.prices else None


def _ensure_sample_data_if_empty(db: Session, enabled: bool | None = None) -> None:
    if enabled is None:
        enabled = get_settings().sample_data_enabled
    if enabled and db.query(CanonicalProduct.id).first() is None:
        ensure_sample_data(db)


def _coupon_types_from_price(price) -> list[str]:
    types = []
    text = " ".join(filter(None, [price.coupon_text, price.promotion_text]))
    types.extend(normalize_coupon_type(text))
    if price.shop_coupon_amount:
        types.append("shop_coupon")
    if price.platform_coupon_amount:
        types.append("platform_coupon")
    if price.discount_amount:
        types.append("discount")
    if price.member_coupon_amount:
        types.append("member_coupon")
    if price.limited_coupon_amount:
        types.append("limited_coupon")
    if price.red_packet_amount:
        types.append("red_packet")
    return sorted(set(types)) or ["direct_price"]


def _weighted_rate(product: Product, keywords: set[str], fallback: float = 0.0) -> float:
    total = 0.0
    matched = 0.0
    for comment in product.comments:
        quality = comment.quality_analysis
        negative = comment.negative_analysis
        weight = quality.effective_comment_weight if quality else 0.2
        if weight <= 0:
            continue
        total += weight
        values = [
            negative.negative_type if negative else "",
            negative.affected_dimension if negative else "",
            quality.risk_tags if quality else "",
            comment.comment_text,
        ]
        haystack = " ".join(str(value) for value in values if value).lower()
        if any(keyword in haystack for keyword in keywords):
            matched += weight
    if total <= 0:
        return fallback
    return max(0.0, min(matched / total, 1.0))


def _risk_tags_for_product(product: Product, return_risk_score: float, data_confidence: float) -> list[str]:
    tags = []
    for comment in product.comments:
        if comment.quality_analysis:
            tags.extend(_parse_tags(comment.quality_analysis.risk_tags))
        if comment.negative_analysis and comment.negative_analysis.risk_level == "high":
            tags.append(comment.negative_analysis.negative_type or "high_risk")
    if return_risk_score >= 70:
        tags.append("return_high_risk")
    elif return_risk_score >= 50:
        tags.append("return_medium_risk")
    if data_confidence < 50:
        tags.append("low_data_confidence")
    return sorted(set(tags))


def _shop_reputation_score(product: Product) -> float:
    score = 50 + min(product.positive_rate or 0, 100) * 0.35
    if product.benefit:
        if product.benefit.official_store:
            score += 5
        if product.benefit.self_operated:
            score += 5
        if product.benefit.price_protection:
            score += 3
    if product.sales_volume:
        score += min(product.sales_volume / 1000, 5)
    return round(max(0.0, min(score, 100.0)), 2)


def _after_sale_service_score(product: Product, return_risk_score: float) -> float:
    base = 100 - return_risk_score
    if product.benefit:
        if product.benefit.fast_refund:
            base += 5
        if product.benefit.shipping_insurance:
            base += 4
        if product.benefit.return_7_days:
            base += 4
    if product.return_policy:
        if product.return_policy.quality_issue_free_return:
            base += 5
        if product.return_policy.refund_full_amount:
            base += 3
        if product.return_policy.partial_refund_risk:
            base -= 8
    if product.return_policy and product.return_policy.seller_return_attitude:
        attitude = product.return_policy.seller_return_attitude
        if "积极" in attitude or "positive" in attitude.lower():
            base += 8
        if "不" in attitude or "unstable" in attitude.lower():
            base -= 8
    return round(max(0.0, min(base, 100.0)), 2)


def _service_dispute_cost(stable_final_price: float, return_risk_score: float) -> float:
    if return_risk_score < 50:
        return 0.0
    return round(stable_final_price * (0.03 if return_risk_score < 70 else 0.06), 2)


def _mvp_data_confidence_score(
    spec_completeness: float,
    review_evidence_confidence: float,
    platform_price_count: int,
    return_field_completeness: float,
) -> float:
    price_score = min(max(platform_price_count, 0) / 2, 1.0) * 100
    return_score = max(0.0, min(return_field_completeness, 1.0)) * 100
    spec_score = max(0.0, min(spec_completeness, 1.0)) * 100
    score = (
        0.55 * review_evidence_confidence
        + 0.20 * return_score
        + 0.15 * price_score
        + 0.10 * spec_score
    )
    return round(max(0.0, min(score, 100.0)), 2)


def _calculate_mvp_product_score(
    price_value_score: float,
    return_after_sale_score: float,
    review_evidence_score: float,
    data_confidence_score: float,
) -> float:
    score = (
        0.65 * review_evidence_score
        + 0.13 * return_after_sale_score
        + 0.12 * price_value_score
        + 0.10 * data_confidence_score
    )
    return round(max(0.0, min(score, 82.0)), 2)


def _calculate_mvp_dimension_score(risk_rate: float, neutral_score: float = 76.0) -> float:
    # In sparse-spec MVP mode, low risk mentions are not proof of strong specs.
    # Start from a neutral score and only move downward as calibrated risk rises.
    score = neutral_score - max(0.0, min(float(risk_rate or 0.0), 1.0)) * 120
    return round(max(40.0, min(score, neutral_score)), 2)


def calculate_and_update_platform_offers(db: Session, user_preference: str = "balanced") -> dict:
    products = (
        db.query(Product)
        .options(
            joinedload(Product.canonical_product),
            joinedload(Product.prices),
            joinedload(Product.benefit),
            joinedload(Product.return_policy),
            joinedload(Product.platform_offer_analysis),
            joinedload(Product.comments).joinedload(Comment.quality_analysis),
            joinedload(Product.comments).joinedload(Comment.negative_analysis),
        )
        .all()
    )
    products_by_canonical: dict[int, list[Product]] = {}
    for product in products:
        products_by_canonical.setdefault(product.canonical_product_id, []).append(product)

    updated = 0
    for canonical_products in products_by_canonical.values():
        price_rows = [(_latest_price(product), product) for product in canonical_products if _latest_price(product)]
        if not price_rows:
            continue
        stable_values = []
        for price, _product in price_rows:
            price.stable_final_price = calculate_stable_final_price(
                price.current_price,
                price.shop_coupon_amount,
                price.platform_coupon_amount,
                price.discount_amount,
                price.shipping_fee,
            )
            price.theoretical_lowest_price = calculate_theoretical_lowest_price(
                price.current_price,
                price.shop_coupon_amount,
                price.platform_coupon_amount,
                price.member_coupon_amount,
                price.limited_coupon_amount,
                price.red_packet_amount,
                price.discount_amount,
                price.shipping_fee,
            )
            coupon_score = calculate_coupon_reliability_score(_coupon_types_from_price(price))
            price.coupon_reliability_score = round(coupon_score * 100, 2)
            stable_values.append(price.stable_final_price)
        min_price = min(stable_values)
        max_price = max(stable_values)

        offer_inputs = []
        for price, product in price_rows:
            benefit = product.benefit
            return_policy = product.return_policy
            product_review_evidence = calculate_review_evidence(list(product.comments))
            gift_value = estimate_gift_value(benefit.gift_items if benefit else [])
            gift_usefulness = calculate_gift_usefulness_score(benefit.gift_items if benefit else [])
            if benefit:
                benefit.gift_estimated_value = gift_value
                benefit.gift_usefulness_score = gift_usefulness

            return_difficulty_rate = product_review_evidence["dimension_risk_rates"].get("return_after_sale", 0.0)
            refund_amount_issue_rate = _weighted_rate(
                product,
                {"partial_refund", "refund_amount", "少退", "部分"},
                return_policy.refund_dispute_rate if return_policy else 0,
            )
            refund_speed_issue_rate = _weighted_rate(product, {"slow_refund", "退款慢", "审核"})
            shipping_fee_dispute_rate = _weighted_rate(product, {"shipping_dispute", "运费"})
            bad_customer_service_rate = _weighted_rate(product, {"bad_service", "客服"})
            calculated_return_risk_score = calculate_return_risk_score(
                return_difficulty_rate,
                refund_amount_issue_rate,
                refund_speed_issue_rate,
                shipping_fee_dispute_rate,
                bad_customer_service_rate,
            )
            prior_return_risk_score = return_policy.return_risk_score if return_policy else 0
            return_risk_score = max(calculated_return_risk_score, prior_return_risk_score)
            return_protection_score = calculate_return_protection_score(
                benefit.return_7_days if benefit else False,
                bool(return_policy and return_policy.return_shipping_insurance),
                bool(return_policy and return_policy.quality_issue_free_return),
                benefit.fast_refund if benefit else False,
                return_policy.return_policy_clarity if return_policy else 0,
                bool(benefit and (benefit.official_store or benefit.self_operated)),
            )
            return_risk_cost = calculate_return_risk_cost(price.stable_final_price, return_risk_score)
            if return_policy:
                return_policy.return_protection_score = return_protection_score
                return_policy.return_risk_score = return_risk_score
                return_policy.return_risk_cost = return_risk_cost

            coupon_score_ratio = max(0.0, min(price.coupon_reliability_score / 100, 1.0))
            coupon_uncertainty_cost = calculate_coupon_uncertainty_cost(
                price.stable_final_price,
                price.theoretical_lowest_price,
                coupon_score_ratio,
            )
            service_cost = _service_dispute_cost(price.stable_final_price, return_risk_score)
            risk_adjusted_cost = calculate_risk_adjusted_cost(
                price.stable_final_price,
                gift_value,
                coupon_uncertainty_cost,
                return_risk_cost,
                service_cost,
            )
            price_advantage_score = calculate_price_advantage_score(price.stable_final_price, min_price, max_price)
            after_sale_score = _after_sale_service_score(product, return_risk_score)
            shop_reputation = _shop_reputation_score(product)
            data_confidence = product.canonical_product.data_confidence_score if product.canonical_product else 60
            platform_buy_score = calculate_platform_buy_score(
                price_advantage_score,
                price.coupon_reliability_score,
                gift_usefulness,
                return_protection_score,
                after_sale_score,
                shop_reputation,
                data_confidence,
                user_preference=user_preference,
            )
            analysis = product.platform_offer_analysis or PlatformOfferAnalysis(product_id=product.id)
            analysis.gift_adjusted_cost = calculate_gift_adjusted_cost(price.stable_final_price, gift_value)
            analysis.coupon_uncertainty_cost = coupon_uncertainty_cost
            analysis.risk_adjusted_cost = risk_adjusted_cost
            analysis.platform_buy_score = platform_buy_score
            analysis.warning_tags = _json_list(_risk_tags_for_product(product, return_risk_score, data_confidence))
            analysis.recommendation_reason = "Pending final platform comparison."
            db.add(analysis)
            db.flush()
            offer_inputs.append(
                {
                    "product_id": product.id,
                    "platform": product.platform,
                    "stable_final_price": price.stable_final_price,
                    "theoretical_lowest_price": price.theoretical_lowest_price,
                    "risk_adjusted_cost": risk_adjusted_cost,
                    "platform_buy_score": platform_buy_score,
                    "return_risk_score": return_risk_score,
                    "return_protection_score": return_protection_score,
                    "coupon_reliability_score": price.coupon_reliability_score,
                    "data_confidence_score": data_confidence,
                }
            )

        lowest = select_lowest_price_offer(offer_inputs)
        recommended = select_recommended_offer(offer_inputs, user_preference=user_preference)
        explanation = generate_platform_explanation(lowest, recommended)
        for product in canonical_products:
            analysis = product.platform_offer_analysis
            if not analysis:
                continue
            analysis.is_lowest_price = product.id == lowest.get("product_id")
            analysis.is_recommended_platform = product.id == recommended.get("product_id")
            analysis.recommendation_reason = explanation if analysis.is_recommended_platform else "Not selected after price, coupon, return and service comparison."
            updated += 1

    db.commit()
    return {"updated_platform_offers": updated}


def _spec_completeness(products: list[Product]) -> float:
    fields = [
        "waterproof_index_outer",
        "waterproof_index_floor",
        "weight_kg",
        "expanded_length_cm",
        "expanded_width_cm",
        "expanded_height_cm",
        "floor_area_m2",
        "packed_volume_l",
        "pole_material",
        "outer_material",
        "setup_type",
    ]
    total = 0
    present = 0
    for product in products:
        if not product.spec:
            total += len(fields)
            continue
        for field in fields:
            total += 1
            if getattr(product.spec, field) not in (None, ""):
                present += 1
    return present / total if total else 0


def _avg(values: list[float], default: float = 0.0) -> float:
    values = [float(value) for value in values if value is not None]
    return sum(values) / len(values) if values else default


def _param_scores(products: list[Product]) -> dict[str, float]:
    specs = [product.spec for product in products if product.spec]
    waterproof_values = []
    for spec in specs:
        values = [value for value in (spec.waterproof_index_outer, spec.waterproof_index_floor) if value]
        if values:
            waterproof_values.append(min(sum(values) / 70, 100))
    windproof_values = []
    durability_values = []
    for spec in specs:
        pole = spec.pole_material or ""
        if not pole:
            continue
        if "铝" in pole:
            windproof_values.append(82)
            durability_values.append(82)
        elif "铁" in pole:
            windproof_values.append(72)
            durability_values.append(72)
        elif "玻纤" in pole or "玻璃纤维" in pole:
            windproof_values.append(68)
            durability_values.append(70)
    space_values = [
        min(float(spec.floor_area_m2) * 18 + float(spec.expanded_height_cm or 0) * 0.25, 100)
        for spec in specs
        if spec.floor_area_m2 is not None and spec.expanded_height_cm is not None
    ]
    portable_values = []
    for spec in specs:
        parts = []
        if spec.weight_kg is not None:
            parts.append(100 - float(spec.weight_kg) * 8)
        if spec.packed_volume_l is not None:
            parts.append(100 - float(spec.packed_volume_l) * 0.6)
        if parts:
            portable_values.append(max(30, sum(parts) / len(parts)))
    setup_values = []
    for spec in specs:
        setup_text = spec.setup_type or ""
        if not setup_text:
            continue
        setup_values.append(88 if any(keyword in setup_text for keyword in ("快", "自动", "速开", "弹簧")) else 70)
    waterproof = _avg(waterproof_values, 60)
    windproof = _avg(windproof_values, 65)
    space = _avg(space_values, 65)
    portable = _avg(portable_values, 60)
    setup = _avg(setup_values, 70)
    durability = _avg(durability_values, 70)
    return {
        "waterproof": waterproof,
        "windproof": windproof,
        "space": space,
        "portable": portable,
        "setup": setup,
        "durability": durability,
    }


def _dimension_negative_rate(products: list[Product], keywords: set[str]) -> float:
    total = 0.0
    matched = 0.0
    for product in products:
        for comment in product.comments:
            quality = comment.quality_analysis
            negative = comment.negative_analysis
            weight = quality.effective_comment_weight if quality else 0.2
            if weight <= 0:
                continue
            total += weight
            haystack = " ".join(
                str(value)
                for value in [
                    negative.negative_type if negative else "",
                    negative.affected_dimension if negative else "",
                    quality.risk_tags if quality else "",
                    comment.comment_text,
                ]
                if value
            ).lower()
            if any(keyword in haystack for keyword in keywords):
                matched += weight
    return matched / total if total else 0.0


def _canonical_risk_tags(canonical: CanonicalProduct) -> list[str]:
    tags = []
    for product in canonical.products:
        if product.platform_offer_analysis:
            tags.extend(_parse_tags(product.platform_offer_analysis.warning_tags))
    for note in canonical.redbook_notes:
        tags.extend(_parse_tags(note.risk_tags))
    if canonical.data_confidence_score < 50:
        tags.append("low_data_confidence")
    return sorted(set(tags))


def calculate_and_update_product_scores(db: Session, scenario: str = "newbie_weekend") -> dict:
    canonicals = (
        db.query(CanonicalProduct)
        .options(
            joinedload(CanonicalProduct.products).joinedload(Product.spec),
            joinedload(CanonicalProduct.products).joinedload(Product.prices),
            joinedload(CanonicalProduct.products).joinedload(Product.platform_offer_analysis),
            joinedload(CanonicalProduct.products).joinedload(Product.return_policy),
            joinedload(CanonicalProduct.products).joinedload(Product.comments).joinedload(Comment.quality_analysis),
            joinedload(CanonicalProduct.products).joinedload(Product.comments).joinedload(Comment.negative_analysis),
            joinedload(CanonicalProduct.redbook_notes),
            joinedload(CanonicalProduct.product_score),
        )
        .all()
    )
    updated = 0
    for canonical in canonicals:
        products = list(canonical.products)
        if not products:
            continue
        params = _param_scores(products)
        rates = {
            "waterproof": _dimension_negative_rate(products, {"leak", "condensation", "waterproof", "漏水"}),
            "windproof": _dimension_negative_rate(products, {"broken_pole", "collapse", "windproof", "杆"}),
            "space": _dimension_negative_rate(products, {"space_overclaim", "space", "空间"}),
            "portable": _dimension_negative_rate(products, {"hard_to_pack", "portable", "收纳"}),
            "setup": _dimension_negative_rate(products, {"setup", "搭建"}),
            "durability": _dimension_negative_rate(products, {"broken_pole", "durability", "断"}),
            "return": _dimension_negative_rate(products, {"return", "refund", "退"}),
        }
        waterproof_score = calculate_dimension_score(params["waterproof"], calculate_comment_score_from_negative_rate(rates["waterproof"]))
        windproof_score = calculate_dimension_score(params["windproof"], calculate_comment_score_from_negative_rate(rates["windproof"]))
        space_score = calculate_dimension_score(params["space"], calculate_comment_score_from_negative_rate(rates["space"]))
        portable_score = calculate_dimension_score(params["portable"], calculate_comment_score_from_negative_rate(rates["portable"]))
        setup_score = calculate_dimension_score(params["setup"], calculate_comment_score_from_negative_rate(rates["setup"]))
        durability_score = calculate_dimension_score(params["durability"], calculate_comment_score_from_negative_rate(rates["durability"]))

        comments = [comment for product in products for comment in product.comments]
        review_evidence = calculate_review_evidence(comments)
        evidence_rates = review_evidence["dimension_risk_rates"]
        spec_completeness = _spec_completeness(products)
        sparse_spec_mvp = spec_completeness < 0.35 and len(comments) >= 20
        if sparse_spec_mvp:
            waterproof_score = _calculate_mvp_dimension_score(evidence_rates.get("waterproof", 0.0))
            windproof_score = _calculate_mvp_dimension_score(evidence_rates.get("windproof", 0.0))
            space_score = _calculate_mvp_dimension_score(evidence_rates.get("space", 0.0))
            portable_score = _calculate_mvp_dimension_score(evidence_rates.get("storage", 0.0))
            setup_score = _calculate_mvp_dimension_score(evidence_rates.get("setup", 0.0))
            durability_score = _calculate_mvp_dimension_score(evidence_rates.get("durability", 0.0))
        else:
            waterproof_score = calculate_dimension_score(
                params["waterproof"], calculate_comment_score_from_negative_rate(evidence_rates.get("waterproof", 0.0))
            )
            windproof_score = calculate_dimension_score(
                params["windproof"], calculate_comment_score_from_negative_rate(evidence_rates.get("windproof", 0.0))
            )
            space_score = calculate_dimension_score(
                params["space"], calculate_comment_score_from_negative_rate(evidence_rates.get("space", 0.0))
            )
            portable_score = calculate_dimension_score(
                params["portable"], calculate_comment_score_from_negative_rate(evidence_rates.get("storage", 0.0))
            )
            setup_score = calculate_dimension_score(
                params["setup"], calculate_comment_score_from_negative_rate(evidence_rates.get("setup", 0.0))
            )
            durability_score = calculate_dimension_score(
                params["durability"], calculate_comment_score_from_negative_rate(evidence_rates.get("durability", 0.0))
            )

        offers = [product.platform_offer_analysis for product in products if product.platform_offer_analysis]
        prices = [_latest_price(product).stable_final_price for product in products if _latest_price(product)]
        min_price = min(prices) if prices else 0
        price_value_score = max(35.0, min(100.0, 100 - max(min_price - 250, 0) / 12)) if min_price else 50.0
        platform_benefit_score = _avg([offer.platform_buy_score for offer in offers], 55)
        return_after_sale_score = _avg(
            [product.return_policy.return_protection_score - product.return_policy.return_risk_score * 0.35 for product in products if product.return_policy],
            55,
        )
        redbook_score = _avg(
            [note.sentiment_score * 0.7 + note.credibility_score * 0.3 for note in canonical.redbook_notes],
            55,
        )
        comments = [comment for product in products for comment in product.comments]
        suspected_fake = sum(1 for comment in comments if comment.quality_analysis and comment.quality_analysis.is_suspected_fake)
        valid_comments = sum(1 for comment in comments if comment.quality_analysis and comment.quality_analysis.effective_comment_weight > 0.2)
        data_confidence = calculate_data_confidence_score(
            _spec_completeness(products),
            valid_comments,
            suspected_fake / len(comments) if comments else 0,
            len({product.platform for product in products if product.prices}),
            sum(1 for product in products if product.return_policy) / len(products),
            len(canonical.redbook_notes),
            updated_recently=True,
        )
        if sparse_spec_mvp:
            data_confidence = _mvp_data_confidence_score(
                spec_completeness,
                review_evidence["evidence_confidence_score"],
                len({product.platform for product in products if product.prices}),
                sum(1 for product in products if product.return_policy) / len(products),
            )
        risk_tags = _canonical_risk_tags(canonical)
        risk_penalty = calculate_risk_penalty(risk_tags)
        final_score = calculate_final_product_score(
            waterproof_score,
            windproof_score,
            space_score,
            portable_score,
            setup_score,
            durability_score,
            price_value_score,
            platform_benefit_score,
            return_after_sale_score,
            redbook_score,
            risk_penalty,
            scenario=scenario,
        )
        if sparse_spec_mvp:
            risk_penalty = round((100 - review_evidence["review_evidence_score"]) * 0.25, 2)
            final_score = _calculate_mvp_product_score(
                price_value_score,
                return_after_sale_score,
                review_evidence["review_evidence_score"],
                data_confidence,
            )
        score = canonical.product_score or ProductScore(canonical_product_id=canonical.id, recommend_level="cautious")
        score.waterproof_score = waterproof_score
        score.windproof_score = windproof_score
        score.space_score = space_score
        score.portable_score = portable_score
        score.setup_score = setup_score
        score.durability_score = durability_score
        score.price_value_score = round(price_value_score, 2)
        score.platform_benefit_score = round(platform_benefit_score, 2)
        score.return_after_sale_score = round(max(0.0, min(return_after_sale_score, 100.0)), 2)
        score.redbook_score = round(max(0.0, min(redbook_score, 100.0)), 2)
        score.data_confidence_score = data_confidence
        score.risk_penalty = risk_penalty
        score.final_score = final_score
        score.recommend_level = "strong_recommend" if final_score >= 82 else "recommend" if final_score >= 70 else "cautious" if final_score >= 60 else "not_recommended"
        canonical.data_confidence_score = data_confidence
        db.add(score)
        updated += 1
    db.commit()
    return {"updated_product_scores": updated}


def build_recommendation_response(db: Session, filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    try:
        _ensure_sample_data_if_empty(db)
        calculate_and_update_platform_offers(db, user_preference=filters.get("preference", "balanced"))
        calculate_and_update_product_scores(db, scenario=filters.get("scenario", "newbie_weekend"))
    except OperationalError as error:
        db.rollback()
        if "database is locked" not in str(error).lower():
            raise
    return build_recommendations(
        db,
        min_price=filters.get("min_price"),
        max_price=filters.get("max_price"),
        scenario=filters.get("scenario", "newbie_weekend"),
        preference=filters.get("preference", "balanced"),
        limit=filters.get("limit", 10),
    )


def calculate_all_scores(
    db: Session,
    scenario: str = "newbie_weekend",
    preference: str = "balanced",
    seed_sample_data: bool | None = None,
) -> dict:
    _ensure_sample_data_if_empty(db, enabled=seed_sample_data)
    platform_result = calculate_and_update_platform_offers(db, user_preference=preference)
    product_result = calculate_and_update_product_scores(db, scenario=scenario)
    return {
        **platform_result,
        **product_result,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
