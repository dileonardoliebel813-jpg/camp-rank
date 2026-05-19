import { labelRiskTag } from "../utils/format.js";

export default function RiskTag({ children }) {
  return <span className="risk-tag">{labelRiskTag(children)}</span>;
}
