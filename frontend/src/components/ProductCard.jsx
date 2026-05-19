import { cleanText, formatCount, formatMoney } from "../utils/format.js";

function displayProductName(product) {
  return cleanText(product?.recommended_product_title || product?.product_name || product?.normalized_name || "等待计算").replace(/^已购\s*/, "");
}

function metricText(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.round(number) : "--";
}

function metricWidth(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, number));
}

function fallbackDecision(product, plan) {
  return {
    role: plan?.role || "candidate",
    decision_label: plan?.tagline || "继续核对",
    recommend_type: plan?.label || "候选商品",
    recommend_grade: "--",
    product_name: displayProductName(product),
    price: product?.stable_final_price,
    match_score: product?.user_match_score ?? product?.final_score,
    risk_score: Number(product?.standardized_risk_rate || 0) * 100,
    confidence_score: product?.data_confidence_score ?? product?.evidence_confidence_score,
    reason_tags: [plan?.reason].filter(Boolean).slice(0, 3),
    parameter_reason_tags: [plan?.reason].filter(Boolean).slice(0, 3),
    comment_reason_tags: [],
    risk_tags: [plan?.attention].filter(Boolean).slice(0, 2),
    evidence_summary: {
      review_count: product?.comment_count,
      matched_need_count: 0,
      risk_label_count: 0,
    },
  };
}

function safeList(value) {
  return Array.isArray(value) ? value : [];
}

function parameterDecision(view) {
  return view.parameter_decision || view.parameter_analysis?.decision || {};
}

function parameterJudgmentLines(view) {
  const decision = parameterDecision(view);
  const lines = [
    decision.space_judgment,
    decision.scene_judgment,
    decision.missing_parameter_text,
  ].filter(Boolean);
  if (lines.length) return lines.slice(0, 3);
  return safeList(view.parameter_summary || view.parameter_highlights).filter(Boolean).slice(0, 3);
}

function rawParameterFacts(view) {
  const decision = parameterDecision(view);
  return safeList(view.parameter_raw_facts || decision.raw_parameter_facts || view.parameter_summary)
    .filter(Boolean)
    .slice(0, 2);
}

function selectionClass(value) {
  if (value === "core_match") return "core";
  if (value === "partial_match") return "partial";
  return "fallback";
}

function MetricTile({ label, value, tone = "good", hint }) {
  return (
    <div className={`metric-tile ${tone}`}>
      <div className="metric-tile-head">
        <span>{label}</span>
        <strong>{metricText(value)}</strong>
      </div>
      <div className="metric-track" aria-hidden="true">
        <i style={{ width: `${metricWidth(value)}%` }} />
      </div>
      {hint && <small>{hint}</small>}
    </div>
  );
}

export default function ProductCard({
  product,
  plan,
  compact = false,
  decision,
  onOpenEvidence,
  onOpenCompare,
}) {
  const view = decision || fallbackDecision(product, plan);
  const role = view.role || "candidate";
  const className = ["decision-product-card", role, compact ? "compact" : ""].filter(Boolean).join(" ");
  const parameterReasons = safeList(view.parameter_reason_tags).filter(Boolean).slice(0, 3);
  const commentReasons = safeList(view.comment_reason_tags).filter(Boolean).slice(0, 3);
  const risks = (view.risk_tags || []).filter(Boolean).slice(0, 2);
  const evidence = view.evidence_summary || {};
  const parameterLines = parameterJudgmentLines(view);
  const rawFacts = rawParameterFacts(view);

  return (
    <article className={className}>
      <div className="decision-card-label">
        <div>
          <span>购买定位</span>
          <strong>{view.recommend_type || "候选商品"}｜{view.decision_label || "继续核对"}</strong>
        </div>
        <div className="decision-label-stack">
          {view.selection_label && <em className={`selection-badge ${selectionClass(view.selection_tier)}`}>{view.selection_label}</em>}
          <b className="decision-grade">{view.recommend_grade || "--"}</b>
        </div>
      </div>

      <div className="decision-card-main">
        <h3 title={view.product_name}>{view.product_name}</h3>
        <div className="decision-price">
          <span>到手价</span>
          <strong>{formatMoney(view.price)}</strong>
        </div>
      </div>

      <section className="decision-metrics" aria-label="核心推荐指标">
        <MetricTile label="匹配度" value={view.match_score} hint="越高越贴合本次需求" />
        <MetricTile label="风险指数" value={view.risk_score} tone="risk" hint="越低越省心" />
        <MetricTile label="依据充分度" value={view.confidence_score} hint="信息越充分越可参考，不代表质量更高" />
      </section>

      <section className="parameter-card-strip">
        <h4>参数判断</h4>
        {parameterLines.length ? (
          <ul>
            {parameterLines.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : (
          <p>当前商品尚未接入可展示的商品参数</p>
        )}
        {rawFacts.length > 0 && (
          <div className="raw-parameter-mini">
            {rawFacts.map((item) => <span key={item}>{item}</span>)}
          </div>
        )}
      </section>

      <section className="decision-reason-groups">
        <div className="decision-list-block">
          <h4>参数匹配</h4>
          <ul className="reason-list">
            {parameterReasons.length ? parameterReasons.map((item) => (
              <li key={item}><span className="check-symbol">✓</span>{item}</li>
            )) : <li><span className="check-symbol">✓</span>当前参数依据较少，下单前需确认</li>}
          </ul>
        </div>
        <div className="decision-list-block">
          <h4>评论验证</h4>
          <ul className="reason-list">
            {commentReasons.length ? commentReasons.map((item) => (
            <li key={item}><span className="check-symbol">✓</span>{item}</li>
            )) : <li><span className="check-symbol">✓</span>当前接口未返回可拆分的评论验证短句</li>}
          </ul>
        </div>
      </section>

      <section className="decision-list-block">
        <h4>买前注意</h4>
        <ul className="risk-list">
          {risks.length ? risks.map((item) => (
            <li key={item}><span className="risk-symbol">!</span>{item}</li>
          )) : <li><span className="risk-symbol">!</span>当前接口未返回明显集中风险</li>}
        </ul>
      </section>

      <p className="evidence-summary-line">
        基于 {formatCount(evidence.review_count)} 条评论｜
        命中 {formatCount(evidence.matched_need_count)} 个需求点｜
        发现 {formatCount(evidence.risk_label_count)} 类主要风险
      </p>

      <div className="card-actions">
        <button type="button" onClick={onOpenEvidence}>查看推荐证据</button>
        <button type="button" className="secondary" onClick={onOpenCompare}>加入对比</button>
      </div>
    </article>
  );
}
