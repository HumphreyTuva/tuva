import { Children, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  Boxes,
  ChartNoAxesCombined,
  CircleAlert,
  Edit2,
  Headset,
  LoaderCircle,
  LogOut,
  PackageCheck,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  ShoppingBag,
  Trash2,
  X,
} from "lucide-react";
import { api } from "./api";
import { productUseCases } from "./productUseCases";

const money = (value) => `KSh ${Number(value || 0).toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
const date = (value) => new Date(value).toLocaleString(undefined, {
  month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
});

function AdminLogin({ onLogin, onClose, notice }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onLogin(username, password);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-login-wrap">
      <section className="admin-login-card" aria-labelledby="admin-login-title">
        <button className="admin-close" type="button" onClick={onClose} aria-label="Close dashboard"><X size={20} /></button>
        <span className="admin-login-mark"><ShieldCheck size={23} /></span>
        <p className="admin-eyebrow">TUVA · STORE MANAGEMENT</p>
        <h1 id="admin-login-title">Welcome back</h1>
        <p className="admin-login-copy">Sign in with a Django staff account to access your store dashboard.</p>
        <button className="admin-return-store" type="button" onClick={onClose}><ArrowLeft size={16} /> Back to TUVA storefront</button>
        {notice && <p className="admin-error" role="status">{notice}</p>}
        <form className="admin-login-form" onSubmit={submit}>
          <label htmlFor="admin-username">Staff username</label>
          <input id="admin-username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
          <label htmlFor="admin-password">Password</label>
          <input id="admin-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          {error && <p className="admin-error" role="alert">{error}</p>}
          <button className="btn admin-submit" disabled={busy}>{busy ? <LoaderCircle size={17} className="admin-spin" /> : <ShieldCheck size={17} />} Sign in securely</button>
        </form>
        <p className="admin-login-foot">Your staff credentials are checked securely by TUVA.</p>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value, note }) {
  return (
    <article className="admin-metric">
      <span className="admin-metric-icon"><Icon size={19} /></span>
      <span className="admin-metric-label">{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function AdminTable({ children, empty }) {
  return children && Children.count(children) > 0 ? <div className="admin-table-scroll"><table className="admin-table">{children}</table></div> :
    <div className="admin-empty"><PackageCheck size={22} /><span>{empty}</span></div>;
}

function ProductEditor({ product, saving, imageAction, onReplaceImage, onDeleteImage, onSave, onCancel }) {
  const imageInputRef = useRef(null);
  const [imageDropActive, setImageDropActive] = useState(false);
  const [imageError, setImageError] = useState("");
  const [formError, setFormError] = useState("");
  const [values, setValues] = useState(() => ({
    name: product?.name || "",
    subtitle: product?.subtitle || "",
    category: product?.category || "",
    use_cases: product?.use_cases || [],
    price: product?.price || product?.price_min || "",
    compare_price: product?.compare_price || "",
    stock: product ? String(product.stock ?? 0) : "",
    badge: product?.badge || "",
    specs: (product?.specs || []).join("\n"),
    images: [],
  }));
  const update = (field, value) => setValues((current) => ({ ...current, [field]: value }));
  const addImages = (files) => {
    const selected = Array.from(files || []);
    const imageFiles = selected.filter((file) => file.type.startsWith("image/"));
    update("images", [...values.images, ...imageFiles]);
    setImageError(imageFiles.length === selected.length ? "" : "Only image files can be added.");
  };
  const handlePaste = (event) => {
    const images = Array.from(event.clipboardData?.items || [])
      .filter((item) => item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter(Boolean);
    if (images.length) {
      event.preventDefault();
      addImages(images);
    }
  };
  const handleSubmit = (event) => {
    event.preventDefault();
    const price = Number(values.price);
    if (!/^\d+(?:\.\d{1,2})?$/.test(values.price) || !Number.isFinite(price) || price <= 0 || price >= 100_000_000) {
      setFormError("Enter a valid price greater than zero (up to two decimal places).");
      return;
    }
    const comparePrice = values.compare_price === "" ? null : Number(values.compare_price);
    if (comparePrice !== null && (!/^\d+(?:\.\d{1,2})?$/.test(values.compare_price) || !Number.isFinite(comparePrice) || comparePrice < price || comparePrice >= 100_000_000)) {
      setFormError("Compare price must be blank or at least the selling price (up to two decimal places).");
      return;
    }
    const stock = values.stock === "" ? 0 : Number(values.stock);
    if (!Number.isInteger(stock) || stock < 0 || stock > 1_000_000) {
      setFormError("Enter a whole-number stock quantity from 0 to 1,000,000.");
      return;
    }
    setFormError("");
    if (!product && !values.images.length) {
      setImageError("Add at least one product image.");
      return;
    }
    onSave({ ...values, stock: String(stock) });
  };

  return (
    <form className="admin-product-form" onSubmit={handleSubmit}>
      <div className="admin-product-form-heading"><strong>{product ? "Edit product" : "Add product"}</strong>
        <button type="button" className="admin-form-cancel" onClick={onCancel} aria-label="Cancel product editing"><X size={17} /></button></div>
      <label>Product name<input required maxLength={120} value={values.name} onChange={(event) => update("name", event.target.value)} /></label>
      <label>Subtitle<input maxLength={120} value={values.subtitle} onChange={(event) => update("subtitle", event.target.value)} /></label>
      <label>Category<input required maxLength={40} value={values.category} onChange={(event) => update("category", event.target.value)} /></label>
      <fieldset className="admin-product-use-cases">
        <legend>Suitable for <small>Select all that apply</small></legend>
        {productUseCases.map(({ id, name }) => <label key={id}>
          <input type="checkbox" checked={values.use_cases.includes(id)}
            onChange={(event) => update("use_cases", event.target.checked
              ? [...values.use_cases, id]
              : values.use_cases.filter((useCase) => useCase !== id))} />
          {name}
        </label>)}
      </fieldset>
      {formError && <p className="admin-product-form-error" role="alert">{formError}</p>}
      <label>Price (KSh)<input required type="text" inputMode="decimal" placeholder="0" value={values.price} onChange={(event) => { update("price", event.target.value); setFormError(""); }} /></label>
      <label>Compare price (optional)<input type="text" inputMode="decimal" placeholder="Leave blank for no sale price" value={values.compare_price} onChange={(event) => { update("compare_price", event.target.value); setFormError(""); }} /></label>
      <label>Stock<input type="text" inputMode="numeric" placeholder="0" value={values.stock} onChange={(event) => { update("stock", event.target.value); setFormError(""); }} /></label>
      <label>Badge<input maxLength={30} value={values.badge} onChange={(event) => update("badge", event.target.value)} /></label>
      <label className="admin-product-specs">Specifications <small>Enter one per line</small><textarea rows="3" value={values.specs} onChange={(event) => update("specs", event.target.value)} /></label>
      <div className="admin-product-image"><strong>Product images</strong><small>{product ? "Replace or remove existing images, or add more." : "Select one or more images."}</small>
        {product?.image_items?.length > 0 && <span className="admin-product-image-list">{product.image_items.map((image, index) => {
          const actionKey = `${image.id}`;
          const busy = Boolean(imageAction);
          return <span className="admin-product-image-item" key={actionKey}>
            <img src={image.url} alt={`${product.name} ${image.primary ? "main image" : `photo ${index + 1}`}`} />
            <small>{image.primary ? "Main image" : `Photo ${index + 1}`}</small>
            <span className="admin-product-image-actions">
              <label className="admin-image-replace">Replace<input type="file" accept="image/*" disabled={busy}
                onChange={(event) => { onReplaceImage(image.id, event.target.files?.[0]); event.target.value = ""; }} /></label>
              <button type="button" className="admin-image-delete" aria-label={`Delete ${product.name} ${image.primary ? "main image" : `photo ${index + 1}`}`}
                disabled={busy} onClick={() => onDeleteImage(image.id)}>{imageAction === `delete:${actionKey}` ? <LoaderCircle className="admin-spin" size={13} /> : <Trash2 size={13} />}</button>
            </span>
          </span>;
        })}</span>}
        <div className={`admin-image-dropzone${imageDropActive ? " active" : ""}`} role="group" tabIndex={0}
          aria-label="Add product images by dropping or pasting"
          onDragOver={(event) => { event.preventDefault(); setImageDropActive(true); }}
          onDragLeave={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) setImageDropActive(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setImageDropActive(false);
            addImages(event.dataTransfer.files);
          }}
          onPaste={handlePaste}>
          <input ref={imageInputRef} className="admin-image-file-input" type="file" accept="image/*" multiple
            onChange={(event) => { addImages(event.target.files); event.target.value = ""; }} />
          <span>Drop images here, or focus this area and paste with Ctrl+V</span>
          <button type="button" onClick={(event) => { event.stopPropagation(); imageInputRef.current?.click(); }}>Browse files</button>
        </div>
        {imageError && <small className="admin-image-error" role="alert">{imageError}</small>}
        {values.images.length > 0 && <span className="admin-product-image-pending">{values.images.map((image, index) =>
          <span key={`${image.name}-${index}`}>{image.name}<button type="button" aria-label={`Remove ${image.name}`} onClick={() =>
            { update("images", values.images.filter((_, fileIndex) => fileIndex !== index)); setImageError(""); }}><X size={12} /></button></span>)}</span>}
      </div>
      <div className="admin-product-form-actions"><button type="button" className="admin-form-cancel" onClick={onCancel}>Cancel</button>
        <button className="admin-save-stock" disabled={saving}>{saving ? <LoaderCircle className="admin-spin" size={15} /> : product ? "Save changes" : "Add product"}</button></div>
    </form>
  );
}

export default function AdminDashboard({ onClose }) {
  const [token, setToken] = useState(() => localStorage.getItem("tuva_admin_token") || "");
  const [staffName, setStaffName] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeSection, setActiveSection] = useState("Overview");
  const adminOverlayRef = useRef(null);
  const productEditorRef = useRef(null);
  const productScrollPosition = useRef(0);
  const [stockSaving, setStockSaving] = useState(null);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productSaving, setProductSaving] = useState(false);
  const [productDeleting, setProductDeleting] = useState(null);
  const [imageAction, setImageAction] = useState("");
  const [productQuery, setProductQuery] = useState("");
  const [productSearchResult, setProductSearchResult] = useState(null);
  const [productSearchBusy, setProductSearchBusy] = useState(false);
  const productSearchRequest = useRef(0);
  const productQueryRef = useRef("");
  productQueryRef.current = productQuery.trim();
  const [deleteConfirmation, setDeleteConfirmation] = useState(null);
  const [deleteConfirmationBusy, setDeleteConfirmationBusy] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState("");
  const [conversationMessages, setConversationMessages] = useState([]);
  const [reply, setReply] = useState("");
  const [replyBusy, setReplyBusy] = useState(false);

  const refresh = useCallback(async (authToken = token) => {
    if (!authToken) return;
    setBusy(true);
    setError("");
    try {
      const data = await api.adminDashboard(authToken);
      setDashboard(data);
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.status === 401 || requestError.status === 403) {
        localStorage.removeItem("tuva_admin_token");
        setToken("");
      }
    } finally {
      setBusy(false);
    }
  }, [token]);

  const refreshProductSearch = async () => {
    const query = productQuery.trim();
    if (!query) return;
    const result = await api.adminProducts(query, 0, token);
    if (productQueryRef.current === query) setProductSearchResult({ query, ...result });
  };

  useEffect(() => {
    if (token) refresh(token);
  }, []); // Load a previously authenticated staff session once.

  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === "Escape" && !event.target.closest?.('[role="alertdialog"]')) onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.classList.remove("modal-open");
    };
  }, [onClose]);

  useEffect(() => {
    if (!token || !selectedConversation) return undefined;
    let active = true;
    const loadMessages = async () => {
      try {
        const result = await api.adminConversation(selectedConversation, token);
        if (active) setConversationMessages(result.messages);
      } catch (requestError) {
        if (active) setError(requestError.message);
      }
    };
    loadMessages();
    const timer = window.setInterval(loadMessages, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [selectedConversation, token]);

  useEffect(() => {
    const query = productQuery.trim();
    if (!token || !query) {
      setProductSearchResult(null);
      setProductSearchBusy(false);
      return undefined;
    }
    let active = true;
    setProductSearchBusy(true);
    const timer = window.setTimeout(async () => {
      const requestId = ++productSearchRequest.current;
      try {
        const result = await api.adminProducts(query, 0, token);
        if (active && requestId === productSearchRequest.current) {
          setProductSearchResult({ query, ...result });
        }
      } catch (requestError) {
        if (active && requestId === productSearchRequest.current) {
          setError(requestError.message);
          if (requestError.status === 401 || requestError.status === 403) {
            localStorage.removeItem("tuva_admin_token");
            setToken("");
            setDashboard(null);
          }
        }
      } finally {
        if (active && requestId === productSearchRequest.current) setProductSearchBusy(false);
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
      productSearchRequest.current += 1;
    };
  }, [productQuery, token]);

  useEffect(() => {
    if (editingProduct) productEditorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [editingProduct]);

  const openProductEditor = (product = {}) => {
    productScrollPosition.current = adminOverlayRef.current?.scrollTop || 0;
    setEditingProduct(product);
  };
  const closeProductEditor = () => {
    setEditingProduct(null);
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        adminOverlayRef.current?.scrollTo({ top: productScrollPosition.current, behavior: "smooth" });
      });
    });
  };

  const login = async (username, password) => {
    const result = await api.adminLogin(username, password);
    localStorage.setItem("tuva_admin_token", result.token);
    setToken(result.token);
    setStaffName(result.name);
    await refresh(result.token);
  };

  const logout = async () => {
    const activeToken = token;
    setError("");
    localStorage.removeItem("tuva_admin_token");
    setToken("");
    setDashboard(null);
    setSelectedConversation("");
    setConversationMessages([]);
    setStaffName("");
    if (activeToken) {
      try {
        await api.logout(activeToken);
      } catch (requestError) {
        setError(`Signed out on this device, but the server session could not be revoked: ${requestError.message}`);
      }
    }
  };

  const saveStock = async (product) => {
    const stock = Number(product.stock);
    if (!Number.isInteger(stock) || stock < 0 || stock > 1_000_000) {
      setError("Enter a whole-number stock quantity between 0 and 1,000,000.");
      return;
    }
    setStockSaving(product.id);
    setError("");
    try {
      await api.adminUpdateStock(product.id, stock, token);
      await refresh(token);
      await refreshProductSearch();
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.status === 401 || requestError.status === 403) {
        localStorage.removeItem("tuva_admin_token");
        setToken("");
        setDashboard(null);
      }
    } finally {
      setStockSaving(null);
    }
  };

  const saveProduct = async (values) => {
    setProductSaving(true);
    setError("");
    const form = new FormData();
    ["name", "subtitle", "category", "price", "compare_price", "stock", "badge"].forEach((field) => {
      form.append(field, values[field]);
    });
    form.append("use_cases", JSON.stringify(values.use_cases));
    form.append("specs", JSON.stringify(values.specs.split("\n").map((spec) => spec.trim()).filter(Boolean)));
    values.images.forEach((image) => form.append("image_files", image));
    form.append("is_active", "true");
    try {
      if (editingProduct?.id) await api.adminUpdateProduct(editingProduct.id, form, token);
      else await api.adminCreateProduct(form, token);
      await refresh(token);
      await refreshProductSearch();
      closeProductEditor();
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.status === 401 || requestError.status === 403) {
        localStorage.removeItem("tuva_admin_token");
        setToken("");
        setDashboard(null);
      }
    } finally {
      setProductSaving(false);
    }
  };

  const updateProductImage = async (imageId, file) => {
    if (!editingProduct?.id || !file) return;
    setImageAction(`replace:${imageId}`);
    setError("");
    try {
      const updatedProduct = await api.adminUpdateProductImage(editingProduct.id, imageId, file, token);
      setEditingProduct((current) => current?.id === updatedProduct.id ? updatedProduct : current);
      await refresh(token);
      await refreshProductSearch();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setImageAction("");
    }
  };

  const loadMoreProducts = async () => {
    if (!productSearchResult || productSearchBusy) return;
    const { query, results } = productSearchResult;
    const requestId = ++productSearchRequest.current;
    setProductSearchBusy(true);
    setError("");
    try {
      const result = await api.adminProducts(query, results.length, token);
      if (requestId === productSearchRequest.current) {
        setProductSearchResult((current) => current?.query === query
          ? { ...current, results: [...current.results, ...result.results], count: result.count }
          : current);
      }
    } catch (requestError) {
      if (requestId === productSearchRequest.current) setError(requestError.message);
    } finally {
      if (requestId === productSearchRequest.current) setProductSearchBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirmation || deleteConfirmationBusy) return;
    const confirmation = deleteConfirmation;
    setDeleteConfirmationBusy(true);
    setError("");
    try {
      if (confirmation.type === "image") {
        setImageAction(`delete:${confirmation.imageId}`);
        const updatedProduct = await api.adminDeleteProductImage(
          confirmation.product.id,
          confirmation.imageId,
          token,
        );
        setEditingProduct((current) => current?.id === updatedProduct.id ? updatedProduct : current);
      } else {
        setProductDeleting(confirmation.product.id);
        await api.adminDeleteProduct(confirmation.product.id, token);
      }
      await refresh(token);
      await refreshProductSearch();
      setDeleteConfirmation(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setImageAction("");
      setProductDeleting(null);
      setDeleteConfirmationBusy(false);
    }
  };

  const sendReply = async (event) => {
    event.preventDefault();
    if (!reply.trim() || replyBusy) return;
    setReplyBusy(true);
    setError("");
    try {
      const message = await api.adminReply(selectedConversation, reply.trim(), token);
      setConversationMessages((messages) => [...messages, message]);
      setReply("");
      await refresh(token);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setReplyBusy(false);
    }
  };

  if (!token) return <div className="admin-overlay"><AdminLogin onLogin={login} onClose={onClose} notice={error} /></div>;
  if (!dashboard) return (
    <div className="admin-overlay admin-loading">
      {busy ? <><LoaderCircle className="admin-spin" size={28} /><span>Loading your store dashboard…</span></> :
        <><CircleAlert size={25} /><span>{error || "Your dashboard could not be loaded."}</span><button className="btn" onClick={() => refresh(token)}>Try again</button><button className="admin-loading-close" onClick={logout}>Sign out</button></>}
      <button className="admin-return-store" type="button" onClick={onClose}><ArrowLeft size={16} /> Back to TUVA storefront</button>
    </div>
  );

  const sections = ["Overview", "Products", "Orders", "Support"];
  const metrics = dashboard?.metrics;
  const productRows = productQuery.trim()
    ? (productSearchResult?.query === productQuery.trim() ? productSearchResult.results : [])
    : dashboard.products;

  return (
    <div className="admin-overlay" ref={adminOverlayRef}>
      <div className="admin-app" role="dialog" aria-modal="true" aria-label="TUVA store dashboard">
        <aside className="admin-sidebar">
          <a className="admin-brand" href="/" aria-label="Back to TUVA storefront" onClick={(event) => { event.preventDefault(); onClose(); }}><img src="/logo.png" alt="TUVA" /><span>STORE ADMIN</span></a>
          <p className="admin-side-label">WORKSPACE</p>
          <nav aria-label="Dashboard sections">
            {sections.map((section, index) => {
              const icons = [ChartNoAxesCombined, Boxes, ShoppingBag, Headset];
              const Icon = icons[index];
              return <button key={section} className={activeSection === section ? "active" : ""} onClick={() => setActiveSection(section)}>
                <Icon size={18} />{section}
                {section === "Support" && dashboard.conversations.length > 0 && <span className="admin-nav-count">{dashboard.conversations.length}</span>}
              </button>;
            })}
          </nav>
          <button className="admin-sidebar-home" type="button" onClick={onClose}><ArrowLeft size={16} /> Back to storefront</button>
          <div className="admin-sidebar-bottom"><ShieldCheck size={17} /><span>Staff access protected</span></div>
        </aside>

        <main className="admin-main">
          <header className="admin-topbar">
            <div className="admin-topbar-title"><button className="admin-mobile-back" onClick={onClose} aria-label="Back to storefront"><ArrowLeft size={19} /></button>
              <span className="admin-eyebrow">STORE MANAGEMENT</span><strong>{activeSection}</strong></div>
            <div className="admin-topbar-actions"><span className="admin-staff-name"><ShieldCheck size={15} />{staffName || "Staff account"}</span>
              <button onClick={() => refresh(token)} disabled={busy} aria-label="Refresh dashboard"><RefreshCw className={busy ? "admin-spin" : ""} size={17} /></button>
              <button onClick={logout} aria-label="Sign out"><LogOut size={17} /><span>Sign out</span></button>
              <button onClick={onClose} aria-label="Close dashboard"><X size={19} /></button>
            </div>
          </header>

          <section className="admin-content">
            {error && <div className="admin-error-banner" role="alert"><CircleAlert size={17} />{error}</div>}
            {activeSection === "Overview" && metrics && <>
              <div className="admin-welcome"><div><p className="admin-eyebrow">YOUR STORE AT A GLANCE</p><h1>Good to have you back{staffName ? `, ${staffName}` : ""}.</h1><p>Here’s what’s happening with TUVA today.</p></div>
                <span className="admin-welcome-icon"><ChartNoAxesCombined size={25} /></span></div>
              <div className="admin-metrics">
                <Metric icon={Boxes} label="Products" value={metrics.products} note={`${metrics.in_stock} currently in stock`} />
                <Metric icon={ShoppingBag} label="Orders" value={metrics.orders} note={`${metrics.pending_orders} awaiting payment`} />
              <Metric icon={ChartNoAxesCombined} label="Paid sales" value={money(metrics.paid_revenue)} note="Catalog value in KSh" />
                <Metric icon={CircleAlert} label="Stock alerts" value={metrics.open_alerts} note={`${metrics.low_stock} products running low`} />
              </div>
              <div className="admin-overview-grid">
                <section className="admin-panel"><div className="admin-panel-heading"><div><h2>Recent orders</h2><p>Your latest customer checkouts</p></div><button onClick={() => setActiveSection("Orders")}>View all <ArrowDownToLine size={15} /></button></div>
                  <AdminTable empty="No orders yet. New checkouts will appear here.">{dashboard.orders.length > 0 && <>
                    <thead><tr><th>ORDER</th><th>PRODUCT</th><th>AMOUNT</th><th>STATUS</th></tr></thead><tbody>
                      {dashboard.orders.slice(0, 5).map((order) => <tr key={order.id}><td>#{order.id}<small>{date(order.created)}</small></td><td>{order.product}<small>{order.customer}</small></td><td>{money(order.amount)}</td><td><span className={`admin-status ${order.status}`}>{order.status}</span></td></tr>)}
                    </tbody>
                  </>}</AdminTable>
                </section>
                <section className="admin-panel"><div className="admin-panel-heading"><div><h2>Needs attention</h2><p>Customers waiting for a product</p></div><span className="admin-count-pill">{dashboard.alerts.length}</span></div>
                  {dashboard.alerts.length ? <ul className="admin-alert-list">{dashboard.alerts.slice(0, 5).map((alert) => <li key={alert.id}><span className="admin-alert-icon"><CircleAlert size={16} /></span><span><strong>{alert.query}</strong><small>{alert.email} · {date(alert.created)}</small></span></li>)}</ul> : <div className="admin-empty"><PackageCheck size={22} /><span>No outstanding stock alerts.</span></div>}
                </section>
              </div>
            </>}

            {activeSection === "Products" && <section className="admin-panel admin-full-panel"><div className="admin-panel-heading"><div><h2>Product inventory</h2><p>Add, edit, or remove products and update their stock.</p></div><div className="admin-products-heading"><span className="admin-count-pill">{productQuery.trim() ? (productSearchResult?.query === productQuery.trim() ? `${productSearchResult.count} found` : "Searching…") : `${dashboard.metrics.products} products`}</span><button className="admin-save-stock" onClick={() => openProductEditor()}><Plus size={14} /> Add product</button></div></div>
              <div className="admin-product-search"><Search size={17} /><input type="search" value={productQuery} placeholder="Search products by name, category, brand, or SKU"
                aria-label="Search products in inventory" onChange={(event) => setProductQuery(event.target.value)} />
                {productQuery && <button type="button" aria-label="Clear product search" onClick={() => setProductQuery("")}><X size={15} /></button>}
              </div>
              {editingProduct && <div ref={productEditorRef} className="admin-product-editor-anchor"><ProductEditor key={editingProduct.id || "new"} product={editingProduct.id ? editingProduct : null} saving={productSaving} imageAction={imageAction} onReplaceImage={updateProductImage} onDeleteImage={(imageId) => setDeleteConfirmation({ type: "image", product: editingProduct, imageId })} onSave={saveProduct} onCancel={closeProductEditor} /></div>}
              {productSearchBusy && (!productSearchResult || productSearchResult.query !== productQuery.trim()) &&
                <div className="admin-product-search-state"><LoaderCircle className="admin-spin" size={17} /> Searching products…</div>}
              <AdminTable empty={productQuery.trim() ? "No products match your search." : "No products found."}>{productRows.length > 0 && <>
                <thead><tr><th>PRODUCT</th><th>CATEGORY</th><th>PRICE</th><th>AVAILABLE STOCK</th><th>ACTIONS</th></tr></thead><tbody>
                  {productRows.map((product) => <tr key={product.id}><td><span className="admin-product-cell"><img src={product.image} alt="" /><span><strong>{product.name}</strong><small>{product.subtitle}</small></span></span></td><td>{product.category}</td><td>{money(product.price_min)}</td>
                    <td><input className="admin-stock-input" type="text" inputMode="numeric" aria-label={`${product.name} stock`} value={product.stock} onChange={(event) => {
                      setDashboard((current) => ({ ...current, products: current.products.map((item) => item.id === product.id ? { ...item, stock: event.target.value } : item) }));
                      setProductSearchResult((current) => current ? { ...current, results: current.results.map((item) => item.id === product.id ? { ...item, stock: event.target.value } : item) } : current);
                    }} /></td>
                    <td><div className="admin-product-actions"><button className="admin-save-stock" disabled={stockSaving === product.id} onClick={() => saveStock(product)}>{stockSaving === product.id ? <LoaderCircle className="admin-spin" size={15} /> : "Save stock"}</button>
                      <button className="admin-icon-action" aria-label={`Edit ${product.name}`} onClick={() => openProductEditor(product)}><Edit2 size={15} /></button>
                      <button className="admin-icon-action danger" aria-label={`Delete ${product.name}`} disabled={productDeleting === product.id} onClick={() => setDeleteConfirmation({ type: "product", product })}>{productDeleting === product.id ? <LoaderCircle className="admin-spin" size={15} /> : <Trash2 size={15} />}</button></div></td>
                  </tr>)}
                </tbody>
              </>}</AdminTable>
              {productSearchResult?.query === productQuery.trim() && productSearchResult.results.length < productSearchResult.count &&
                <button className="admin-load-more-products" type="button" onClick={loadMoreProducts} disabled={productSearchBusy}>
                  {productSearchBusy ? <LoaderCircle className="admin-spin" size={15} /> : null}
                  {productSearchBusy ? "Loading…" : `Load more (${productSearchResult.results.length} of ${productSearchResult.count})`}
                </button>}
            </section>}

            {activeSection === "Orders" && <section className="admin-panel admin-full-panel"><div className="admin-panel-heading"><div><h2>Customer orders</h2><p>Latest M-PESA checkouts and payment status.</p></div><span className="admin-count-pill">{dashboard.orders.length} recent</span></div>
              <AdminTable empty="No orders yet. New checkouts will appear here.">{dashboard.orders.length > 0 && <>
                <thead><tr><th>ORDER</th><th>CUSTOMER</th><th>PRODUCT</th><th>QTY</th><th>AMOUNT (KSh)</th><th>PAYMENT</th><th>STATUS</th></tr></thead><tbody>
                  {dashboard.orders.map((order) => <tr key={order.id}><td>{order.reference || `#${order.id}`}<small>{date(order.created)}</small></td><td>{order.customer}</td><td>{order.product}</td><td>{order.quantity}</td><td>{money(order.amount)}</td><td>{order.payment_amount ? `KES ${Number(order.payment_amount).toLocaleString()}` : "—"}</td><td><span className={`admin-status ${order.status}`}>{order.status}</span><small>Payment: {order.payment_status}</small></td></tr>)}
                </tbody>
              </>}</AdminTable>
            </section>}

            {activeSection === "Support" && <div className="admin-support-layout">
              <section className="admin-panel admin-inbox"><div className="admin-panel-heading"><div><h2>Support inbox</h2><p>Recent storefront conversations</p></div></div>
                {dashboard.conversations.length ? <div className="admin-conversation-list">{dashboard.conversations.map((conversation) => <button key={conversation.conversation} className={conversation.conversation === selectedConversation ? "selected" : ""} onClick={() => setSelectedConversation(conversation.conversation)}>
                  <span className="admin-conversation-avatar">{conversation.sender === "customer" ? "C" : "T"}</span><span><strong>{conversation.sender === "customer" ? "Customer" : "TUVA support"}</strong><small>{conversation.message}</small><small>{date(conversation.updated)}</small></span>
                </button>)}</div> : <div className="admin-empty"><Headset size={22} /><span>No customer conversations yet.</span></div>}
              </section>
              <section className="admin-panel admin-thread">
                {selectedConversation ? <>
                  <div className="admin-panel-heading"><div><h2>Conversation</h2><p>Reply from the TUVA support team</p></div></div>
                  <div className="admin-thread-messages" aria-live="polite">{conversationMessages.map((message) => <p key={message.id} className={`admin-chat-bubble ${message.sender}`}><span>{message.sender === "customer" ? "Customer" : "TUVA support"}</span>{message.message}<small>{date(message.created)}</small></p>)}</div>
                  <form className="admin-reply-form" onSubmit={sendReply}><input aria-label="Reply to customer" maxLength={2000} value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Write a helpful reply…" /><button className="btn" aria-label="Send reply" disabled={replyBusy || !reply.trim()}>{replyBusy ? <LoaderCircle className="admin-spin" size={17} /> : <Send size={16} />}</button></form>
                </> : <div className="admin-thread-empty"><Headset size={25} /><strong>Select a conversation</strong><span>Choose a customer message to read and reply.</span></div>}
              </section>
            </div>}
          </section>
        </main>
      </div>
      {deleteConfirmation && <DeleteConfirmation
        type={deleteConfirmation.type}
        itemName={deleteConfirmation.product.name}
        busy={deleteConfirmationBusy}
        onCancel={() => setDeleteConfirmation(null)}
        onConfirm={confirmDelete}
      />}
    </div>
  );
}

