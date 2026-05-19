# CampRank 项目可用数据合同

## 当前合同覆盖：京东-only 最小可用合同

当前继续导入剩余数据时，只使用京东帐篷商品、京东评论、京东价格、京东售后服务、京东店铺名称和京东商品链接。本文档里关于淘宝/天猫、小红书、跨平台比价的内容属于历史扩展合同，本轮不执行。

当前标准 JSON 仍保留 8 个数组以兼容导入服务，但本轮要求：

- `platform_products.platform` 固定为 `JD`。
- `comments.platform` 固定为 `JD`。
- `redbook_notes` 固定为空数组。
- 缺失字段保持空值或写入 `_warnings`。
- 任何未在真实京东数据中出现的字段都不能编造。

本文档根据 CampRank 当前后端数据库模型、导入服务、评论分析、评分计算和推荐展示反推而来。给数据服务方时，请把本文档作为“必须满足的项目数据合同”。

配套文档：

- `docs/data_collection_task_list.md`：告诉数据服务方去哪些平台、找哪些商品、用哪些关键词。
- `docs/data_vendor_requirements.md`：说明交付边界、文件命名、质量报告和验收要求。
- 本文档：说明 CampRank 到底能用哪些字段，缺哪些字段会影响系统结果。

## 1. 最重要的结论

CampRank 最终需要的是一份能直接导入后端的结构化 JSON。推荐一个总文件包含以下 8 个数组：

```json
{
  "canonical_products": [],
  "platform_products": [],
  "product_specs": [],
  "product_prices": [],
  "product_benefits": [],
  "return_policies": [],
  "comments": [],
  "redbook_notes": [],
  "_warnings": []
}
```

这 8 类数据分别对应项目里的 8 条核心链路：

| 数据数组 | 用途 | 缺失后果 |
| --- | --- | --- |
| `canonical_products` | 京东同款/同套餐组归并 | 无法合并同款不同规格、颜色或套餐 |
| `platform_products` | 平台商品基础表 | 价格、参数、评论无法挂到商品上 |
| `product_specs` | 防水、防风、空间、便携、搭建、耐用评分 | 商品能力评分偏低，数据置信度下降 |
| `product_prices` | 稳定到手价、理论低价、最低价平台 | 无法比价，无法推荐购买平台 |
| `product_benefits` | 包邮、运费险、价保、官方店、赠品 | 平台购买分和售后分不准 |
| `return_policies` | 退货保障、退款风险、售后成本 | 售后风险和平台推荐不准 |
| `comments` | 评论可信度、有效差评、风险维度 | 评论分析和风险标签不足 |
| `redbook_notes` | 历史 schema 兼容字段 | 当前京东-only 流水线固定为空，不作为缺失风险 |

## 2. 同款归并数据：`canonical_products`

这是最容易被忽略但最关键的数据。CampRank 比较的是“同一款帐篷在不同平台怎么买更合适”，所以必须先把不同平台上的同款商品归到同一个 `external_group_id`。

必须字段：

```json
{
  "external_group_id": "naturehike-cloud-up-2-20d",
  "normalized_name": "Naturehike Cloud Up 2 20D",
  "brand": "Naturehike",
  "model_name": "Cloud Up 2",
  "capacity": "2 person",
  "use_case": "hiking_lightweight",
  "main_image_url": "https://example.com/image.jpg"
}
```

字段说明：

- `external_group_id`：同款归并 ID。不同平台同一款商品必须使用同一个值。
- `normalized_name`：统一商品名，建议格式为 `品牌 + 型号 + 关键版本`。
- `brand`：品牌。
- `model_name`：型号。
- `capacity`：人数或容量，例如 `2 person`、`3 person`、`family 4 person`。
- `use_case`：使用场景。
- `main_image_url`：主图，可为空，但建议提供。

建议 `use_case` 取值：

```text
newbie_weekend
overnight
hiking_lightweight
family_camping
windy_mountain
park_camping
car_camping
```

同款归并要求：

