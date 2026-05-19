# CampRank 新 Agent 数据流水线交接说明

本文档给另一个窗口里的 Agent 使用。目标是：用户把新爬取的京东帐篷评论表格放进当前项目后，Agent 不重新设计项目、不改乱架构，直接按固定生产线完成：

```text
原始表格 -> 标准 JSON -> 导入数据库 -> 评论分析 -> 评分计算 -> 前端展示 -> 验收检查
```

## 0. 当前任务硬边界：京东-only，禁止编造

当前后续数据导入只接京东帐篷商品、京东评论、京东价格、京东售后服务文本，以及用户提供或真实页面可见的商品参数文字。不要接入小红书评论/笔记，不要接入淘宝/天猫评论，不要为页面补造跨平台价格、外部口碑、销量、材质、重量、检测报告、排除数量或售后承诺。

真实数据口径高于所有旧规划文档：

- 当前有什么京东数据，就只分析什么京东数据。
- 表格或接口没有返回的字段，前端显示“当前接口未返回”，后端写 warning 或保持空值。
- 商品参数只来自真实页面参数文字、参数图整理结果或用户明确提供的文字；只能表达“页面标称/按尺寸推算”，不能表达成实测防水、抗风、耐用或舒适度结论。
- `redbook_notes` 只作为历史 schema 兼容字段存在；当前标准 JSON 中必须保持为空数组，不参与评分和推荐依据。
- 淘宝/天猫、小红书、拼多多、什么值得买只算历史扩展规划，当前另一个窗口导入剩余数据时不得使用。
- 推荐结论只能写成“基于京东价格、京东评论、京东售后文本和页面标称参数的购买风险参考”，不能写成专业户外性能测评。
- 生产库是长期累计商品库，已经跑通全链路且由用户确认的历史商品必须保留；新增数据默认只追加或更新，不能因为接入新表格而覆盖历史商品。当前确认的历史恢复来源是 `backend/data/import_reports/camp_rank_backup_20260519_152836.db`。不要把 4 条评论的旧 sample/mock 占位批次误当成历史商品恢复或推荐，尤其是 `RainGuard`、`BudgetGo`、`FamilyHall`、`StarNest`、`StormMax`、`FreshAir`、`LowCost`、`SafeCamp` 这批演示名。只有用户明确指定要清理某批商品时，才允许先备份数据库，再删除用户指定商品及其全部关联数据。

## 1. 新 Agent 必读文件

开始任何修改前，先阅读：

```text
README.md
AGENTS.md
docs/camprank_data_to_frontend_pipeline.md
docs/jd_mvp_review_scoring_and_ingestion.md
docs/platform_field_mapping.md
docs/review_quality_control.md
docs/testing_strategy.md
```

如果只是把新爬取数据跑进 MVP，优先执行本文档，不要先重构。

## 2. 当前项目状态

当前项目已经跑通：

- 京东帐篷本地表格清洗。
- 标准 CampRank JSON 生成。
- 统一 ingestion 导入。
- Comment 表写入和去重。
- 低信息评论、评论可信度、有效差评、风险维度分析。
- 评论采样结构校正。
- 购买推荐指数计算。
- 商品参数 JSON 导入和 `parameter_analysis` 展示。
- React 前端购买建议页展示。

当前前端定位是：

```text
基于价格、评论风险和售后保障的购买风险辅助决策系统
```

不要把页面或文案写成“商品质量评测系统”。即使接入了商品页参数，也只是页面标称或尺寸推算，不是实测防水、抗风、材质强度、重量复核或官方检测报告。

## 3. 新数据放入方式

推荐把新爬取的京东帐篷表格放在项目根目录，例如：

```text
data.xlsx
jd_tents_2026_05_09.xlsx
```

如果文件名不是 `data.xlsx`，运行命令时用 `--input-xlsx` 指向它。

## 4. 表格字段要求

新表格至少需要这些列：