function DeleteConfirmation({ type, itemName, busy, onCancel, onConfirm }) {
  const cancelButtonRef = useRef(null);
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);
  const cancelRef = useRef(onCancel);
  const busyRef = useRef(busy);
  const titleId = "admin-delete-confirmation-title";
  const descriptionId = "admin-delete-confirmation-description";
  const isImage = type === "image";
  cancelRef.current = onCancel;
  busyRef.current = busy;

  useEffect(() => {
    previousFocusRef.current = document.activeElement;
    cancelButtonRef.current?.focus();
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        if (!busyRef.current) cancelRef.current();
      } else if (event.key === "Tab") {
        const focusable = [...dialogRef.current.querySelectorAll("button:not(:disabled)")];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (previousFocusRef.current?.isConnected) previousFocusRef.current.focus();
    };
  }, []);

  return (
    <div className="admin-confirm-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busyRef.current) cancelRef.current();
    }}>
      <section ref={dialogRef} className="admin-confirm-dialog" role="alertdialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={descriptionId}>
        <button className="admin-confirm-close" type="button" aria-label="Close confirmation"
          disabled={busy} onClick={onCancel}><X size={18} /></button>
        <span className="admin-confirm-icon"><Trash2 size={21} /></span>
        <span className="admin-confirm-eyebrow">PLEASE CONFIRM</span>
        <h2 id={titleId}>{isImage ? "Delete this image?" : "Delete this product?"}</h2>
        <p id={descriptionId}>{isImage
          ? <>The selected image for <strong>{itemName}</strong> will be permanently removed.</>
          : <> <strong>{itemName}</strong> will be removed from your active inventory. This action cannot be undone.</>}</p>
        <div className="admin-confirm-actions">
          <button ref={cancelButtonRef} type="button" className="admin-confirm-cancel"
            disabled={busy} onClick={onCancel}>Keep {isImage ? "image" : "product"}</button>
          <button type="button" className="admin-confirm-delete" disabled={busy} onClick={onConfirm}>
            {busy ? <><LoaderCircle className="admin-spin" size={15} /> Deleting…</> : <><Trash2 size={15} /> Delete {isImage ? "image" : "product"}</>}
          </button>
        </div>
      </section>
    </div>
  );
}
