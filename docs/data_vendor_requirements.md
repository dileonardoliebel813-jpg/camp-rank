# CampRank 平台数据接入外包需求说明

## 当前状态：本轮只要京东数据

从当前项目继续导入剩余数据时，本轮只接受京东帐篷商品、京东评论、京东价格、京东售后服务、京东店铺名称和京东商品链接。淘宝/天猫、小红书、拼多多、什么值得买相关要求暂不执行，不能混入当前数据包，也不能为了补齐展示而编造。

本轮交付必须遵守：

- 所有字段来自真实京东表格、真实京东商品页/评论页公开或授权可获取信息，或用户手工整理的真实京东数据。
- 缺失字段写空值或 warning，不允许补造销量、材质、重量、防水等级、抗风等级、检测报告、外部口碑或跨平台价格。
- `redbook_notes` 当前固定为空数组，不要求小红书笔记。
- 推荐链条只基于京东价格、京东评论和京东售后文本做购买风险辅助判断。

本文档用于向数据服务方说明 CampRank 项目需要的数据范围、字段格式、交付文件、合规边界和验收标准。字段必须以 `docs/camprank_required_data_contract.md` 为准，具体采集对象见 `docs/data_collection_task_list.md`。

重要：如果数据不能按 CampRank 的八类结构导入，即使数量很多也无法使用。请先确认能交付 `canonical_products / platform_products / product_specs / product_prices / product_benefits / return_policies / comments / redbook_notes`。

## 1. 项目背景

CampRank 是一个面向户外帐篷消费决策的系统。系统会整合京东、淘宝/天猫、小红书等平台上的商品信息、价格优惠、售后保障、商品参数和公开评价摘要，用于后续的评论质量分析、有效差评识别、价格对比、售后风险分析和推荐评分。

本项目不是单纯收集大量文本数据。交付数据必须结构化、可追溯、可导入现有 CampRank 后端。

## 2. 数据来源边界

允许的数据来源：

- 官方开放平台或授权 API。
- 用户可合法导出的平台数据。
- 公开可访问页面或接口中的低频公开数据读取结果。
- 人工整理后的公开商品、价格、参数、售后和评价摘要。

明确不需要：

- 账号密码。
- Cookie。
- 验证码处理。
- 登录态数据。
- 非公开内容。
- 用户隐私字段。
- 高频访问。
- 承诺获取全部评价。

如果遇到访问受限、登录页、验证码页、空响应、结构变化或字段不可用，应停止当前任务，并在交付数据中输出 `warnings`，不要继续尝试额外访问方式。

## 3. 完整交付目标

注意：本节以下“淘宝/天猫、小红书”相关内容为旧版多平台目标。当前项目继续导入数据时不执行；当前完整交付只要求京东数据包、京东字段覆盖报告、warnings 汇总和可导入 JSON/表格。

本次可以按“完整数据接入交付”来要求数据服务方完成。这里的“完整”指平台范围、字段范围、文件结构、导入链路、质量报告和复核材料完整，不是承诺获取平台上的全部商品或全部评价。

完整交付应覆盖：

- 京东帐篷商品数据。
- 淘宝/天猫帐篷商品数据。
- 小红书公开口碑摘要。
- 商品基础信息。
- 商品参数。
- 价格和优惠。
- 售后和退货信息。
- 公开评价摘要。
- 字段缺失和访问受限 warnings。
- 可导入 CampRank 的最终 JSON/CSV 文件。

建议完整交付数量：

- 京东：不少于 50 个真实帐篷 SKU。
- 淘宝/天猫：不少于 50 个真实帐篷商品。
- 小红书：不少于 100 条帐篷相关公开口碑摘要。
- 每个电商商品尽量提供 20-100 条公开评价摘要；如果平台只公开有限数量，则按实际可访问结果交付，并写入 warning。
- 每个商品尽量包含基础信息、参数、价格、优惠、售后和公开评价摘要。
- 每个平台需要单独提供字段缺失统计和 warnings 汇总。

建议执行顺序：

1. 先交付 3-5 个真实商品的试验包，用于验证字段、文件结构和 CampRank 导入链路。
2. 试验包验收通过后，按完整数量扩展。
3. 最终交付完整数据包、warnings 汇总、字段覆盖率报告和数据来源说明。

试验包不是最终交付规模，只用于确认数据格式能被 CampRank 正确导入，避免后续大批量返工。

## 4. 通用字段要求