| 表格字段 | 必要性 | 用途 |
| --- | --- | --- |
| SKU | 必需 | 商品标题、规格、套餐信息，进入原始元数据 |
| pid | 必需 | 京东商品 ID，进入 `Product.platform_product_id` |
| 商家回复 | 建议 | 进入 `Comment.seller_reply` |
| 图片数量 | 建议 | 转成 `Comment.has_image` |
| 得分类型 | 建议 | 辅助判断 positive / neutral / negative |
| 评论内容 | 必需 | 进入 `Comment.comment_text` |
| 评论得分 | 必需 | 进入 `Comment.rating` |
| 评论时间 | 必需 | 进入 `Comment.comment_time` |
| 追评 | 建议 | 合并为后续体验证据 |
| 追评时间 | 建议 | 有追评时优先作为评论时间 |
| 当前价格 | 必需 | 用于价格分组，前端显示为“最低套餐价” |
| 商品链接 | 建议 | 进入 `Product.product_url` |
| 售后服务 | 建议 | 进入售后保障和风险字段，并在前端商品卡片展示 |
| 店铺名称 / 商品名称 | 必需二选一 | 前端商品卡片和比价表展示；如果表格没有单独 `店铺名称` 列，使用 `商品名称` 列作为当前显示名来源 |

字段规则：

- `店铺名称` 可以写完整名称。
- 如果本次表格没有单独 `店铺名称`，但有 `商品名称`，脚本会把 `商品名称` 写入 `platform_products.shop_name`，前端按真实表格内容展示。
- `店铺名称` 或 `商品名称` 也可以写 `同Z2` 这种简写，脚本会读取同一工作表 `Z2` 单元格的完整内容。
- `售后服务` 可以写完整内容。
- `售后服务` 也可以写 `同Y2` 这种简写，脚本会读取同一工作表 `Y2` 单元格的完整内容。
- `当前价格` 在前端统一叫“最低套餐价”。
- `backend/scripts/build_jd_mvp_from_xlsx.py` 默认导入表格中全部真实商品。商品分组优先按 `店铺名称` / `商品名称` 等真实商品显示名归并，避免同价不同商品被合并，也避免同一商品下多个 SKU、颜色、套餐链接被拆散。`当前价格` 仍作为“最低套餐价”和价格筛选依据。只有用户明确要求时，才用 `--price-groups` 限制指定价格组。
- 不要导入昵称、头像、用户主页、账号字段、图片 URL、视频 URL 等非必要字段。

## 5. 一条命令跑完整生产线

在项目根目录执行：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx
```

如果新文件不是 `data.xlsx`：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx jd_tents_2026_05_09.xlsx --output-json backend/data/real_samples/jd_tents_2026_05_09_mvp.json
```

如果用户同时给了商品页参数文字或参数图整理结果，先整理成 `backend/data/product_parameters_YYYYMMDD.json`，再执行：

```bash
python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json
```

该脚本只用于更新当前库中已存在京东商品的 `product_specs` 和可追溯 `raw_specs_json`，会先备份 `backend/camp_rank.db`。参数字段必须来自用户提供的真实文字；缺失字段填 `null`，不能补造。

这条命令会自动执行：

1. `backend/scripts/build_jd_mvp_from_xlsx.py`
2. 生成 `backend/data/real_samples/*.json`
3. `backend/scripts/run_real_data_pipeline.py`
4. 追加或更新数据库中的同款组，不删除历史商品
5. 评论分析
6. 评分计算
7. `python scripts/check_all.py`

默认一键命令代表“把这次真实京东表格追加进长期商品库”。不要删除旧商品，不要重建数据库，不要用新文件覆盖历史候选。只有用户明确说“清空、重建、只保留本次数据、替换当前商品库”时，才允许使用：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx --reset-db
```

即使使用 `--reset-db`，脚本也会先把旧 `backend/camp_rank.db` 备份到 `backend/data/import_reports/`；恢复前必须先确认用户意图。

看到下面输出才算完整通过：

```text
All CampRank checks passed.
```

## 6. 快速预览模式

如果用户只是想先看页面，可以先跳过测试：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx --skip-checks
```

注意：正式展示、提交、面试前必须再运行：

