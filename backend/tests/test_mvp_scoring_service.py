from app.services.scoring_service import _calculate_mvp_dimension_score, _calculate_mvp_product_score


def test_sparse_spec_mvp_dimension_score_stays_neutral_without_risk():
    assert _calculate_mvp_dimension_score(0.0) == 76.0
    assert _calculate_mvp_dimension_score(0.12) < 65
    assert _calculate_mvp_dimension_score(0.6) == 40.0


def test_sparse_spec_mvp_product_score_uses_calibrated_review_evidence():
    stronger_evidence = _calculate_mvp_product_score(
        price_value_score=100,
        return_after_sale_score=95,
        review_evidence_score=74,
        data_confidence_score=82,
    )
    weaker_evidence = _calculate_mvp_product_score(
        price_value_score=100,
        return_after_sale_score=85,
        review_evidence_score=70,
        data_confidence_score=82,
    )

    assert stronger_evidence > weaker_evidence
    assert stronger_evidence <= 82
