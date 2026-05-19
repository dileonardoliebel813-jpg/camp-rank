export const SCENARIO_LABELS = {
  newbie_weekend: "短途休闲露营",
  family_camping: "家庭亲子露营",
  overnight: "短途过夜露营",
  rain_backup: "雨天/潮湿环境备用",
  group_party: "多人聚会/大空间需求",
  hiking_lightweight: "步行携带/收纳约束",
};

export const PREFERENCE_LABELS = {
  balanced: "综合购买风险控制",
  lowest_price: "价格敏感/到手价优先",
  after_sale: "售后与退换保障",
  gift_package: "容量与空间匹配",
  portable: "收纳携带负担",
  weather_protection: "防水/防风负面反馈",
  easy_setup: "搭建复杂度敏感",
  less_stuffy: "闷热/异味负面反馈",
};

export const DIMENSION_LABELS = {
  waterproof: "防水",
  windproof: "防风",
  space: "空间",
  storage: "收纳",
  setup: "搭建",
  smell_heat: "异味/闷热",
  durability: "耐用",
  return_after_sale: "售后",
};

const RISK_TAG_LABELS = {
  low_data_confidence: "数据覆盖不足",
  return_high_risk: "售后高风险",
  return_medium_risk: "售后中等风险",
  return_after_sale: "售后争议",
  return_denied: "退换受阻",
  return_hassle: "退换流程麻烦",
  slow_refund: "退款较慢",
  bad_service: "客服体验风险",
  shipping_dispute: "运费争议",
  leak: "漏水反馈",
  waterproof: "防水反馈",
  windproof: "防风反馈",
  condensation: "冷凝水反馈",
  broken_pole: "杆件/结构风险",
  collapse: "结构不稳",
  space_overclaim: "空间虚标",
  hard_to_pack: "收纳困难",
  setup: "搭建困难",
  smell: "异味反馈",
  portable: "便携性风险",
  durability: "耐用性",
  quality: "质量反馈",
  heat: "闷热",
  sunproof: "不防晒",
  "不给退": "不给退",
  "不防晒": "不防晒",
  "刺鼻": "刺鼻",
  "漏水": "漏水",
  "熏人": "熏人",
  "退不了": "退不了",
  "闷热": "闷热",
  "压抑": "压抑",
};

export function formatScore(value) {
  if (value === undefined || value === null || value === "") return "--";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(1).replace(".0", "") : value;
}

export function formatMoney(value) {
  if (value === undefined || value === null || value === "") return "--";
  const number = Number(value);
  return Number.isFinite(number) ? `¥${number.toFixed(0)}` : value;
}

export function formatPercentRatio(value) {
  if (value === undefined || value === null || value === "") return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${Math.round(number * 100)}%`;
}

export function formatCount(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : "--";
}

export function confidenceLabel(value) {
  const number = Number(value || 0);
  if (number >= 75) return "较高";
  if (number >= 55) return "中等";
  return "较低";
}

export function labelRiskTag(value) {
  if (!value) return "暂无明显风险标签";
  const cleaned = cleanText(String(value))
    .replace("Risk tag retained for review:", "")
    .replace(".", "")
    .trim();
  return RISK_TAG_LABELS[cleaned] || RISK_TAG_LABELS[value] || cleaned.replaceAll("_", " ");
}

export function safeList(value) {
  return Array.isArray(value) ? value : [];
}

export function cleanText(value) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  if (!/[\u0080-\u00ff]/.test(text) || /[\u4e00-\u9fff]/.test(text)) return text;
  try {
    const bytes = Uint8Array.from(Array.from(text), (char) => char.charCodeAt(0));
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return text;
  }
}
