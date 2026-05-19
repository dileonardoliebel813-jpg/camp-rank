import { useState } from "react";
import CommentRiskPanel from "../components/CommentRiskPanel.jsx";
import RiskTag from "../components/RiskTag.jsx";
import ScoreBadge from "../components/ScoreBadge.jsx";
import {
  cleanText,
  DIMENSION_LABELS,
  formatCount,
  formatMoney,
  formatPercentRatio,
  labelRiskTag,
  safeList,
} from "../utils/format.js";

function lowestRecommendationPrice(rows = []) {
  const prices = rows.map((row) => Number(row.stable_final_price)).filter(Number.isFinite);
  return prices.length ? Math.min(...prices) : null;
}

function currentPrice(detail, recommendation) {
  if (Number.isFinite(Number(recommendation?.stable_final_price))) return Number(recommendation.stable_final_price);
  const prices = detail?.prices || [];
  const stable = prices.map((row) => Number(row.stable_final_price)).filter(Number.isFinite);
  return stable.length ? stable[0] : null;
}

function distributionText(distribution = {}) {
  return `好评 ${distribution.positive ?? 0} / 中评 ${distribution.neutral ?? 0} / 差评 ${distribution.negative ?? 0}`;
}

function openProductUrl(url) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

function riskRows(rates = {}) {
  return ["return_after_sale", "durability", "waterproof", "windproof", "space", "storage", "setup", "smell_heat"].map((key) => ({
    key,
    label: DIMENSION_LABELS[key] || key,
    value: Number(rates[key] || 0),
  }));
}

function riskLabel(rate) {
  if (rate >= 0.2) return "中等偏高风险";
  if (rate >= 0.08) return "中等风险";
  if (rate >= 0.005) return "较低风险";
  return "暂未发现明显反馈";
}

function displayProductName(recommendation, product) {
  const sourceTitle = safeList(recommendation?.source_sku_titles)[0] || "";
  return cleanText(sourceTitle || recommendation?.recommended_product_title || product?.normalized_name || "当前商品").replace(/^已购\s*/, "");
}

function selectedProduct(products, recommendation) {
  const id = recommendation?.recommended_platform_product_id;
  return products.find((item) => item.platform_product_id === id) || products[0] || {};
}

function selectedByProductId(rows = [], productId) {
  return rows.find((row) => row.product_id === productId) || rows[0] || {};
}

function selectedParameterAnalysis(detail, chosenProduct, recommendation) {
  const rows = detail?.parameter_analysis || [];
  return rows.find((row) => row.product_id === chosenProduct?.id)?.analysis || recommendation?.parameter_analysis || {};
}

function parameterFactList(analysis = {}) {
  const facts = analysis.facts || {};
  return [
    facts.expanded_size_text && `展开尺寸：${facts.expanded_size_text}`,
    facts.inner_size_text && `内帐尺寸：${facts.inner_size_text}`,
    facts.weight_text && `重量：${facts.weight_text}`,
    facts.packed_size_text && `收纳尺寸：${facts.packed_size_text}`,
    facts.outer_material && `面料：${facts.outer_material}`,
    facts.floor_material && `底布/帐底：${facts.floor_material}`,
    facts.pole_material && `帐杆：${facts.pole_material}`,
    facts.capacity_text && `容量文字：${facts.capacity_text}`,
  ].filter(Boolean);
}

function riskTagText(recommendation) {
  const tags = safeList(recommendation?.risk_tags).slice(0, 5).map(labelRiskTag).filter(Boolean);
  return tags.length ? tags.join("、") : "当前接口未返回高频风险标签";
}

function priceExplanation(current, lowest, priceGap, recommendation) {
  const score = Number(recommendation?.final_score || 0).toFixed(1).replace(".0", "");
  if (priceGap > 0) {
    return `这款到手价为 ${formatMoney(current)}，比当前候选中的最低到手价高 ${formatMoney(priceGap)}。系统没有只按最低价排序，而是同时参考购买推荐指数 ${score}、评论样本 ${formatCount(recommendation?.comment_count)} 条、售后文本和风险标签，所以只能说它在当前候选中相对更稳妥，不代表一定最适合所有人。`;
  }
  return `这款到手价为 ${formatMoney(current)}，在当前候选中属于较低价格区间。系统仍会继续参考购买推荐指数 ${score}、评论样本 ${formatCount(recommendation?.comment_count)} 条、售后文本和风险标签，避免只因为便宜就直接下结论。`;
}

