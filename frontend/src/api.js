const API = (import.meta.env.VITE_API || "http://localhost:8080/api").replace(/\/$/, "");
const tok = () => window.localStorage.getItem("tuva_token");
async function req(path, opts = {}, authToken = tok()) {
  const headers = {
    ...(opts.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(authToken ? { Authorization: `Token ${authToken}` } : {}),
    ...opts.headers,
  };
  let response;
  try {
    response = await fetch(API + path, { ...opts, headers });
  } catch {
    throw new Error("Unable to reach TUVA right now. Check your connection and try again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.error || data.detail || Object.values(data).flat().find((value) => typeof value === "string");
    const error = new Error(detail || "Something went wrong. Please try again.");
    error.status = response.status;
    throw error;
  }
  return data;
}
export const api = {
  products: (q = "", category = "") => req(`/products/?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}`),
  imageSearch: (file) => { const f = new FormData(); f.append("image", file); return req("/image-search/", { method: "POST", body: f }); },
  alert: (email, query) => req("/alerts/", { method: "POST", body: JSON.stringify({ email, query }) }),
  google: (credential) => req("/auth/google/", { method: "POST", body: JSON.stringify({ credential }) }),
  register: (name, email, password) => req("/auth/register/", { method: "POST", body: JSON.stringify({ name, email, password }) }, ""),
  login: (email, password) => req("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }, ""),
  logout: (token) => req("/auth/logout/", { method: "POST" }, token),
  quote: (product, qty = 1) => req(`/checkout/quote/?product=${encodeURIComponent(product)}&qty=${encodeURIComponent(qty)}`),
  checkout: (product, phone, qty = 1) => req("/checkout/", { method: "POST", body: JSON.stringify({ product, phone, qty }) }),
  order: (id) => req(`/orders/${id}/`),
  assistant: (messages) => req("/assistant/", { method: "POST", body: JSON.stringify({ messages }) }),
  chat: (conversation) => req(`/chat/?conversation=${encodeURIComponent(conversation)}`),
  sendChat: (conversation, message) => req("/chat/", { method: "POST", body: JSON.stringify({ conversation, message }) }),
  adminLogin: (username, password) => req("/management/login/", { method: "POST", body: JSON.stringify({ username, password }) }, ""),
  adminDashboard: (token) => req("/management/dashboard/", {}, token),
  adminUpdateStock: (product, stock, token) => req(`/management/products/${product}/stock/`, { method: "PATCH", body: JSON.stringify({ stock }) }, token),
  adminCreateProduct: (form, token) => req("/management/products/", { method: "POST", body: form }, token),
  adminUpdateProduct: (product, form, token) => req(`/management/products/${product}/`, { method: "PATCH", body: form }, token),
  adminDeleteProduct: (product, token) => req(`/management/products/${product}/delete/`, { method: "DELETE" }, token),
  adminConversation: (conversation, token) => req(`/management/conversations/${encodeURIComponent(conversation)}/`, {}, token),
  adminReply: (conversation, message, token) => req(`/management/conversations/${encodeURIComponent(conversation)}/reply/`, { method: "POST", body: JSON.stringify({ message }) }, token),
};
