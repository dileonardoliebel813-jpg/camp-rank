import { confidenceLabel, formatScore } from "../utils/format.js";

export default function ScoreBadge({ finalScore, confidenceScore, evidenceScore }) {
  return (
    <div className="score-badge buyer-score" aria-label="购买推荐指数、口碑证据强度与判断可信度">
      <div>
        <span className="score-value">{formatScore(finalScore)}</span>
        <span className="score-label">购买推荐指数</span>
      </div>
      <div>
        <span className="score-value small">{formatScore(evidenceScore)}</span>
        <span className="score-label">口碑证据强度</span>
      </div>
      <div>
        <span className="score-value small">{confidenceLabel(confidenceScore)}</span>
        <span className="score-label">判断可信度</span>
      </div>
    </div>
  );
}
