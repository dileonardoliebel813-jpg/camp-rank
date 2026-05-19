import { cleanText, formatMoney, formatScore } from "../utils/format.js";
import RiskTag from "./RiskTag.jsx";

export default function PriceCompareTable({ offers = [] }) {
  if (!offers.length) {
    return <p className="empty">暂无比价数据。</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>平台</th>
            <th>店铺</th>
            <th>最低套餐价</th>
            <th>理论最低价</th>
            <th>优惠可靠性</th>
            <th>赠品估值</th>
            <th>赠品折算成本</th>
            <th>建议下单平台</th>
            <th>当前最低价来源</th>
            <th>售后保障</th>
            <th>售后风险</th>
            <th>售后风险成本</th>
            <th>平台购买分</th>
            <th>风险标签</th>
          </tr>
        </thead>
        <tbody>
          {offers.map((offer) => (
            <tr key={`${offer.platform}-${offer.shop_name}`}>
              <td><strong>{offer.platform}</strong></td>
              <td>{cleanText(offer.shop_name)}</td>
              <td>{formatMoney(offer.stable_final_price)}</td>
              <td>{formatMoney(offer.theoretical_lowest_price)}</td>
              <td>{formatScore(offer.coupon_reliability_score)}</td>
              <td>{formatMoney(offer.gift_estimated_value)}</td>
              <td>{formatMoney(offer.gift_adjusted_cost)}</td>
              <td>{offer.is_recommended_platform ? "是" : "否"}</td>
              <td>{offer.is_lowest_price ? "是" : "否"}</td>
              <td>{formatScore(offer.return_protection_score)}</td>
              <td>{formatScore(offer.return_risk_score)}</td>
              <td>{formatMoney(offer.return_risk_cost)}</td>
              <td>{formatScore(offer.platform_buy_score)}</td>
              <td>
                <div className="tag-row">
                  {(offer.warning_tags || []).length
                    ? offer.warning_tags.map((tag) => <RiskTag key={tag}>{tag}</RiskTag>)
                    : <span className="muted">--</span>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
