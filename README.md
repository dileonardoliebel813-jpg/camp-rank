# CampRank

## 当前数据接入口径：只使用京东真实数据

从 2026-05-09 起，当前项目后续数据导入只按“京东帐篷商品 + 京东评论 + 京东售后/价格”进入生产链。小红书、淘宝/天猫、拼多多、什么值得买等多平台内容仅保留为历史规划或代码兼容能力，不作为当前推荐依据，不要求补充，也不能为了页面完整而编造。

下次新增数据时，直接提供京东表格或京东标准 JSON，按下面两份文档执行：

```text
docs/next_agent_data_pipeline_handoff.md
docs/camprank_data_to_frontend_pipeline.md
```

重要导入方式：

- 默认一键命令 `python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx` 是追加/更新长期商品库，不删除历史商品。
- 只有用户明确说“清空、重建、只保留本次数据、替换当前商品库”时，才允许使用 `--reset-db`。
- 使用 `--reset-db` 前必须确认用户意图；脚本会先备份旧数据库到 `backend/data/import_reports/`。

硬性规则：

- 推荐、详情页、对比页、筛选状态和候选数量必须全部来自真实导入数据、后端接口、数据库统计或导入报告。
- 没有返回的字段只能显示“当前接口未返回”或写入 warning，不能补造淘宝价格、小红书口碑、销量、检测报告、排除数量或售后承诺。
- 当前新增的商品参数只能来自用户提供的页面参数文字、参数图整理结果或同一商品真实页面可见字段；这些参数只能作为页面标称或尺寸推算，不得写成实测防水、抗风、耐用或舒适度结论。
- 当前 `redbook_notes` 仅作为历史 schema 兼容字段，京东-only 流水线中固定为空数组，不进入评分或前端推荐依据。
- 当前不接入淘宝/天猫评论，不接入小红书评论或笔记，不做跨平台评论一致性判断。
- 当前推荐只能作为“基于京东价格、评论、售后文本和页面标称参数的购买风险参考”，不能写成专业户外性能测评。
- 生产库是长期累计商品库，新增数据默认只能追加或更新，不能因为接入新表格而覆盖历史商品。历史商品以用户确认过的真实导入库和备份为准；当前确认的历史恢复来源是 `backend/data/import_reports/camp_rank_backup_20260519_152836.db`。不要把 4 条评论的旧 sample/mock 占位批次误当成历史商品恢复或推荐，尤其是 `RainGuard`、`BudgetGo`、`FamilyHall`、`StarNest`、`StormMax`、`FreshAir`、`LowCost`、`SafeCamp` 这批演示名。只有用户明确指定要清理某批商品，并且先完成数据库备份后，才允许删除指定商品及关联记录。

## 当前首页展示约定：购买决策页，不是商品列表页

首页不能默认铺满商品卡片。数据进入项目后，系统必须先完成筛选、同款归并、排序和风险解释，再给用户少量明确选择。页面展示的商品数量、候选数量、评论数量、排除数量都必须来自实际接口、导入报告或数据库统计，不能写死、预估或把未来可能接入的数据量当成当前结果。

首页固定三层：

1. 购买结论区和“本次推荐结论”横幅：说明已按预算、使用场景和购买偏好分析当前接口返回的候选商品，当前首选是谁、一句话结论、推荐等级和主要风险是什么。
2. 三张精选方案卡片：默认只展示“首选方案｜建议购买”“低价备选｜预算紧可选”“谨慎选择｜下单前需确认”。
3. 候选商品列表：默认折叠，按钮文案为“查看全部候选商品”。这里只展示未进入三张精选方案的候选同款组，不重复展示已进入精选方案的商品，不把同款不同颜色、规格、套装重复铺满页面。

购买决策卡只保留：顶部强标签和推荐等级、两行以内商品名、到手价、匹配度、风险指数、依据充分度、参数判断、三条以内参数匹配、三条以内评论验证、两条以内风险提醒、证据摘要，以及“查看推荐证据”“加入对比”两个按钮。`confidence_score` 在前端展示名固定为“依据充分度”，表示可参考信息是否充分，不代表商品质量越高。口碑证据强度、原始分布、评论结构偏离度、方案 ID、京东 SKU / pid、完整商品参数表等指标放到证据弹窗、详情页或调查数据区域。

