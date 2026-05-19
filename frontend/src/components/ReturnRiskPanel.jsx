import RiskTag from "./RiskTag.jsx";
import { cleanText, formatMoney, formatScore } from "../utils/format.js";

export default function ReturnRiskPanel({ offers = [], policies = [] }) {
  const rows = offers.length
    ? offers
    : policies.map((policy, index) => ({
        platform: `平台 ${index + 1}`,
        return_protection_score: policy.return_protection_score,
        return_risk_score: policy.return_risk_score,
        return_risk_cost: policy.return_risk_cost,
        warning_tags: [],
      }));

  return (
    <section className="info-panel">
      <h3>售后风险与成本修正</h3>
      {rows.length ? (
        <div className="return-list">
          {rows.map((row) => (
            <div key={`${row.platform}-${row.shop_name || row.return_risk_cost}`}>
              <div className="return-title">
                <strong>{row.platform}</strong>
                <span>{cleanText(row.shop_name) || "售后样例"}</span>
              </div>
              <dl>
                <div><dt>售后保障</dt><dd>{formatScore(row.return_protection_score)}</dd></div>
                <div><dt>售后风险</dt><dd>{formatScore(row.return_risk_score)}</dd></div>
                <div><dt>售后风险成本</dt><dd>{formatMoney(row.return_risk_cost)}</dd></div>
              </dl>
              <div className="tag-row">
                {(row.warning_tags || []).map((tag) => <RiskTag key={tag}>{tag}</RiskTag>)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty">暂无售后风险数据。</p>
      )}
    </section>
  );
}
