# 退货、退款与售后风险方案

## 1. 退货比较必要性

帐篷属于大件户外用品，漏水、异味、空间虚标、杆子断、防晒差等问题经常在使用后才发现，因此退货保障必须作为核心指标。

如果平台价格低，但拆封后不能退、质量问题退货要买家承担运费、退款速度慢或客服扯皮，用户的实际购买成本会显著上升。CampRank 必须把退货风险折算进平台推荐，而不是只比较页面价格。

## 2. 退货字段

平台报价和店铺售后信息应尽量标准化为以下字段：

- `return_7_days`：是否支持 7 天无理由。
- `return_shipping_insurance`：是否有运费险。
- `return_shipping_payer`：退货运费承担方。
- `return_condition_text`：退货条件原文。
- `opened_return_allowed`：拆封后是否允许退。
- `used_return_allowed`：使用后是否允许退。
- `quality_issue_free_return`：质量问题是否免费退。
- `refund_speed_type`：退款速度类型，例如极速退款、普通退款、验货后退款。
- `refund_full_amount`：是否支持全额退款。
- `partial_refund_risk`：是否存在只退部分金额风险。
- `seller_return_attitude`：卖家退货态度。
- `return_policy_clarity`：退货政策清晰度。
- `return_negative_rate`：退货负面率。
- `refund_dispute_rate`：退款争议率。

缺失字段不得默认视为良好，应降低 DataConfidenceScore。

## 3. 退货关键词

### 3.1 退货困难类

- 不给退。
- 拆了不给退。
- 用过不给退。
- 质量问题也不给退。
- 退货麻烦。
- 来回扯皮。
- 客服一直拖。
- 要求自己举证。

### 3.2 退款金额类

- 少退款。
- 只退一部分。
- 扣运费。
- 扣包装费。
- 扣折旧费。
- 退款金额不对。
- 赠品要折价扣款。

### 3.3 退款速度类

- 退款慢。
- 一直不到账。
- 等验货很久。
- 催了才退。
- 审核很久。

### 3.4 运费争议类

- 运费自理。
- 质量问题还要我出运费。
- 运费险不赔。
- 大件运费很贵。
- 退回去运费高。

### 3.5 客服态度类

- 客服不理。
- 客服敷衍。
- 客服推责任。
- 客服态度差。
- 售后没人处理。

## 4. ReturnProtectionScore

ReturnProtectionScore =

- 0.25 × 7天无理由保障
- 0.20 × 运费险 / 免费退货
- 0.20 × 质量问题免费退
- 0.15 × 极速退款
- 0.10 × 退货政策清晰度
- 0.10 × 官方/自营保障

建议输出 0-100 分。官方/自营保障不是替代退货政策的理由，只能作为其中一个加分项。

## 5. ReturnRiskScore

ReturnRiskScore =

- 0.30 × 退货困难负面率
- 0.25 × 退款金额争议率
- 0.20 × 退款速度负面率
- 0.15 × 运费争议率
- 0.10 × 客服态度负面率

ReturnRiskScore 越高，说明售后风险越高。它应来自有效差评加权后的负面率，而不是简单统计差评数量。

## 6. ReturnRiskCost

ReturnRiskCost = StableFinalPrice × ReturnRiskRate

ReturnRiskCost 是把售后不确定性折算成金额，用于平台间比较。它不是实际一定发生的费用，而是风险成本估计。

## 7. ReturnRiskRate 分层

- 0-15：0.02
- 15-30：0.05
- 30-50：0.10
- 50-70：0.18
- 70+：0.30

示例：

- StableFinalPrice 为 500 元，ReturnRiskScore 为 42，则 ReturnRiskRate 为 0.10，ReturnRiskCost 为 50 元。
- 这意味着该平台虽然页面价格是 500 元，但风险调整后需要额外考虑 50 元的售后不确定性。

## 8. RiskAdjustedCost

RiskAdjustedCost =

StableFinalPrice
- 0.5 × GiftEstimatedValue
+ CouponUncertaintyCost
+ ReturnRiskCost
+ ServiceDisputeCost

字段说明：

- GiftEstimatedValue 使用保守估值。
- CouponUncertaintyCost 来自优惠不稳定、抢券、复杂凑单等不确定性。
- ReturnRiskCost 来自退货和退款风险。
- ServiceDisputeCost 来自客服扯皮、店铺信誉和售后争议。

平台推荐应优先使用 RiskAdjustedCost，而不是只用页面价格。

## 9. 退货风险标签

正向标签：

- 退货友好。
- 支持极速退款。
- 有运费险。
- 质量问题免费退。

负向标签：

- 退货政策不清晰。
- 拆封后退货风险。
- 退款慢风险。
- 退款少风险。
- 客服扯皮风险。
- 退货运费风险。

## 10. 推荐解释要求

当 recommended_platform 不是 lowest_price_platform 时，必须解释原因。

示例：

- “拼多多理论低价低 35 元，但该链接退货政策不清晰，且售后差评中退款慢和运费争议较集中；京东自营价格略高，但支持运费险、极速退款和价保，因此综合推荐京东。”

解释必须具体到风险类型，不能只写“综合更好”。