三张精选方案卡片必须用用户能看懂的购买语言。卡片里的 `match_score`、`risk_score`、`confidence_score` 只能来自现有接口字段或文档规定的 fallback：`user_match_score` / `final_score`、`standardized_risk_rate * 100`、`data_confidence_score` / `evidence_confidence_score`。推荐理由必须拆成“参数匹配”和“评论验证”：参数匹配只能来自真实到手价、页面标称参数和按尺寸推算结果；评论验证只能来自真实评论样本数、风险标签、风险维度和样本 warning。不能补造售后承诺或硬件性能。

“查看推荐证据”弹窗必须展示当前商品自己的推荐结论、评分拆解、参数证据、评论证据、推荐依据、风险依据、综合结论和不适合购买场景。参数证据必须来自 `parameter_analysis.decision`、`parameter_analysis.facts` 和真实原始参数；评论证据只能从详情接口返回的 `comments.comment_text` 中截取；接口没有评论原文时，必须写“当前商品详情接口没有返回可展示的评论原文”，不得伪造评价。

“和低价款对比”页面必须优先比较当前点击商品和本次推荐列表中的真实低价候选，而不是只展示同款平台报价表。若当前商品本身就是低价款，则和当前首选对照。对比内容只使用推荐接口已返回的真实字段：到手价、评论样本、校正后购买风险、风险维度、售后文本、商品链接。若同款平台报价只有 1 个，页面必须说明“当前接口没有返回更多同款平台报价”，不能补造淘宝、拼多多或其他平台价格。

详情页继续展示完整推荐依据：价格依据、评论依据、售后依据、商品参数依据、风险维度、评论采样结构校正和数据边界。详情页默认先用普通用户能看懂的话解释“这款为什么进入建议、买前主要看什么、售后怎么确认、页面参数怎么看”，不要把专业指标堆在第一屏；口碑证据强度、判断可信度、评论结构偏离度、标准化权重、风险维度明细、参数完整度等专业调查数据必须放进“查看调查数据”按钮后的展开区域。页面必须说明：当前系统仅基于价格、评论、售后和页面标称参数进行购买风险辅助判断，不能证明帐篷的防水、抗风、材质或重量表现一定优秀；本推荐只能作为购买风险参考，不能替代专业户外装备测评。

每个商品点进“查看推荐证据”或详情页后，必须展示该商品自己的实际情况，不能共用同一段模板结论。说明必须基于后端返回的事实字段生成，包括：商品名、店铺、到手价、评论样本数、原始评论分布、校正后购买风险、主要风险标签、售后服务和商品链接。措辞必须避免绝对化，只能说“当前评论样本中”“相对需要留意”“作为购买风险参考”，不能说“一定好”“一定不会踩坑”“绝对推荐”。

用户在首页选择不同使用场景和购买偏好后，后端必须基于真实字段重新计算本次推荐排序，不能只返回固定 `final_score` 榜单。第一题“使用场景”是单选，第二题“购买决策侧重点”必须支持多选；多选偏好用逗号传给后端，例如 `preference=lowest_price,after_sale,weather_protection`。`final_score` 是商品基础分，`user_match_score` 是本次用户选择下的匹配分；它只能由当前接口已有字段计算，包括到手价、评论样本、校正后购买风险、各风险维度、容量标签、售后文本、数据置信度、商品场景字段和真实接入的页面参数字段。前端可以展示 `user_match_score` 和 `ranking_factors`，但不能为了让结果变化而编造防水、重量、材质、销量或排除数量。首页选项名称必须使用专业决策术语，例如综合购买风险控制、价格敏感/到手价优先、售后与退换保障、容量与空间匹配、收纳携带负担、防水/防风负面反馈、搭建复杂度敏感、闷热/异味负面反馈。

首页多选交互约定：默认勾选“综合购买风险控制”。当用户勾选任何具体侧重点时，前端自动取消默认综合项；当用户重新勾选“综合购买风险控制”时，前端清空其他具体侧重点。这样传给后端的 `preference` 不会同时混入“默认综合”和“具体偏好”，推荐链条更容易复现和排查。后端解析层也做同样保护：如果外部调用传入 `balanced,after_sale` 这类混合值，会剔除默认综合项，只合并具体偏好权重。

