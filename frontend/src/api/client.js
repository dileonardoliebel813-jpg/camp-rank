const DEFAULT_API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || DEFAULT_API_BASE).replace(/\/$/, "");

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

async function postRequest(path, body = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      const detail = data.detail || {};
      message = detail.error_code
        ? `${detail.error_code}: ${detail.message || message}`
        : detail.message || message;
    } catch {
      // Keep the status-based message when the backend does not return JSON.
    }
    throw new Error(message);
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

export function chatRecommendation(payload = {}) {
  return postRequest("/api/chat/recommendation", payload);
}
