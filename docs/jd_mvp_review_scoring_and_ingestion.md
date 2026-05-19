# 京东帐篷评论 MVP 接入与客观评分说明

当前本文档是后续导入数据的主执行文档之一。当前只接受京东数据，不接入小红书、淘宝/天猫、拼多多或什么值得买评论；`redbook_notes` 固定为空数组。所有评分和推荐必须来自真实京东价格、京东评论、京东售后文本、店铺名称、商品链接，以及用户提供或真实页面可见的商品参数文字，缺失字段不能补造。

本文档说明当前京东帐篷商品如何从本地表格进入 CampRank，并说明后续新整理的数据如何直接复用同一条现有通道。

## 1. 项目背景

CampRank 不是单纯的数据读取项目，而是“户外帐篷消费决策系统”。系统要回答两个问题：

1. 哪款帐篷更值得买。
2. 同一款帐篷在哪个平台买更合适。

所以评论不能直接当成最终结论。评论进入系统后，只作为“风险证据”参与分析，必须经过低信息评论识别、疑似异常评论降权、有效差评识别、维度风险归类、样本结构修正和数据置信度计算。

当前 MVP 处理你已经整理出的京东帐篷商品。脚本会按真实 `当前价格` 分组生成同款组，默认导入表格里所有真实价格组；只有手动传 `--price-groups` 时才限制指定价格组。它的目标是跑通：

本地表格 -> 标准 JSON -> 现有导入服务 -> Comment 表 -> analyze_comments.py -> calculate_scores.py -> 前端展示

## 2. 当前 MVP 数据来源

源文件：

```bash
data.xlsx
```

生成后的标准 JSON：

```bash
backend/data/real_samples/jd_tents_mvp.json
```

当前商品：

| 字段 | 说明 |
| --- | --- |
| SKU / platform_product_id | 来自京东表格的真实 `pid` |
| 价格分组 | 来自京东表格的真实 `当前价格` |
| 去重后评论数 | 来自表格中真实评论去重结果 |
| 用途 | 生成京东同款组、评论风险分析、售后风险分析和前端购买建议 |

说明：

- 当前价格按表格中该商品可见最低价格分组。
- 不补造防水指数、重量、尺寸、杆材等硬参数；只有商品页参数文字或用户提供的真实参数图整理结果里明确出现时，才允许写入 `product_specs`。
- 昵称、评论 ID、图片 URL、视频 URL 等个人或非必要字段不进入项目。
- 表格中的追评会合并进 `comment_text`，同时保留 `is_follow_up=true`。

## 3. 表格需要包含的字段

后续你的数据只要整理成同样字段，就可以直接走现有脚本：

| 表格字段 | 项目用途 |
| --- | --- |
| SKU | 商品标题/规格信息，保留为原始规格参考 |
| pid | 商品平台 ID，进入 `Product.platform_product_id` |
| 商家回复 | 进入 `Comment.seller_reply` |
| 图片数量 | 转成 `Comment.has_image` |
| 得分类型 | 辅助判断 positive / neutral / negative |
| 评论内容 | 进入 `Comment.comment_text` |
| 评论得分 | 进入 `Comment.rating` |
| 评论时间 | 进入 `Comment.comment_time` |
| 追评 | 合并为后续体验证据 |
| 追评时间 | 如果存在，优先作为评论时间 |
| 当前价格 | 进入价格表，用于 MVP 价格分组 |
| 商品链接 | 进入 `Product.product_url` |
| 售后服务 | 进入 `return_policies.return_condition_text`，用于前端商品卡片展示、退换/售后字段和平台购买风险字段；支持 `同Y2` 这类同表单元格引用简写 |
| 店铺名称 / 商品名称 | 进入 `platform_products.shop_name`，用于前端商品卡片和比价表展示；优先使用 `店铺名称`，如果表格没有该列，则使用 `商品名称`；两列都支持 `同Z2` 这类同表单元格引用简写 |

如果另有商品参数文字，使用独立 JSON 导入，不要塞进评论表格里：

```bash
python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json
```

本次已使用的标准样例是 `backend/data/product_parameters_20260519.json`。参数 JSON 必须用真实 `platform_product_id` 关联商品，`null` 表示当前没有真实字段；不能为了评分或展示效果补齐不存在的重量、尺寸、PU 指数、材质或配件。