价格偏好权重约定：用户只选“价格敏感/到手价优先”时，推荐排序会更明显向真实到手价低的候选倾斜；如果价格和售后、天气反馈等偏好一起多选，价格权重必须降低到可平衡状态，不能覆盖售后文本、评论风险维度和数据置信度。

## MVP 数据到前端完整流水线

以后有新的京东帐篷表格数据进来，优先按总流程文档执行：

```text
docs/next_agent_data_pipeline_handoff.md
docs/camprank_data_to_frontend_pipeline.md
```

如果要另开一个 Agent 接手，先让它阅读 `docs/next_agent_data_pipeline_handoff.md`。这份文档已经写清楚新爬取表格的字段要求、一条命令生产线、前后端启动方式、验收命令和禁止改乱的边界。

最短一键命令：

```bash
python scripts/run_mvp_data_pipeline.py --input-xlsx data.xlsx
```

这条命令会按固定顺序完成：表格清洗生成标准 JSON、导入数据库、评论分析、评分计算、后端测试和前端构建检查。前端不直接写死新数据，只消费后端 API 返回的购买建议、风险摘要和推荐依据。

默认清洗会导入京东表格中的全部真实商品。商品边界优先按 `店铺名称` / `商品名称` 等真实商品显示名归并；同价不同商品不会被合并，同一商品下不同 SKU、颜色、套餐链接不会被拆散。`当前价格` 仍作为“最低套餐价”和价格筛选依据。只有用户明确要求限制范围时，才使用 `--price-groups`。

如果用户另外提供商品页参数文字或参数图整理结果，按 `backend/data/product_parameters_YYYYMMDD.json` 的结构整理后执行：

```bash
python scripts/import_product_parameters.py --input backend/data/product_parameters_YYYYMMDD.json
```

脚本会先备份 `backend/camp_rank.db`，再把真实参数写入 `product_specs` 和 `raw_specs_json`。本次参数样例为 `backend/data/product_parameters_20260519.json`。参数缺失必须保持空值，不能为了评分或前端展示补造。

参数导入后，后端 `backend/app/services/spec_analysis_service.py` 会生成 `parameter_analysis.decision` 给前端复用。固定规则如下：

- 有展开长宽时按长 × 宽推算占地面积；小于 3㎡ 写“空间偏小，更适合单人或临时遮阳”，3㎡ 到小于 5㎡ 写“适合 1-2 人短途休闲”，5㎡ 到 8㎡ 写“适合 2-3 人或小家庭休闲”，大于 8㎡ 写“空间较大，适合多人或家庭露营，但要关注重量和搭建难度”。
- 场景判断只能从真实商品名、页面参数文字、标称功能和帐篷类型中提取，例如公园、沙滩、遮阳、野餐、露营、过夜、天幕；没有文字依据时写“待确认”或保守短途休闲判断。
- 缺少防水指数、重量、材质、搭建方式时，前端必须显示“待确认参数”，不隐藏、不补造，也不直接判定商品差；只降低参数完整度和依据充分度，并提示下单前确认。
- 页面文案固定表达为“商品参数决定适不适合，用户评论验证有没有坑”。参数是页面标称或尺寸推算，评论是京东样本中的风险反馈，两者都不能写成实测性能结论。

### 当前表格和前端展示约定

后续新数据表格必须保留 `店铺名称` 和 `售后服务` 列。`店铺名称` 会写入 `platform_products.shop_name`，`售后服务` 会写入 `return_policies.return_condition_text`，前端商品卡片展示店铺和售后服务。两列都可以填写完整内容，也可以使用 `同Z2`、`同Y2` 这类单元格引用简写，清洗脚本会自动读取同一工作表对应单元格的完整内容。

价格展示口径统一为“最低套餐价”：表格里的 `当前价格` 仍用于价格分组和 `stable_final_price`，前端统一显示为“最低套餐价”。

首页商品卡片不展示“原始规格样例”“京东 SKU / pid”和“风险后预估成本”。规格/套餐信息只保留为简短摘要或详情页元数据；售后服务直接来自表格，售后风险可以展示为风险等级和售后风险成本，但不再把“风险后预估成本”作为用户主决策字段。

## 京东帐篷 MVP 数据通道

当前京东帐篷商品已通过本地表格生成标准 JSON，并接入现有导入、评论分析、评分和前端展示闭环。具体字段、清洗规则、执行命令和 MVP 评分边界见：