```bash
python scripts/check_all.py
```

## 7. 启动前端和后端

流水线跑完后，启动后端：

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端启动前端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

```text
http://127.0.0.1:5173/
```

如果页面还是旧数据：

1. 浏览器按 `Ctrl + F5` 强制刷新。
2. 确认后端 API 有新数据：

```text
http://127.0.0.1:8000/api/recommendations?min_price=100&max_price=250&scenario=newbie_weekend&preference=balanced&limit=2
```

3. 如果 API 是新数据但页面旧，重启前端服务。

## 7.1 前端展示验收：购买决策页

新数据接入后，前端首页不能作为“商品卡片列表页”验收。首页展示数量必须以当前接口、导入报告或数据库统计为准；不能把未来可能接入的数据规模写成当前结果，也不能编造排除数量、排除分类或候选数量。

首页验收固定三层：

1. 购买结论区和“本次推荐结论”横幅：说明系统已按预算、使用场景和购买偏好分析当前接口返回的候选商品，展示当前首选、一句话结论、推荐等级和主要风险。
2. 三张精选方案卡片：默认只展示“首选方案｜建议购买”“低价备选｜预算紧可选”“谨慎选择｜下单前需确认”。
3. 候选商品列表：默认折叠，按钮叫“查看全部候选商品”。这里只展示未进入三张精选方案的候选同款组，不重复展示已进入精选方案的商品。

首页购买决策卡只保留：顶部强标签和推荐等级、两行以内商品名、醒目的到手价、匹配度、风险指数、依据充分度、参数判断、三条以内参数匹配、三条以内评论验证、两条以内风险提醒、证据摘要，以及“查看推荐证据”“加入对比”两个按钮。`confidence_score` 前端展示名固定为“依据充分度”，表示可参考信息是否充分，不代表商品质量分。

三张精选方案卡片必须讲用户能懂的话。卡片允许展示 `match_score`、`risk_score`、`confidence_score` 三个决策指标，但不能写成长报告。卡片理由必须拆成“参数匹配”和“评论验证”：参数匹配来自真实到手价、页面标称参数和尺寸推算；评论验证来自真实评论样本、风险标签、风险维度和样本 warning。完整 `final_score`、原始评论分布、评论结构偏离度、维度明细、京东 SKU / pid 和完整售后原文放进证据弹窗、详情页或“查看调查数据”。售后重点可以从真实售后文本中提取，例如免费上门退换、退款处理较快、7 天无理由、使用后退货有限制；不能补造售后承诺。

字段 fallback 固定规则：`match_score` 缺失时用 `user_match_score`，再缺失用 `final_score`；`risk_score` 缺失时用 `standardized_risk_rate * 100`；`confidence_score` 缺失时用 `data_confidence_score` 或 `evidence_confidence_score`。fallback 只能用已有字段，不能为了展示效果补造事实。

“查看推荐证据”打开结构化弹窗，必须展示推荐结论、评分拆解、参数证据、评论证据、推荐依据、风险依据、综合结论和不适合购买场景。参数证据来自 `parameter_analysis.decision` 和 `parameter_analysis.facts`；真实评论证据只能从 `GET /api/products/{canonical_product_id}` 返回的 `comments.comment_text` 中截取；如果接口没有可展示的评论原文，写“当前商品详情接口没有返回可展示的评论原文”，不得编造评价。

“和低价款对比”页面要比较当前点击商品和本次推荐列表里的真实低价候选。不要只依赖同款平台报价表，因为当前真实数据可能每个同款组只有一个京东报价。若当前商品就是低价款，则和当前首选对照。对比内容只能来自真实推荐字段：到手价、评论样本、校正后购买风险、风险维度、售后文本和商品链接。同款报价不足时必须提示接口未返回更多平台报价，不能补造其他平台价格。

除匹配度、风险指数、依据充分度三个决策指标外，不要在首页卡片里堆这些指标：

- 口碑证据强度
- 判断可信度
- 原始评论分布
- 评论结构偏离度
- 方案 ID
- 京东 SKU / pid

