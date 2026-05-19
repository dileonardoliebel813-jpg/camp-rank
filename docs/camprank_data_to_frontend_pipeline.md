# CampRank 数据到前端完整流水线

本文档用于固定 CampRank MVP 的项目层级、数据进入方式、后端处理步骤、前端展示规则和验收命令。以后每次有新的帐篷数据进来，优先按本文档执行，不要临时改散乱脚本，也不要跳过现有 ingestion、comment analysis、scoring 和 frontend API 闭环。

## 0. 当前数据范围硬规则：只用京东真实数据

当前流水线只接受京东帐篷表格或由京东表格转换出的标准 JSON。不要接入小红书评论/笔记，不要接入淘宝/天猫评论，不要用拼多多、什么值得买或其他平台补齐当前推荐内容。

所有后端分析和前端展示必须满足：

- 只基于真实导入的京东价格、京东评论、京东售后服务、店铺名称、商品链接和清洗后规格摘要。
- 不允许编造淘宝价格、小红书口碑、销量、材质、重量、防水等级、抗风等级、检测报告、排除数量或售后承诺。
- 如果商品页或你提供的参数图里有真实的页面参数文字，可以进入 `product_specs` 和前端商品参数分析；这些参数只能作为页面标称或按尺寸推算，不得写成实测防水、抗风、耐用或舒适度结论。
- 当前标准 JSON 保留 `redbook_notes: []` 只是为了兼容旧 schema；京东-only 数据中必须为空数组，不参与评分、排序、详情页结论或推荐文案。
- 如果某个事实字段没有返回，前端写“当前接口未返回”，后端保留空值或 warning。
- 当前推荐只能表达为“购买风险辅助判断”，不能表达为“性能实测结论”。
- 生产库是长期累计商品库，已经跑通全链路且由用户确认的历史商品必须保留；新增数据默认只追加或更新，不能因为接入新表格而覆盖历史商品。当前确认的历史恢复来源是 `backend/data/import_reports/camp_rank_backup_20260519_152836.db`。不要把 4 条评论的旧 sample/mock 占位批次误当成历史商品恢复或推荐，尤其是 `RainGuard`、`BudgetGo`、`FamilyHall`、`StarNest`、`StormMax`、`FreshAir`、`LowCost`、`SafeCamp` 这批演示名。只有用户明确指定要清理某批商品时，才允许先备份 `backend/camp_rank.db` 到 `backend/data/import_reports/`，再删除用户指定商品及其关联记录。

## 1. 当前项目定位

CampRank 当前不是“商品质量评测系统”，而是“基于价格、评论风险和售后保障的购买风险辅助决策系统”。

当前可用数据：

- 价格：最低套餐价、理论低价、优惠稳定性、售后风险成本。
- 评论：评论正文、评分、追评、图片标记、评论时间、商家回复。
- 售后：店铺名称、退换、运费、退款速度、售后争议、服务保障。
- 商品参数：用户提供或真实页面可见的重量、展开/收纳尺寸、面料、杆材、PU 指数、搭建方式等页面标称字段。

当前不能证明：

- 帐篷实测防水性能。
- 帐篷实测抗风性能。
- 帐杆材质真实强度。
- 面料参数真实性。
- 重量和收纳体积真实性。
- 官方检测报告结论。

前端表达必须始终围绕：

- 更稳
- 更便宜
- 适合谁
- 风险在哪里
- 为什么不是最低价

## 2. 项目层级固定说明

```text
camp-rank/
  README.md
  AGENTS.md
  data.xlsx
  scripts/
    check_all.py
    run_mvp_data_pipeline.py
  docs/
    camprank_data_to_frontend_pipeline.md
    jd_mvp_review_scoring_and_ingestion.md
    platform_field_mapping.md
    real_data_ingestion_plan.md
    review_quality_control.md
    scoring_model.md
    testing_strategy.md
  backend/
    app/
      api/
      ingestion/
      models/
      nlp/
      scoring/
      services/
      schemas/
    data/
      real_samples/
      import_reports/
    scripts/
      build_jd_mvp_from_xlsx.py
      import_real_data.py
      run_real_data_pipeline.py
      analyze_comments.py
      calculate_scores.py
      init_db.py
      seed_sample_data.py
    tests/
  frontend/
    src/
      api/
      components/
      pages/
      utils/
      App.jsx
      main.jsx
      styles.css
```

