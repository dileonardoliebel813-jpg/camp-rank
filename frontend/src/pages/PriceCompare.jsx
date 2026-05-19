import PriceCompareTable from "../components/PriceCompareTable.jsx";
import PlatformCompareBadge from "../components/PlatformCompareBadge.jsx";
import {
  cleanText,
  DIMENSION_LABELS,
  formatCount,
  formatMoney,
  formatPercentRatio,
  labelRiskTag,
  safeList,
} from "../utils/format.js";

function displayProductName(item) {
  const sourceTitle = safeList(item?.source_sku_titles)[0] || "";
  return cleanText(sourceTitle || item?.recommended_product_title || item?.product_name || item?.normalized_name || "当前商品").replace(/^已购\s*/, "");
}

function topRiskAreas(item, limit = 3) {
  return Object.entries(item?.dimension_risk_rates || {})
    .map(([key, value]) => ({
      label: DIMENSION_LABELS[key] || key,
      value: Number(value || 0),
    }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, limit)
    .map((row) => row.label)
    .join("、");
}

function riskTagText(item) {
  const tags = safeList(item?.risk_tags).slice(0, 3).map(labelRiskTag).filter(Boolean);
  return tags.join("、");
}

function riskText(item) {
  return topRiskAreas(item) || riskTagText(item) || "当前接口未返回明显集中风险";
}

function afterSaleHighlights(value) {
  const text = cleanText(value);
  if (!text) return "当前接口未返回售后文本";
  const highlights = [];
  if (text.includes("免费上门退换")) highlights.push("免费上门退换");
  if (text.includes("闪电退款") || text.includes("极速审核")) highlights.push("退款处理较快");
  if (text.includes("京东发货&售后") || text.includes("京东售后")) highlights.push("京东相关售后");
  if (text.includes("7天无理由退货")) highlights.push("7 天无理由");
  if (text.includes("使用后不支持")) highlights.push("使用后退货有限制");
  return highlights.length ? highlights.slice(0, 4).join(" / ") : "售后文本已返回，建议下单前核对限制";
}

function priceDifferenceText(current, target) {
  const currentPrice = Number(current?.stable_final_price);
  const targetPrice = Number(target?.stable_final_price);
  if (!Number.isFinite(currentPrice) || !Number.isFinite(targetPrice)) return "当前接口缺少可比较价格";
  const gap = Math.abs(currentPrice - targetPrice);
  if (gap === 0) return "两款当前到手价相同";
  if (currentPrice > targetPrice) return `低价款便宜 ${formatMoney(gap)}`;
  return `你点的这款便宜 ${formatMoney(gap)}`;
}

function riskDifferenceText(current, target) {
  const currentRisk = Number(current?.standardized_risk_rate);
  const targetRisk = Number(target?.standardized_risk_rate);
  if (!Number.isFinite(currentRisk) || !Number.isFinite(targetRisk)) return "当前接口缺少可比较的评论风险统计";
  if (Math.abs(currentRisk - targetRisk) < 0.005) return "两款评论风险信号接近";
  if (currentRisk < targetRisk) {
    return `你点的这款评论风险信号更低一些：${formatPercentRatio(currentRisk)} vs ${formatPercentRatio(targetRisk)}`;
  }
  return `低价对比款评论风险信号更低一些：${formatPercentRatio(targetRisk)} vs ${formatPercentRatio(currentRisk)}`;
}

function conclusionText(current, target, targetRole) {
  const currentPrice = Number(current?.stable_final_price);
  const targetPrice = Number(target?.stable_final_price);
  const currentRisk = Number(current?.standardized_risk_rate);
  const targetRisk = Number(target?.standardized_risk_rate);
  const targetName = targetRole === "low_price" ? "低价款" : "当前首选";
  if (!current || !target) {
    return "当前缺少可对比的候选商品。请先回到购买建议页，让系统生成本次推荐结果后再对比。";
  }
  if (Number.isFinite(currentPrice) && Number.isFinite(targetPrice) && currentPrice > targetPrice) {
    if (Number.isFinite(currentRisk) && Number.isFinite(targetRisk) && currentRisk <= targetRisk) {
      return `${targetName}确实更便宜，但你点的这款在当前评论样本里的风险信号没有更高。是否多花这部分钱，主要看你是否更在意稳妥和售后条件。`;
    }
    return `${targetName}更便宜。你点的这款如果还要继续考虑，需要看它是否在售后、容量或评论反馈上更符合你的使用场景。`;
  }
  if (Number.isFinite(currentPrice) && Number.isFinite(targetPrice) && currentPrice < targetPrice) {
    return `你点的这款当前反而更便宜。这里主要帮你确认：便宜的同时，评论风险和售后条件是否还能接受。`;
  }
  return `两款价格接近，建议主要比较评论里集中提到的问题和售后限制。`;
}

function openProductUrl(url) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

function CompareProductPanel({ title, item, emphasis }) {
  if (!item) {
    return (
      <section className="compare-product-panel">
        <p className="eyebrow">{title}</p>
        <p className="empty">当前接口没有返回这部分候选商品。</p>
      </section>
    );
  }

  return (
    <section className={`compare-product-panel ${emphasis || ""}`}>
      <p className="eyebrow">{title}</p>
      <h3>{displayProductName(item)}</h3>
      <div className="compare-fact-grid">
        <div>
          <span>到手价</span>
          <strong>{formatMoney(item.stable_final_price)}</strong>
        </div>
        <div>
          <span>评论样本</span>
          <strong>{formatCount(item.comment_count)} 条</strong>
        </div>
        <div>
          <span>主要留意</span>
          <strong>{riskText(item)}</strong>
        </div>
        <div>
          <span>售后重点</span>
          <strong>{afterSaleHighlights(item.recommended_after_sale_service)}</strong>
        </div>
      </div>
      <p className="muted">
        按当前评论样本校正后，购买风险参考值约 {formatPercentRatio(item.standardized_risk_rate)}。
        这个数值只用于比较风险信号，不代表真实使用中一定会出问题。
      </p>
      {item.recommended_product_url && (
        <button type="button" className="link-button" onClick={() => openProductUrl(item.recommended_product_url)}>打开商品链接</button>
      )}
    </section>
  );
}

export default function PriceCompare({ compare }) {
  const current = compare?.selected_recommendation;
  const target = compare?.comparison_target;
  const targetRole = compare?.comparison_target_role;
  const isDifferent = compare?.recommended_platform && compare?.lowest_price_platform
    && compare.recommended_platform !== compare.lowest_price_platform;
  const hasMultiplePlatformOffers = (compare?.offers || []).length > 1;

  if (!compare) {
    return (
      <section className="workspace">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">Price Compare</p>
            <h2>和低价款对比</h2>
            <p className="lead">请先在购买建议中选择一款商品，再查看它和当前低价候选的差别。</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="compare-page">
      <div className="workspace-heading compare-heading">
        <div>
          <p className="eyebrow">和低价款对比</p>
          <h2>{current && target ? `${displayProductName(current)} vs ${displayProductName(target)}` : cleanText(compare.canonical_product?.normalized_name) || "对比结果"}</h2>
          <p className="lead">
            这里不是重新编一套结论，只比较当前推荐接口已经返回的真实候选数据：价格、评论样本、风险信号、售后文本和商品链接。
          </p>
        </div>
      </div>

      <section className="compare-summary">
        <div>
          <span>价格差别</span>
          <strong>{priceDifferenceText(current, target)}</strong>
        </div>
        <div>
          <span>评论风险信号</span>
          <strong>{riskDifferenceText(current, target)}</strong>
        </div>
        <div>
          <span>怎么选</span>
          <strong>{conclusionText(current, target, targetRole)}</strong>
        </div>
      </section>

      <div className="compare-product-grid">
        <CompareProductPanel title="你点的这款" item={current} emphasis="selected" />
        <CompareProductPanel title={targetRole === "low_price" ? "当前低价款" : "当前首选对照"} item={target} emphasis="target" />
      </div>

      <section className="decision-section full-width">
        <h3>同款平台报价</h3>
        <p>
          这一块只展示同一个标准商品下已经接入的报价。如果当前只有一个京东报价，说明接口没有返回更多同款平台报价，不会强行补造淘宝、拼多多或其他平台价格。
        </p>
        {hasMultiplePlatformOffers ? (
          <>
            <PlatformCompareBadge
              recommendedPlatform={compare.recommended_platform}
              lowestPricePlatform={compare.lowest_price_platform}
              priceGap={compare.price_gap}
              reason={compare.explanation}
            />
            {isDifferent && (
              <p className="notice">
                当前最低价来源不一定是更稳的下单选择。系统会把售后保障、优惠稳定性和潜在售后成本一起纳入判断。
              </p>
            )}
            <PriceCompareTable offers={compare.offers || []} />
          </>
        ) : (
          <p className="notice">
            当前同款只返回 {(compare.offers || []).length} 个平台报价；本页上方已改为使用当前候选商品里的低价款做真实对比。
          </p>
        )}
      </section>
    </section>
  );
}
