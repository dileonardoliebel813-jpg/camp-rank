# CampRank 多 Agent 工作流

本文档定义 5 个 Agent 的分工、输入、输出、测试要求和禁止事项。后续 Agent 必须按顺序推进，避免重复搭建、越界实现或破坏已有结构。

所有 Agent 必须阅读并遵守 `docs/testing_strategy.md`。没有测试结果，不算完成；新增功能必须新增或更新对应测试。

## Agent 1：项目需求、总体设计与规范文档

负责内容：

- 创建项目目录和文档结构。
- 编写 README、AGENTS 和核心设计文档。
- 明确项目不是简单爬虫，而是多平台消费决策系统。
- 定义采集、同款识别、评论质量、价格优惠、退货风险、评分模型和 Agent 工作规范。
- 补充 `docs/testing_strategy.md`，规定后续每个 Agent 的测试责任和验收标准。

输入文档：

- 用户需求。

输出文件：

- `README.md`
- `AGENTS.md`
- `docs/project_design.md`
- `docs/data_acquisition_and_comparison_plan.md`
- `docs/review_quality_control.md`
- `docs/platform_price_benefit_plan.md`
- `docs/return_and_refund_risk_plan.md`
- `docs/scoring_model.md`
- `docs/agent_workflow.md`
- `docs/interview_script.md`
- `docs/testing_strategy.md`

测试要求：

- 本阶段不写业务代码，因此不运行后端或前端测试。
- 需要确认只新增文档文件。
- 需要确认没有创建 `backend`、`frontend`、数据库或爬虫实现。

不允许做什么：

- 不写后端代码。
- 不写前端代码。
- 不写数据库模型。
- 不写爬虫代码。
- 不创建业务实现目录来抢占后续 Agent 工作。

## Agent 2：项目骨架、数据库模型与样例数据

负责内容：

- 创建后端和前端基础目录。
- 搭建 FastAPI 项目骨架。
- 建立 SQLite 数据库连接。
- 设计商品、平台报价、评论、退货政策、评分结果等数据库模型。
- 准备 mock/sample 数据，确保系统流程可跑通。
- 创建基础 API 和数据库测试。

输入文档：

- `README.md`
- `AGENTS.md`
- `docs/project_design.md`
- `docs/data_acquisition_and_comparison_plan.md`
- `docs/scoring_model.md`
- `docs/testing_strategy.md`

输出文件：

- `backend/` 项目骨架。
- `backend` 下数据库模型、schema、基础 API。
- `backend/tests/` 测试。
- `data/` 或后端约定目录下的 sample 数据。
- 必要的依赖说明文件。
- `scripts/check_all.py` 一键检查脚本。

测试要求：

- `cd backend && python -m pytest`
- `cd frontend && npm run build`
- `python scripts/check_all.py`
- 新增数据库模型必须写数据库测试。
- 新增 API 必须写接口测试。
- 必须覆盖 `docs/testing_strategy.md` 中 Agent 2 的 health、数据库、seed、产品 API、比价 API 和前端构建要求。

不允许做什么：

- 不实现复杂评论分析算法。
- 不实现最终评分算法。
- 不写真实爬虫。
- 不把样例数据伪装成真实采集数据。
- 不删除 Agent 1 文档。

## Agent 3：评论真实性、刷评过滤、差评识别、小红书口碑分析

负责内容：

- 实现低信息评论过滤。
- 实现 FakeReviewRiskScore。
- 实现 CommentCredibilityScore。
- 实现 EffectiveCommentWeight。
- 实现有效差评分类。
- 实现小红书口碑可信度和 RedBookScore 计算。
- 输出评论风险标签和维度负面率。

输入文档：

- `README.md`
- `AGENTS.md`
- `docs/project_design.md`
- `docs/review_quality_control.md`
- `docs/scoring_model.md`
- `docs/testing_strategy.md`

输出文件：

- 评论分析服务模块。
- 评论规则词典。
- 小红书口碑分析模块。
- 评论分析测试。

测试要求：

- `cd backend && python -m pytest`
- 新增评论分析函数必须写评论识别测试。
- 必须覆盖低信息评论、疑似刷评、高可信评论、有效差评、无效差评、小红书疑似广告样本。
- 必须覆盖 `docs/testing_strategy.md` 中 Agent 3 的退货评论识别、WeightedNegativeRate 和风险标签测试。
- 若修改前端展示或联调内容，也必须运行 `cd frontend && npm run build`。

不允许做什么：

- 不默认所有评论都真实。
- 不把星级评分直接当真实口碑。
- 不把小红书种草笔记直接正向加分。
- 不绕过采集合规要求。
- 不修改数据库结构时跳过迁移或测试。

