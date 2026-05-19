# CampRank 测试与验收策略

## 当前验收覆盖：京东-only 数据链

当前继续导入剩余数据时，验收重点是京东表格到前端购买决策页的完整闭环：京东表格清洗、标准 JSON、数据库导入、京东评论分析、评分计算、推荐接口、详情页、低价对比页和 `python scripts/check_all.py`。

旧文档中“必须包含淘宝/天猫、拼多多、什么值得买、小红书样例数据”的条目属于历史多平台规划；本轮不作为验收要求。当前验收不得要求小红书笔记、淘宝评论或跨平台价格。缺失的非京东数据只能作为“当前未接入”边界说明，不能用 mock 或编造内容补齐。

本文档规定 CampRank 后续每个 Agent 如何测试、测试什么、如何定位问题。所有 Agent 必须把测试当作交付的一部分，而不是完成后的附加步骤。

## 1. 总体测试原则

- 每个 Agent 不能只写功能，必须同步写测试。
- 每个 Agent 完成后必须运行自动化测试。
- 测试失败时，Agent 必须先修复测试，再汇报完成。
- 不允许为了通过测试删除已有测试。
- 不允许只说“已测试”，必须给出测试命令和测试结果。
- 所有关键业务逻辑必须有单元测试。
- 所有 API 必须有接口测试。
- 所有数据库模型和 seed 数据必须有数据完整性测试。
- 所有前端页面至少必须通过构建测试。
- 每个阶段都要能通过一键检查命令。
- 测试应覆盖正常路径、边界条件、缺失数据和高风险业务场景。
- 推荐、评分、比价、评论识别等核心逻辑必须测试可解释字段，而不只测试总分。

测试失败时，Agent 的处理顺序：

1. 阅读失败信息，定位失败测试文件和断言。
2. 判断是实现错误、测试预期错误、样例数据错误、依赖环境错误还是接口契约变化。
3. 优先修复实现或样例数据，只有当测试确实与文档标准冲突时，才更新测试并说明原因。
4. 重新运行相关测试。
5. 最后运行本阶段要求的完整测试命令。

## 2. 一键检查脚本规划

后续 Agent 2 需要创建：

```text
scripts/check_all.py
```

后续应在项目根目录运行：

```bash
python scripts/check_all.py
```

该脚本应自动执行：

后端测试：

```bash
cd backend
python -m pytest
```

前端构建：

```bash
cd frontend
npm run build
```

脚本行为要求：

- 如果当前阶段还没有 `backend`，应输出清晰提示，例如 `backend directory not found, skipping backend checks for current stage.`，而不是直接崩溃。
- 如果当前阶段还没有 `frontend`，应输出清晰提示，例如 `frontend directory not found, skipping frontend checks for current stage.`，而不是直接崩溃。
- 如果存在 `backend`，但后端测试失败，脚本必须返回非 0 状态码。
- 如果存在 `frontend`，但前端构建失败，脚本必须返回非 0 状态码。
- 如果任意一步失败，脚本返回非 0 状态码。
- 如果全部通过，输出：

```text
All CampRank checks passed.
```

定位问题时，脚本应保留每一步的命令输出，方便 Agent 直接看到失败原因。

## 3. Agent 2 历史测试要求

Agent 2 负责项目骨架、后端基础、前端基础、数据库模型、样例数据。以下是早期多平台样例阶段的历史要求；当前继续导入京东剩余数据时，不要求补齐淘宝/天猫、拼多多、什么值得买或小红书样例。

必须测试：

- `GET /health` 返回 200。
- `GET /health` 返回 `project = CampRank`。
- 数据库所有核心表可以创建。
- 数据库连接正常。
- seed 样例数据可以导入。
- 至少 8 个 canonical products。
- 每个 canonical product 至少 2 个平台商品。
- 历史样例阶段曾要求京东、淘宝/天猫、拼多多、什么值得买、小红书样例数据；当前京东-only 数据导入不执行该项。
- 当前京东-only 数据导入只要求存在京东评论、价格、优惠/权益、退货、售后和评分数据。
- `GET /api/products` 返回 200。
- `GET /api/products/{id}` 返回商品详情。
- `GET /api/price-compare/{id}` 在当前京东-only 数据下可以只返回一个京东报价，并明确提示接口未返回更多平台报价。
- `npm run build` 通过。
- 首页可以展示项目名称。
- 推荐页可以展示 mock 或 sample 推荐结果。

建议测试文件：

- `backend/tests/test_health.py`
- `backend/tests/test_database_models.py`
- `backend/tests/test_seed_sample_data.py`
- `backend/tests/test_products_api.py`
- `backend/tests/test_price_compare_api.py`

Agent 2 还需要创建 `scripts/check_all.py`，并在最终汇报中说明：

- `python scripts/check_all.py` 是否已能运行。
- 没有 `backend` 或 `frontend` 时的提示逻辑是否已覆盖。
- 后端测试和前端构建的执行结果。

## 4. Agent 3 测试要求

Agent 3 负责评论真实性、刷评过滤、有效差评、小红书口碑、退货评论识别。

必须测试低信息评论识别：

- “好评”
- “不错”
- “物流很快”
- “还没用，先好评”

必须测试疑似刷评识别：

- 模板化好评。
- 短时间集中好评。
- 大量重复文本。
- 只夸不讲细节。

必须测试高可信评论识别：

- 包含使用场景。
- 包含天气。
- 包含人数。
- 包含搭建或收纳体验。
- 追评 / 带图评论。