不能随意新增的位置：

- 不要在根目录新增临时 `jd_spider.py`、`clean_data.py`、`test_frontend.py` 这类散乱脚本。
- 不要把数据清洗逻辑写进前端。
- 不要把评分逻辑写进前端。
- 不要直接改数据库表数据绕过导入服务。
- 不要把一次性测试输出、截图、日志长期放在根目录。

允许新增的位置：

- 新的数据源适配：`backend/app/ingestion/`
- 新的后端执行脚本：`backend/scripts/`
- 项目级一键流程脚本：`scripts/`
- 新的前端页面：`frontend/src/pages/`
- 新的前端组件：`frontend/src/components/`
- 新的长期文档：`docs/`
- 新的测试：`backend/tests/`

## 3. 一键执行方式

以后如果你拿到的是和当前 `data.xlsx` 同结构的京东帐篷评论表格，直接在项目根目录执行：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx
```

这条命令会自动执行：

1. 表格清洗并生成标准 JSON。
2. 追加或更新数据库中的同款组。
3. 评论分析。
4. 评分计算。
5. 后端测试和前端构建检查。

默认清洗规则会导入表格中全部真实商品。商品边界优先使用表格里的 `店铺名称` / `商品名称` 这类真实商品显示名；同一商品下不同 SKU、颜色、套餐链接会归并到同一个候选商品，不会拆成多个商品；同价但显示名不同的商品会保留为不同候选商品。`当前价格` 仍作为“最低套餐价”和价格筛选依据。只有明确传入 `--price-groups` 时，才限制指定价格范围内的商品。

如果同一批商品还补充了商品页参数文字或参数图整理结果，先把参数整理成 `backend/data/product_parameters_YYYYMMDD.json`，再执行：

```bash
python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json
```

参数 JSON 必须用真实 `platform_product_id` 关联当前库里的京东商品。结构化字段只填写用户提供文字里明确出现的重量、尺寸、面料、杆材、防水指数等；拿不到的字段保持 `null`。脚本会先备份 `backend/camp_rank.db` 到 `backend/data/import_reports/`，再更新 `product_specs.raw_specs_json` 和结构化参数字段。不要用这个脚本补造缺失参数。

参数导入后的解释工作流固定如下：

1. 后端 `backend/app/services/spec_analysis_service.py` 读取 `product_specs` 和 `raw_specs_json`，生成 `parameter_analysis.summary`、`highlights`、`cautions`、`facts`、`scores` 和 `decision`。
2. `decision.space_judgment` 只按真实展开长宽推算面积解释空间：小于 3㎡ = 空间偏小，更适合单人或临时遮阳；3㎡ 到小于 5㎡ = 适合 1-2 人短途休闲；5㎡ 到 8㎡ = 适合 2-3 人或小家庭休闲；大于 8㎡ = 空间较大，适合多人或家庭露营，但要关注重量和搭建难度。
3. `decision.scene_judgment` 只能从真实商品名、页面参数文字、标称功能和帐篷类型中提取公园、沙滩、遮阳、野餐、露营、过夜、天幕等词；没有文字依据时必须写“待确认”或保守短途休闲判断。
4. `decision.missing_parameters` 固定检查防水指数、重量、材质、搭建方式。缺失项必须在前端展示为“待确认参数”，不能隐藏、不能补造、不能因为缺失就直接判定商品差。
5. 前端购买决策卡和证据弹窗必须表达：商品参数决定适不适合，用户评论验证有没有坑。参数证据来自页面标称或尺寸推算，评论证据来自京东评论样本和风险维度，二者都不能写成实测防水、抗风、耐用或舒适度结论。

一键命令默认代表“把这次真实京东表格追加进长期商品库”，不会清空旧商品，也不会重建数据库。只有用户明确说“清空、重建、只保留本次数据、替换当前商品库”时，才使用：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx --reset-db
```