这些指标放在详情页或推荐依据页。详情页必须展示价格依据、评论依据、售后依据、风险维度、评论采样结构校正和数据边界，并说明当前系统只能做购买风险辅助判断，不能替代专业户外装备测评。

详情页默认先给普通用户看得懂的购买说明：先看结论、价格怎么看、评论里看到了什么、买前主要注意什么、售后要怎么确认。口碑证据强度、判断可信度、评论结构偏离度、标准化计算权重、风险维度明细、评论采样结构校正等专业调查数据，不在默认视图铺开，必须放在“查看调查数据”按钮后的展开区域。展开区域不能删减事实内容，只调整信息层级。

后续接入更多商品时，必须先做同款归并，再展示同款组。不要把同款不同颜色、不同规格、不同套装重复铺满首页。

硬性数据口径：

- 当前有几个商品，就展示几个真实候选数量。
- 默认预览预算不要把本次真实候选误筛掉；当前前端默认 `min_price=100`、`max_price=1000`，用于一打开页面先看到本次导入候选。用户手动改成更窄预算时，后端仍按真实价格过滤。
- 默认 `limit=50`，与当前后端接口上限一致，用于让长期商品库里当前预算内的候选进入排序和折叠列表；首页仍只直接展示 3 张精选方案卡。
- 排除数量和排除分类必须来自后端或导入报告；没有真实字段时，写“当前接口未返回排除分类明细”。
- 用户选择必须影响后端排序：第一题“使用场景”单选，第二题“购买决策侧重点”多选。多个偏好用逗号传给后端，例如 `preference=lowest_price,after_sale,weather_protection`。`scenario` 和 `preference` 进入 `backend/app/scoring/recommendation_ranker.py` 后，要基于真实字段生成 `user_match_score` 和 `ranking_factors`。不要只返回固定 `final_score` 榜单，也不要为了让结果变化而编造字段。
- 首页选项名称必须使用专业决策术语：综合购买风险控制、价格敏感/到手价优先、售后与退换保障、容量与空间匹配、收纳携带负担、防水/防风负面反馈、搭建复杂度敏感、闷热/异味负面反馈。不要使用“别踩坑”“越便宜越好”“搭建省事”这类口语词作为决策标签。
- 首页多选默认项规则：默认只选“综合购买风险控制”；一旦用户选择具体侧重点，前端应移除默认综合项；用户重新选择“综合购买风险控制”时，应清空其他具体侧重点。后端只按最终传入的 `preference` 列表合并权重；如果外部调用混传 `balanced` 和具体偏好，后端应剔除 `balanced`。
- 价格权重规则：只有单选 `preference=lowest_price` 时才明显提高到手价权重；多选同时包含价格、售后、天气反馈等偏好时，价格权重必须回落，不能压过风险和置信度约束。
- `user_match_score` 只能来自现有事实字段：到手价、评论样本、校正后购买风险、各评论风险维度、容量标签、售后文本、数据置信度、商品场景字段和真实接入的页面参数字段。当前没有真实重量、收纳体积、PU 指数、面料、杆材等页面参数时，不能把这些作为推荐事实；即使有页面参数，也只能表达为页面标称，不是实测性能。
- 参数解释固定由 `backend/app/services/spec_analysis_service.py` 生成 `parameter_analysis.decision`。面积规则：小于 3㎡ = 空间偏小，更适合单人或临时遮阳；3㎡ 到小于 5㎡ = 适合 1-2 人短途休闲；5㎡ 到 8㎡ = 适合 2-3 人或小家庭休闲；大于 8㎡ = 空间较大，适合多人或家庭露营，但要关注重量和搭建难度。缺少防水指数、重量、材质、搭建方式时，前端显示“待确认参数”，不能隐藏或补造。
- 卡片理由必须基于后端返回的价格、匹配分、评论样本、风险标签、风险维度、店铺、售后和商品链接生成，不得套用同一句理由。
- 商品进入“首选方案 / 低价备选 / 谨慎选择”后，不得再次出现在折叠候选列表。
- 每个商品点“查看推荐证据”后，弹窗或详情页必须展示该商品自己的事实数据：商品名、店铺、到手价、商品链接、售后服务、评论样本数、原始评论分布、评论结构偏离度、校正后购买风险、主要风险标签和风险维度。候选列表中的商品也必须能打开自己的推荐证据。
- 如果接口没有返回某项事实字段，前端只能提示“当前接口未返回”，不能补造。推荐文案必须避免绝对化，只能表达“当前评论样本中”“相对更稳”“需要留意”“购买风险参考”，不能写“一定好”“一定不会踩坑”“绝对推荐”。

