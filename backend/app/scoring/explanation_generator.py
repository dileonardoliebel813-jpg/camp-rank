def generate_platform_explanation(lowest_offer: dict, recommended_offer: dict) -> str:
    if not lowest_offer or not recommended_offer:
        return "No comparable platform offer is available yet."
    lowest_platform = lowest_offer.get("platform")
    recommended_platform = recommended_offer.get("platform")
    price_gap = round(
        float(recommended_offer.get("stable_final_price", 0))
        - float(lowest_offer.get("stable_final_price", 0)),
        2,
    )
    if lowest_platform == recommended_platform:
        return (
            f"{recommended_platform} is both the lowest stable price platform and the recommended platform. "
            "The recommendation is based on price, coupon stability, return protection, service and data confidence."
        )

    reasons = []
    if float(lowest_offer.get("return_risk_score", 0)) >= 50:
        reasons.append("higher return or refund risk")
    if float(lowest_offer.get("coupon_reliability_score", 100)) < 70:
        reasons.append("less stable coupon conditions")
    if float(lowest_offer.get("return_protection_score", 100)) < float(recommended_offer.get("return_protection_score", 0)):
        reasons.append("weaker return protection")
    if float(lowest_offer.get("data_confidence_score", 100)) < 55:
        reasons.append("lower data confidence")
    reason_text = ", ".join(reasons) if reasons else "a weaker overall platform buy score"
    return (
        f"{lowest_platform} has the lowest stable price, while {recommended_platform} is recommended. "
        f"The stable price gap is {price_gap:.2f}. The lowest-price offer is not preferred because of {reason_text}."
    )


def generate_product_recommendation_reason(product_summary: dict) -> str:
    name = product_summary.get("product_name") or product_summary.get("normalized_name") or "This tent"
    platform = product_summary.get("recommended_platform") or "the recommended platform"
    score = product_summary.get("final_score", 0)
    confidence = product_summary.get("data_confidence_score", 0)
    advantages = product_summary.get("advantages") or []
    risks = product_summary.get("risks") or []
    advantage_text = ", ".join(advantages[:3]) if advantages else "balanced product and platform performance"
    risk_text = ", ".join(risks[:2]) if risks else "no major high-risk tag in the current sample"
    confidence_note = " Data confidence is limited, so the result should be treated cautiously." if confidence < 55 else ""
    return (
        f"{name} ranks well with a final score of {score:.2f}. "
        f"It is recommended on {platform} because of {advantage_text}. "
        f"Main watch-outs: {risk_text}.{confidence_note}"
    )


def generate_risk_explanation(risk_tags: list[str]) -> list[str]:
    if not risk_tags:
        return ["No major risk tag is present in the current sample data."]
    explanations = []
    for tag in sorted(set(str(item) for item in risk_tags)):
        if "leak" in tag or "漏水" in tag:
            explanations.append("Leak-related feedback can directly affect overnight comfort and should be checked carefully.")
        elif "return" in tag or "退货" in tag:
            explanations.append("Return or refund risk may raise the real purchase cost beyond the page price.")
        elif "space" in tag or "空间" in tag:
            explanations.append("Space overclaim feedback means the labeled capacity may be optimistic.")
        elif "odor" in tag or "异味" in tag:
            explanations.append("Odor complaints are usually medium risk but matter for first use.")
        else:
            explanations.append(f"Risk tag retained for review: {tag}.")
    return explanations