```text
docs/jd_mvp_review_scoring_and_ingestion.md
```

## 京东公开评价数据接入

CampRank 支持通过京东商品 SKU ID 进行公开评价摘要接入。该入口只做低频公开数据读取，用户可以设置 `max_pages`、`page_size`、`delay` 和请求超时；默认只进行本地 JSON 保存，不直接写入数据库。

使用方式：
```bash
cd backend
python scripts/fetch_jd_comments.py --sku-id 100000000000 --max-pages 3 --page-size 10 --delay 2 --save-only
python scripts/fetch_jd_comments.py --sku-id 100000000000 --max-pages 3 --import-db
```

保存路径：
```text
backend/data/real_samples/jd_comments_<sku_id>.json
```

边界说明：
- 不使用账号、Cookie、验证码或非公开内容。
- 不承诺获取全部评价，只保存公开可访问的有限页数评价摘要。
- 遇到访问受限、登录页、验证码页、空响应或结构异常时，会停止并返回 warning。
- 导入数据库需要显式使用 `--import-db`，导入时只匹配已有 `Product.platform_product_id`，不会强行创建商品。
- 导入现有评论表后，可以继续运行评论分析和评分闭环：

```bash
cd backend
python scripts/analyze_comments.py
python scripts/calculate_scores.py
```

## 历史多平台 API / 授权数据源规划，当前导入不使用

以下内容是早期多平台扩展规划和代码兼容说明。当前用户数据导入只使用京东，不接入淘宝/天猫、小红书、拼多多或什么值得买评论，也不把这些平台作为当前推荐依据。除非用户在后续任务中明确重新开启多平台接入，否则不要运行本节的多平台命令。

CampRank 曾接入 JD、SMZDM、淘宝/天猫、PDD 的官方 API client 与 adapter 链路，小红书仅保留授权数据 guard。所有平台默认关闭，不使用账号密码、Cookie、验证码、非公开内容或个人隐私数据；缺少 Key 时会清晰报错，不会用 sample 数据伪造 live 成功。

常用命令：

```bash
cd backend
python scripts/live_smoke_test.py
python scripts/fetch_real_data.py --source jd --keyword 帐篷 --limit 5 --live --dry-run
python scripts/fetch_real_data.py --source smzdm --keyword 帐篷 --limit 5 --live --dry-run --save-json
python -m pytest tests/test_official_response_contracts.py
```

需要配置的 Key 见 `.env.example` 和 `docs/official_api_integration.md`。无 Key 时可以运行 contract test 验证官方响应样例字段映射；有 Key 时可以运行 live smoke test 或 `fetch_real_data.py --live --dry-run` 验证真实接口返回。

## 历史真实平台数据接入，当前只走京东表格

当前项目后续实际导入只走京东帐篷表格或京东标准 JSON。旧的官方 API、授权数据、手动 CSV 或 JSON、合规公开页面低频读取入口保留为工程能力，不作为当前数据入口。默认不会联网；官方 API 必须通过环境变量显式启用，例如 `JD_API_ENABLED=true`，且缺少 API Key、Secret、Base URL 或 Method 时会返回清晰错误，不会用 sample 数据伪装成功。

淘宝、拼多多、小红书默认只保留授权数据接口框架；当前导入任务不要使用这些平台，也不要补造这些平台的价格、评论或口碑。项目不支持登录态数据、账号密码、Cookie、验证码处理、非公开内容读取或个人隐私采集。平台字段缺失时导入不中断，但会写入 warning，并通过字段完整度报告降低数据置信度。

真实/手动数据进入系统后的推荐流水线：

```bash
cd backend
python scripts/run_real_data_pipeline.py --json data/real_samples/tents_real_sample.json --platform JD
python scripts/run_real_data_pipeline.py --adapter smzdm --input data/real_samples/smzdm_tents_sample.json --platform SMZDM
python scripts/run_real_data_pipeline.py --adapter jd --input data/real_samples/jd_tents_sample.json --platform JD
```

字段映射摘要可查看 `docs/platform_field_mapping.md`，接口可访问：

- `GET /api/ingestion/platform-mapping`
- `GET /api/ingestion/quality-report`

## 历史真实采集执行层，当前不作为默认流程