使用 `--reset-db` 前必须确认用户确实要替换商品库；脚本会先备份旧 `backend/camp_rank.db` 到 `backend/data/import_reports/`。

如果新文件叫 `jd_tents_2026_05_08.xlsx`，建议放在根目录或你自己固定的数据目录，然后执行：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx jd_tents_2026_05_08.xlsx --output-json backend/data/real_samples/jd_tents_2026_05_08_mvp.json
```

如果你已经有标准 CampRank JSON，不需要从表格生成：

```bash
python scripts/run_mvp_data_pipeline.py --json backend/data/real_samples/jd_tents_mvp.json
```

如果只是快速导入和看页面，暂时不跑完整测试：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx --skip-checks
```

正式展示、提交、面试前必须跑完整检查，不要使用 `--skip-checks`。

## 4. 手动分步流程

如果一键脚本失败，按下面步骤定位。

### 4.1 表格转标准 JSON

```bash
cd backend
python scripts/build_jd_mvp_from_xlsx.py --input ../data.xlsx --output data/real_samples/jd_tents_mvp.json --sheet data
```

输出文件：

```text
backend/data/real_samples/jd_tents_mvp.json
```

### 4.2 导入、分析、评分一体执行

```bash
cd backend
python scripts/run_real_data_pipeline.py --json data/real_samples/jd_tents_mvp.json --platform JD --no-sample-data
```

这一步内部会执行：

- `import_from_json`
- `analyze_and_update_comments`
- `analyze_and_update_redbook_notes`，当前京东-only 数据的 `redbook_notes` 固定为空，因此这一步只保留兼容，不产生小红书推荐依据
- `calculate_all_scores`

### 4.3 单独导入

```bash
cd backend
python scripts/import_real_data.py --json data/real_samples/jd_tents_mvp.json --source-name jd_manual_xlsx_mvp
```

### 4.4 单独评论分析

```bash
cd backend
python scripts/analyze_comments.py
```

写入或更新：

- `CommentQualityAnalysis`
- `NegativeReviewAnalysis`
- 小红书摘要相关分析字段仅为历史兼容；当前京东-only 流水线不导入小红书数据

### 4.5 单独评分

```bash
cd backend
python scripts/calculate_scores.py
```

写入或更新：

- `PlatformOfferAnalysis`
- `ProductScore`

### 4.6 验收

```bash
cd backend
python -m pytest

cd ..
python scripts/check_all.py
```

`scripts/check_all.py` 会自动执行：

- `cd backend && python -m pytest`
- `cd frontend && npm run build`

看到下面输出才算通过：

```text
All CampRank checks passed.
```

## 5. 数据文件要求

当前京东 MVP 表格至少需要这些列：

| 表格字段 | 系统用途 |
| --- | --- |
| SKU | 商品标题、规格、套餐信息，进入原始元数据 |
| pid | 商品平台 ID，进入 `Product.platform_product_id` |
| 商家回复 | 进入 `Comment.seller_reply` |
| 图片数量 | 转成 `Comment.has_image` |
| 得分类型 | 辅助判断 positive / neutral / negative |
| 评论内容 | 进入 `Comment.comment_text` |
| 评论得分 | 进入 `Comment.rating` |
| 评论时间 | 进入 `Comment.comment_time` |
| 追评 | 合并为后续体验证据 |
| 追评时间 | 有追评时优先作为评论时间 |
| 当前价格 | 进入价格表，也用于 MVP 商品分组 |
| 商品链接 | 进入 `Product.product_url` |
| 售后服务 | 进入 `return_policies.return_condition_text`，用于商品卡片展示和售后风险字段；支持 `同Y2` 这类同表单元格引用简写 |
| 店铺名称 / 商品名称 | 进入 `platform_products.shop_name`，用于商品卡片和比价表展示；优先使用 `店铺名称`，没有该列时使用 `商品名称`；两列都支持 `同Z2` 这类同表单元格引用简写 |

不需要进入项目的数据：

- 用户昵称
- 用户头像
- 用户主页
- 评论 ID
- 图片 URL
- 视频 URL
- 账号相关字段
- 任何个人隐私字段