## 4. 清洗规则

当前脚本 `backend/scripts/build_jd_mvp_from_xlsx.py` 做以下清洗：

1. 读取 `data.xlsx` 的 `data` 工作表。
2. 按 `当前价格` 获取全部真实价格分组，作为京东候选同款组；只有命令手动传入 `--price-groups` 时才限制指定价格组。
3. 每个价格分组内选择出现最多的 `pid` 作为该组代表商品 ID。
4. 同一组内按“评论正文 + 追评 + 购买规格”去重。
5. 去除空评论。
6. 图片数量大于 0 时，设置 `has_image=true`。
7. 有追评时，设置 `is_follow_up=true`。
8. 不采集、不导入昵称、头像、评论 ID、图片 URL、视频 URL 等字段。
9. 缺失硬参数时，只写入 `raw_specs_json`，并在导入报告中产生 warning。
10. 表格存在 `店铺名称` 时，按价格分组取高频店铺名写入平台商品；前端直接使用该店铺名。
11. 如果表格没有单独 `店铺名称`，但存在 `商品名称`，脚本使用 `商品名称` 作为当前前端显示名和 `shop_name` 来源，不补造店铺字段。
12. `店铺名称` 或 `商品名称` 如果写成 `同Z2`，脚本会读取同一工作表 `Z2` 单元格的完整内容，不会把 `同Z2` 原样展示到前端。
13. `售后服务` 如果写成 `同Y2`，脚本会读取同一工作表 `Y2` 单元格的完整内容，不会把 `同Y2` 原样展示到前端。

## 5. 标准 JSON 结构

脚本会生成 CampRank 现有导入服务能识别的 JSON：

```json
{
  "source_name": "jd_manual_xlsx_mvp",
  "canonical_products": [],
  "platform_products": [],
  "product_specs": [],
  "product_prices": [],
  "product_benefits": [],
  "return_policies": [],
  "comments": [],
  "redbook_notes": []
}
```

其中评论字段会转成：

```json
{
  "platform_product_id": "10096493107826",
  "platform": "JD",
  "comment_text": "...",
  "rating": 5,
  "comment_type": "positive",
  "has_image": true,
  "is_follow_up": false,
  "comment_time": "2026-01-01",
  "seller_reply": null
}
```

## 6. 执行命令

推荐从项目根目录使用一键生产线。默认会把新表格追加或更新到长期商品库里，不删除历史商品，也不重建数据库：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx
```

如果需要指定本次文件名：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data3-5.xlsx
```

只有用户明确说“清空、重建、只保留本次数据、替换当前商品库”时，才允许加 `--reset-db`。使用 `--reset-db` 前必须确认用户意图，因为它会用本次数据替换当前商品库；脚本会先备份旧数据库。

从项目根目录进入后端：

```bash
cd backend
```

生成标准 JSON：

```bash
python scripts/build_jd_mvp_from_xlsx.py --input ../data.xlsx --output data/real_samples/jd_tents_mvp.json --sheet data
```

导入数据库：

```bash
python scripts/import_real_data.py --json data/real_samples/jd_tents_mvp.json --source-name jd_manual_xlsx_mvp
```

执行评论分析：

```bash
python scripts/analyze_comments.py
```

执行评分：

```bash
python scripts/calculate_scores.py
```

运行测试：

```bash
python -m pytest
```

回到项目根目录运行一键检查：

```bash
cd ..
python scripts/check_all.py
```

## 7. 评论证据评分机制

为了解决“评论主观”和“不同商品好评/差评比例不同”的问题，当前 MVP 不按原始好评率直接评分。

系统会先把评论分为三层：

| 评论层 | 标准化权重 |
| --- | ---: |
| positive | 45% |
| neutral | 20% |
| negative | 35% |

这样即使某个商品采集到的负面评论更多，也不会直接因为样本结构不同而被简单压低；系统会同时输出：

- `raw_review_distribution`：原始评论分布。
- `raw_review_ratio`：原始比例。
- `normalized_review_weights`：统一比较权重。
- `sampling_bias_index`：样本结构偏差指数。
- `evidence_confidence_score`：评论证据置信度。
- `review_sample_warnings`：样本不足或结构异常提示。

风险维度包括：