- 当前京东-only 流水线中，同一款帐篷的不同颜色、规格或套餐应共享同一个 `external_group_id`；淘宝、天猫等平台归并仅为历史扩展规划。
- 不同容量、不同面料、不同版本不能随便合并。例如 Cloud Up 2 和 Cloud Up 3 应分开。
- 商品标题相似但参数明显不同，应分开。

## 3. 平台商品数据：`platform_products`

每个平台商品都必须能通过 `external_group_id` 关联到 `canonical_products`。

必须字段：

```json
{
  "external_group_id": "naturehike-cloud-up-2-20d",
  "platform": "JD",
  "platform_product_id": "100000000000",
  "title": "挪客云尚2 20D 双人户外帐篷",
  "shop_name": "挪客京东旗舰店",
  "shop_type": "official",
  "product_url": "https://item.jd.com/100000000000.html",
  "image_url": "https://example.com/image.jpg",
  "sales_volume": 2300,
  "rating_count": 860,
  "positive_rate": 96.4
}
```

字段重要性：

| 字段 | 是否必须 | 用途 |
| --- | --- | --- |
| `external_group_id` | 必须 | 关联同款商品 |
| `platform` | 必须 | 区分 JD / TAOBAO / TMALL / REDBOOK / SMZDM / PDD |
| `platform_product_id` | 必须 | 后续价格、参数、评论全部靠它关联 |
| `title` | 必须 | 展示和人工复核 |
| `shop_name` | 强烈建议 | 平台购买分、展示 |
| `shop_type` | 强烈建议 | 判断旗舰店、官方店、普通店 |
| `product_url` | 强烈建议 | 追溯来源 |
| `image_url` | 建议 | 前端展示 |
| `sales_volume` | 建议 | 店铺/商品热度参考 |
| `rating_count` | 建议 | 评论样本可信度 |
| `positive_rate` | 建议 | 店铺口碑和平台购买分 |

平台取值：

```text
JD
TAOBAO
TMALL
PDD
SMZDM
REDBOOK
```

## 4. 商品参数数据：`product_specs`

这部分直接影响产品能力评分，包括防水、防风、空间、便携、搭建、耐用。

必须尽量提供：

```json
{
  "platform_product_id": "100000000000",
  "waterproof_index_outer": "2000mm",
  "waterproof_index_floor": "4000mm",
  "weight": "1.8kg",
  "expanded_size": "210*125*100cm",
  "packed_size": "45*15*15cm",
  "pole_material": "aluminum",
  "outer_material": "20D nylon",
  "setup_type": "manual",
  "tent_type": "double wall",
  "raw_specs_json": {}
}
```

字段和评分关系：

| 字段 | 影响 |
| --- | --- |
| `waterproof_index_outer` | 防水评分 |
| `waterproof_index_floor` | 防水评分 |
| `weight` | 便携评分 |
| `expanded_size` | 空间评分 |
| `packed_size` | 便携评分 |
| `pole_material` | 防风、耐用评分 |
| `outer_material` | 耐用、人工复核 |
| `setup_type` | 搭建评分 |
| `tent_type` | 场景判断和人工复核 |
| `raw_specs_json` | 保留原始参数，便于追溯 |

特别要求：

- 防水指数请保留数字和单位，例如 `2000mm`、`PU3000mm`。
- 重量请保留单位，例如 `1.8kg`、`1800g`。
- 尺寸请尽量是长宽高，例如 `210*125*100cm`。
- 如果页面只有参数图，请人工整理成结构化字段。
- 所有商品参数必须来自真实京东商品页、真实页面参数图或用户明确提供的参数文字；缺失字段保持空值，不允许补造。
- 页面标称参数只能作为购买风险辅助字段，不能写成实测防水、抗风、耐用、舒适度或材质强度结论。
- 当前项目可用 `python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json` 把后补参数写入 `product_specs`；脚本会先备份生产库。

## 5. 价格数据：`product_prices`

这部分直接影响稳定到手价、理论低价、最低价平台和推荐平台。

必须字段：

