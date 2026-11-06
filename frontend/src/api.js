const DEFAULT_API = import.meta.env.PROD
  // ? "https://tuvacomputers.pythonanywhere.com/api"
  // : "https://tuvacomputers.pythonanywhere.com/api";
  ? "http://127.0.0.1:8080/api"
  : "http://127.0.0.1:8080/api";
const configuredAPI = import.meta.env.VITE_API;
const pointsAtThisComputer = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(configuredAPI || "");
const API = ((import.meta.env.PROD && pointsAtThisComputer ? "" : configuredAPI) || DEFAULT_API).replace(/\/$/, "");
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
function adminReq(path, opts, authToken) {
  const staffToken = authToken || window.localStorage.getItem("tuva_admin_token");
  if (!staffToken) {
    const error = new Error("Your staff session has expired. Sign in again to manage products.");
    error.status = 401;
    throw error;
  }
  return req(path, opts, staffToken);
}
export const api = {
  products: (q = "", category = "", offset = 0, includeCount = false, filters = {}) => req(`/products/?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&offset=${encodeURIComponent(offset)}${includeCount ? "&include_count=true" : ""}&sort=${encodeURIComponent(filters.sort || "newest")}&min_price=${encodeURIComponent(filters.minPrice || "")}&max_price=${encodeURIComponent(filters.maxPrice || "")}&in_stock=${filters.inStock ? "true" : "false"}`),
  product: (id) => req(`/products/${encodeURIComponent(id)}/`),
  storeConfig: () => req("/store-config/", {}, ""),
  deliveryZones: () => req("/delivery-zones/", {}, ""),
  imageSearch: (file) => { const f = new FormData(); f.append("image", file); return req("/image-search/", { method: "POST", body: f }); },
  alert: (email, query, consent) => req("/alerts/", { method: "POST", body: JSON.stringify({ email, query, consent }) }),
  google: (credential) => req("/auth/google/", { method: "POST", body: JSON.stringify({ credential }) }),
  register: (name, email, password) => req("/auth/register/", { method: "POST", body: JSON.stringify({ name, email, password }) }, ""),
  login: (email, password) => req("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }, ""),
  logout: (token) => req("/auth/logout/", { method: "POST" }, token),
  quote: (product, qty = 1, deliveryZone = "") => req(`/checkout/quote/?product=${encodeURIComponent(product)}&qty=${encodeURIComponent(qty)}&delivery_zone=${encodeURIComponent(deliveryZone)}`),
  quoteCart: (items, deliveryZone = null) => req("/checkout/quote/", { method: "POST", body: JSON.stringify({ items, delivery_zone: deliveryZone }) }, ""),
  checkout: (product, phone, qty = 1, idempotencyKey, customer = {}) => req("/checkout/", { method: "POST", headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}, body: JSON.stringify({ product, phone, qty, ...customer }) }),
  checkoutCart: (items, phone, deliveryZone, idempotencyKey) => req("/checkout/", { method: "POST", headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}, body: JSON.stringify({ items, phone, delivery_zone: deliveryZone }) }),
  order: (id, accessToken = "") => req(`/orders/${id}/`, { headers: accessToken ? { "X-Order-Access-Token": accessToken } : {} }),
  assistant: (messages) => req("/assistant/", { method: "POST", body: JSON.stringify({ messages }) }),
  chat: (conversation) => req(`/chat/?conversation=${encodeURIComponent(conversation)}`),
  sendChat: (conversation, message) => req("/chat/", { method: "POST", body: JSON.stringify({ conversation, message }) }),
  adminLogin: (username, password) => req("/management/login/", { method: "POST", body: JSON.stringify({ username, password }) }, ""),
  adminDashboard: (token) => adminReq("/management/dashboard/", {}, token),
  adminProducts: (query, offset, token) => adminReq(`/management/products/?q=${encodeURIComponent(query)}&offset=${encodeURIComponent(offset)}`, {}, token),
  adminUpdateStock: (product, stock, token) => adminReq(`/management/products/${product}/stock/`, { method: "PATCH", body: JSON.stringify({ stock }) }, token),
  adminCreateProduct: (form, token) => adminReq("/management/products/", { method: "POST", body: form }, token),
  adminUpdateProduct: (product, form, token) => adminReq(`/management/products/${product}/`, { method: "PATCH", body: form }, token),
  adminUpdateProductImage: (product, image, file, token) => { const form = new FormData(); form.append("image", file); return adminReq(`/management/products/${product}/images/${encodeURIComponent(image)}/`, { method: "PATCH", body: form }, token); },
  adminDeleteProductImage: (product, image, token) => adminReq(`/management/products/${product}/images/${encodeURIComponent(image)}/`, { method: "DELETE" }, token),
  adminDeleteProduct: (product, token) => adminReq(`/management/products/${product}/delete/`, { method: "DELETE" }, token),
  adminConversation: (conversation, token) => adminReq(`/management/conversations/${encodeURIComponent(conversation)}/`, {}, token),
  adminReply: (conversation, message, token) => adminReq(`/management/conversations/${encodeURIComponent(conversation)}/reply/`, { method: "POST", body: JSON.stringify({ message }) }, token),
};
