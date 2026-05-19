import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    CanonicalProduct,
    Comment,
    CommentQualityAnalysis,
    NegativeReviewAnalysis,
    PlatformOfferAnalysis,
    Product,
    ProductBenefit,
    ProductPrice,
    ProductScore,
    ProductSpec,
    RedBookNote,
    ReturnPolicyAnalysis,
)


PLATFORM_ROTATION = [
    ("JD", "自营旗舰店", "京东自营"),
    ("TMALL", "品牌旗舰店", "天猫旗舰店"),
    ("TAOBAO", "户外专营店", "淘宝专营店"),
    ("PDD", "百亿补贴店", "拼多多店铺"),
    ("SMZDM", "值友爆料", "什么值得买线索"),
]


RISK_COMMENT_POOL = [
    ("下雨一晚后门厅边角有漏水，追评才发现底布接缝渗水。", "leak", "waterproof", "high"),
    ("人多睡一晚冷凝水很多，内帐早上都是水珠。", "condensation", "waterproof", "high"),
    ("第二次搭建杆子断了，风绳拉紧也没有用。", "broken_pole", "durability", "high"),
    ("新帐篷味道大，晾了两天还是有塑料味。", "odor", "material", "medium"),
    ("收纳袋太紧，不好收纳，女生一个人塞回去很费劲。", "hard_to_pack", "portable", "medium"),
    ("标四人实际两大一小刚好，空间虚标比较明显。", "space_overclaim", "space", "medium"),
    ("海边晒半天里面很闷，防晒差，黑胶效果一般。", "poor_sun_protection", "comfort", "medium"),
    ("申请退款慢，客服说要等仓库验货。", "slow_refund", "return", "medium"),
    ("只退了一部分，赠品还要折价扣款，退款少。", "partial_refund", "return", "high"),
    ("拆开试搭后不给退，说影响二次销售。", "return_denied", "return", "high"),
    ("退货麻烦，要自己拍很多证明材料。", "return_hassle", "return", "medium"),
    ("客服态度差，一直推责任。", "bad_service", "return", "medium"),
    ("质量问题还要我出退货运费，退货运费争议很烦。", "shipping_dispute", "return", "high"),
    ("还没用先好评，习惯好评。", "low_information", "comment_quality", "low"),
    ("物流很快，包装很好。", "logistics_only", "comment_quality", "low"),
    ("质量很好做工很好值得购买质量很好做工很好值得购买。", "template_praise", "comment_quality", "low"),
]