```json
{
  "platform_product_id": "100000000000",
  "original_price": 899,
  "current_price": 799,
  "shop_coupon_amount": 40,
  "platform_coupon_amount": 30,
  "member_coupon_amount": 0,
  "limited_coupon_amount": 0,
  "red_packet_amount": 0,
  "discount_amount": 20,
  "shipping_fee": 0,
  "coupon_text": "店铺券满799减40，平台券满500减30",
  "promotion_text": "户外节活动价",
  "price_update_time": "2026-05-01 12:00:00"
}
```

字段和计算关系：

| 字段 | 影响 |
| --- | --- |
| `current_price` | 必须，没有它无法导入价格 |
| `original_price` | 原价展示和折扣判断 |
| `shop_coupon_amount` | 稳定到手价 |
| `platform_coupon_amount` | 稳定到手价 |
| `discount_amount` | 稳定到手价 |
| `shipping_fee` | 稳定到手价 |
| `member_coupon_amount` | 理论最低价 |
| `limited_coupon_amount` | 理论最低价和优惠不确定性 |
| `red_packet_amount` | 理论最低价和优惠不确定性 |
| `coupon_text` | 优惠可靠性识别 |
| `promotion_text` | 优惠可靠性识别 |
| `price_update_time` | 数据新鲜度 |

稳定到手价大致使用：

```text
current_price - shop_coupon_amount - platform_coupon_amount - discount_amount + shipping_fee
```

理论最低价还会考虑会员券、限量券、红包等更不稳定优惠。

## 6. 平台权益数据：`product_benefits`

这部分影响平台购买分、售后分、赠品折算成本。

字段：

```json
{
  "platform_product_id": "100000000000",
  "free_shipping": true,
  "shipping_insurance": true,
  "return_7_days": true,
  "fast_refund": true,
  "price_protection": true,
  "official_store": true,
  "self_operated": false,
  "gift_items": ["地布", "修补包", "地钉"]
}
```

字段和评分关系：

| 字段 | 影响 |
| --- | --- |
| `free_shipping` | 展示和人工判断 |
| `shipping_insurance` | 售后保障 |
| `return_7_days` | 售后保障 |
| `fast_refund` | 售后服务分 |
| `price_protection` | 平台购买分 |
| `official_store` | 店铺信誉和售后保障 |
| `self_operated` | 店铺信誉和售后保障 |
| `gift_items` | 赠品价值、赠品实用性、风险调整成本 |

赠品要求：

- 请写真实赠品名称，不要只写“豪华礼包”。
- 如果赠品价值无法确认，只保留名称即可。

## 7. 退货售后数据：`return_policies`

这部分直接影响退货保障分、退货风险分、风险调整成本。

字段：

```json
{
  "platform_product_id": "100000000000",
  "return_shipping_insurance": true,
  "return_shipping_payer": "quality_issue_seller_pays",
  "return_condition_text": "支持7天无理由，质量问题商家承担运费",
  "opened_return_allowed": true,
  "used_return_allowed": false,
  "quality_issue_free_return": true,
  "refund_speed_type": "fast_refund",
  "refund_full_amount": true,
  "partial_refund_risk": false,
  "seller_return_attitude": "positive",
  "return_policy_clarity": 88
}
```

字段和评分关系：

| 字段 | 影响 |
| --- | --- |
| `return_shipping_insurance` | 退货保障分 |
| `return_shipping_payer` | 人工复核、warning |
| `return_condition_text` | 人工复核、展示、warning |
| `opened_return_allowed` | 退货条件判断 |
| `used_return_allowed` | 退货条件判断 |
| `quality_issue_free_return` | 退货保障分 |
| `refund_speed_type` | 售后体验判断 |
| `refund_full_amount` | 退款风险 |
| `partial_refund_risk` | 退款风险 |
| `seller_return_attitude` | 售后服务分 |
| `return_policy_clarity` | 退货保障分 |

`return_policy_clarity` 建议 0-100：

- 90-100：规则明确，质量问题、运费、退款方式都清楚。
- 60-89：大体清楚，但部分条件缺失。
- 30-59：规则模糊。
- 0-29：几乎无法判断。

## 8. 评论数据：`comments`

评论数据用于评论可信度、低信息评论、有效差评、风险维度和加权负面率。

字段：