function reviewExplanation(distribution, commentCount, recommendation) {
  const riskRate = recommendation?.standardized_risk_rate;
  return `当前用于判断的评论样本约 ${formatCount(commentCount)} 条，原始分布为 ${distributionText(distribution)}。系统会把评论结构偏离度和校正后购买风险一起看；这款的校正后购买风险约为 ${formatPercentRatio(riskRate)}。这个数值只是基于当前评论样本的风险参考，不等于真实使用中一定会或一定不会出问题。`;
}

function riskExplanation(rows, recommendation) {
  const top = rows.filter((row) => row.value > 0).sort((a, b) => b.value - a.value).slice(0, 3);
  if (!top.length) {
    return `当前接口没有返回明显集中的风险维度。仍建议结合售后服务、商品链接和原始评论进一步确认，因为没有集中反馈不等于没有风险。`;
  }
  const text = top.map((row) => `${row.label} ${formatPercentRatio(row.value)}`).join("、");
  return `当前评论样本里，提到相对集中的担心是：${text}。风险标签里还出现：${riskTagText(recommendation)}。这些来自评论和售后文本，只能说明当前样本里有人提到过这些问题，不是实验室检测结论。`;
}

function simpleRiskList(rows, recommendation) {
  const top = rows.filter((row) => row.value > 0).sort((a, b) => b.value - a.value).slice(0, 3);
  if (top.length) return top.map((row) => row.label).join("、");
  const tags = riskTagText(recommendation);
  return tags === "当前接口未返回高频风险标签" ? "暂无特别集中的风险反馈" : tags;
}

function userSummary({ displayName, current, recommendation, sortedRiskRows, commentCount }) {
  const risks = simpleRiskList(sortedRiskRows, recommendation);
  const userScore = recommendation?.user_match_score !== undefined ? `本次匹配分 ${Number(recommendation.user_match_score).toFixed(1).replace(".0", "")}，` : "";
  return `${displayName} 当前到手价是 ${formatMoney(current)}，${userScore}评论样本约 ${formatCount(commentCount)} 条，校正后购买风险约 ${formatPercentRatio(recommendation?.standardized_risk_rate)}。系统把它放进建议里，是因为这些字段综合看下来有参考价值；但评论里仍然有 ${risks} 这些需要留意的信号，所以它更适合作为购买风险参考，而不是“闭眼买”的结论。`;
}

function plainPriceText(current, lowest, priceGap) {
  if (current === null || current === undefined) {
    return "当前接口没有返回可用到手价，暂时不能只凭价格判断。建议先打开商品链接核对页面价格。";
  }
  if (priceGap > 0) {
    return `这款不是当前最便宜的。它的到手价是 ${formatMoney(current)}，比候选里最低到手价高 ${formatMoney(priceGap)}。如果你只看价格，需要再和低价备选对比；如果你更在意综合购买风险控制，还要一起看评论和售后风险。`;
  }
  return `这款到手价是 ${formatMoney(current)}，在当前候选里价格相对靠低。如果你预算紧，它有价格优势，但仍要看评论和售后风险。`;
}

function plainReviewText(distribution, commentCount, recommendation) {
  return `这款有约 ${formatCount(commentCount)} 条评论样本。好中差分布是 ${distributionText(distribution)}。系统没有直接按好评多就推荐，而是把差评、中评里的风险词也一起看；当前校正后购买风险约 ${formatPercentRatio(recommendation?.standardized_risk_rate)}，只能说明当前样本里的风险水平，不能证明真实使用中一定好或一定不好。`;
}

function plainAfterSaleText(afterSaleText) {
  if (!afterSaleText) return "当前接口没有返回明确售后服务文本，购买前建议进入商品链接确认退换、运费和退款规则。";
  return `售后文本显示：${afterSaleText}。这些是下单前需要确认的保障信息，尤其要看是否支持无理由退货、是否上门退换、使用后是否有限制。`;
}

function plainActionText(sortedRiskRows, recommendation) {
  const risks = simpleRiskList(sortedRiskRows, recommendation);
  return `买前重点看两件事：第一，能不能接受 ${risks} 相关反馈；第二，商品页里的售后规则是否和你能接受的退换条件一致。当前页面只能帮你缩小选择范围，不能替代实际商品页确认。`;
}

