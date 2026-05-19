import { formatMoney } from "../utils/format.js";

export default function PlatformCompareBadge({ recommendedPlatform, lowestPricePlatform, priceGap }) {
  const isDifferent = recommendedPlatform && lowestPricePlatform && recommendedPlatform !== lowestPricePlatform;
  const explanation = isDifferent
    ? `${recommendedPlatform || "--"} 不是当前最低价来源，但从售后保障、优惠稳定性和购买风险看，更适合作为建议下单平台。`
    : `${recommendedPlatform || "--"} 同时是建议下单平台和当前最低价来源，系统仍会保留售后、优惠稳定性和判断可信度校验。`;

  return (
    <div className={isDifferent ? "platform-badge warning" : "platform-badge"}>
      <div className="platform-pair">
        <div>
          <span>建议下单平台</span>
          <strong>{recommendedPlatform || "--"}</strong>
        </div>
        <div>
          <span>当前最低价来源</span>
          <strong>{lowestPricePlatform || "--"}</strong>
        </div>
        <div>
          <span>价差</span>
          <strong>{formatMoney(priceGap)}</strong>
        </div>
      </div>
      {isDifferent && <p className="alert-text">当前最低价来源不一定是更稳的下单选择</p>}
      <p className="muted">{explanation}</p>
    </div>
  );
}