当前项目已经支持真实联网采集入口，但默认所有平台 adapter 都不联网。`live=true` 或命令行 `--live` 才表示真实联网采集；不带 `--live` 时只能读取本地 JSON 文件，这类流程只能称为本地文件导入，不能伪装成真实采集结果。

历史真实采集入口曾规划支持：

- 什么值得买：通过 `SMZDM_BASE_URL` 配置开放平台或授权 API URL，请求参数包含 `keyword`、`limit` 和 `api_key`。
- 京东：通过 `JD_BASE_URL` 和 `JD_API_METHOD` 配置京东开放平台、联盟 API 或授权中转 API；签名逻辑保留 `sign_params` 扩展点，需要按实际官方方法补充。
- 淘宝、拼多多、小红书：默认不联网，只保留官方授权 API 接入框架。当前京东-only 流水线不使用这些入口。

项目不使用模拟登录、验证码处理、Cookie、登录态、非公开数据或个人隐私数据。缺少 API Key、Secret、Base URL 或 Method 时，真实数据接入会明确报错，不会退回离线样例来伪装成功。

真实联网采集命令：

```bash
cd backend
python scripts/fetch_real_data.py --source smzdm --keyword 帐篷 --limit 20 --live
python scripts/fetch_real_data.py --source jd --keyword 双人帐篷 --limit 20 --live
```

本地文件导入命令：

```bash
cd backend
python scripts/fetch_real_data.py --source smzdm --keyword 帐篷 --limit 20 --input data/real_samples/smzdm_tents_sample.json
python scripts/fetch_real_data.py --source jd --keyword 帐篷 --limit 20 --input data/real_samples/jd_tents_sample.json
```

真实采集或本地导入成功后继续运行：

```bash
python scripts/analyze_comments.py
python scripts/calculate_scores.py
```

需要配置的环境变量见 `.env.example`，默认均为关闭：

```bash
SMZDM_API_ENABLED=false
SMZDM_API_KEY=
SMZDM_BASE_URL=

JD_API_ENABLED=false
JD_APP_KEY=
JD_APP_SECRET=
JD_BASE_URL=
JD_API_METHOD=
```

## 真实数据导入与采集适配

当前支持从 CSV/JSON 导入人工整理的真实或半真实公开数据，并复用现有数据库、评论分析、评分计算和前端展示流程。平台适配器已经具备可插拔框架，但默认不联网；后续接入真实 API 时需要配置 `.env` 中的平台环境变量，并优先使用官方开放平台、联盟 API 或授权数据源。

本项目不使用登录态、验证码、Cookie、账号密码、非公开内容或个人隐私数据。当前京东-only 流水线不导入小红书数据；旧的小红书授权数据能力只保留为历史兼容，不做当前推荐依据。

导入真实数据后请运行评论分析和评分脚本：

```bash
cd backend
python scripts/import_real_data.py --json data/real_samples/tents_real_sample.json
python scripts/analyze_comments.py
python scripts/calculate_scores.py
python -m pytest

cd ..
python scripts/check_all.py
```

也可以使用 CSV 文件夹或离线平台样例：

```bash
cd backend
python scripts/import_real_data.py --csv-folder data/real_samples/csv
python scripts/import_real_data.py --adapter jd --input data/real_samples/jd_tents_sample.json
python scripts/import_real_data.py --adapter smzdm --input data/real_samples/smzdm_tents_sample.json
```

## 历史项目规划记录，当前京东-only 导入不按本段扩展

下面内容记录早期多平台项目规划，用于理解代码来源。当前继续导入剩余数据时，只执行本文档顶部的京东-only 口径，不按本段要求采集淘宝/天猫、小红书、拼多多或什么值得买数据。

中文名：多平台户外帐篷智能消费决策系统

CampRank 早期规划面向 18-28 岁大学生、刚上班族和轻露营新手用户，整合京东、淘宝/天猫、拼多多、什么值得买、小红书等平台上的户外帐篷商品、价格、评论、优惠、赠品、退货保障和口碑信息，帮助用户做出更稳妥的购买决策。

本项目不是普通爬虫项目。爬虫或公开数据采集只是数据进入系统的一层，核心能力是数据标准化、同款识别、评论可信度分析、疑似刷评过滤、有效差评识别、平台真实到手成本比较、退货风险折算、场景化评分和可解释推荐。

## 目标用户