当前 Agent 3 实际输出补充：

- 新增 `backend/app/nlp/`，包含关键词词典、评论质量、疑似刷评、有效差评、退货评论、小红书口碑和加权负面率模块。
- 新增 `backend/app/services/comment_analysis_service.py`，将分析结果写入 `CommentQualityAnalysis`、`NegativeReviewAnalysis` 和 `RedBookNote`。
- 新增 `backend/scripts/analyze_comments.py`，用于分析当前 sample 数据。
- 新增 `/api/products/{canonical_product_id}/comment-risk-summary` 和 `/api/products/{canonical_product_id}/redbook-summary`。
- 新增 Agent 3 测试文件，覆盖低信息评论、刷评风险、有效差评、退货评论、小红书口碑、加权负面率和 API。

## Agent 4：价格优惠、退货风险、评分推荐算法

负责内容：

- 实现同款商品的平台比价逻辑。
- 实现 StableFinalPrice 和 TheoreticalLowestPrice。
- 实现 CouponReliabilityScore。
- 实现 GiftAdjustedCost。
- 实现 ReturnProtectionScore、ReturnRiskScore、ReturnRiskCost。
- 实现 RiskAdjustedCost。
- 实现 FinalProductScore 和 PlatformBuyScore。
- 实现场景化推荐和解释生成。

输入文档：

- `README.md`
- `AGENTS.md`
- `docs/project_design.md`
- `docs/data_acquisition_and_comparison_plan.md`
- `docs/platform_price_benefit_plan.md`
- `docs/return_and_refund_risk_plan.md`
- `docs/scoring_model.md`
- `docs/testing_strategy.md`

输出文件：

- 价格比较服务。
- 退货风险服务。
- 评分推荐服务。
- 推荐解释生成模块。
- 评分、比价和退货风险测试。

测试要求：

- `cd backend && python -m pytest`
- 新增评分函数必须写评分排序测试。
- 新增比价函数必须写平台推荐测试。
- 新增退货风险函数必须写风险分层测试。
- 必须测试 lowest_price_platform 和 recommended_platform 不一致的情况。
- 必须覆盖 `docs/testing_strategy.md` 中 Agent 4 的价格、优惠、赠品、退货风险、场景化权重、预算筛选和 TopN 排序测试。
- 若修改前端联调或展示字段，也必须运行 `cd frontend && npm run build`。

不允许做什么：

- 不默认最低价平台就是推荐平台。
- 不在未完成同款识别时跨平台比价。
- 不把赠品宣传价值等同现金。
- 不忽略退货风险。
- 不输出不可解释的黑箱推荐。

## Agent 5：前端展示、联调、README、面试包装、GitHub 推送

负责内容：

- 搭建 React + Vite + Tailwind CSS 前端。
- 展示商品推荐、平台比价、风险标签、评论风险、小红书口碑和数据置信度。
- 与后端 API 联调。
- 补充 README 运行说明、项目截图说明和面试展示材料。
- 准备 GitHub 推送前检查。

输入文档：

- `README.md`
- `AGENTS.md`
- `docs/project_design.md`
- `docs/scoring_model.md`
- `docs/interview_script.md`
- `docs/testing_strategy.md`
- 后端 API 文档或接口实现。

输出文件：

- `frontend/` 项目。
- 前端页面和组件。
- API 调用模块。
- 构建配置。
- 更新后的 README。
- 面试展示补充材料。

测试要求：

- `cd frontend && npm run build`
- 如果联调时修改后端，也必须运行 `cd backend && python -m pytest`
- `python scripts/check_all.py`
- 前端必须能展示 recommended_platform 和 lowest_price_platform 的区别。
- 必须覆盖 `docs/testing_strategy.md` 中 Agent 5 的页面展示字段、预算筛选、场景选择和偏好切换验收要求。

不允许做什么：

- 不把前端做成普通商品列表。
- 不只展示总分而不展示解释。
- 不隐藏风险标签。
- 不删除后端测试。
- 不绕过 API 直接写死所有结果，除非明确是 demo mock 且已标注。

## 跨 Agent 协作要求

- 每个 Agent 开始前必须确认前一阶段产物存在。
- 每个 Agent 只能在自己职责范围内修改。
- 如发现文档与实现冲突，先在最终汇报中说明，再做最小必要调整。
- 所有新增功能必须有测试。
- 所有 Agent 必须遵守 `docs/testing_strategy.md` 的分阶段测试要求。
- 最终汇报必须包含完成内容、文件清单、测试命令、测试结果、未完成内容和下一步建议。
