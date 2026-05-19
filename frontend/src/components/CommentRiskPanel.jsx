import RiskTag from "./RiskTag.jsx";
import { DIMENSION_LABELS, formatPercentRatio, formatScore } from "../utils/format.js";

const COMMENT_FIELDS = [
  ["waterproof_negative_rate", "防水相关反馈"],
  ["windproof_negative_rate", "防风相关反馈"],
  ["space_negative_rate", "空间相关反馈"],
  ["storage_negative_rate", "收纳相关反馈"],
  ["setup_negative_rate", "搭建相关反馈"],
  ["smell_negative_rate", "异味相关反馈"],
  ["sunproof_negative_rate", "防晒相关反馈"],
  ["return_after_sale_negative_rate", "退换售后反馈"],
];

function countText(distribution = {}) {
  return `好评 ${distribution.positive ?? 0} / 中评 ${distribution.neutral ?? 0} / 差评 ${distribution.negative ?? 0}`;
}

function riskLabel(rate) {
  const value = Number(rate || 0);
  if (value >= 0.2) return "中等偏高";
  if (value >= 0.08) return "中等";
  if (value >= 0.005) return "较低";
  return "暂未明显";
}

export default function CommentRiskPanel({ summary }) {
  if (!summary) {
    return (
      <section className="decision-section full-width">
        <h3>口碑风险来源</h3>
        <p className="empty">暂无评论风险摘要。</p>
      </section>
    );
  }

  const dimensionRates = summary.dimension_risk_rates || {};

  return (
    <section className="decision-section full-width evidence-panel">
      <h3>口碑风险来源</h3>
      <div className="detail-metrics">
        <div><span>口碑证据强度</span><strong>{formatScore(summary.review_evidence_score)}</strong></div>
        <div><span>判断可信度</span><strong>{formatScore(summary.evidence_confidence_score)}</strong></div>
        <div><span>评论结构偏离度</span><strong>{formatPercentRatio(summary.sampling_bias_index)}</strong></div>
        <div><span>校正后购买风险</span><strong>{formatPercentRatio(summary.standardized_risk_rate)}</strong></div>
      </div>
      <p className="muted">原始分布：{countText(summary.raw_review_distribution)}</p>
      <p className="muted">这里的低风险只表示当前评论中相关负面反馈较少，不代表商品经过专业测试。</p>

      <div className="dimension-board detail-board">
        {Object.entries(dimensionRates).map(([key, value]) => (
          <div className="dimension-row" key={key}>
            <span>{DIMENSION_LABELS[key] || key}</span>
            <div className="dimension-track">
              <i style={{ width: `${Math.min(Number(value || 0) * 100, 100)}%` }} />
            </div>
            <strong>{formatPercentRatio(value)} · {riskLabel(value)}</strong>
          </div>
        ))}
      </div>

      <div className="detail-metrics">
        {COMMENT_FIELDS.map(([key, label]) => (
          <div key={key}>
            <span>{label}</span>
            <strong>{formatPercentRatio(summary[key])}</strong>
          </div>
        ))}
        <div><span>疑似异常评论</span><strong>{summary.suspected_fake_review_count ?? 0}</strong></div>
        <div><span>低信息评论</span><strong>{summary.low_information_review_count ?? 0}</strong></div>
        <div><span>有效差评</span><strong>{summary.valid_negative_review_count ?? 0}</strong></div>
      </div>
      <div className="tag-row">
        {(summary.high_risk_tags || []).map((tag) => <RiskTag key={tag}>{tag}</RiskTag>)}
        {(summary.review_sample_warnings || []).map((warning) => <RiskTag key={warning}>{warning}</RiskTag>)}
      </div>
    </section>
  );
}