- 18-28 岁大学生
- 刚上班、预算有限但希望买得稳妥的年轻用户
- 轻露营新手、第一次购买帐篷的用户
- 想比较不同平台价格、售后和真实口碑的用户

## 用户痛点

- 看不懂防水指数、杆材、面料、尺寸、重量等帐篷参数。
- 同一款帐篷在不同平台名称、套餐、赠品和价格口径不同，难以比较。
- 商家宣传容易夸大，例如空间虚标、防水虚标、赠品价值虚标。
- 评论真假混杂，低信息好评、模板化好评、疑似刷评会干扰判断。
- 差评不一定都有效，需要区分质量问题、参数虚标、售后退货和个人偏好。
- 最低价平台不一定最划算，券是否可用、赠品是否实用、退货成本都要折算。
- 漏水、断杆、异味、空间偏小、退款慢、退货麻烦等风险常在购买后才暴露。

## 核心能力

- 多平台商品信息采集与统一字段标准化。
- 品牌、型号、标题、参数和主图占位特征的同款识别。
- 评论可信度分析、疑似刷评过滤、低信息评论过滤。
- 有效差评识别，按漏水、断杆、异味、空间虚标、退款慢等风险维度归类。
- 最低套餐价、理论最低价、赠品保守估值和优惠稳定性比较。
- 退货保障、退款速度、运费争议、客服扯皮等售后风险折算。
- 面向不同场景的帐篷评分：新手公园露营、过夜轻露营、徒步轻量、家庭多人露营。
- 推荐结果可解释展示，说明为什么推荐、为什么避坑、为什么最低价不一定是推荐平台。

## 系统最终回答的两个问题

1. 哪款帐篷值得买？
2. 同一款帐篷应该在哪个平台买？

系统会先判断标准商品本身是否值得买，再判断同一标准商品在不同平台购买时的价格、优惠、赠品、退货保障和售后风险。

## 技术栈规划

- 后端：Python + FastAPI
- 数据库：SQLite，后续可扩展 PostgreSQL
- 数据分析：pandas、jieba、规则词典
- 爬虫/采集：requests、BeautifulSoup、Playwright，优先开放平台或公开数据源
- 前端：React + Vite + Tailwind CSS
- 测试：pytest、npm run build

## 后续 Agent 开发顺序

1. Agent 1：项目需求、总体设计与规范文档。
2. Agent 2：项目骨架、数据库模型与样例数据。
3. Agent 3：评论真实性、刷评过滤、差评识别、小红书口碑分析。
4. Agent 4：价格优惠、退货风险、评分推荐算法。
5. Agent 5：前端展示、联调、README、面试包装、GitHub 推送。

## 测试与验收策略

- 项目测试策略详见 `docs/testing_strategy.md`。
- 后续每个 Agent 都必须补充测试，不能只写功能。
- 后端改动必须运行 `python -m pytest`。
- 前端改动必须运行 `npm run build`。
- Agent 2 需要创建 `scripts/check_all.py`。
- 每个 Agent 最终必须汇报测试命令和测试结果。

## 后端启动方式

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_sample_data.py
uvicorn app.main:app --reload
```

后端默认使用 SQLite：`backend/camp_rank.db`。启动后可访问：

- `GET /health`
- `GET /api/products`
- `GET /api/products/{canonical_product_id}`
- `GET /api/price-compare/{canonical_product_id}`
- `GET /api/recommendations/mock`
- `GET /api/products/{canonical_product_id}/comment-risk-summary`
- `GET /api/products/{canonical_product_id}/redbook-summary`

## 前端启动方式

```bash
cd frontend
npm install
npm run dev
```

前端使用 React + Vite，开发服务器默认代理 `/api` 到 `http://127.0.0.1:8000`。

## 数据库初始化与样例数据

```bash
cd backend
python scripts/init_db.py
python scripts/seed_sample_data.py
```

`seed_sample_data.py` 可重复运行，会避免重复插入同一批标准商品样例数据。

## 一键测试命令

```bash
python scripts/check_all.py
```

该命令会在存在后端时运行 `cd backend && python -m pytest`，在存在前端时运行 `cd frontend && npm run build`。全部通过时输出：

```text
All CampRank checks passed.
```

## 评论分析脚本