表格省略写法说明：

- 如果 `店铺名称` 写完整名称，系统直接使用该值。
- 如果没有单独 `店铺名称` 列，但有 `商品名称` 列，系统把 `商品名称` 作为当前显示名和 `shop_name` 来源，不补造店铺字段。
- 如果 `店铺名称` 或 `商品名称` 写 `同Z2`，系统会读取当前工作表 `Z2` 单元格的完整内容，再写入标准 JSON。
- 如果 `售后服务` 写 `同Y2`，系统会读取当前工作表 `Y2` 单元格的完整内容，再写入标准 JSON。
- 不要把 `同Z2`、`同Y2` 这种简写直接导入前端展示；必须先经过 `build_jd_mvp_from_xlsx.py` 清洗。

## 6. 标准 JSON 合同

表格最终必须被转换成 CampRank 统一 JSON：

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

`redbook_notes` 当前必须保持为空数组。不要为了让字段看起来完整而补充小红书笔记、淘宝评论或外部口碑摘要。

最重要的对象关系：

- `canonical_products`：标准商品，同款归并后的商品。
- `platform_products`：平台商品，必须有 `platform_product_id`。
- `product_prices`：价格和优惠。
- `product_benefits`：平台保障、赠品、权益。
- `return_policies`：售后和退换风险。
- `comments`：评论表，后续评论分析全部从这里开始。

评论字段最低要求：

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

## 7. 后端固定流水线

数据进入后端的顺序必须固定：

```text
原始表格
  -> build_jd_mvp_from_xlsx.py
  -> backend/data/real_samples/*.json
  -> import_real_data.py 或 run_real_data_pipeline.py
  -> Product / Comment / ProductPrice / ReturnPolicyAnalysis
  -> analyze_comments.py
  -> CommentQualityAnalysis / NegativeReviewAnalysis
  -> calculate_scores.py
  -> PlatformOfferAnalysis / ProductScore
  -> FastAPI
  -> React 前端
```

各模块职责：

| 模块 | 职责 |
| --- | --- |
| `backend/app/ingestion/` | 数据标准化、导入、质量报告 |
| `backend/app/nlp/` | 评论可信度、低信息评论、有效差评、风险维度识别 |
| `backend/app/scoring/` | 价格、售后、评论风险、购买推荐指数 |
| `backend/app/services/` | 把分析和评分写入数据库 |
| `backend/app/api/` | 给前端提供推荐、详情、比价、风险摘要 |
| `frontend/src/api/client.js` | 前端 API 调用入口 |
| `frontend/src/pages/Recommendations.jsx` | 购买建议首页 |
| `frontend/src/components/ProductCard.jsx` | 购买决策卡片 |
| `frontend/src/pages/ProductDetail.jsx` | 推荐依据详情页 |

## 8. 前端固定展示逻辑

新数据进来后，只要后端 API 字段保持一致，前端不需要手动改。

前端读取：

```text
GET /api/recommendations
GET /api/products/{canonical_product_id}
GET /api/products/{canonical_product_id}/comment-risk-summary
GET /api/price-compare/{canonical_product_id}
```

首页优先级固定：

```text
购买结论区
  -> 本次推荐结论横幅
  -> 三张精选方案卡片
  -> 为什么不是最低价
  -> 筛选过程
  -> 折叠候选商品列表
  -> 详情页推荐依据
```

首页是“用户购买决策页”，不是“商品卡片列表页”。首页默认只给出少量明确选择，当前数量必须来自后端接口返回结果，不能写死、预估或把未来可能接入的数据量当成当前结果：

- 首选方案｜建议购买，推荐等级 A，绿色强调。
- 低价备选｜预算紧可选，推荐等级 B，橙色或中性色强调。
- 谨慎选择｜下单前需确认，推荐等级 C，红色或浅红色强调。

首页顶部文案需要表达：系统已根据用户预算、使用场景和购买偏好分析当前接口返回的候选商品，并给出少量购买建议。只有当后端接口、导入报告或数据库统计明确返回排除数量和排除分类时，前端才可以展示“已排除 N 个商品”和分类明细；否则必须显示“当前接口未返回排除分类明细”，不得编造数量。