PRODUCT_SCENARIOS = [
    {
        "normalized_name": "清溪 RainGuard 2P 防水双人帐",
        "brand": "清溪",
        "model_name": "RainGuard 2P",
        "capacity": "2人",
        "use_case": "过夜轻露营",
        "main_image_url": "https://example.com/images/rainguard-2p.jpg",
        "match_confidence": 92,
        "data_confidence_score": 86,
        "score": (88, 80, 74, 73, 78, 82, 76, 79, 84, 72, 6, 82, "推荐"),
        "risks": ["冷凝水风险"],
        "adv": ["防水口碑稳定", "双人空间够用", "京东售后稳"],
        "reason": "适合新手过夜轻露营，防水反馈较好，最低价不是唯一依据。",
    },
    {
        "normalized_name": "山野 BudgetGo 2P 低价帐",
        "brand": "山野",
        "model_name": "BudgetGo 2P",
        "capacity": "2人",
        "use_case": "新手公园露营",
        "main_image_url": "https://example.com/images/budgetgo-2p.jpg",
        "match_confidence": 88,
        "data_confidence_score": 70,
        "score": (62, 58, 66, 72, 74, 55, 83, 52, 40, 50, 18, 61, "谨慎"),
        "risks": ["退货政策不清晰", "退款慢风险"],
        "adv": ["入门价格低", "搭建简单"],
        "reason": "低价适合预算敏感用户，但退货和退款风险需要明确提示。",
    },
    {
        "normalized_name": "牧云 FamilyHall 6P 家庭大帐",
        "brand": "牧云",
        "model_name": "FamilyHall 6P",
        "capacity": "5-6人",
        "use_case": "家庭多人露营",
        "main_image_url": "https://example.com/images/familyhall-6p.jpg",
        "match_confidence": 90,
        "data_confidence_score": 82,
        "score": (76, 78, 92, 38, 55, 80, 68, 76, 78, 66, 9, 75, "可选"),
        "risks": ["重量高", "不好收纳"],
        "adv": ["空间大", "家庭多人舒适", "结构稳定"],
        "reason": "空间优势明显，但重量和收纳压力较高，更适合自驾家庭。",
    },
    {
        "normalized_name": "云顶 StarNest 3P 颜值帐",
        "brand": "云顶",
        "model_name": "StarNest 3P",
        "capacity": "3人",
        "use_case": "新手公园露营",
        "main_image_url": "https://example.com/images/starnest-3p.jpg",
        "match_confidence": 86,
        "data_confidence_score": 78,
        "score": (72, 70, 82, 60, 79, 73, 58, 80, 78, 88, 5, 76, "可选"),
        "risks": ["价格偏高"],
        "adv": ["小红书口碑好", "搭建友好", "颜值高"],
        "reason": "小红书体验样例偏正向，但价格偏高，适合看重颜值和售后的用户。",
    },
    {
        "normalized_name": "岩盾 StormMax 2P 高防水帐",
        "brand": "岩盾",
        "model_name": "StormMax 2P",
        "capacity": "2人",
        "use_case": "过夜轻露营",
        "main_image_url": "https://example.com/images/stormmax-2p.jpg",
        "match_confidence": 89,
        "data_confidence_score": 74,
        "score": (78, 86, 70, 68, 60, 75, 70, 68, 64, 58, 14, 70, "谨慎"),
        "risks": ["漏水反馈", "冷凝水风险"],
        "adv": ["参数防水高", "抗风结构较强"],
        "reason": "防水参数高，但样例评论存在漏水和冷凝水反馈，不能只看参数。",
    },
    {
        "normalized_name": "松谷 FreshAir 3P 快开帐",
        "brand": "松谷",
        "model_name": "FreshAir 3P",
        "capacity": "3人",
        "use_case": "新手公园露营",
        "main_image_url": "https://example.com/images/freshair-3p.jpg",
        "match_confidence": 84,
        "data_confidence_score": 73,
        "score": (70, 64, 78, 66, 86, 60, 72, 70, 62, 60, 12, 69, "谨慎"),
        "risks": ["味道大", "防晒差"],
        "adv": ["快开方便", "空间够用"],
        "reason": "快开体验友好，但异味和防晒风险在样例评论中出现。",
    },
    {
        "normalized_name": "旷野 LowCost 4P 拼团帐",
        "brand": "旷野",
        "model_name": "LowCost 4P",
        "capacity": "4人",
        "use_case": "家庭多人露营",
        "main_image_url": "https://example.com/images/lowcost-4p.jpg",
        "match_confidence": 81,
        "data_confidence_score": 66,
        "score": (58, 60, 76, 52, 66, 55, 86, 42, 36, 45, 22, 57, "不推荐"),
        "risks": ["低价平台售后差", "退货运费争议"],
        "adv": ["页面价格低", "拼团价明显"],
        "reason": "低价平台便宜，但福利、退货和售后样例风险较高。",
    },
    {
        "normalized_name": "北岭 SafeCamp 2P 售后稳帐",
        "brand": "北岭",
        "model_name": "SafeCamp 2P",
        "capacity": "2人",
        "use_case": "过夜轻露营",
        "main_image_url": "https://example.com/images/safecamp-2p.jpg",
        "match_confidence": 93,
        "data_confidence_score": 88,
        "score": (82, 76, 73, 76, 80, 78, 74, 88, 92, 70, 4, 84, "强推荐"),
        "risks": ["价格略高"],
        "adv": ["退货保障强", "平台福利稳", "数据置信度高"],
        "reason": "京东或天猫价格略高，但运费险、价保和极速退款样例更稳。",
    },
]