Agent 3 新增了评论质量、疑似刷评、有效差评、退货评论和小红书口碑分析。运行方式：

```bash
cd backend
python scripts/analyze_comments.py
```

脚本会基于当前 SQLite sample 数据写入或更新 `CommentQualityAnalysis`、`NegativeReviewAnalysis` 和 `RedBookNote` 的分析字段。

## Agent 3 新增 API

评论风险摘要：

```bash
GET /api/products/{canonical_product_id}/comment-risk-summary
```

返回字段包括防水、防风、空间、收纳、搭建、异味、防晒、退货售后维度负面率，以及高风险标签、疑似刷评数、低信息评论数和有效差评数。

小红书口碑摘要：

```bash
GET /api/products/{canonical_product_id}/redbook-summary
```

返回字段包括笔记数量、疑似广告数量、平均可信度、平均情绪分和风险标签。

## 当前 Agent 3 已实现内容

- 新增 `backend/app/nlp/` 规则分析模块和核心关键词词典。
- 实现低信息评论识别、评论可信度、疑似刷评风险、有效差评分类、退货评论组件识别、小红书疑似广告/可信度/情绪分析。
- 实现 `EffectiveCommentWeight` 和按维度 `WeightedNegativeRate`。
- 新增 `backend/app/services/comment_analysis_service.py`，负责把分析结果写入现有数据库模型。
- 新增 `backend/scripts/analyze_comments.py`，用于对 sample 数据执行评论和小红书分析。
- 新增评论风险摘要和小红书摘要 API。
- 新增 Agent 3 对应后端测试，覆盖规则函数、加权负面率和 API 字段完整性。

## 当前 Agent 2 已实现内容

- 创建 `backend/`、`frontend/`、`scripts/` 工程骨架。
- 搭建 FastAPI + SQLAlchemy + SQLite 后端。
- 建立标准商品、平台商品、参数、价格、福利、退货、评论、小红书、平台购买分析和综合评分占位表。
- 导入不少于 8 个标准商品、每个标准商品不少于 2 个平台商品的 sample/mock 数据。
- 提供基础商品列表、商品详情、同款平台比价和 mock 推荐 API。
- 创建 React + Vite 前端基础页面和组件。
- 新增后端自动化测试和一键检查脚本。

## 当前阶段边界

Agent 2 阶段只使用 sample/mock 数据跑通工程骨架、数据库模型、基础 API 和测试体系；不实现真实爬虫、不实现复杂推荐算法、不实现评论真实性/刷评/小红书分析算法、不实现完整价格优惠和退货风险算法。

## Agent 4 评分脚本

Agent 4 新增价格优惠、赠品估值、退货风险、平台购买分、产品综合分、推荐排序和推荐解释。运行方式：

```bash
cd backend
python scripts/calculate_scores.py
```

脚本会确保 sample 数据存在，先更新 Agent 3 评论/小红书分析，再写入或更新 `PlatformOfferAnalysis` 与 `ProductScore`，并输出：

```text
updated platform offers: xx
updated product scores: xx
```

## Agent 4 推荐 API

新增完整推荐接口，保留 `GET /api/recommendations/mock`：

```bash
GET /api/recommendations?min_price=300&max_price=900&scenario=newbie_weekend&preference=balanced&limit=10
```

返回字段包括：

- `canonical_product_id`
- `product_name`
- `brand`
- `model_name`
- `final_score`
- `data_confidence_score`
- `recommended_platform`
- `lowest_price_platform`
- `stable_final_price`
- `theoretical_lowest_price`
- `price_gap`
- `reason`
- `advantages`
- `risks`
- `risk_tags`

`GET /api/price-compare/{canonical_product_id}` 已升级为使用 Agent 4 计算后的平台分析结果，返回 `lowest_price_platform`、`recommended_platform`、`price_gap` 和解释文本。sample 数据中保留了“拼多多价格更低，但因退货/售后风险较高，推荐京东或天猫”的场景。

## 当前 Agent 4 已实现内容

- 新增 `backend/app/scoring/`：价格计算、优惠可靠性、赠品估值、退货风险、平台购买分、产品综合评分、推荐排序和解释生成模块。
- 新增 `backend/app/services/scoring_service.py`：统一计算并更新 `PlatformOfferAnalysis` 与 `ProductScore`。
- 新增 `backend/scripts/calculate_scores.py`：一键计算 sample 数据评分。
- 新增 `GET /api/recommendations`，升级 `GET /api/price-compare/{canonical_product_id}`。
- 新增 Agent 4 后端测试，覆盖价格、优惠、赠品、退货风险、平台推荐、产品评分、推荐排序和推荐 API。