```json
{
  "platform_product_id": "100000000000",
  "platform": "JD",
  "comment_text": "雨天露营一晚没有漏水，搭建大约8分钟，但两个大背包放进去有点挤。",
  "rating": 4.6,
  "comment_type": "experience",
  "has_image": true,
  "is_follow_up": false,
  "comment_time": "2026-05-01 12:00:00",
  "seller_reply": "感谢反馈"
}
```

必须字段：

- `platform_product_id`
- `platform`
- `comment_text`

强烈建议字段：

- `rating`
- `comment_type`
- `has_image`
- `is_follow_up`
- `comment_time`
- `seller_reply`

评论质量要求：

- 每个商品尽量 20-100 条公开评价摘要。
- 不要只收集好评。
- 必须保留真实使用场景、追评、带图标记、具体问题描述。
- 低信息评论可以保留，但不能全是低信息评论。

最有价值的评论类型：

| 类型 | 示例 |
| --- | --- |
| 使用场景 | 公园露营、山里过夜、海边、大风、下雨 |
| 人数信息 | 一个人、两个人、两大一小、家庭露营 |
| 时间信息 | 用了一晚、两次露营、周末使用 |
| 防水反馈 | 漏水、进水、冷凝水、睡袋湿了 |
| 防风反馈 | 风一吹就倒、杆子断、结构不稳 |
| 空间反馈 | 空间小、双人放不下、放垫子关不上门 |
| 收纳反馈 | 不好收纳、收不回去、袋子太小 |
| 搭建反馈 | 难搭、说明书看不懂、一个人搭不了 |
| 异味反馈 | 味道大、刺鼻、晾很久还有味 |
| 防晒反馈 | 太热、不防晒、黑胶没用 |
| 售后反馈 | 不给退、退款慢、运费争议、客服态度差 |

不要采集或交付：

- 用户昵称。
- 用户头像。
- 用户 ID。
- IP。
- 详细地区。
- 账号主页。
- 任何个人隐私字段。

## 9. 历史小红书口碑数据：`redbook_notes`，当前不使用

本节是历史多平台扩展合同。当前京东-only 流水线中 `redbook_notes` 必须保持为空数组，不需要采集小红书内容，不参与评分、推荐、详情页解释或数据置信度扣分。

如果后续用户明确重新开启小红书授权数据接入，才参考下面字段；否则不要执行本节。

字段：

```json
{
  "external_group_id": "naturehike-cloud-up-2-20d",
  "title": "云尚2雨天露营体验",
  "content": "这篇公开笔记主要提到轻量、防雨还可以，但前厅空间有限。",
  "comments_text": "评论里多人追问两个背包能不能放下，也有人反馈冷凝水。",
  "likes": 120,
  "favorites": 38,
  "comment_count": 16,
  "note_url": "https://example.com/redbook/note"
}
```

必须字段：

- `external_group_id`
- `title`
- `content`

强烈建议：

- `comments_text`
- `likes`
- `favorites`
- `comment_count`
- `note_url`

系统会分析：

- 是否疑似广告化内容。
- 是否有真实使用体验。
- 是否包含天气、场景、人数、搭建、收纳、缺点。
- 是否包含风险标签，例如漏水、冷凝水、空间小、退货麻烦。

请优先收集：

- 真实体验。
- 测评。
- 避坑。
- 翻车。
- 下雨、防风、收纳、搭建、空间、售后相关内容。

## 10. CampRank 评分真正需要的数据覆盖

如果想让系统结果可用，每个 `canonical_product` 最好达到以下覆盖：

| 模块 | 最低可用 | 推荐完整 |
| --- | --- | --- |
| 同款归并 | 1 个平台商品 | 2-3 个平台商品 |
| 商品参数 | 至少防水、重量、尺寸 | 防水、重量、展开/收纳、杆材、面料、搭建方式全有 |
| 价格 | 至少当前价 | 原价、当前价、优惠、运费、更新时间全有 |
| 售后 | 至少 7 天退货和运费险 | 退货条件、退款方式、质量问题退货、规则清晰度全有 |
| 评论 | 至少 10 条 | 50 条以上，包含追评/带图/负面/场景评论 |
| 小红书 | 至少 1 条 | 5 条以上，包含真实体验和避坑内容 |
| 跨平台价格 | 至少 1 个平台 | 3 个平台以上 |