def ensure_sample_data(db: Session) -> None:
    for index, scenario in enumerate(PRODUCT_SCENARIOS):
        existing = (
            db.query(CanonicalProduct)
            .filter(CanonicalProduct.normalized_name == scenario["normalized_name"])
            .first()
        )
        if existing:
            continue
        canonical = _create_canonical_product(db, index, scenario)
        _create_products_for_canonical(db, canonical, index, scenario)
    db.commit()


def _create_canonical_product(db: Session, index: int, scenario: dict) -> CanonicalProduct:
    canonical = CanonicalProduct(
        normalized_name=scenario["normalized_name"],
        brand=scenario["brand"],
        model_name=scenario["model_name"],
        capacity=scenario["capacity"],
        use_case=scenario["use_case"],
        main_image_url=scenario["main_image_url"],
        match_confidence=scenario["match_confidence"],
        data_confidence_score=scenario["data_confidence_score"],
    )
    db.add(canonical)
    db.flush()

    score_values = scenario["score"]
    db.add(
        ProductScore(
            canonical_product_id=canonical.id,
            waterproof_score=score_values[0],
            windproof_score=score_values[1],
            space_score=score_values[2],
            portable_score=score_values[3],
            setup_score=score_values[4],
            durability_score=score_values[5],
            price_value_score=score_values[6],
            platform_benefit_score=score_values[7],
            return_after_sale_score=score_values[8],
            redbook_score=score_values[9],
            risk_penalty=score_values[10],
            final_score=score_values[11],
            recommend_level=score_values[12],
            data_confidence_score=scenario["data_confidence_score"],
        )
    )
    db.add(
        RedBookNote(
            canonical_product_id=canonical.id,
            title=f"{scenario['model_name']} 露营体验笔记",
            content=f"样例小红书内容：{scenario['reason']} 优点包括{','.join(scenario['adv'])}。",
            comments_text=json.dumps(["真实使用场景反馈", "有人问雨天表现"], ensure_ascii=False),
            likes=120 + index * 15,
            favorites=45 + index * 6,
            comment_count=12 + index,
            is_suspected_ad=index in {3},
            credibility_score=82 - index if index != 3 else 55,
            sentiment_score=76 - index,
            risk_tags=json.dumps(scenario["risks"], ensure_ascii=False),
        )
    )
    return canonical