## Agent 5 前端展示与最终验收说明

### 完整启动方式

数据库初始化：

```bash
cd backend
python scripts/init_db.py
python scripts/seed_sample_data.py
```

评论分析脚本：

```bash
cd backend
python scripts/analyze_comments.py
```

评分脚本：

```bash
cd backend
python scripts/calculate_scores.py
```

后端启动：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端启动：

```bash
cd frontend
npm install
npm run dev
```

前端接口基础地址支持环境变量：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001
```

如果未配置环境变量，前端默认使用相对 `/api` 路径，开发环境由 Vite 代理到 `http://127.0.0.1:8000`。

环境变量模板已提供在 `.env.example`：

```bash
DATABASE_URL=sqlite:///./camp_rank.db
VITE_API_BASE_URL=http://127.0.0.1:8001
```

本地真实环境文件 `.env` 不应提交到 Git。

### Git 提交边界

- `backend/camp_rank.db` 和其他 `*.db` 文件只作为本地运行产物，不提交到 Git。
- 演示数据通过 `cd backend && python scripts/seed_sample_data.py` 生成，不依赖提交数据库文件。
- `frontend/package-lock.json` 建议保留并提交，用于锁定前端依赖版本，保证 `npm install` 和 `npm run build` 可复现。

一键测试：

```bash
python scripts/check_all.py
```

### 核心页面说明

- 首页：展示 CampRank 项目定位，支持最低预算、最高预算、场景和偏好输入。
- 推荐结果页：调用 `GET /api/recommendations`，展示建议下单平台、当前最低价来源、价差、推荐原因、优势、风险和判断可信度。
- 商品详情页：调用商品详情、评论风险摘要和小红书口碑摘要接口，展示 ProductScore、商品参数、评论风险、小红书口碑和主要风险标签。
- 比价页：调用 `GET /api/price-compare/{canonical_product_id}`，用表格展示同款跨平台最低套餐价、理论最低价、优惠可靠性、赠品折算、售后风险、售后风险成本和平台购买分。

### 项目亮点

- 多平台同款识别：先归并标准商品，再做跨平台比价。
- 评论真实性分析：用评论可信度降低低信息评论影响。
- 疑似刷评过滤：识别模板化、低信息、异常正向评论。
- 有效差评识别：区分漏水、断杆、异味、空间虚标、退款慢等真正影响购买的风险。
- 小红书口碑修正：小红书只作为轻量口碑修正，不直接当作商品参数或价格依据。
- 最低套餐价 vs 理论最低价：区分表格当前最低套餐价格和复杂条件下的理论低价。
- 退货风险成本：把退款慢、退货运费、售后扯皮等风险折算进购买成本。
- 最低价平台和推荐平台分离：最低价只是一项信息，推荐平台综合价格、优惠稳定性、售后和置信度。
- 场景化评分：新手周末、过夜轻露营、徒步轻量、家庭多人露营使用不同权重。
- 可解释推荐：每个推荐结果展示为什么推荐、为什么避坑、为什么不一定推荐最低价。

### 当前数据边界

当前项目使用 sample/mock 数据跑通完整系统闭环，包括数据库、评论分析、评分、推荐 API、前端展示和一键测试。真实数据接入不在 Agent 5 范围内，后续可作为 Agent 6 以可插拔采集模块扩展，且必须遵守平台规则和访问限制。

### 前端手动验收清单

- 首页能输入预算、选择场景和偏好，并点击“开始推荐”。
- 推荐结果页能展示商品卡片，并出现商品名称、店铺名称、售后服务、商品链接、`recommended_platform`、`lowest_price_platform`、`price_gap` 和 `risk_tags`。
- 当推荐平台与最低价平台不一致时，页面显示“最低价平台不是系统推荐平台”。
- 商品详情页能展示商品参数、ProductScore、评论风险、小红书摘要和退货风险。
- 比价页表格能展示每个平台的最低套餐价、优惠、赠品、售后风险成本和平台购买分。
- `cd frontend && npm run build` 能通过。
