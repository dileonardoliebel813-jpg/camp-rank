# 官方 API / 授权数据源接入

当前项目继续导入剩余数据时不使用本文件里的多平台 live API。当前只接受京东本地表格或京东标准 JSON；淘宝/天猫、小红书、拼多多、什么值得买入口只保留为历史扩展规划，不参与当前推荐依据。

CampRank 只支持官方 API、开放平台、联盟 API、授权数据源和手动整理数据。默认所有官方 API 都关闭，不使用账号密码、Cookie、验证码、非公开内容，也不采集个人隐私。

## 接入状态

| 平台 | 状态 | 已支持能力 |
| --- | --- | --- |
| JD | 已接入 SDK client 与 adapter | 商品关键词查询、详情扩展点、标题/品牌/价格/优惠/店铺/自营服务标签映射 |
| SMZDM | 已接入 SDK client 与 adapter | 好价搜索、详情扩展点、标题/价格摘要/优惠说明/链接/发布时间/值不值映射 |
| TAOBAO/TMALL | 已接入 TOP client 与 adapter | 淘宝客物料搜索封装、标题/价格/券后价/销量/店铺/图片/链接映射 |
| PDD | 已接入开放平台 client 与 adapter | 多多进宝商品搜索/详情封装、价格分转元、券后价/销量/主图/店铺映射 |
| REDBOOK | 仅保留授权 guard | 不做公开内容采集；启用但未接入授权实现时返回 unsupported message |

## 环境变量

所有平台默认关闭。开启 live 前必须配置对应 Key、Secret、Base URL 和 method/path。

```bash
JD_API_ENABLED=true
JD_APP_KEY=your_app_key
JD_APP_SECRET=your_app_secret
JD_BASE_URL=https://official-jd-router.example
JD_API_METHOD_SEARCH=your.jd.search.method
JD_API_METHOD_DETAIL=your.jd.detail.method

SMZDM_API_ENABLED=true
SMZDM_API_KEY=your_api_key
SMZDM_BASE_URL=https://authorized-smzdm.example
SMZDM_SEARCH_PATH=/search
SMZDM_DETAIL_PATH=/detail

TAOBAO_API_ENABLED=true
TAOBAO_APP_KEY=your_app_key
TAOBAO_APP_SECRET=your_app_secret
TAOBAO_BASE_URL=https://eco.taobao.com/router/rest
TAOBAO_ADZONE_ID=your_adzone_id
TAOBAO_SEARCH_METHOD=taobao.tbk.dg.material.optional

PDD_API_ENABLED=true
PDD_CLIENT_ID=your_client_id
PDD_CLIENT_SECRET=your_client_secret
PDD_BASE_URL=https://gw-api.pinduoduo.com/api/router
PDD_SEARCH_METHOD=pdd.ddk.goods.search
PDD_DETAIL_METHOD=pdd.ddk.goods.detail
```

Key 需要从对应官方开放平台、联盟平台或授权数据合作方申请。项目不会猜测接口地址，也不会用 sample 数据伪装 live 成功。

## Dry-run 与保存样例

```bash
cd backend
python scripts/fetch_real_data.py --source jd --keyword 帐篷 --limit 5 --live --dry-run
python scripts/fetch_real_data.py --source smzdm --keyword 帐篷 --limit 5 --live --dry-run --save-json
python scripts/fetch_real_data.py --source taobao --keyword 帐篷 --limit 5 --live --dry-run
python scripts/fetch_real_data.py --source pdd --keyword 帐篷 --limit 5 --live --dry-run
```

`--dry-run` 只请求并标准化，不写入数据库。`--save-json` 会把标准化结果保存到 `backend/data/real_samples/live_fetch_{platform}_{timestamp}.json`，不包含密钥。

## Live Smoke Test

```bash
cd backend
python scripts/live_smoke_test.py
```

如果没有任何平台启用，脚本输出 `no official api enabled, skipped live smoke test.` 并返回 0。如果某个平台启用但请求或字段映射失败，脚本返回非 0。

## API 调用

```http
POST /api/ingestion/fetch-official
```

```json
{
  "source": "jd",
  "keyword": "帐篷",
  "limit": 5,
  "live": true,
  "dry_run": true
}
```

默认 `dry_run=true`。只有调用方显式传入 `dry_run=false` 时，结果才进入现有 pipeline：SDK Client -> Adapter -> Platform Mapper -> Import Service -> Comment Analysis -> Score Calculation -> Frontend Display。

## Contract Test

无 Key 时运行官方响应样例的字段映射测试：

```bash
cd backend
python -m pytest tests/test_official_response_contracts.py
```

样例位于 `backend/data/official_response_samples/`，不包含密钥或个人信息。

## 合规边界

- 不支持账号密码。
- 不支持 Cookie。
- 不处理验证码。
- 不访问非公开内容。
- 不采集个人隐私。
- 不做高频请求，client 默认有 rate limit 和 timeout。
- 缺少 Key 或必要 method/path 时清晰报错，不伪造成功。