def _create_products_for_canonical(db: Session, canonical: CanonicalProduct, index: int, scenario: dict) -> None:
    first_platform = PLATFORM_ROTATION[index % len(PLATFORM_ROTATION)]
    second_platform = PLATFORM_ROTATION[(index + 1) % len(PLATFORM_ROTATION)]
    if index == 7:
        first_platform = ("JD", "北岭京东自营旗舰店", "京东自营")
        second_platform = ("PDD", "北岭低价拼团店", "拼多多店铺")
    if index == 6:
        first_platform = ("PDD", "旷野拼团工厂店", "拼多多店铺")
        second_platform = ("TMALL", "旷野天猫旗舰店", "天猫旗舰店")

    for offer_index, platform_info in enumerate([first_platform, second_platform]):
        platform, shop_name, shop_type = platform_info
        base_price = 299 + index * 80 + offer_index * 28
        if platform == "PDD":
            base_price -= 45
        if platform in {"JD", "TMALL"}:
            base_price += 20
        stable_price = float(max(159, base_price))
        theoretical_price = stable_price - (20 if platform in {"PDD", "TAOBAO", "SMZDM"} else 8)
        protection = 86 if platform in {"JD", "TMALL"} else 55
        risk_score = 18 if platform in {"JD", "TMALL"} else 52
        if index in {1, 6} and platform == "PDD":
            risk_score = 78
            protection = 32
        return_risk_cost = round(stable_price * (0.30 if risk_score >= 70 else 0.10 if risk_score >= 30 else 0.03), 2)
        gift_value = 35 + offer_index * 15
        coupon_uncertainty = 8 if platform in {"JD", "TMALL"} else 26
        risk_adjusted = round(stable_price - 0.5 * gift_value + coupon_uncertainty + return_risk_cost, 2)
        platform_buy_score = max(35, min(92, 84 - offer_index * 4 - (risk_score / 5) + (10 if platform in {"JD", "TMALL"} else 0)))

        product = Product(
            canonical_product_id=canonical.id,
            platform=platform,
            platform_product_id=f"{platform}-{canonical.id}-{offer_index}",
            title=f"{scenario['brand']} {scenario['model_name']} {scenario['capacity']} {platform}样例链接",
            shop_name=shop_name,
            shop_type=shop_type,
            product_url=None,
            image_url=scenario["main_image_url"],
            sales_volume=1200 + index * 220 + offer_index * 100,
            rating_count=350 + index * 40 + offer_index * 25,
            positive_rate=95 - index * 1.7 - offer_index,
        )
        db.add(product)
        db.flush()

        db.add(_build_spec(product.id, index))
        db.add(_build_price(product.id, stable_price, theoretical_price, platform))
        db.add(_build_benefit(product.id, platform, gift_value, protection))
        db.add(_build_return_policy(product.id, platform, protection, risk_score, return_risk_cost))
        db.add(
            PlatformOfferAnalysis(
                product_id=product.id,
                gift_adjusted_cost=round(stable_price - 0.5 * gift_value, 2),
                coupon_uncertainty_cost=coupon_uncertainty,
                risk_adjusted_cost=risk_adjusted,
                platform_buy_score=round(platform_buy_score, 2),
                is_lowest_price=False,
                is_recommended_platform=False,
                recommendation_reason="样例占位：综合价格、优惠稳定、赠品、退货保障和售后风险后给出。",
                warning_tags=json.dumps(scenario["risks"], ensure_ascii=False),
            )
        )
        _create_comments(db, product.id, platform, index, offer_index)

    db.flush()
    products = list(canonical.products)
    lowest = min(products, key=lambda p: p.prices[-1].stable_final_price)
    recommended = max(products, key=lambda p: p.platform_offer_analysis.platform_buy_score)
    lowest.platform_offer_analysis.is_lowest_price = True
    recommended.platform_offer_analysis.is_recommended_platform = True


def _build_spec(product_id: int, index: int) -> ProductSpec:
    return ProductSpec(
        product_id=product_id,
        waterproof_index_outer=2000 + index * 350,
        waterproof_index_floor=2500 + index * 300,
        weight_kg=2.2 + index * 0.55,
        expanded_length_cm=210 + index * 12,
        expanded_width_cm=140 + index * 18,
        expanded_height_cm=115 + index * 8,
        floor_area_m2=2.8 + index * 0.45,
        packed_volume_l=18 + index * 4,
        pole_material="铝合金" if index % 2 == 0 else "玻璃纤维",
        outer_material="210T涤纶 PU涂层",
        setup_type="快开" if index in {3, 5} else "手搭",
        tent_type="双层帐" if index != 6 else "单层帐",
        raw_specs_json=json.dumps({"source": "sample", "agent": "Agent 2"}, ensure_ascii=False),
    )


def _build_price(product_id: int, stable_price: float, theoretical_price: float, platform: str) -> ProductPrice:
    return ProductPrice(
        product_id=product_id,
        original_price=stable_price + 80,
        current_price=stable_price + 20,
        shop_coupon_amount=15,
        platform_coupon_amount=10 if platform in {"JD", "TMALL", "TAOBAO"} else 5,
        member_coupon_amount=0 if platform in {"JD", "TMALL"} else 12,
        limited_coupon_amount=0 if platform in {"JD", "TMALL"} else 18,
        red_packet_amount=0 if platform in {"JD", "TMALL"} else 6,
        discount_amount=20,
        shipping_fee=0 if platform != "SMZDM" else 8,
        stable_final_price=stable_price,
        theoretical_lowest_price=theoretical_price,
        coupon_reliability_score=88 if platform in {"JD", "TMALL"} else 58,
        coupon_text="普通店铺券和平台券样例",
        promotion_text="sample/mock 优惠，不代表真实可购买价格",
        price_update_time=datetime.now(timezone.utc),
    )


