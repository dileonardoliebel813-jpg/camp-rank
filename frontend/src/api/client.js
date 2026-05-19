const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

async function request(path, params) {
  const response = await fetch(`${API_BASE}${withQuery(path, params)}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function fetchRecommendations(params = {}) {
  return request("/api/recommendations", params);
}

export function fetchProducts() {
  return request("/api/products");
}

export function fetchProductDetail(id) {
  return request(`/api/products/${id}`);
}

export function fetchPriceCompare(id) {
  return request(`/api/price-compare/${id}`);
}

export function fetchCommentRiskSummary(id) {
  return request(`/api/products/${id}/comment-risk-summary`);
}

export function fetchRedBookSummary(id) {
  return request(`/api/products/${id}/redbook-summary`);
}