三张推荐卡片上方必须有紧凑的“本次推荐结论”横幅。横幅只展示筛选条件摘要、系统首选商品、一句话推荐结论、推荐等级和主要风险提醒。横幅背景使用浅绿色或浅米色，首选商品名和推荐等级要醒目，不能写成大段报告。横幅中的首选、价格依据、参数依据、评论依据、风险指数、依据充分度和风险提醒必须来自当前推荐接口返回的真实字段。

首页问答入口必须真正影响推荐排序。第一题“使用场景”是单选；第二题“购买决策侧重点”必须支持多选。前端传入 `scenario` 和 `preference` 后，后端不能只按固定 `final_score` 返回同一个首选；必须在推荐层根据当前真实字段计算 `user_match_score`。多选偏好用逗号拼接，例如 `preference=lowest_price,after_sale,weather_protection`，后端必须拆分后合并权重。基础分 `final_score` 保留为商品通用购买风险分，本次匹配分 `user_match_score` 用于响应用户选择。`ranking_factors` 必须说明本次排序参考了哪些真实字段，例如到手价相对得分、校正后风险相对得分、场景相关评论维度得分、容量标签匹配得分、售后文本和售后反馈得分。

前端多选交互必须保持可复现：默认只勾选“综合购买风险控制”。用户勾选任何具体侧重点后，应自动移除默认综合项；用户再勾选“综合购买风险控制”时，应清空其他具体侧重点。最终传给后端的 `preference` 是当前实际勾选项对应参数的逗号拼接，不能把未勾选项也传入排序链条。后端 `_parse_preferences()` 也必须防御外部混合传参：如果收到 `balanced,after_sale`，应剔除默认综合项，只保留具体偏好。

权重约定：如果用户只选择“价格敏感/到手价优先”，后端会更明显提高到手价相对得分权重；如果用户同时选择价格、售后、天气反馈等多个侧重点，价格权重不能压过售后文本、评论风险维度和数据置信度，避免多选变成“只按最低价排”。

默认预览预算约定：前端默认 `min_price=100`、`max_price=1000`，目的是打开页面时先展示本次真实导入候选，避免因为默认预算过窄让用户误以为商品没有导入。用户手动收窄预算后，后端仍按真实到手价过滤，不展示超出预算的商品。

默认候选读取上限：前端默认 `limit=50`，与当前后端接口上限保持一致，让长期商品库中的当前预算内候选先进入后端排序和折叠候选列表；首页仍只展示 3 张精选方案卡，不把大量商品直接铺满页面。

当前可用的用户选择映射：

| 用户选择 | 参数 | 允许使用的真实字段 |
| --- | --- | --- |
| 短途休闲露营 | `scenario=newbie_weekend` | 搭建、售后、闷热/异味、收纳等评论风险维度 |
| 家庭亲子露营 | `scenario=family_camping` | 空间、耐用、售后、搭建、容量标签 |
| 短途过夜露营 | `scenario=overnight` | 防水、防风、耐用、闷热/异味等评论风险维度 |
| 雨天/潮湿环境备用 | `scenario=rain_backup` | 防水、防风、耐用、售后等评论风险维度；不能替代专业防水抗风测试 |
| 多人聚会/大空间需求 | `scenario=group_party` | 空间、耐用、搭建、售后、容量标签 |
| 步行携带/收纳约束 | `scenario=hiking_lightweight` | 收纳、搭建、闷热/异味、耐用等评论风险维度；有真实页面重量/收纳字段时可作为页面标称参考，不能声称实测轻量 |
| 综合购买风险控制 | `preference=balanced` | 基础分、校正后购买风险、数据置信度、售后和耐用反馈 |
| 价格敏感/到手价优先 | `preference=lowest_price` | 到手价相对得分，同时保留风险和置信度约束 |
| 售后与退换保障 | `preference=after_sale` | 售后风险维度、售后文本、校正后购买风险 |
| 容量与空间匹配 | `preference=gift_package` | 空间风险维度、容量标签；不能把容量标签说成实测空间 |
| 收纳携带负担 | `preference=portable` | 收纳、搭建等评论风险维度；有真实页面重量和体积字段时可参与参数匹配，不能声称便携性能已实测优秀 |
| 防水/防风负面反馈 | `preference=weather_protection` | 防水、防风、耐用等评论风险维度；不能替代专业防水抗风测试 |
| 搭建复杂度敏感 | `preference=easy_setup` | 搭建、收纳等评论风险维度 |
| 闷热/异味负面反馈 | `preference=less_stuffy` | 闷热/异味相关评论风险维度 |