## 8. 新 Agent 不要做的事

不要做：

- 不要新建临时 `jd_spider.py`、`clean_data.py`、`test_frontend.py`。
- 不要把清洗逻辑写进前端。
- 不要把评分逻辑写进前端。
- 不要绕过 ingestion 直接手动改数据库。
- 不要删除 `backend/data/real_samples/*.json`。
- 不要删除 `backend/camp_rank.db`，除非用户明确要求重新建库。
- 不要补造防水、抗风、材质、重量、检测报告等硬参数。
- 不要引入账号、Cookie、验证码、登录态、代理、并发、高频访问相关代码。

可以做：

- 如果新表格字段名长期变化，可以更新 `backend/scripts/build_jd_mvp_from_xlsx.py`。
- 如果更新了字段规则，必须同步更新 `README.md` 和本文档。
- 如果改了清洗逻辑，必须新增或更新 `backend/tests/` 中对应测试。

## 9. 常见问题处理

### 9.1 提示 Missing required headers

说明新表格缺少必需字段。先对照第 4 节补齐字段，不要为了一个临时表头去改核心导入服务。

### 9.2 前端显示 `同Z2` 或 `同Y2`

说明数据没有经过最新清洗脚本，或 JSON 是旧文件。重新运行：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx --skip-checks
```

然后检查 JSON：

```bash
python - <<PY
import json
from pathlib import Path
data=json.loads(Path("backend/data/real_samples/jd_tents_mvp.json").read_text(encoding="utf-8"))
for row in data["platform_products"]:
    print(row["platform_product_id"], row["shop_name"])
for row in data["return_policies"]:
    print(row["platform_product_id"], row["return_condition_text"])
PY
```

PowerShell 不支持上面的 heredoc 时，用：

```powershell
@'
import json
from pathlib import Path
data=json.loads(Path("backend/data/real_samples/jd_tents_mvp.json").read_text(encoding="utf-8"))
for row in data["platform_products"]:
    print(row["platform_product_id"], row["shop_name"])
for row in data["return_policies"]:
    print(row["platform_product_id"], row["return_condition_text"])
'@ | python -
```

### 9.3 导入报告显示 imported 为 0

如果是重复跑同一批商品，这是正常的。看 `updated_records` 和前端 API 是否更新即可。

### 9.4 缺少硬件参数 warning

这是当前 MVP 的正常边界。系统会降低数据置信度，不要补造参数。

## 10. 接手时可直接复制给新 Agent 的指令

```text
请先阅读 README.md、AGENTS.md、docs/next_agent_data_pipeline_handoff.md、docs/camprank_data_to_frontend_pipeline.md、docs/jd_mvp_review_scoring_and_ingestion.md。

当前任务不是重新设计项目，而是把我新爬取的京东帐篷评论表格接入 CampRank 现有生产线。

请按固定流程执行：
1. 检查表格字段是否满足文档要求。
2. 用 scripts/run_mvp_data_pipeline.py 从表格生成标准 JSON。
3. 导入数据库。
4. 跑评论分析和评分。
5. 跑 python scripts/check_all.py。
6. 启动 backend 和 frontend。
7. 确认 http://127.0.0.1:5173/ 能看到新商品。

不要新增散乱脚本，不要把逻辑写进前端，不要绕过 ingestion，不要补造硬件参数。若字段规则有变化，更新 README.md 和 docs/next_agent_data_pipeline_handoff.md，并补测试。
```
