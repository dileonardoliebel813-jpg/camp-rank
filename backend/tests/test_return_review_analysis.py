from app.nlp.return_review_analyzer import analyze_return_review


def test_refund_speed_issue_detected():
    assert analyze_return_review("退款慢，等了很久")["refund_speed_issue"] is True


def test_refund_amount_issue_detected():
    assert analyze_return_review("只退一部分，退款少")["refund_amount_issue"] is True


def test_shipping_fee_dispute_detected():
    assert analyze_return_review("退货运费自己出")["shipping_fee_dispute"] is True


def test_bad_customer_service_detected():
    assert analyze_return_review("客服不理人")["bad_customer_service"] is True

