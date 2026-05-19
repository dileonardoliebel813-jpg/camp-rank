# 平台字段映射

当前项目继续导入剩余数据时只使用京东字段映射。本文档中的淘宝/天猫、小红书、拼多多、什么值得买映射仅为历史扩展规划，当前不参与导入、评分、推荐或前端解释。

CampRank 的真实平台数据接入优先使用官方 API、授权数据、用户整理 CSV/JSON 或允许访问的公开页面低频读取。默认不联网，不使用账号密码、Cookie、验证码、非公开内容或个人隐私数据。字段缺失时不应中断导入，但必须进入 data quality warnings，并降低数据置信度。

## 京东 JD

推荐优先使用京东开放平台或京东联盟 API。适合接入商品标题、SKU、价格、优惠券、店铺、自营标识、图片、推广信息等。商品详情参数、完整评论、退货政策可能存在权限或字段缺失，缺失字段必须进入 data quality warnings。

| 原始字段 | 统一字段 |
| --- | --- |
| `sku_id` | `platform_product_id` |
| `ware_name` / `title` | `title` |
| `image_url` | `image_url` |
| `price` | `current_price` |
| `coupon_amount` | `shop_coupon_amount` 或 `platform_coupon_amount` |
| `shop_name` | `shop_name` |
| `is_self_operated` | `self_operated` |
| `product_url` | `product_url` |

## 什么值得买 SMZDM

推荐使用开放平台或授权接口。适合接入好价标题、价格、优惠说明、平台来源、发布时间、跳转链接、值不值互动等。SMZDM 主要作为价格和优惠校验，不直接替代电商商品参数。

| 原始字段 | 统一字段 |
| --- | --- |
| `article_id` | `platform_product_id` |
| `title` | `title` |
| `mall` / `platform` | `platform` |
| `price` | `current_price` |
| `content` / `description` | `promotion_text` |
| `article_url` / `url` | `product_url` |
| `publish_time` | `price_update_time` |

## 淘宝 / 天猫

推荐使用淘宝开放平台或淘宝客接口。适合接入商品、优惠券、物料推荐、部分商品详情。不做登录后评价采集，不使用 Cookie，不处理验证码。

| 原始字段 | 统一字段 |
| --- | --- |
| `item_id` / `num_iid` | `platform_product_id` |
| `title` | `title` |
| `pict_url` | `image_url` |
| `zk_final_price` | `current_price` |
| `coupon_amount` | `shop_coupon_amount` |
| `shop_title` | `shop_name` |
| `user_type` 或 `shop_type` | `shop_type` |

## 拼多多 PDD

推荐使用多多进宝或授权 API。适合接入商品标题、价格、优惠券、销量、图片、店铺、商品详情等。需要明确字段来源和授权状态。

| 原始字段 | 统一字段 |
| --- | --- |
| `goods_id` / `goods_sign` | `platform_product_id` |
| `goods_name` | `title` |
| `min_group_price` | `current_price` |
| `coupon_discount` | `platform_coupon_amount` |
| `goods_thumbnail_url` | `image_url` |
| `mall_name` | `shop_name` |
| `sales_tip` | `sales_volume` |

## 小红书 RedBook

第一版不做公开笔记自动采集，只支持用户整理内容、授权数据或手动导入。小红书数据只作为外部口碑修正因子，不作为主评分唯一依据。

| 原始字段 | 统一字段 |
| --- | --- |
| `note_id` | `note_url` 或外部 ID |
| `title` | `title` |
| `desc` / `content` | `content` |
| `comments` | `comments_text` |
| `likes` | `likes` |
| `collects` / `favorites` | `favorites` |
| `comment_count` | `comment_count` |