首页商品卡片已经改为“购买决策卡”。每张卡只保留下列可扫读信息：

- 顶部强标签：`推荐类型｜购买结论` 和推荐等级 A / B / C。
- 商品名：最多两行，超出省略，不能让长标题占满卡片。
- 到手价：醒目展示为“到手价 ¥xxx”。
- 三个核心指标：匹配度 `match_score`、风险指数 `risk_score`、依据充分度 `confidence_score`。匹配度和依据充分度越高越好，风险指数越低越好；依据充分度只表示信息可参考程度，不代表商品质量越高。
- 参数判断：展示空间判断、场景判断、待确认参数，并保留一两条原始页面参数事实。
- 三条以内参数匹配：只用真实价格、页面标称参数和按尺寸推算结果，例如“价格在预算内”“展开面积约 4.41㎡”“尺寸信息可支撑基础判断”。
- 三条以内评论验证：只用真实评论样本和评论风险结果，例如“评论样本 288 条”“主要风险：耐用、防水”“评论风险已识别，可作为买前参考”。
- 两条以内风险提醒：只用短句，例如“耐用相关反馈约 10%”“评论层级有缺失，结论需谨慎”。
- 证据摘要：评论样本数、命中需求点数量、风险标签数量。
- 两个按钮：“查看推荐证据”和“加入对比”。

三张精选方案卡片必须使用普通用户能理解的购买语言，同时允许提前展示上述三个核心指标。卡片内不要写超过 80 字的连续段落，不要把完整算法解释、原始评论分布、评论结构偏离度、方案 ID、京东 SKU / pid、完整售后原文或完整参数表直接压在卡片里。

字段兼容规则：

- `match_score` 优先读后端字段；没有时用 `user_match_score`，再没有时用 `final_score`。
- `risk_score` 优先读后端字段；没有时用 `standardized_risk_rate * 100`；再没有时只能用风险标签数量做弱 fallback，并在文案中保持谨慎。
- `confidence_score` 优先读后端字段；没有时用 `data_confidence_score` 或 `evidence_confidence_score`。前端展示名必须是“依据充分度”，并说明“越高表示可参考信息越充分，不代表商品质量越高”。
- 推荐理由和风险提醒必须来自真实字段：价格、评论样本、售后文本、风险标签、风险维度、评论样本 warning、`ranking_factors`。不能为了让卡片好看补造“防水好”“抗风强”“轻量便携”等事实。

“查看推荐证据”按钮打开结构化证据弹窗，不再叫“为什么推荐它”。弹窗必须包含：

- 推荐结论：对应当前商品自己的推荐类型、购买结论、等级和一句话说明。
- 评分拆解：价格匹配、场景匹配、风险控制、依据充分度。
- 推荐依据：来自卡片短句和 `ranking_factors`。
- 风险依据：来自风险标签、风险维度和评论样本 warning。
- 参数证据：来自 `parameter_analysis.decision` 和 `parameter_analysis.facts`，展示展开尺寸、推算面积、适合人数判断、适合场景判断、待确认参数、页面原始参数和“页面标称不等于实测”的边界说明。
- 评论证据：展示评论样本数量、正向评论证据和风险评论证据。评论原文只能从真实详情接口返回中截取。
- 综合结论：展示为什么建议买、为什么不是完全无风险、下单前需要确认什么。
- 真实评论证据：正向证据和风险证据都只能从 `GET /api/products/{canonical_product_id}` 返回的 `comments.comment_text` 中截取。当前接口没有返回评论原文时，必须写“当前商品详情接口没有返回可展示的评论原文”，不得伪造用户评价。
- 不适合购买场景：只能根据风险维度、风险标签、评论样本量和当前数据边界生成谨慎提醒。