所有平台商品数据应尽量包含以下字段。字段缺失时不要编造，保留为空，并在 `warnings` 中说明。

```json
{
  "platform": "JD",
  "platform_product_id": "100000000000",
  "title": "商品标题",
  "brand": "品牌",
  "model_name": "型号",
  "product_url": "商品公开链接",
  "image_url": "主图链接",
  "shop_name": "店铺名称",
  "shop_type": "店铺类型",
  "sales_volume": 0,
  "rating_count": 0,
  "positive_rate": 0.0,
  "source": "数据来源说明",
  "fetched_at": "2026-05-01T00:00:00+00:00",
  "warnings": []
}
```

平台取值建议：

- `JD`
- `TAOBAO`
- `TMALL`
- `REDBOOK`
- `SMZDM`
- `PDD`

## 5. 商品参数字段

商品参数用于判断帐篷真实适用场景。请尽量结构化，不要只交付一整段参数文本。

```json
{
  "platform_product_id": "100000000000",
  "waterproof_index_outer": "2000mm",
  "waterproof_index_floor": "4000mm",
  "weight": "1.8kg",
  "expanded_size": "210*125*100cm",
  "packed_size": "45*15*15cm",
  "pole_material": "铝合金",
  "outer_material": "20D 尼龙",
  "setup_type": "自动 / 手动 / 速开",
  "tent_type": "双层 / 单层 / 隧道帐 / 金字塔帐",
  "raw_specs_json": {}
}
```

重点字段：

- 防水指数。
- 重量。
- 展开尺寸。
- 收纳尺寸。
- 杆材。
- 面料。
- 帐篷类型。
- 搭建方式。

## 6. 价格和优惠字段

价格数据用于计算稳定到手价和理论低价。请区分当前价格、优惠券、平台补贴、运费等字段。

```json
{
  "platform_product_id": "100000000000",
  "original_price": 899.0,
  "current_price": 799.0,
  "shop_coupon_amount": 40.0,
  "platform_coupon_amount": 20.0,
  "member_coupon_amount": 0.0,
  "limited_coupon_amount": 0.0,
  "red_packet_amount": 0.0,
  "discount_amount": 0.0,
  "shipping_fee": 0.0,
  "coupon_text": "店铺券满799减40",
  "promotion_text": "平台活动说明",
  "price_update_time": "2026-05-01 12:00:00"
}
```

要求：

- 不要把所有优惠混成一个文本字段。
- 如果只能拿到优惠说明文本，也请保留 `coupon_text` 或 `promotion_text`。
- 不确定的优惠金额留空或填 `0`，并在 `warnings` 中说明。

## 7. 售后和退货字段

售后字段用于判断平台购买风险。

```json
{
  "platform_product_id": "100000000000",
  "free_shipping": true,
  "shipping_insurance": true,
  "return_7_days": true,
  "fast_refund": false,
  "price_protection": true,
  "official_store": true,
  "self_operated": false,
  "return_shipping_payer": "seller_for_quality_issue",
  "return_condition_text": "支持7天无理由，质量问题商家承担运费",
  "opened_return_allowed": true,
  "used_return_allowed": false,
  "quality_issue_free_return": true,
  "refund_speed_type": "fast_refund",
  "refund_full_amount": true,
  "partial_refund_risk": false,
  "seller_return_attitude": "clear",
  "return_policy_clarity": 0.9
}
```

字段缺失时不要推测，保留为空并写入 warning。

## 8. 京东公开评价摘要字段

京东评价数据只需要公开评价摘要，不要求全部评价。

推荐文件名：

```text
jd_comments_<sku_id>.json
```

推荐 JSON 结构：

```json
{
  "source_name": "jd_public_comment",
  "platform": "JD",
  "sku_id": "100000000000",
  "fetched_at": "2026-05-01T00:00:00+00:00",
  "max_pages": 3,
  "page_size": 10,
  "comments": [
    {
      "platform": "JD",
      "platform_product_id": "100000000000",
      "comment_text": "评价正文",
      "rating": 5,
      "comment_type": "positive",
      "has_image": true,
      "is_follow_up": false,
      "follow_up_text": "",
      "comment_time": "2026-05-01 12:00:00",
      "user_tags": ["绿色", "双人款"],
      "seller_reply": "商家回复内容",
      "source": "jd_public_comment",
      "raw_comment_json": {}
    }
  ],
  "warnings": []
}
```

评论字段说明：