数据置信度会受到这些因素影响：

- 参数完整度。
- 有效评论数。
- 疑似低质量评论比例。
- 有价格的平台数量。
- 售后字段完整度。
- 小红书样本数。
- 数据更新时间。

## 11. 完整交付建议规模

为了让项目推荐结果更稳定，建议按“同款商品组”交付，而不是只按平台商品数交付。

推荐目标：

- 30-50 个 `canonical_products`，即 30-50 款帐篷。
- 每款帐篷尽量覆盖 2 个以上平台商品。
- 总平台商品数约 80-150 个。
- 每个平台商品尽量有价格、参数、权益、售后。
- 每个平台商品尽量 20-100 条公开评价摘要。
- 每款帐篷至少 1-5 条小红书公开口碑摘要。

如果对方只给“50 个京东商品 + 50 个淘宝商品”，但没有同款归并，CampRank 仍然很难做跨平台比较。所以必须要求 `external_group_id`。

## 12. 最终交付 JSON 模板

数据服务方最终可以交付一个大 JSON：

```json
{
  "source_name": "vendor_tent_data_full",
  "canonical_products": [
    {
      "external_group_id": "naturehike-cloud-up-2-20d",
      "normalized_name": "Naturehike Cloud Up 2 20D",
      "brand": "Naturehike",
      "model_name": "Cloud Up 2",
      "capacity": "2 person",
      "use_case": "hiking_lightweight",
      "main_image_url": "https://example.com/image.jpg"
    }
  ],
  "platform_products": [],
  "product_specs": [],
  "product_prices": [],
  "product_benefits": [],
  "return_policies": [],
  "comments": [],
  "redbook_notes": [],
  "_warnings": []
}
```

也可以拆成 CSV，但文件名必须对应：

```text
canonical_products.csv
platform_products.csv
product_specs.csv
product_prices.csv
product_benefits.csv
return_policies.csv
comments.csv
redbook_notes.csv
```

## 13. 对数据服务方的硬性验收条件

以下任何一项不满足，数据就算数量很多也可能无法使用：

1. 每个 `platform_product_id` 必须稳定且唯一。
2. `product_specs`、`product_prices`、`product_benefits`、`return_policies`、`comments` 必须能通过 `platform_product_id` 找到对应 `platform_products`。
3. 每个 `platform_products.external_group_id` 必须能找到对应 `canonical_products.external_group_id`。
4. 同款商品必须正确归并，不能把不同容量、不同版本混在一起。
5. 评论必须有 `comment_text`。
6. 价格必须有 `current_price`。
7. 不允许编造缺失字段。
8. 不允许包含用户隐私字段。
9. 缺失字段、访问受限、结构变化必须写入 `_warnings` 或单独 warnings 文件。
10. 最终文件必须能被 Python 直接读取为 JSON 或 CSV。

## 14. 可以直接发给数据服务方的话

请不要只按关键词随便收集一批帐篷数据。CampRank 需要的是能导入系统的结构化数据，必须按照 `canonical_products / platform_products / product_specs / product_prices / product_benefits / return_policies / comments / redbook_notes` 八类交付。

最关键的是：

- 用 `external_group_id` 把同一款帐篷在京东、淘宝、天猫等平台归并起来。
- 用 `platform_product_id` 把商品参数、价格、售后和评论挂到对应平台商品上。
- 商品参数必须覆盖防水、重量、尺寸、杆材、面料、搭建方式。
- 价格必须覆盖当前价、优惠、运费和更新时间。
- 售后必须覆盖 7 天退货、运费险、质量问题退货、退款方式和规则清晰度。
- 评论必须保留具体使用场景和有效差评，尤其是漏水、防风、空间、收纳、搭建、异味、防晒、退货售后。
- 小红书只做口碑补充，重点收集真实体验、测评、避坑和风险反馈。

如果这些字段对不上 CampRank 的导入结构和评分逻辑，即使数据很多也用不了。
