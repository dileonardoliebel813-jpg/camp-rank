import { useMemo, useState } from "react";
import { fetchProductDetail } from "../api/client.js";
import ProductCard from "../components/ProductCard.jsx";
import {
  cleanText,
  DIMENSION_LABELS,
  formatCount,
  formatMoney,
  formatPercentRatio,
  labelRiskTag,
  PREFERENCE_LABELS,
  SCENARIO_LABELS,
  safeList,
} from "../utils/format.js";
import { openPublicProductUrl, PRODUCT_LINK_UNAVAILABLE_TEXT, publicProductUrl } from "../utils/urls.js";

const ROLE_META = {
  primary: {
    recommend_type: "首选方案",
    decision_label: "建议购买",
    recommend_grade: "A",
  },
  budget: {
    recommend_type: "低价备选",
    decision_label: "预算紧可选",
    recommend_grade: "B",
  },
  caution: {
    recommend_type: "谨慎选择",
    decision_label: "下单前需确认",
    recommend_grade: "C",
  },
  candidate: {
    recommend_type: "候选商品",
    decision_label: "继续核对",
    recommend_grade: "候选",
  },
};

function totalComments(items) {
  return items.reduce((sum, item) => sum + Number(item.comment_count || 0), 0);
}

function displayProductName(item) {
  const sourceTitle = safeList(item?.source_sku_titles)[0] || "";
  return cleanText(item?.recommended_product_title || item?.product_name || sourceTitle || "等待计算").replace(/^已购\s*/, "");
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clampScore(value) {
  const number = numberOrNull(value);
  if (number === null) return null;
  return Math.max(0, Math.min(100, number));
}

function firstScore(...values) {
  for (const value of values) {
    const number = clampScore(value);
    if (number !== null) return number;
  }
  return null;
}

function scoreLabel(value) {
  const number = numberOrNull(value);
  return number === null ? "--" : number.toFixed(1).replace(".0", "");
}

function riskIndex(item) {
  const direct = numberOrNull(item?.risk_score);
  if (direct !== null) return clampScore(direct);
  const rate = numberOrNull(item?.standardized_risk_rate);
  if (rate !== null) return clampScore(rate * 100);
  const tagFallback = safeList(item?.risk_tags).length * 12;
  return tagFallback ? clampScore(tagFallback) : null;
}

function riskScoreForSorting(item) {
  const rate = riskIndex(item);
  const afterSale = numberOrNull(item?.dimension_risk_rates?.return_after_sale) || 0;
  return (rate || 0) + afterSale * 60 + safeList(item?.risk_tags).length;
}

function topRiskRows(item, limit = 4) {
  return Object.entries(item?.dimension_risk_rates || {})
    .map(([key, value]) => ({
      key,
      label: DIMENSION_LABELS[key] || key,
      value: Number(value || 0),
    }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function parameterAnalysis(item) {
  return item?.parameter_analysis || {};
}

function parameterSummary(item) {
  const analysis = parameterAnalysis(item);
  return safeList(item?.parameter_summary).length ? safeList(item.parameter_summary) : safeList(analysis.summary);
}

function parameterHighlights(item) {
  const analysis = parameterAnalysis(item);
  return safeList(item?.parameter_highlights).length ? safeList(item.parameter_highlights) : safeList(analysis.highlights);
}

function parameterCautions(item) {
  const analysis = parameterAnalysis(item);
  return safeList(item?.parameter_cautions).length ? safeList(item.parameter_cautions) : safeList(analysis.cautions);
}

function parameterDecision(itemOrAnalysis) {
  const analysis = itemOrAnalysis?.has_specs !== undefined ? itemOrAnalysis : parameterAnalysis(itemOrAnalysis);
  return analysis?.decision || {};
}

function parameterJudgmentLines(item) {
  const decision = parameterDecision(item);
  return [
    decision.space_judgment,
    decision.scene_judgment,
    decision.missing_parameter_text,
  ].filter(Boolean);
}

function parameterRawFacts(itemOrAnalysis) {
  const analysis = itemOrAnalysis?.has_specs !== undefined ? itemOrAnalysis : parameterAnalysis(itemOrAnalysis);
  const decision = analysis?.decision || {};
  return safeList(decision.raw_parameter_facts || analysis?.summary).filter(Boolean);
}

function missingParameterText(itemOrAnalysis) {
  const decision = parameterDecision(itemOrAnalysis);
  return decision.missing_parameter_text || "待确认参数：当前接口未返回";
}

function riskTagText(item, fallback = "当前接口未返回高频风险标签") {
  const tags = safeList(item?.risk_tags).slice(0, 4).map(labelRiskTag).filter(Boolean);
  return tags.length ? tags.join("、") : fallback;
}

function uniqueList(values) {
  const result = [];
  values.filter(Boolean).forEach((value) => {
    if (!result.includes(value)) result.push(value);
  });
  return result;
}

function activeScenario(filters) {
  return SCENARIO_LABELS[filters.scenario] || filters.scenario || "短途休闲露营";
}

function activePreference(filters) {
  return String(filters.preference || "balanced")
    .split(",")
    .map((value) => PREFERENCE_LABELS[value.trim()] || value.trim())
    .filter(Boolean)
    .join("、") || "综合购买风险控制";
}

function tierLabel(value) {
  if (value === "core_match") return "完全满足";
  if (value === "partial_match") return "部分满足";
  if (value === "fallback") return "补位参考";
  return "待确认";
}

function tierRank(value) {
  if (value === "core_match") return 2;
  if (value === "partial_match") return 1;
  return 0;
}

function selectionCounts(items) {
  return items.reduce((acc, item) => {
    const key = item?.selection_tier || "fallback";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, { core_match: 0, partial_match: 0, fallback: 0 });
}

function selectionSummaryText(items, filters) {
  const counts = selectionCounts(items);
  const scope = `${activeScenario(filters)} + ${activePreference(filters)}`;
  if (!items.length) return `已按 ${scope} 筛选，当前接口没有返回符合预算的候选。`;
  if (counts.core_match >= 3) {
    return `已按 ${scope} 强约束筛选，${formatCount(counts.core_match)} 款满足核心要求。`;
  }
  return `已按 ${scope} 强约束筛选，${formatCount(counts.core_match)} 款完全满足；不足 3 款时会用部分匹配或补位参考补齐，并标出未满足项。`;
}

function parseScoreFactor(item, keyword) {
  const factor = safeList(item?.ranking_factors)
    .map(cleanText)
    .find((row) => row.includes(keyword));
  const matches = factor?.match(/-?\d+(\.\d+)?/g) || [];
  return matches.length ? clampScore(matches[matches.length - 1]) : null;
}

function sampleWarningText(value) {
  const text = cleanText(value);
  if (text.includes("missing review layers")) return "评论层级有缺失，结论需谨慎";
  if (text.includes("thin review layers")) return "部分评论层样本偏少";
  if (text.includes("distribution differs")) return "好中差评结构偏离较明显";
  return text;
}

function afterSaleShortTags(value) {
  const text = cleanText(value);
  const tags = [];
  if (text.includes("免费上门退换")) tags.push("售后文本含免费上门退换");
  if (text.includes("闪电退款") || text.includes("极速审核")) tags.push("售后文本含较快退款处理");
  if (text.includes("京东发货&售后") || text.includes("京东售后")) tags.push("售后由京东相关服务承接");
  if (text.includes("7天无理由退货")) tags.push("售后文本含 7 天无理由");
  if (text.includes("使用后不支持")) tags.push("使用后退货有限制");
  return tags;
}

function parameterReasonTags(item, role, filters, recommendations) {
  const price = numberOrNull(item?.stable_final_price);
  const min = numberOrNull(filters.min_price);
  const max = numberOrNull(filters.max_price);
  const primaryPrice = numberOrNull(recommendations[0]?.stable_final_price);
  const decision = parameterDecision(item);
  const analysis = parameterAnalysis(item);
  const facts = analysis.facts || {};
  const tags = [];

  if (role === "budget" && price !== null && primaryPrice !== null && price < primaryPrice) {
    tags.push(`比首选到手价低：${formatMoney(price)}`);
  } else if (price !== null && (min === null || max === null || (price >= min && price <= max))) {
    tags.push(`价格在预算内：${formatMoney(price)}`);
  } else if (price !== null) {
    tags.push(`到手价已返回：${formatMoney(price)}`);
  }

  if (decision.space_fit_text && !decision.space_fit_text.includes("待确认") && !decision.space_fit_text.includes("未接入")) {
    tags.push(`展开面积：${decision.space_fit_text}`);
  } else if (facts.derived_floor_area_m2) {
    tags.push(`推算面积：${facts.derived_floor_area_m2}`);
  }

  if (facts.expanded_size_text || safeList(decision.raw_parameter_facts).some((text) => text.includes("展开"))) {
    tags.push("尺寸信息可支撑基础判断");
  }

  const missing = safeList(decision.missing_parameters);
  if (missing.length) tags.push(`待确认：${missing.slice(0, 3).join("、")}`);
  if (!tags.length) tags.push("当前参数依据较少，下单前需确认");
  return uniqueList(tags).slice(0, 3);
}

function commentReasonTags(item) {
  const commentCount = numberOrNull(item?.comment_count);
  const rows = topRiskRows(item, 3);
  const warnings = safeList(item?.review_sample_warnings).map(sampleWarningText).filter(Boolean);
  const tags = [];
  if (commentCount !== null) tags.push(`评论样本 ${formatCount(commentCount)} 条`);
  if (warnings.length) tags.push(warnings[0]);
  if (rows.length) tags.push(`主要风险：${rows.map((row) => row.label).join("、")}`);
  const riskLabelCount = uniqueList([
    ...safeList(item?.risk_tags).map(labelRiskTag),
    ...rows.map((row) => row.label),
  ]).length;
  tags.push(riskLabelCount ? "评论风险已识别，可作为买前参考" : "当前未识别集中风险，仍需看详情");
  return uniqueList(tags).slice(0, 3);
}

function reasonTags(item, role, filters, recommendations) {
  const price = numberOrNull(item?.stable_final_price);
  const min = numberOrNull(filters.min_price);
  const max = numberOrNull(filters.max_price);
  const primaryPrice = numberOrNull(recommendations[0]?.stable_final_price);
  const match = firstScore(item?.match_score, item?.user_match_score, item?.final_score);
  const confidence = firstScore(item?.confidence_score, item?.data_confidence_score, item?.evidence_confidence_score);
  const commentCount = numberOrNull(item?.comment_count);
  const tags = [];

  if (role === "budget" && price !== null && primaryPrice !== null && price < primaryPrice) {
    tags.push(`比首选更便宜：${formatMoney(price)}`);
  } else if (price !== null && (min === null || max === null || (price >= min && price <= max))) {
    tags.push(`价格在预算内：${formatMoney(price)}`);
  } else if (price !== null) {
    tags.push(`到手价已返回：${formatMoney(price)}`);
  }

  if (match !== null) tags.push(`本次匹配分 ${scoreLabel(match)}`);
  if (commentCount !== null && commentCount >= 30) tags.push(`评论样本较多：${formatCount(commentCount)} 条`);
  else if (commentCount !== null && commentCount > 0) tags.push(`已有评论样本：${formatCount(commentCount)} 条`);

  const parameterTip = parameterHighlights(item)[0];
  if (parameterTip) tags.push(parameterTip);
  tags.push(...afterSaleShortTags(item?.recommended_after_sale_service));
  if (confidence !== null && confidence >= 75) tags.push(`依据充分度较高：${scoreLabel(confidence)}`);
  else if (confidence !== null && confidence >= 55) tags.push(`依据充分度中等：${scoreLabel(confidence)}`);

  if (!tags.length) tags.push("当前后端排序保留为候选");
  return uniqueList(tags).slice(0, 3);
}

function riskTags(item) {
  const rows = topRiskRows(item, 3).map((row) => `${row.label}相关反馈约 ${formatPercentRatio(row.value)}`);
  const labels = safeList(item?.risk_tags).map(labelRiskTag).filter(Boolean).slice(0, 3);
  const warnings = safeList(item?.review_sample_warnings).map(sampleWarningText).filter(Boolean);
  const result = uniqueList([...warnings, ...rows, ...labels, ...parameterCautions(item).slice(0, 1)]);
  return result.length ? result.slice(0, 2) : ["当前接口未返回明显集中风险"];
}

function suitableFor(item, filters) {
  const capacity = cleanText(item?.capacity);
  return uniqueList([
    activeScenario(filters),
    activePreference(filters),
    capacity && !["multi-variant", "unknown"].includes(capacity) ? `规格里出现 ${capacity}` : "",
  ]).slice(0, 3);
}

function notSuitableFor(item) {
  const rows = item?.dimension_risk_rates || {};
  const labels = safeList(item?.risk_tags).map(labelRiskTag).join("、");
  const count = Number(item?.comment_count || 0);
  const result = [];
  if (Number(rows.waterproof || 0) >= 0.02 || labels.includes("漏水") || labels.includes("防水")) {
    result.push("雨天或长时间淋雨前需先确认");
  }
  if (Number(rows.windproof || 0) >= 0.02 || labels.includes("防风")) {
    result.push("大风环境前需先确认");
  }
  if (Number(rows.smell_heat || 0) >= 0.02 || labels.includes("闷热") || labels.includes("异味")) {
    result.push("怕闷热或异味的人需谨慎");
  }
  if (count > 0 && count < 10) result.push("需要高确定性口碑样本时不适合直接下单");
  if (!result.length) result.push("强风雨、过夜或专业户外场景需另看实测数据");
  return result.slice(0, 4);
}

function scoreCards(item, filters) {
  const price = numberOrNull(item?.stable_final_price);
  const min = numberOrNull(filters.min_price);
  const max = numberOrNull(filters.max_price);
  const priceInBudget = price !== null && (min === null || max === null || (price >= min && price <= max));
  const risk = riskIndex(item);
  return [
    {
      label: "价格匹配",
      value: parseScoreFactor(item, "到手价相对得分"),
      text: price === null ? "当前接口未返回到手价" : `${formatMoney(price)}，${priceInBudget ? "在本次预算内" : "需核对预算"}`,
    },
    {
      label: "场景匹配",
      value: parseScoreFactor(item, "场景相关评论维度得分"),
      text: cleanText(safeList(item?.ranking_factors).find((row) => cleanText(row).includes("本次场景"))) || activeScenario(filters),
    },
    {
      label: "风险控制",
      value: parseScoreFactor(item, "校正后风险相对得分") ?? (risk === null ? null : 100 - risk),
      text: risk === null ? "当前接口未返回风险指数" : `风险指数 ${scoreLabel(risk)}，数值越低越好`,
    },
    {
      label: "依据充分度",
      value: firstScore(item?.confidence_score, item?.data_confidence_score, item?.evidence_confidence_score),
      text: `评论样本 ${formatCount(item?.comment_count)} 条；分数高表示信息更充分，不代表质量更高`,
    },
    {
      label: "商品参数",
      value: firstScore(item?.parameter_match_score, item?.parameter_score, item?.parameter_analysis?.scores?.overall),
      text: parameterSummary(item)[0] || "当前商品尚未接入可展示的商品参数",
    },
  ];
}

function oneSentenceReason(item, role, decision) {
  const match = scoreLabel(decision.match_score);
  const risk = scoreLabel(decision.risk_score);
  if (role === "primary") {
    return `当前排序最高，匹配度 ${match}，风险指数 ${risk}。下单前仍要看风险提醒。`;
  }
  if (role === "budget") {
    return `价格更有优势，但风险和依据充分度仍需要一起看。`;
  }
  if (role === "caution") {
    return `保留为提醒项，主要用于下单前确认风险是否能接受。`;
  }
  return `未进入前三个购买建议，可作为候选继续核对。`;
}

function evidenceSummary(item) {
  const riskCount = uniqueList([
    ...safeList(item?.risk_tags).map(labelRiskTag),
    ...topRiskRows(item, 5).filter((row) => row.value >= 0.005).map((row) => row.label),
  ]).length;
  return {
    review_count: item?.comment_count ?? 0,
    matched_need_count: safeList(item?.ranking_factors).length,
    risk_label_count: riskCount,
  };
}

function buildDecisionProduct(item, role, filters, recommendations) {
  const meta = ROLE_META[role] || ROLE_META.candidate;
  const parameterReasons = parameterReasonTags(item, role, filters, recommendations);
  const commentReasons = commentReasonTags(item);
  const matchedRequirements = safeList(item?.matched_requirements).slice(0, 2);
  const unmetRequirements = safeList(item?.unmet_requirements).slice(0, 3);
  const decision = {
    role,
    rank: role === "candidate" ? null : ["primary", "budget", "caution"].indexOf(role) + 1,
    ...meta,
    product_name: displayProductName(item),
    price: item?.stable_final_price,
    match_score: firstScore(item?.match_score, item?.user_match_score, item?.final_score),
    risk_score: riskIndex(item),
    confidence_score: firstScore(item?.confidence_score, item?.data_confidence_score, item?.evidence_confidence_score),
    selection_tier: item?.selection_tier || "fallback",
    selection_label: tierLabel(item?.selection_tier),
    strict_match_score: firstScore(item?.strict_match_score),
    selection_summary: cleanText(item?.selection_summary),
    matched_requirements: matchedRequirements,
    unmet_requirements: unmetRequirements,
    reason_tags: uniqueList([...matchedRequirements, ...parameterReasons, ...commentReasons, ...reasonTags(item, role, filters, recommendations)]).slice(0, 3),
    parameter_reason_tags: uniqueList([...matchedRequirements, ...parameterReasons]).slice(0, 3),
    comment_reason_tags: commentReasons,
    risk_tags: uniqueList([...unmetRequirements, ...riskTags(item)]).slice(0, 3),
    evidence_summary: evidenceSummary(item),
    positive_evidence: [],
    risk_evidence: [],
    suitable_for: suitableFor(item, filters),
    not_suitable_for: notSuitableFor(item),
    score_cards: scoreCards(item, filters),
    ranking_factors: safeList(item?.ranking_factors).map(cleanText).filter(Boolean),
    parameter_analysis: parameterAnalysis(item),
    parameter_decision: parameterDecision(item),
    parameter_judgment_lines: parameterJudgmentLines(item),
    parameter_raw_facts: parameterRawFacts(item),
    parameter_summary: parameterSummary(item),
    parameter_highlights: parameterHighlights(item),
    parameter_cautions: parameterCautions(item),
    product: item,
  };
  decision.one_sentence_reason = oneSentenceReason(item, role, decision);
  return decision;
}

function uniquePush(list, item) {
  if (!item) return;
  if (list.some((row) => row?.canonical_product_id === item.canonical_product_id)) return;
  list.push(item);
}

function buildPlanItems(recommendations, filters) {
  const core = recommendations.filter((item) => item.selection_tier === "core_match");
  const partial = recommendations.filter((item) => item.selection_tier === "partial_match");
  const fallback = recommendations.filter((item) => item.selection_tier === "fallback" || !item.selection_tier);
  const primary = core[0] || partial[0] || recommendations[0];
  const budgetPool = (core.length ? core : partial.length ? partial : recommendations).filter((item) => item !== primary);
  const cheapest = budgetPool
    .sort((a, b) => Number(a.stable_final_price || 0) - Number(b.stable_final_price || 0))[0];
  const selectedSeed = [primary, cheapest].filter(Boolean);
  const caution = [...fallback, ...partial, ...recommendations]
    .filter((item) => item && !selectedSeed.some((row) => row?.canonical_product_id === item.canonical_product_id))
    .sort((a, b) => {
      const aUnmet = safeList(a.unmet_requirements).length;
      const bUnmet = safeList(b.unmet_requirements).length;
      const aUsefulGap = aUnmet > 0 && aUnmet <= 2 ? 1 : 0;
      const bUsefulGap = bUnmet > 0 && bUnmet <= 2 ? 1 : 0;
      return (bUsefulGap - aUsefulGap)
        || (tierRank(a.selection_tier) - tierRank(b.selection_tier))
        || (riskScoreForSorting(b) - riskScoreForSorting(a));
    })[0];

  const selected = [];
  uniquePush(selected, primary);
  uniquePush(selected, cheapest);
  uniquePush(selected, caution);
  recommendations.forEach((item) => {
    if (selected.length < 3) uniquePush(selected, item);
  });

  return selected.map((item, index) => {
    const role = index === 0 ? "primary" : index === 1 ? "budget" : "caution";
    return {
      product: item,
      plan: { role },
      decision: buildDecisionProduct(item, role, filters, recommendations),
    };
  });
}

function budgetText(filters) {
  return `${filters.min_price}-${filters.max_price} 元`;
}

function conclusionText(decision, filters) {
  const product = decision?.product || {};
  const price = numberOrNull(decision?.price);
  const min = numberOrNull(filters.min_price);
  const max = numberOrNull(filters.max_price);
  const priceText = price === null
    ? "当前接口未返回到手价"
    : `到手价 ${formatMoney(price)}${min === null || max === null || (price >= min && price <= max) ? "在预算范围内" : "需核对预算"}`;
  const parameter = decision?.parameter_decision || {};
  const parameterText = parameter.space_fit_text && !parameter.space_fit_text.includes("未接入")
    ? `参数上${parameter.space_fit_text}`
    : "参数上展开面积待确认";
  const commentText = `评论样本 ${formatCount(decision?.evidence_summary?.review_count)} 条`;
  const riskRows = topRiskRows(product, 2).map((row) => row.label);
  const riskText = riskRows.length ? `主要风险集中在${riskRows.join("、")}` : (decision?.risk_tags?.[0] || "当前未返回明显集中风险");
  return `更推荐该商品，是因为${priceText}，${parameterText}，且${commentText}可用于校验评论风险；${riskText}。`;
}

function openProductUrl(url) {
  openPublicProductUrl(url);
}

function selectedDetailProduct(detail, decision) {
  const products = detail?.products || [];
  return products.find((item) => item.platform_product_id === decision?.product?.recommended_platform_product_id) || products[0] || {};
}

function selectedParameterAnalysis(detail, decision) {
  const chosen = selectedDetailProduct(detail, decision);
  const rows = detail?.parameter_analysis || [];
  return rows.find((item) => item.product_id === chosen?.id)?.analysis || decision?.parameter_analysis || {};
}

function cleanCommentSnippet(value) {
  const text = cleanText(value)
    .replace(/\n?Purchased variant:[\s\S]*$/i, "")
    .replace(/&quot;/g, "\"")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^["“”]+|["“”]+$/g, "");
  if (!text || text.includes("此用户未及时填写评价内容")) return "";
  return text.length > 86 ? `${text.slice(0, 86)}...` : text;
}

function commentSnippets(detail, decision, type) {
  const chosen = selectedDetailProduct(detail, decision);
  const allComments = detail?.comments || [];
  const comments = chosen?.id ? allComments.filter((item) => item.product_id === chosen.id) : allComments;
  const filtered = comments.filter((comment) => {
    const rating = Number(comment.rating || 0);
    if (type === "positive") return comment.comment_type === "positive" || rating >= 4;
    return comment.comment_type === "negative" || rating <= 2;
  });
  return filtered.map((comment) => cleanCommentSnippet(comment.comment_text)).filter(Boolean).slice(0, 2);
}

function parameterEvidenceRows(parameter) {
  const facts = parameter?.facts || {};
  const decision = parameterDecision(parameter);
  return [
    ["展开尺寸", facts.expanded_size_text || "待确认"],
    ["推算面积", facts.derived_floor_area_m2 || "待确认"],
    ["适合人数判断", decision.people_judgment?.replace(/^适合人数判断：/, "") || "待确认"],
    ["适合场景判断", decision.scene_judgment?.replace(/^场景判断：/, "") || "待确认"],
    ["待确认参数", safeList(decision.missing_parameters).length ? decision.missing_parameters.join("、") : "暂无"],
  ];
}

function comprehensiveConclusionItems(decision, parameter) {
  const missing = missingParameterText(parameter || decision?.parameter_analysis);
  return [
    `为什么建议买：${decision.one_sentence_reason}`,
    `为什么不是完全无风险：${decision.risk_tags[0] || "当前仍需结合评论和商品页确认"}`,
    `下单前需要确认：${missing.replace(/^待确认参数：/, "") || "商品页价格、售后和当前参数"}`,
  ];
}

function EvidenceModal({ state, onClose, onCompare }) {
  if (!state?.decision) return null;
  const { decision, detail, loading, error } = state;
  const product = decision.product || {};
  const productUrl = publicProductUrl(product.recommended_product_url);
  const positive = detail ? commentSnippets(detail, decision, "positive") : [];
  const risks = detail ? commentSnippets(detail, decision, "risk") : [];
  const parameter = selectedParameterAnalysis(detail, decision);
  const parameterScores = parameter?.scores || {};
  const parameterFacts = parameter?.facts || {};
  const parameterEvidence = parameterEvidenceRows(parameter);
  const comprehensiveItems = comprehensiveConclusionItems(decision, parameter);
  const parameterFactsList = [
    parameterFacts.expanded_size_text && `展开尺寸：${parameterFacts.expanded_size_text}`,
    parameterFacts.derived_floor_area_m2 && `推算面积：${parameterFacts.derived_floor_area_m2}`,
    parameterFacts.weight_text && `重量：${parameterFacts.weight_text}`,
    parameterFacts.packed_size_text && `收纳：${parameterFacts.packed_size_text}`,
    parameterFacts.outer_material && `面料：${parameterFacts.outer_material}`,
    parameterFacts.pole_material && `帐杆：${parameterFacts.pole_material}`,
    parameterFacts.setup_type && `搭建方式：${parameterFacts.setup_type}`,
    parameterFacts.waterproof_index_outer && `外帐防水指数：${parameterFacts.waterproof_index_outer}`,
    parameterFacts.waterproof_index_floor && `帐底防水指数：${parameterFacts.waterproof_index_floor}`,
  ].filter(Boolean);

  return (
    <div className="evidence-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="evidence-modal" role="dialog" aria-modal="true" aria-label="推荐证据" onMouseDown={(event) => event.stopPropagation()}>
        <div className="evidence-modal-head">
          <div>
            <p className="eyebrow">推荐证据</p>
            <h3>{decision.product_name}</h3>
          </div>
          <button type="button" className="secondary" onClick={onClose}>关闭</button>
        </div>

        <section className="evidence-block conclusion">
          <h4>推荐结论</h4>
          <p>
            {decision.recommend_type}｜{decision.decision_label}。
            {decision.one_sentence_reason}
          </p>
          <div className="evidence-chip-row">
            <span>推荐等级 {decision.recommend_grade}</span>
            <span>到手价 {formatMoney(decision.price)}</span>
            <span>评论样本 {formatCount(decision.evidence_summary.review_count)} 条</span>
            {productUrl ? (
              <button type="button" className="link-button" onClick={() => openProductUrl(productUrl)}>打开商品链接</button>
            ) : <span>{PRODUCT_LINK_UNAVAILABLE_TEXT}</span>}
          </div>
        </section>

        <section className="evidence-block">
          <h4>评分拆解</h4>
          <div className="score-breakdown">
            {decision.score_cards.map((card) => (
              <div key={card.label}>
                <span>{card.label}</span>
                <strong>{scoreLabel(card.value)}</strong>
                <p>{card.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="evidence-block parameter-evidence">
          <h4>参数证据</h4>
          {parameter?.has_specs ? (
            <>
              <div className="score-breakdown compact">
                <div><span>空间参数</span><strong>{scoreLabel(parameterScores.space)}</strong><p>按页面尺寸和容量文字辅助判断</p></div>
                <div><span>携带负担</span><strong>{scoreLabel(parameterScores.portability)}</strong><p>按页面重量和收纳尺寸辅助判断</p></div>
                <div><span>搭建友好</span><strong>{scoreLabel(parameterScores.setup)}</strong><p>按页面搭建方式文字辅助判断</p></div>
                <div><span>参数完整度</span><strong>{scoreLabel(parameterScores.completeness)}</strong><p>只统计已接入字段</p></div>
              </div>
              <div className="parameter-fact-grid">
                {parameterEvidence.map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              <div className="evidence-columns">
                <div>
                  <strong>页面原始参数</strong>
                  <ul>
                    {parameterFactsList.length ? parameterFactsList.slice(0, 6).map((item) => <li key={item}>{item}</li>) : <li>当前参数字段较少</li>}
                  </ul>
                </div>
                <div>
                  <strong>参数提醒</strong>
                  <ul>
                    {safeList(parameter.cautions).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </div>
              </div>
              <p className="boundary-copy">{parameter.source_boundary}</p>
            </>
          ) : (
            <p>当前商品尚未接入可展示的商品参数。</p>
          )}
        </section>

        <section className="evidence-columns">
          <div className="evidence-block">
            <h4>推荐依据</h4>
            <ul>
              {uniqueList([...decision.parameter_reason_tags, ...decision.comment_reason_tags, ...decision.ranking_factors]).slice(0, 7).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="evidence-block">
            <h4>风险依据</h4>
            <ul>
              {uniqueList([...decision.risk_tags, ...safeList(product.review_sample_warnings).map(sampleWarningText)]).slice(0, 6).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="evidence-block">
          <div className="fold-header compact">
            <h4>评论证据</h4>
            {loading && <span className="loading-note">正在读取商品详情里的评论原文...</span>}
            {error && <span className="loading-note error">{error}</span>}
          </div>
          <div className="evidence-chip-row">
            <span>评论样本 {formatCount(decision.evidence_summary.review_count)} 条</span>
            <span>命中需求点 {formatCount(decision.evidence_summary.matched_need_count)} 个</span>
            <span>风险标签 {formatCount(decision.evidence_summary.risk_label_count)} 类</span>
          </div>
          <div className="comment-evidence-grid">
            <div>
              <strong>正向证据</strong>
              <ul>
                {positive.length ? positive.map((item) => <li key={item}>“{item}”</li>) : (
                  <li>{loading ? "正在加载评论原文" : "当前商品详情接口没有返回可展示的正向评论原文"}</li>
                )}
              </ul>
            </div>
            <div>
              <strong>风险证据</strong>
              <ul>
                {risks.length ? risks.map((item) => <li key={item}>“{item}”</li>) : (
                  <li>{loading ? "正在加载评论原文" : "当前商品详情接口没有返回可展示的风险评论原文"}</li>
                )}
              </ul>
            </div>
          </div>
        </section>

        <section className="evidence-block">
          <h4>综合结论</h4>
          <ul>
            {comprehensiveItems.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>

        <section className="evidence-block">
          <h4>不适合购买场景</h4>
          <ul className="not-suitable-list">
            {decision.not_suitable_for.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>

        <div className="evidence-modal-actions">
          <button type="button" onClick={() => onCompare(product.canonical_product_id)}>加入对比</button>
          <button type="button" className="secondary" onClick={onClose}>继续看推荐</button>
        </div>
      </section>
    </div>
  );
}

export default function Recommendations({
  filters,
  recommendations,
  loading,
  error,
  onOpenCompare,
  onRefresh,
}) {
  const [showScreening, setShowScreening] = useState(false);
  const [showCandidates, setShowCandidates] = useState(false);
  const [evidenceState, setEvidenceState] = useState(null);
  const planItems = useMemo(() => buildPlanItems(recommendations, filters), [recommendations, filters]);
  const selectionStats = useMemo(() => selectionCounts(recommendations), [recommendations]);
  const selectionSummary = useMemo(() => selectionSummaryText(recommendations, filters), [recommendations, filters]);
  const selectedIds = new Set(planItems.map(({ product }) => product?.canonical_product_id).filter(Boolean));
  const remainingCandidates = recommendations.filter((item) => !selectedIds.has(item.canonical_product_id));
  const candidateItems = useMemo(() => remainingCandidates.map((item, index) => ({
    product: item,
    plan: { role: "candidate" },
    decision: {
      ...buildDecisionProduct(item, "candidate", filters, recommendations),
      rank: index + 4,
    },
  })), [remainingCandidates, filters, recommendations]);
  const bestDecision = planItems[0]?.decision;
  const budgetDecision = planItems[1]?.decision;
  const selectedCount = Math.min(planItems.length, 3);

  async function openEvidence(decision) {
    setEvidenceState({ decision, detail: null, loading: true, error: "" });
    try {
      const detail = await fetchProductDetail(decision.product.canonical_product_id);
      setEvidenceState((current) => (
        current?.decision?.product?.canonical_product_id === decision.product.canonical_product_id
          ? { decision, detail, loading: false, error: "" }
          : current
      ));
    } catch (requestError) {
      setEvidenceState((current) => (
        current?.decision?.product?.canonical_product_id === decision.product.canonical_product_id
          ? { decision, detail: null, loading: false, error: "评论原文读取失败，仍展示推荐接口已返回的证据" }
          : current
      ));
    }
  }

  return (
    <section className="decision-page">
      <div className="decision-hero">
        <div>
          <p className="eyebrow">购买建议</p>
          <h2>{bestDecision ? "先看结论，再看证据" : "系统正在替你筛选帐篷"}</h2>
          <p className="lead">
            当前基于接口返回的 {formatCount(recommendations.length)} 个帐篷同款组进行排序。
            页面只展示真实字段，不补写未返回的数据。
          </p>
        </div>
        <button type="button" onClick={() => onRefresh(filters)}>重新筛选</button>
      </div>

      <div className="decision-stats">
        <div>
          <span>当前候选</span>
          <strong>{formatCount(recommendations.length)} 个</strong>
        </div>
        <div>
          <span>精选展示</span>
          <strong>{formatCount(selectedCount)} 个</strong>
        </div>
        <div>
          <span>完全满足</span>
          <strong>{formatCount(selectionStats.core_match)} 个</strong>
        </div>
        <div>
          <span>折叠候选</span>
          <strong>{formatCount(remainingCandidates.length)} 个</strong>
        </div>
        <div>
          <span>当前样本评论</span>
          <strong>{formatCount(totalComments(recommendations))} 条</strong>
        </div>
      </div>

      <div className="context-strip">
        <span>预算：{budgetText(filters)}</span>
        <span>场景：{activeScenario(filters)}</span>
        <span>偏好：{activePreference(filters)}</span>
        <span>完全满足：{formatCount(selectionStats.core_match)} 个</span>
      </div>

      <div className="selection-summary-strip">
        <strong>强约束筛选</strong>
        <span>{selectionSummary}</span>
      </div>

      {loading ? (
        <p className="empty">正在读取后端数据并计算购买建议...</p>
      ) : error ? (
        <p className="empty error-text">{error}</p>
      ) : !recommendations.length ? (
        <p className="empty">暂无符合当前预算和场景的推荐结果。</p>
      ) : (
        <>
          {bestDecision && (
            <section className="decision-conclusion-banner">
              <div className="conclusion-copy">
                <span>本次推荐结论</span>
                <h3>更推荐「{bestDecision.product_name}」</h3>
                <p>
                  根据预算 {budgetText(filters)}、{activeScenario(filters)}、{activePreference(filters)}，
                  {conclusionText(bestDecision, filters)}
                  匹配度 {scoreLabel(bestDecision.match_score)}，风险指数 {scoreLabel(bestDecision.risk_score)}，依据充分度 {scoreLabel(bestDecision.confidence_score)}。
                </p>
              </div>
              <div className="conclusion-grade">
                <span>推荐等级</span>
                <strong>{bestDecision.recommend_grade}</strong>
                <small>{bestDecision.recommend_type}｜{bestDecision.decision_label}</small>
              </div>
              <div className="conclusion-risk">
                <span>主要风险提醒</span>
                <strong>{bestDecision.risk_tags[0] || "当前未返回明显集中风险"}</strong>
              </div>
            </section>
          )}

          <section className="selected-plans">
            {planItems.map(({ product, plan, decision }) => (
              <ProductCard
                key={`${plan.role}-${product.canonical_product_id}`}
                product={product}
                plan={plan}
                decision={decision}
                onOpenEvidence={() => openEvidence(decision)}
                onOpenCompare={() => onOpenCompare(product.canonical_product_id)}
              />
            ))}
          </section>

          <section className="why-not-cheapest decision-explain">
            <div>
              <p className="eyebrow">为什么不是最低价</p>
              <h3>系统不是简单选择最低价</h3>
            </div>
            <p>
              当前首选和低价备选都来自后端推荐接口。页面不会编造未返回的排除数量，也不会把未来可能接入的数据写成当前结果。
            </p>
            <p>
              当前低价备选是 {budgetDecision ? budgetDecision.product_name : "等待计算"}，到手价 {formatMoney(budgetDecision?.price)}。
              是否作为首选，还要看匹配度、评论样本、风险标签和售后信息。
            </p>
          </section>

          <section className="screening-panel">
            <div className="fold-header">
              <div>
                <p className="eyebrow">筛选状态</p>
                <h3>当前只展示接口返回的真实结果</h3>
              </div>
              <button type="button" className="secondary" onClick={() => setShowScreening((value) => !value)}>
                {showScreening ? "收起筛选状态" : "查看筛选状态"}
              </button>
            </div>
            {showScreening && (
              <div className="screening-grid">
                <div>
                  <span>接口返回候选同款组</span>
                  <strong>{formatCount(recommendations.length)} 个</strong>
                </div>
                <div>
                  <span>首页精选展示</span>
                  <strong>{formatCount(selectedCount)} 个</strong>
                </div>
                <div>
                  <span>完全满足核心要求</span>
                  <strong>{formatCount(selectionStats.core_match)} 个</strong>
                </div>
                <div>
                  <span>部分满足/补位参考</span>
                  <strong>{formatCount((selectionStats.partial_match || 0) + (selectionStats.fallback || 0))} 个</strong>
                </div>
                <div>
                  <span>折叠候选商品</span>
                  <strong>{formatCount(remainingCandidates.length)} 个</strong>
                </div>
                <div>
                  <span>当前评论样本</span>
                  <strong>{formatCount(totalComments(recommendations))} 条</strong>
                </div>
                <div>
                  <span>排除分类明细</span>
                  <strong>当前接口未返回</strong>
                </div>
              </div>
            )}
          </section>

          <section className="candidate-panel">
            <div className="fold-header">
              <div>
                <p className="eyebrow">候选商品列表</p>
                <h3>只展示未进入三张精选方案的候选同款组</h3>
              </div>
              <button type="button" className="secondary" onClick={() => setShowCandidates((value) => !value)}>
                {showCandidates ? "收起候选商品" : "查看全部候选商品"}
              </button>
            </div>
            {showCandidates && (
              <div className="candidate-list">
                {candidateItems.length ? candidateItems.map(({ product, plan, decision }) => (
                  <ProductCard
                    key={product.canonical_product_id || product.product_name}
                    product={product}
                    compact
                    plan={plan}
                    decision={decision}
                    onOpenEvidence={() => openEvidence(decision)}
                    onOpenCompare={() => onOpenCompare(product.canonical_product_id)}
                  />
                )) : <p className="empty">当前没有未进入三张精选方案的剩余候选商品。</p>}
              </div>
            )}
          </section>

          <EvidenceModal
            state={evidenceState}
            onClose={() => setEvidenceState(null)}
            onCompare={onOpenCompare}
          />
        </>
      )}
    </section>
  );
}