- `platform`：固定为 `JD`。
- `platform_product_id`：京东 SKU ID。
- `comment_text`：评价正文，不能为空。
- `rating`：评价星级。
- `comment_type`：可取 `positive`、`neutral`、`negative`、`experience`、`unknown`。
- `has_image`：是否带图。
- `is_follow_up`：是否包含追评。
- `follow_up_text`：追评内容。
- `comment_time`：评价时间。
- `user_tags`：公开可见的规格、颜色、标签等，不包含用户身份信息。
- `seller_reply`：商家回复。
- `raw_comment_json`：可保留非隐私原始字段，方便追溯。

不要包含：

- 用户昵称。
- 用户头像。
- 用户 ID。
- IP。
- 详细地区。
- 账号主页。
- 任何个人隐私字段。

## 9. 淘宝/天猫商品字段

淘宝/天猫第一阶段重点是商品基础信息、价格、优惠、参数和售后，不要求评论全量数据。

```json
{
  "platform": "TAOBAO",
  "platform_product_id": "item_id_or_num_iid",
  "title": "商品标题",
  "brand": "品牌",
  "model_name": "型号",
  "product_url": "公开商品链接",
  "image_url": "主图链接",
  "shop_name": "店铺名称",
  "shop_type": "淘宝店 / 天猫店 / 官方旗舰店",
  "current_price": 0.0,
  "original_price": 0.0,
  "coupon_text": "优惠说明",
  "promotion_text": "活动说明",
  "sales_volume": 0,
  "rating_count": 0,
  "positive_rate": 0.0,
  "raw_source_json": {},
  "warnings": []
}
```

如果是天猫，`platform` 使用 `TMALL`。

## 10. 小红书公开口碑摘要字段

小红书数据只作为口碑补充，不作为价格、商品参数或售后政策的权威来源。

```json
{
  "source_name": "redbook_public_summary",
  "platform": "REDBOOK",
  "notes": [
    {
      "note_url": "公开笔记链接",
      "title": "笔记标题",
      "content": "笔记正文摘要",
      "comments_text": "公开评论摘要",
      "likes": 0,
      "favorites": 0,
      "comment_count": 0,
      "related_brand": "品牌",
      "related_model_name": "型号",
      "source": "redbook_public_summary",
      "fetched_at": "2026-05-01T00:00:00+00:00",
      "warnings": []
    }
  ]
}
```

不要采集：

- 账号隐私信息。
- 用户主页信息。
- 用户 ID。
- 头像。
- 私信或非公开内容。
- 登录态可见内容。

## 11. CampRank 可导入的组合 JSON 示例

如果数据服务方希望一次性交付商品、价格、参数、售后和评论，可使用下面的组合结构：

```json
{
  "source_name": "vendor_tent_data_batch_001",
  "platform_products": [
    {
      "external_group_id": "naturehike-cloud-up-2",
      "platform": "JD",
      "platform_product_id": "100000000000",
      "title": "挪客云尚2双人帐篷",
      "brand": "Naturehike",
      "model_name": "Cloud Up 2",
      "shop_name": "品牌旗舰店",
      "shop_type": "official",
      "product_url": "https://example.com/item",
      "image_url": "https://example.com/image.jpg",
      "sales_volume": 1000,
      "rating_count": 500,
      "positive_rate": 0.96
    }
  ],
  "product_specs": [
    {
      "platform_product_id": "100000000000",
      "waterproof_index_outer": "2000mm",
      "waterproof_index_floor": "4000mm",
      "weight": "1.8kg",
      "expanded_size": "210*125*100cm",
      "packed_size": "45*15*15cm",
      "pole_material": "铝合金",
      "outer_material": "20D尼龙"
    }
  ],
  "product_prices": [
    {
      "platform_product_id": "100000000000",
      "original_price": 899,
      "current_price": 799,
      "shop_coupon_amount": 40,
      "platform_coupon_amount": 0,
      "shipping_fee": 0,
      "coupon_text": "满799减40",
      "price_update_time": "2026-05-01 12:00:00"
    }
  ],
  "return_policies": [
    {
      "platform_product_id": "100000000000",
      "return_7_days": true,
      "shipping_insurance": true,
      "quality_issue_free_return": true,
      "return_condition_text": "质量问题支持退货"
    }
  ],
  "comments": [
    {
      "platform": "JD",
      "platform_product_id": "100000000000",
      "comment_text": "雨天露营一晚没有漏水，收纳体积也可以接受。",
      "rating": 5,
      "comment_type": "experience",
      "has_image": true,
      "is_follow_up": false,
      "follow_up_text": "",
      "comment_time": "2026-05-01 12:00:00",
      "source": "jd_public_comment"
    }
  ],
  "warnings": []
}
```