必须测试有效差评识别：

- 漏水。
- 冷凝水。
- 杆子断。
- 味道大。
- 空间虚标。
- 不好收纳。
- 防晒差。

必须测试售后退货差评识别：

- 退款慢。
- 退款少。
- 不给退。
- 退货麻烦。
- 客服态度差。
- 退货运费争议。

必须测试小红书内容判断：

- 疑似广告种草。
- 真实避坑笔记。
- 正常体验笔记。

必须测试加权负面率：

- WeightedNegativeRate 计算正确。
- 疑似刷评不会显著影响评分。
- 高可信差评能触发风险标签。

建议测试文件：

- `backend/tests/test_review_quality.py`
- `backend/tests/test_fake_review_detector.py`
- `backend/tests/test_negative_review_classifier.py`
- `backend/tests/test_return_review_analysis.py`
- `backend/tests/test_redbook_analysis.py`
- `backend/tests/test_weighted_comment_metrics.py`

Agent 3 完成后必须运行：

```bash
cd backend && python -m pytest
```

如果 Agent 3 修改了前端展示或联调内容，也必须运行：

```bash
cd frontend && npm run build
```

## 5. Agent 4 测试要求

Agent 4 负责价格优惠、赠品估值、退货风险、平台购买推荐、产品评分、推荐排序。

必须测试：

- StableFinalPrice 计算正确。
- TheoreticalLowestPrice 计算正确。
- CouponUncertaintyCost 计算正确。
- 普通店铺券得分高。
- 新人券、直播券、限量券得分低。
- 理论低价不等于稳妥到手价。
- 赠品估值不采信商家宣传价值。
- GiftAdjustedCost 计算正确。
- ReturnProtectionScore 计算正确。
- ReturnRiskScore 计算正确。
- ReturnRiskCost 计算正确。
- lowest_price_platform 识别正确。
- recommended_platform 可以不同于 lowest_price_platform。
- 拼多多最低价但退货风险高时，系统可以推荐京东。
- 用户选择“最低价优先”时推荐逻辑变化。
- 用户选择“售后优先”时推荐逻辑变化。
- FinalProductScore 计算正确。
- 高风险项可以触发 RiskPenalty。
- 预算筛选正确。
- 场景化权重生效。
- 数据置信度低时不能强推荐。
- TopN 返回顺序正确。

建议测试文件：

- `backend/tests/test_price_calculation.py`
- `backend/tests/test_coupon_reliability.py`
- `backend/tests/test_gift_value.py`
- `backend/tests/test_return_risk.py`
- `backend/tests/test_platform_buy_score.py`
- `backend/tests/test_product_scoring.py`
- `backend/tests/test_recommendation_ranker.py`

Agent 4 完成后必须运行：

```bash
cd backend && python -m pytest
```

如果 Agent 4 修改了前端联调或展示字段，也必须运行：

```bash
cd frontend && npm run build
```

## 6. Agent 5 测试要求

Agent 5 负责前端页面、接口联调、展示逻辑、README、面试包装、GitHub 推送。

必须测试：

- `npm run build` 通过。
- 首页正常展示。
- 推荐结果页展示商品卡片。
- 商品详情页展示参数、评论风险、小红书口碑。
- 比价页展示不同平台价格、优惠、赠品、退货风险。
- 避坑榜展示漏水、断杆、异味、退款慢等风险。

必须展示字段：

- `final_score`
- `data_confidence_score`
- `lowest_price_platform`
- `recommended_platform`
- `stable_final_price`
- `theoretical_lowest_price`
- `price_gap`
- `return_protection_score`
- `return_risk_score`
- `risk_adjusted_cost`
- `risk_tags`

用户交互必须验证：

- 预算筛选可用。
- 使用场景选择可用。
- 最低价优先 / 售后优先 / 综合性价比优先可切换。
- 切换偏好后推荐结果能变化或显示对应解释。

Agent 5 完成后必须运行：

```bash
cd frontend && npm run build
```

如果 Agent 5 修改了后端 API、后端数据结构或联调契约，也必须运行：

```bash
cd backend && python -m pytest
```

最终还必须运行：

```bash
python scripts/check_all.py
```

## 7. 每个 Agent 最终汇报格式

后续每个 Agent 最终汇报必须包含：

- 本阶段完成内容。
- 修改/新增文件。
- 新增测试文件。
- 运行的测试命令。
- 测试结果，例如：
  - `python -m pytest`：`xx passed`
  - `npm run build`：成功
  - `python scripts/check_all.py`：`All CampRank checks passed`
- 如果测试失败，失败原因是什么，如何修复。
- 未完成内容。
- 下一步建议。

没有测试结果，不算完成。若当前阶段因尚未创建后端或前端而不能运行对应命令，必须明确说明原因，并运行当前阶段可用的检查命令。

## 8. 问题定位标准

后端测试失败时优先检查：

- API 路由是否与文档约定一致。
- schema 字段是否缺失或命名不一致。
- 数据库表结构和 seed 数据是否匹配。
- 样例数据是否满足最小数量要求。
- 评分、比价、评论识别是否返回解释字段。

前端构建失败时优先检查：

- API 类型定义是否与后端返回一致。
- 必须展示字段是否存在空值处理。
- 路由和页面组件是否导出正确。
- 样式和依赖是否已安装并记录。

一键检查失败时优先检查：

- 是否在项目根目录运行。
- `backend` 或 `frontend` 是否存在。
- Python、Node、依赖安装是否完成。
- 子命令失败输出中的第一处错误。
