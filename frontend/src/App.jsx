import { useEffect, useState } from "react";
import {
  fetchCommentRiskSummary,
  fetchPriceCompare,
  fetchProductDetail,
  fetchRecommendations,
  fetchRedBookSummary,
} from "./api/client.js";
import ChatAssistant from "./components/ChatAssistant.jsx";
import Home from "./pages/Home.jsx";
import Recommendations from "./pages/Recommendations.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import PriceCompare from "./pages/PriceCompare.jsx";

const DEFAULT_FILTERS = {
  min_price: 100,
  max_price: 1000,
  scenario: "newbie_weekend",
  scenario_answer: "weekend_park",
  preference: "balanced",
  concern_answers: ["risk_control"],
  limit: 50,
};

export default function App() {
  const [view, setView] = useState("home");
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [selectedRecommendation, setSelectedRecommendation] = useState(null);
  const [commentRisk, setCommentRisk] = useState(null);
  const [redbookSummary, setRedbookSummary] = useState(null);
  const [compare, setCompare] = useState(null);

  useEffect(() => {
    if (view !== "recommendations" || recommendations.length || loading) return;
    loadRecommendations(filters);
  }, [view]);

  async function loadRecommendations(nextFilters = filters) {
    setFilters(nextFilters);
    setLoading(true);
    setError("");
    try {
      const data = await fetchRecommendations(nextFilters);
      setRecommendations(data);
      setView("recommendations");
    } catch (requestError) {
      setRecommendations([]);
      setError(`购买建议接口调用失败：${requestError.message}`);
      setView("recommendations");
    } finally {
      setLoading(false);
    }
  }

  function applyChatRecommendations(nextFilters, nextRecommendations) {
    setFilters(nextFilters);
    setRecommendations(nextRecommendations);
    setLoading(false);
    setError("");
    setDetail(null);
    setDetailError("");
    setSelectedRecommendation(null);
    setCommentRisk(null);
    setRedbookSummary(null);
    setCompare(null);
    setView("recommendations");
  }

  async function openDetail(id) {
    if (!id) return;
    const selected = recommendations.find((item) => item.canonical_product_id === id) || null;
    setSelectedRecommendation(selected);
    setDetail(null);
    setDetailError("");
    setCommentRisk(null);
    setRedbookSummary(null);
    setView("detail");
    setError("");

    try {
      const data = await fetchProductDetail(id);
      setDetail(data);
    } catch (requestError) {
      setDetailError(`推荐依据接口调用失败：${requestError.message}`);
      return;
    }

    try {
      const commentSummary = await fetchCommentRiskSummary(id);
      setCommentRisk(commentSummary);
    } catch {
      setCommentRisk(null);
    }

    try {
      const redbookData = await fetchRedBookSummary(id);
      setRedbookSummary(redbookData);
    } catch {
      setRedbookSummary(null);
    }
  }

  async function openCompare(id) {
    if (!id) return;
    const selected = recommendations.find((item) => item.canonical_product_id === id) || null;
    const sortedByPrice = [...recommendations]
      .filter((item) => Number.isFinite(Number(item.stable_final_price)))
      .sort((a, b) => Number(a.stable_final_price) - Number(b.stable_final_price));
    const cheapest = sortedByPrice[0] || null;
    const primary = recommendations[0] || null;
    const comparisonTarget = cheapest?.canonical_product_id !== id
      ? cheapest
      : primary?.canonical_product_id !== id
        ? primary
        : sortedByPrice.find((item) => item.canonical_product_id !== id) || null;
    const data = await fetchPriceCompare(id);
    setCompare({
      ...data,
      selected_recommendation: selected,
      comparison_target: comparisonTarget,
      comparison_target_role: cheapest?.canonical_product_id === comparisonTarget?.canonical_product_id ? "low_price" : "current_primary",
      recommendation_context: recommendations,
    });
    setView("compare");
  }

  return (
    <main>
      <nav className="top-nav" aria-label="CampRank 页面导航">
        <button className={view === "home" ? "active" : ""} onClick={() => setView("home")}>开始筛选</button>
        <button className={view === "recommendations" ? "active" : ""} onClick={() => setView("recommendations")}>购买建议</button>
        <button className={view === "detail" ? "active" : ""} onClick={() => setView("detail")}>推荐依据</button>
        <button className={view === "compare" ? "active" : ""} onClick={() => setView("compare")}>和低价款对比</button>
      </nav>
      {view === "home" && <Home onStart={loadRecommendations} />}
      {view === "recommendations" && (
        <Recommendations
          filters={filters}
          recommendations={recommendations}
          loading={loading}
          error={error}
          onOpenDetail={openDetail}
          onOpenCompare={openCompare}
          onRefresh={loadRecommendations}
        />
      )}
      {view === "detail" && (
        <ProductDetail
          detail={detail}
          error={detailError}
          commentRisk={commentRisk}
          redbookSummary={redbookSummary}
          recommendation={selectedRecommendation}
          recommendations={recommendations}
        />
      )}
      {view === "compare" && <PriceCompare compare={compare} />}
      <ChatAssistant currentFilters={filters} onRecommendationsReady={applyChatRecommendations} />
    </main>
  );
}