- waterproof：防水/进水/冷凝水。
- windproof：防风/支架/结构稳定。
- space：空间虚标/压抑。
- storage：收纳难度。
- setup：搭建难度。
- smell_heat：异味、闷热、防晒相关体验。
- durability：材质、做工、损坏、耐用度。
- return_after_sale：退换、售后、退款、客服。

## 8. MVP 评分边界

如果当前只有评论表格、没有真实商品页参数，则 MVP 模式采用保守评分：

1. 维度分从中性基线开始。
2. 评论风险证据越强，维度分越低。
3. “没有看到风险评论”不等于“该维度表现优秀”。
4. 最终分由校准后的评论证据、售后、价格、页面参数字段和数据置信度综合计算。
5. 缺硬参数时不输出高置信度的强结论。

如果后续补充了商品参数，评分链路会读取 `product_specs` 中的真实字段，例如重量、展开尺寸、收纳尺寸、PU 指数、杆材、面料和搭建方式。参数来自页面标称或用户提供的参数文字，只能辅助判断空间、便携、搭建和页面防护标称，不能写成实测防水、防风、耐用或舒适度结论。

当前 MVP 最终分公式在 `backend/app/services/scoring_service.py` 中：

```text
MVPFinalScore =
0.65 * ReviewEvidenceScore
+ 0.13 * ReturnAfterSaleScore
+ 0.12 * PriceValueScore
+ 0.10 * DataConfidenceScore
```

并设置最高上限，避免在硬参数不足时给出过强结论。

## 9. 前端展示

前端评论风险面板已经展示：

- 评论证据分。
- 证据置信度。
- 采样偏差指数。
- 原始评论分布。
- 标准化权重。
- 低信息评论数。
- 疑似异常评论数。
- 有效差评数。
- 风险维度分布。
- 样本 warning。

这样面试展示时可以说明：系统不是直接相信评论，而是把评论转成可解释、可比较、可降权的风险证据。

当前前端商品卡片展示规则：

- `当前价格` 在前端统一叫“最低套餐价”。
- 店铺名优先来自表格 `店铺名称` 列；如果没有该列，则来自真实 `商品名称` 列，不再使用占位店铺名。
- 售后服务来自表格 `售后服务` 列，商品卡片第一行展示“店铺 / 售后服务”。
- 商品参数来自 `product_specs` 和 `parameter_analysis`。后端会生成 `parameter_analysis.decision`，卡片展示“参数判断”，包括空间判断、场景判断、待确认参数和一两条原始页面参数；完整参数、参数分数和边界说明放进“查看推荐证据”或详情页“查看调查数据”。
- 参数判断固定规则：有展开长宽时按面积解释空间；小于 3㎡ = 空间偏小，更适合单人或临时遮阳；3㎡ 到小于 5㎡ = 适合 1-2 人短途休闲；5㎡ 到 8㎡ = 适合 2-3 人或小家庭休闲；大于 8㎡ = 空间较大，适合多人或家庭露营，但要关注重量和搭建难度。缺少防水指数、重量、材质、搭建方式时，必须显示“待确认参数”，不能补造。
- 首页不展示“原始规格样例”列表。
- 首页不展示“京东 SKU / pid”栏。
- 首页不展示“风险后预估成本”，只保留购买推荐、适合场景、主要风险和判断可信度。

## 10. 后续数据如何直接进入项目

后续你整理新的京东帐篷数据时，按以下要求准备：

1. 保持与 `data.xlsx` 相同字段名。
2. 每条评论至少保留：`pid`、`评论内容`、`评论得分`、`评论时间`、`当前价格`。
3. 如果有追评、图片数量、售后服务、店铺名称或商品名称，尽量保留。
4. 不需要保留昵称、头像、账号主页、评论 ID、图片 URL、视频 URL。
5. 如果有商品参数文字，整理成 `backend/data/product_parameters_YYYYMMDD.json`，只填真实出现的字段。
6. 生成 JSON 后必须先导入，再运行评论分析和评分。

最短路径：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx
```

补充商品参数时：

```bash
python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json
```

如果后续不是京东，而是其他平台，也不要直接改评分逻辑；先把原始表格转换成 CampRank 的统一 JSON 字段，再进入同一套导入、评论分析和评分流程。