候选列表中的每个候选商品也必须有“查看推荐证据”和“加入对比”入口。进入三张精选方案的商品不得重复出现在候选列表中。

“和低价款对比”必须是用户购买决策对比，不只是同款平台报价表。前端点击卡片按钮时，要把当前商品、本次推荐列表、当前最低价候选一起带入对比页：

- 如果当前商品不是最低价候选：比较“你点的这款” vs “当前低价款”。
- 如果当前商品本身就是最低价候选：比较“你点的这款” vs “当前首选对照”。
- 对比字段只允许来自真实推荐接口：到手价、评论样本、校正后购买风险、风险维度、售后文本、商品链接。
- 若后端同款报价 `offers` 只有 1 个，页面必须说明当前接口没有返回更多同款平台报价，不能补造淘宝、拼多多或其他平台价格。
- 同款平台报价表保留为补充信息；当同款报价不足时，优先展示候选商品之间的真实 A/B 对比。

除“匹配度 / 风险指数 / 依据充分度”这三个购买决策指标外，首页默认不要展示：

- 方案 ID
- 原始模型字段
- 样本偏差细节
- 原始评论分布细节
- 过多算法解释
- 原始规格样例列表
- 京东 SKU / pid
- 商品参数完整表
- 风险后预估成本
- 口碑证据强度
- 判断可信度
- 风险条
- 评论结构偏离度

候选商品列表默认折叠，按钮文案固定为“查看全部候选商品”。候选列表只展示未进入三张精选方案的候选商品，并且必须按同款组展示；已进入“首选方案 / 低价备选 / 谨慎选择”的商品不得在候选列表重复出现。商品数量必须来自接口实际返回。

筛选过程模块可折叠展示，目的是让用户知道系统已经替他做了筛选，而不是让用户自己看完全部商品。分类数量必须来自真实统计；如果当前接口没有返回分类统计，只展示真实的候选数量、精选数量、折叠候选数量和评论样本数量，不展示虚构排除分类。

- 价格超预算
- 评论样本不足
- 售后风险偏高
- 疑似同款重复
- 校正后风险偏高

详情页可以展示：

- 原始评论分布
- 标准化计算权重
- 评论结构偏离度
- 校正后购买风险
- 口碑证据强度
- 数据边界
- 商品链接
- 京东 SKU / pid
- 店铺名称
- 售后服务

详情页必须展示完整推荐依据，包括：

- 价格依据
- 评论依据
- 售后依据
- 商品参数依据
- 风险维度
- 评论采样结构校正
- 数据边界

详情页默认必须先用普通用户能看懂的购买语言展示结论，不要直接把专业指标铺出来。默认内容应解释：这款为什么进入建议、价格怎么看、评论里看到了什么、买前主要注意什么、售后要怎么确认、页面参数怎么看。口碑证据强度、判断可信度、评论结构偏离度、标准化计算权重、风险维度明细、评论采样结构校正、参数完整度等专业调查数据，必须放在“查看调查数据”按钮后的展开区域；展开后内容不能减少，只是从默认视图移到调查数据区域。

每个商品点进详情页后，都必须展示该商品自己的实际情况，不能所有商品共用同一句推荐理由。详情页说明必须基于后端实际返回字段：

- 商品名
- 店铺
- 到手价
- 商品链接
- 售后服务
- 评论样本数
- 原始评论分布
- 评论结构偏离度
- 校正后购买风险
- 主要风险标签
- 各风险维度

候选列表里的每个商品也必须能打开自己的推荐证据或详情页，并看到对应商品的事实数据。若后端没有返回某项字段，前端应显示“当前接口未返回”，不得补造。文案必须避免绝对化，只能使用“当前评论样本中”“相对需要留意”“可作为购买风险参考”等表达，不得写“一定好”“一定不会踩坑”“绝对推荐”。

详情页必须说明：