def _build_benefit(product_id: int, platform: str, gift_value: float, protection: float) -> ProductBenefit:
    strong = platform in {"JD", "TMALL"}
    return ProductBenefit(
        product_id=product_id,
        free_shipping=True,
        shipping_insurance=strong,
        return_7_days=strong or platform == "TAOBAO",
        fast_refund=strong,
        price_protection=strong,
        official_store=platform in {"JD", "TMALL"},
        self_operated=platform == "JD",
        gift_items=json.dumps(["地布", "营钉", "收纳袋"], ensure_ascii=False),
        gift_estimated_value=gift_value,
        gift_usefulness_score=72,
        platform_benefit_score=protection,
    )


def _build_return_policy(
    product_id: int,
    platform: str,
    protection: float,
    risk_score: float,
    return_risk_cost: float,
) -> ReturnPolicyAnalysis:
    strong = platform in {"JD", "TMALL"}
    return ReturnPolicyAnalysis(
        product_id=product_id,
        return_shipping_insurance=strong,
        return_shipping_payer="平台/商家" if strong else "买家可能承担",
        return_condition_text="sample/mock 退货政策占位，后续由 Agent 4 接入真实计算。",
        opened_return_allowed=strong,
        used_return_allowed=False,
        quality_issue_free_return=strong,
        refund_speed_type="极速退款" if strong else "验货后退款",
        refund_full_amount=strong,
        partial_refund_risk=not strong,
        seller_return_attitude="积极" if strong else "不稳定",
        return_policy_clarity=90 if strong else 50,
        return_negative_rate=0.08 if strong else 0.32,
        refund_dispute_rate=0.04 if strong else 0.26,
        return_protection_score=protection,
        return_risk_score=risk_score,
        return_risk_cost=return_risk_cost,
    )


def _create_comments(db: Session, product_id: int, platform: str, index: int, offer_index: int) -> None:
    selected = [
        RISK_COMMENT_POOL[(index * 2 + offer_index) % len(RISK_COMMENT_POOL)],
        RISK_COMMENT_POOL[(index * 2 + offer_index + 7) % len(RISK_COMMENT_POOL)],
    ]
    for comment_index, (text, negative_type, dimension, level) in enumerate(selected):
        is_low_info = negative_type in {"low_information", "logistics_only", "template_praise"}
        comment = Comment(
            product_id=product_id,
            platform=platform,
            comment_text=text,
            rating=2.0 if level in {"high", "medium"} and not is_low_info else 5.0,
            comment_type="好评" if is_low_info else "差评",
            has_image=comment_index == 0 and not is_low_info,
            is_follow_up=comment_index == 0,
            comment_time=datetime.now(timezone.utc) - timedelta(days=comment_index + index),
            seller_reply="您好，样例售后回复占位。" if dimension == "return" else None,
        )
        db.add(comment)
        db.flush()
        db.add(
            CommentQualityAnalysis(
                comment_id=comment.id,
                comment_credibility_score=35 if is_low_info else 78,
                fake_review_risk_score=72 if negative_type == "template_praise" else 18,
                effective_comment_weight=0.12 if is_low_info else 0.84,
                is_low_information=is_low_info,
                is_suspected_fake=negative_type == "template_praise",
                risk_tags=json.dumps([negative_type], ensure_ascii=False),
            )
        )
        db.add(
            NegativeReviewAnalysis(
                comment_id=comment.id,
                negative_type=negative_type,
                affected_dimension=dimension,
                risk_level=level,
                is_valid_negative=not is_low_info,
            )
        )