## 12. 文件命名建议

完整交付建议文件：

```text
jd_tents_products_full.json
jd_comments_full.json
taobao_tents_products_full.json
tmall_tents_products_full.json
redbook_tents_notes_full.json
multi_platform_tents_full.json
field_coverage_report.json
vendor_data_warnings.md
```

如果分批交付，请使用批次编号：

```text
jd_tents_products_batch_001.json
jd_comments_batch_001.json
taobao_tents_products_batch_001.json
tmall_tents_products_batch_001.json
redbook_tents_notes_batch_001.json
```

如果某个 SKU 单独交付公开评价摘要，也可以使用：

```text
jd_comments_<sku_id>.json
```

最终交付时需要提供一个总索引文件：

```text
manifest.json
```

`manifest.json` 应说明每个文件的数据来源、平台、记录数量、生成时间和 warnings 数量。

示例：

```json
{
  "generated_at": "2026-05-01T00:00:00+00:00",
  "files": [
    {
      "path": "jd_tents_products_full.json",
      "platform": "JD",
      "record_type": "products",
      "record_count": 50,
      "warnings_count": 3
    },
    {
      "path": "jd_comments_full.json",
      "platform": "JD",
      "record_type": "comments",
      "record_count": 2500,
      "warnings_count": 12
    }
  ]
}
```

## 13. warnings 要求

如果字段缺失、读取受限、评论数量不足或结构变化，请在 JSON 中写入 `warnings`。

示例：

```json
{
  "warnings": [
    "comments limited by max_pages=3",
    "missing waterproof_index_outer",
    "return policy text unavailable",
    "public comment summary unavailable for sku_id=100000000000"
  ]
}
```

不要为了字段完整而补假数据。

## 14. 验收标准

交付后 CampRank 会按以下标准验收：

1. JSON 或 CSV 文件可以被 Python 正常读取。
2. 每个商品必须有 `platform` 和 `platform_product_id`。
3. 评论必须有 `comment_text`，否则不会导入。
4. 价格、优惠、参数、售后和评论必须结构化。
5. 不包含账号、Cookie、用户 ID、头像、昵称、IP 等隐私字段。
6. 字段缺失必须通过 `warnings` 说明。
7. 数据可以导入 CampRank 后端现有表。
8. 导入后可以运行：

```bash
cd backend
python scripts/analyze_comments.py
python scripts/calculate_scores.py
python -m pytest
```

项目根目录还会运行：

```bash
python scripts/check_all.py
```

完整交付还需要额外验收：

1. 至少覆盖京东、淘宝/天猫、小红书三个来源。
2. 商品、评论、价格、参数、售后文件之间可以通过 `platform_product_id` 对齐。
3. 每个平台需要提供字段覆盖率报告。
4. 每个平台需要提供 warnings 汇总。
5. 每条记录需要保留 `source` 或 `fetched_at`，方便追溯。
6. 评论摘要可以进入现有 `Comment` 表，并能继续运行评论质量分析。
7. 商品价格、参数和售后字段可以进入后续评分流程。

字段覆盖率报告建议结构：

```json
{
  "platform": "JD",
  "record_count": 50,
  "field_coverage": {
    "platform_product_id": 1.0,
    "title": 1.0,
    "brand": 0.92,
    "current_price": 0.98,
    "waterproof_index_outer": 0.76,
    "return_condition_text": 0.64,
    "comment_text": 1.0
  },
  "warnings": [
    "some products missing waterproof_index_outer",
    "some products missing return_condition_text"
  ]
}
```

## 15. 给数据服务方的简短说明

请按本文档提供结构化 JSON/CSV 数据。我们需要的是能导入 CampRank 系统的完整标准平台数据，不是临时文本集合。数据重点是户外帐篷商品、价格、优惠、参数、售后和公开评价摘要。请只使用公开可访问或授权可获取的数据，不使用账号、Cookie、验证码、登录态或非公开内容。评论不要求全部，但每个商品请尽量提供公开可访问范围内的足量摘要样本，并说明页数、数量和缺失原因。遇到访问受限、空响应或结构异常时，请停止并输出 warning。