function plainParameterText(parameter) {
  if (!parameter?.has_specs) {
    return "当前商品尚未接入可展示的商品参数，所以这一部分不会参与购买判断。";
  }
  const summary = safeList(parameter.summary);
  const cautions = safeList(parameter.cautions);
  const firstSummary = summary[0] || "已接入页面参数文字";
  const firstCaution = cautions[0] || "这些参数只代表页面标称，不能替代实测结果。";
  return `${firstSummary}。系统会把这些页面参数和价格、评论、售后一起看，但不会把页面标称直接当成实测表现。${firstCaution}`;
}

export default function ProductDetail({ detail, error, commentRisk, recommendation, recommendations = [] }) {
  const [showInvestigation, setShowInvestigation] = useState(false);

  if (!detail) {
    return (
      <section className="workspace">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">Recommendation Detail</p>
            <h2>{recommendation ? `正在读取：${displayProductName(recommendation, {})}` : "推荐证据"}</h2>
            <p className={error ? "lead error-text" : "lead"}>
              {error || (recommendation ? "正在读取当前商品的价格、评论、售后和风险依据..." : "请先在购买建议中选择一款商品，再查看价格、评论、风险和数据边界。")}
            </p>
          </div>
        </div>
      </section>
    );
  }

  const score = detail.product_score || {};
  const product = detail.canonical_product || {};
  const products = detail.products || [];
  const chosenProduct = selectedProduct(products, recommendation);
  const chosenPolicy = selectedByProductId(detail.return_policy || [], chosenProduct.id);
  const current = currentPrice(detail, recommendation);
  const lowest = lowestRecommendationPrice(recommendations) ?? current;
  const priceGap = current !== null && lowest !== null ? current - lowest : 0;
  const distribution = commentRisk?.raw_review_distribution || recommendation?.raw_review_distribution || {};
  const rates = commentRisk?.dimension_risk_rates || recommendation?.dimension_risk_rates || {};
  const sortedRiskRows = riskRows(rates).sort((a, b) => b.value - a.value);
  const platformIds = products.map((item) => item.platform_product_id).filter(Boolean);
  const commentCount = recommendation?.comment_count ?? commentRisk?.total_comments;
  const displayName = displayProductName(recommendation, product);
  const afterSaleText = cleanText(recommendation?.recommended_after_sale_service || chosenPolicy.return_condition_text);
  const productUrl = recommendation?.recommended_product_url || chosenProduct.product_url;
  const parameter = selectedParameterAnalysis(detail, chosenProduct, recommendation);
  const parameterScores = parameter?.scores || {};
  const parameterFacts = parameterFactList(parameter);

  return (
    <section className="detail-decision-page">
      <div className="detail-hero">
        <div>
          <p className="eyebrow">推荐证据</p>
          <h2>{displayName}</h2>
          <p className="lead">
            {userSummary({ displayName, current, recommendation, sortedRiskRows, commentCount })}
          </p>
          <p className="boundary-copy">
            当前系统只看京东价格、评论、售后文本和用户提供的页面商品参数。它能帮你判断“这款风险大不大、值不值得进一步看”，
            不能证明防水、抗风、材质或重量表现一定优秀。
          </p>
        </div>
        <button type="button" onClick={() => setShowInvestigation((value) => !value)}>
          {showInvestigation ? "收起调查数据" : "查看调查数据"}
        </button>
      </div>

      <section className="decision-section full-width">
        <h3>先看结论</h3>
        <div className="detail-metrics">
          <div><span>商品名</span><strong>{displayName}</strong></div>
          <div><span>店铺</span><strong>{cleanText(recommendation?.recommended_shop_name || chosenProduct.shop_name) || "--"}</strong></div>
          <div><span>到手价</span><strong>{formatMoney(current)}</strong></div>
          <div><span>本次匹配分</span><strong>{recommendation?.user_match_score !== undefined ? Number(recommendation.user_match_score).toFixed(1).replace(".0", "") : "--"}</strong></div>
          <div><span>评论样本</span><strong>{formatCount(commentCount)} 条</strong></div>
          <div><span>主要风险标签</span><strong>{riskTagText(recommendation)}</strong></div>
          <div><span>售后服务</span><strong>{afterSaleText || "--"}</strong></div>
          <div>
            <span>商品链接</span>
            {productUrl ? (
              <button type="button" className="link-button" onClick={() => openProductUrl(productUrl)}>打开商品链接</button>
            ) : (
              <strong>当前接口未返回</strong>
            )}
          </div>
        </div>
        <p>
          {plainActionText(sortedRiskRows, recommendation)}
        </p>
        {safeList(recommendation?.ranking_factors).length > 0 && (
          <div className="tag-row">
            {recommendation.ranking_factors.slice(0, 5).map((factor) => <RiskTag key={factor}>{factor}</RiskTag>)}
          </div>
        )}
      </section>

      <div className="plain-decision-grid">
        <section className="decision-section">
          <span className="step-number">01</span>
          <h3>价格怎么看</h3>
          <p>{plainPriceText(current, lowest, Math.max(priceGap, 0))}</p>
        </section>

        <section className="decision-section">
          <span className="step-number">02</span>
          <h3>评论里看到了什么</h3>
          <p>{plainReviewText(distribution, commentCount, recommendation)}</p>
        </section>

        <section className="decision-section">
          <span className="step-number">03</span>
          <h3>买前主要注意什么</h3>
          <p>{riskExplanation(sortedRiskRows, recommendation)}</p>
        </section>

        <section className="decision-section">
          <span className="step-number">04</span>
          <h3>售后要怎么确认</h3>
          <p>{plainAfterSaleText(afterSaleText)}</p>
        </section>

        <section className="decision-section">
          <span className="step-number">05</span>
          <h3>商品参数怎么看</h3>
          <p>{plainParameterText(parameter)}</p>
        </section>
      </div>

      <section className="decision-section full-width">
        <div className="fold-header">
          <div>
            <p className="eyebrow">调查数据</p>
            <h3>专业数据和计算过程</h3>
          </div>
          <button type="button" className="secondary" onClick={() => setShowInvestigation((value) => !value)}>
            {showInvestigation ? "收起调查数据" : "查看调查数据"}
          </button>
        </div>
        <p>
          下面是系统用来形成上面结论的原始指标和校正结果。普通用户可以先看上面的结论；想核对依据时再展开这里。
        </p>
      </section>

      {showInvestigation && (
        <>
          <section className="decision-section full-width">
            <h3>推荐分数和证据强度</h3>
            <ScoreBadge
              finalScore={score.final_score ?? recommendation?.final_score}
              evidenceScore={commentRisk?.review_evidence_score ?? recommendation?.review_evidence_score}
              confidenceScore={score.data_confidence_score ?? recommendation?.data_confidence_score}
            />
            <p>
              {cleanText(recommendation?.reason) || "当前接口未返回单独推荐说明，页面会基于价格、评论和风险字段展示可解释依据。"}
            </p>
          </section>

          <div className="detail-section-grid">
            <section className="decision-section">
              <span className="step-number">01</span>
              <h3>价格依据</h3>
              <div className="detail-metrics">
                <div><span>当前到手价</span><strong>{formatMoney(current)}</strong></div>
                <div><span>最低可比价</span><strong>{formatMoney(lowest)}</strong></div>
                <div><span>价差</span><strong>{formatMoney(Math.max(priceGap, 0))}</strong></div>
                <div><span>平台商品 ID</span><strong>{recommendation?.recommended_platform_product_id || chosenProduct.platform_product_id || platformIds[0] || "--"}</strong></div>
                <div>
                  <span>商品链接</span>
                  {productUrl ? (
                    <button type="button" className="link-button" onClick={() => openProductUrl(productUrl)}>打开商品链接</button>
                  ) : (
                    <strong>暂无链接</strong>
                  )}
                </div>
              </div>
              <p>{priceExplanation(current, lowest, Math.max(priceGap, 0), recommendation)}</p>
            </section>

            <section className="decision-section">
              <span className="step-number">02</span>
              <h3>评论依据</h3>
              <div className="detail-metrics">
                <div><span>评论样本</span><strong>{formatCount(commentCount)}</strong></div>
                <div><span>原始评论分布</span><strong>{distributionText(distribution)}</strong></div>
                <div><span>标准化计算权重</span><strong>好评 45% / 中评 20% / 差评 35%</strong></div>
                <div><span>评论结构偏离度</span><strong>{formatPercentRatio(commentRisk?.sampling_bias_index ?? recommendation?.sampling_bias_index)}</strong></div>
              </div>
              <p>{reviewExplanation(distribution, commentCount, recommendation)}</p>
            </section>

            <section className="decision-section">
              <span className="step-number">03</span>
              <h3>风险依据</h3>
              <div className="detail-metrics">
                <div><span>校正后购买风险</span><strong>{formatPercentRatio(commentRisk?.standardized_risk_rate ?? recommendation?.standardized_risk_rate)}</strong></div>
                {sortedRiskRows.slice(0, 4).map((row) => (
                  <div key={row.key}>
                    <span>{row.label}</span>
                    <strong>{formatPercentRatio(row.value)} · {riskLabel(row.value)}</strong>
                  </div>
                ))}
              </div>
              <p>{riskExplanation(sortedRiskRows, recommendation)}</p>
            </section>

            <section className="decision-section">
              <span className="step-number">04</span>
              <h3>售后依据</h3>
              <div className="detail-metrics">
                <div><span>店铺</span><strong>{cleanText(recommendation?.recommended_shop_name || chosenProduct.shop_name) || "当前接口未返回"}</strong></div>
                <div><span>建议下单平台</span><strong>{recommendation?.recommended_platform || chosenProduct.platform || "当前接口未返回"}</strong></div>
                <div><span>售后服务文本</span><strong>{afterSaleText || "当前接口未返回"}</strong></div>
                <div>
                  <span>商品链接</span>
                  {productUrl ? (
                    <button type="button" className="link-button" onClick={() => openProductUrl(productUrl)}>打开商品链接</button>
                  ) : (
                    <strong>当前接口未返回</strong>
                  )}
                </div>
              </div>
              <p>{plainAfterSaleText(afterSaleText)}</p>
            </section>

            <section className="decision-section">
              <span className="step-number">05</span>
              <h3>商品参数依据</h3>
              {parameter?.has_specs ? (
                <>
                  <div className="detail-metrics">
                    <div><span>参数总分</span><strong>{parameterScores.overall ?? "--"}</strong></div>
                    <div><span>空间参数</span><strong>{parameterScores.space ?? "--"}</strong></div>
                    <div><span>携带负担</span><strong>{parameterScores.portability ?? "--"}</strong></div>
                    <div><span>搭建友好</span><strong>{parameterScores.setup ?? "--"}</strong></div>
                    <div><span>页面防护标称</span><strong>{parameterScores.weather_claim ?? "--"}</strong></div>
                    <div><span>参数完整度</span><strong>{parameterScores.completeness ?? "--"}</strong></div>
                  </div>
                  <div className="parameter-fact-grid">
                    <div>
                      <strong>页面参数事实</strong>
                      <ul>
                        {parameterFacts.length ? parameterFacts.map((item) => <li key={item}>{item}</li>) : <li>当前参数字段较少</li>}
                      </ul>
                    </div>
                    <div>
                      <strong>参数提醒</strong>
                      <ul>
                        {safeList(parameter.cautions).map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                  </div>
                  <p>{parameter.source_boundary}</p>
                </>
              ) : (
                <p>当前商品尚未接入可展示的商品参数。</p>
              )}
            </section>

            <section className="decision-section">
              <span className="step-number">06</span>
              <h3>数据边界</h3>
              <div className="boundary-grid">
                <div>
                  <strong>当前数据来源</strong>
                  <p>当前商品的京东价格、京东评论、京东售后文本、京东商品链接，以及用户提供的京东页面商品参数。</p>
                </div>
                <div>
                  <strong>暂未接入</strong>
                  <p>实验室实测防水、实测抗风、长期耐用测试、专业测评数据和官方检测报告。</p>
                </div>
                <div>
                  <strong>跨平台覆盖</strong>
                  <p>MVP 阶段先完成单平台闭环，评分机制和 SKU 分组逻辑支持后续扩展到多平台。</p>
                </div>
                <div>
                  <strong>结论边界</strong>
                  <p>本推荐只能作为购买风险参考，不能替代专业户外装备测评。</p>
                </div>
              </div>
            </section>
          </div>

          <section className="decision-section full-width">
            <h3>评论采样结构校正</h3>
            <p>
              如果某一层评论样本不足，系统不会强行给出高可信度结论，而是降低判断可信度，并在前端提示采样不足。
              当前 SKU：{platformIds.length ? platformIds.join(" / ") : "--"}
            </p>
            <div className="tag-row">
              {(commentRisk?.review_sample_warnings || []).length
                ? commentRisk.review_sample_warnings.map((warning) => <RiskTag key={warning}>{warning}</RiskTag>)
                : <RiskTag>当前评论层覆盖较完整</RiskTag>}
            </div>
          </section>

          <CommentRiskPanel summary={commentRisk} />
        </>
      )}
    </section>
  );
}