```text
当前系统仅基于价格、评论、售后和页面标称商品参数进行购买风险辅助判断，不能证明帐篷的防水、抗风、材质或重量表现一定优秀。本推荐只能作为购买风险参考，不能替代专业户外装备测评。
```

前端关键术语固定：

| 内部字段 | 前端展示 |
| --- | --- |
| final_score | 购买推荐指数 |
| review_evidence_score | 口碑证据强度 |
| data_confidence_score / confidence_score | 依据充分度；表示可参考信息是否充分，不代表商品质量分 |
| sampling_bias_index | 评论结构偏离度 |
| standardized_risk_rate | 校正后购买风险 |
| stable_final_price | 最低套餐价 |
| return_risk_cost | 售后风险成本 |
| shop_name / recommended_shop_name | 店铺 |
| return_condition_text / recommended_after_sale_service | 售后服务 |
| recommended_platform | 建议下单平台 |
| lowest_price_platform | 当前最低价来源 |

## 9. 启动页面

先启动后端：

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

再启动前端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

```text
http://127.0.0.1:5173/
```

如果页面还是旧内容：

1. 确认前端服务端口是 `5173`。
2. 浏览器按 `Ctrl + F5` 强制刷新。
3. 重新执行 `npm run build` 看是否有编译错误。
4. 确认后端 `GET /api/recommendations` 返回的是最新数据。

## 10. 文件清理规则

可以删除的临时文件：

- `*.log`
- `frontend-current.png`
- `.pytest_cache/`
- `__pycache__/`
- `docs/_docx_render_check/`

不要删除：

- `backend/data/real_samples/*.json`
- `data.xlsx`
- `backend/camp_rank.db`
- `camp_rank.db`
- `frontend/src/`
- `backend/app/`
- `backend/tests/`
- `docs/*.md`

如果要清空数据库重跑，需要先确认你是否还需要当前导入结果。默认不要删除数据库。

## 11. 常见失败和处理

### 表格字段缺失

表现：

```text
Missing required headers
```

处理：

- 对照本文档第 5 节补齐字段。
- 不要改导入服务去适配一个临时字段名。
- 如果字段名长期变化，再统一更新 `build_jd_mvp_from_xlsx.py` 和本文档。

### 导入后前端没有新商品

检查：

```bash
cd backend
python scripts/run_real_data_pipeline.py --json data/real_samples/jd_tents_mvp.json --platform JD --no-sample-data
python scripts/calculate_scores.py
```

再打开：

```text
http://127.0.0.1:8000/api/recommendations?min_price=100&max_price=1000&scenario=newbie_weekend&preference=balanced&limit=5
```

如果 API 有数据但前端没有，检查前端服务和缓存。

### 评论重复导入

当前导入服务会按商品和评论文本去重。重复跑流水线不会重复插入同一条评论。

### 缺少硬件参数

这是当前 MVP 的正常边界。不要补造参数。系统会通过数据质量 warning 和判断可信度表达数据不足。

## 12. 每次新数据进入后的检查清单

1. 新数据是否保留了必要字段。
2. 是否删除了昵称、头像、主页、账号等不需要字段。
3. 是否能生成标准 JSON。
4. JSON 是否保存在 `backend/data/real_samples/`。
5. 是否成功导入数据库。
6. 是否运行了 `analyze_comments.py`。
7. 是否运行了 `calculate_scores.py`。
8. `GET /api/recommendations` 是否返回新结果。
9. 前端是否显示首选和低价备选。
10. 是否运行 `python scripts/check_all.py` 并通过。

## 13. 面试时的简短说明

可以这样说：

```text
这个项目的数据进入不是前端手动写死，而是固定成一条流水线：
原始表格先转成统一 JSON，再进入 ingestion 服务导入数据库。
评论进入 Comment 表后，会经过低信息评论识别、有效差评分析、风险维度归类和采样结构校正。
之后评分服务把价格、售后和校正后的评论风险合并成购买推荐指数。
前端只消费 FastAPI 返回的推荐和风险摘要，所以每次新数据进来，只要字段合同一致，就能自动刷新成新的购买建议页。
```
