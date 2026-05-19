import RiskTag from "./RiskTag.jsx";
import { formatScore } from "../utils/format.js";

export default function RedBookSummaryPanel({ summary }) {
  if (!summary) {
    return (
      <section className="info-panel">
        <h3>小红书口碑</h3>
        <p className="empty">暂无小红书摘要。</p>
      </section>
    );
  }

  return (
    <section className="info-panel">
      <h3>小红书口碑</h3>
      <div className="metric-list compact">
        <div><span>笔记数</span><strong>{summary.note_count ?? 0}</strong></div>
        <div><span>疑似广告</span><strong>{summary.suspected_ad_count ?? 0}</strong></div>
        <div><span>平均可信度</span><strong>{formatScore(summary.average_credibility_score)}</strong></div>
        <div><span>平均情绪分</span><strong>{formatScore(summary.average_sentiment_score)}</strong></div>
      </div>
      <div className="tag-row">
        {(summary.risk_tags || []).map((tag) => <RiskTag key={tag}>{tag}</RiskTag>)}
      </div>
    </section>
  );
}
