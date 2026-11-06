import { useCallback, useEffect, useId, useRef, useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { createPortal } from "react-dom";
import {
  ArrowUp,
  BadgeCheck,
  BellRing,
  Box,
  BriefcaseBusiness,
  Building2,
  Camera,
  Check,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleHelp,
  Download,
  Gamepad2,
  Globe2,
  Grid2X2,
  Headphones,
  House,
  LaptopMinimal,
  Languages,
  LockKeyhole,
  LoaderCircle,
  LogOut,
  MapPin,
  Menu,
  MessageCircle,
  MessageSquare,
  Minus,
  Package,
  PackageCheck,
  Percent,
  Plus,
  Search,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Store,
  Tag,
  Tablet,
  Truck,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { siWhatsapp } from "simple-icons";
import { api } from "./api";
import AdminDashboard from "./AdminDashboard";

const categories = [
  { name: "Business", id: "business", icon: "briefcase", hint: "Reliable for work" },
  { name: "Gaming", id: "gaming", icon: "gaming", hint: "High performance" },
  { name: "Ultrabooks", id: "ultrabooks", icon: "laptop", hint: "Thin, light, powerful" },
  { name: "2-in-1 laptops", id: "2-in-1", icon: "tablet", hint: "Flexible productivity" },
  { name: "Accessories", id: "accessories", icon: "headphones", hint: "Make it complete" },
];
const PRODUCT_PAGE_SIZE = 48;
const money = (value) => value == null ? "Price unavailable" : `KSh ${Number(value).toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const productIdFromPath = () => window.location.pathname.match(/^\/products\/(\d+)\/?$/)?.[1] || null;
const isCatalogPath = () => /^\/products\/?$/.test(window.location.pathname);
const isAdminPath = () => /^\/admin\/?$/.test(window.location.pathname);

function Icon({ name, size = 22, className = "", strokeWidth = 1.8 }) {
  const icons = {
    badge: BadgeCheck,
    box: Box,
    briefcase: BriefcaseBusiness,
    building: Building2,
    camera: Camera,
    cart: ShoppingCart,
    check: CircleCheck,
    chevronDown: ChevronDown,
    chevronRight: ChevronRight,
    circleHelp: CircleHelp,
    delivery: PackageCheck,
    download: Download,
    gaming: Gamepad2,
    globe: Globe2,
    grid: Grid2X2,
    headphones: Headphones,
    home: House,
    laptop: LaptopMinimal,
    languages: Languages,
    location: MapPin,
    loading: LoaderCircle,
    lock: LockKeyhole,
    menu: Menu,
    message: MessageSquare,
    package: Package,
    percent: Percent,
    search: Search,
    shieldCheck: ShieldCheck,
    bag: ShoppingBag,
    sparkle: Sparkles,
    store: Store,
    tablet: Tablet,
    tag: Tag,
    truck: Truck,
    user: UserRound,
    chat: MessageCircle,
  };
  if (name === "whatsapp") {
    return <svg aria-hidden="true" className={`svg-icon whatsapp-mark ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d={siWhatsapp.path} />
    </svg>;
  }
  const LucideIcon = icons[name];
  if (!LucideIcon) return null;
  return <LucideIcon aria-hidden="true" className={`svg-icon icon-${name} ${className}`} size={size} strokeWidth={strokeWidth} />;
}

function ProductCard({ product, onAdd, onOpen }) {
  const images = product.images?.length ? product.images : product.image ? [product.image] : [];
  const [selectedImage, setSelectedImage] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  const changeImage = (index) => {
    setSelectedImage(index);
    setImageFailed(false);
  };

  return (
    <article className="product-card">
      {product.badge && <span className="badge">{product.badge}</span>}
      <button className="product-image" type="button" onClick={() => onOpen(product)}
        aria-label={`View ${product.name} details`}>
        {images.length > 0 && !imageFailed ? <img key={images[selectedImage]} src={images[selectedImage]} alt={product.name}
          loading="lazy" onError={() => setImageFailed(true)} /> : <span className="product-image-unavailable">Image unavailable</span>}
        {images.length > 1 && <span className="product-image-count">{images.length} photos · view details</span>}
      </button>
      {images.length > 1 && <div className="product-image-thumbnails" aria-label={`${product.name} photos`}>
        {images.map((image, index) => <button key={`${image}-${index}`} type="button"
          className={index === selectedImage ? "selected" : ""} onClick={() => changeImage(index)}
          aria-label={`Show ${product.name} photo ${index + 1}`} aria-pressed={index === selectedImage}>
          <img src={image} alt="" loading="lazy" onError={(event) => { event.currentTarget.hidden = true; }} />
        </button>)}
      </div>}
      <div className="product-info">
        <button className="product-title product-title-link" type="button" onClick={() => onOpen(product)}>
          <h3>{product.name}</h3><span className="supplier-check" title="Verified supplier"><Check size={10} strokeWidth={3} /></span>
        </button>
        <p className="product-subtitle">{product.subtitle}</p>
        <p className="price">{money(product.price_min_kes)}</p>
        <p className="verified"><BadgeCheck size={12} aria-hidden="true" /> Verified supplier</p>
      </div>
      <div className="specs">{(product.specs || []).slice(0, 4).map((spec) => <span key={spec}>{spec}</span>)}</div>
      <div className="card-bottom">
        <span className={product.in_stock ? "stock-label" : "stock-label unavailable"}>
          {product.in_stock ? "In stock" : "Currently unavailable"}
        </span>
        <button className={`btn card-cta${product.in_stock ? "" : " notify-cta"}`}
          aria-label={product.in_stock ? `Add ${product.name} to cart` : `Get notified when ${product.name} is back in stock`}
          onClick={() => product.in_stock ? onAdd(product) : onOpen(product, true)}>
          {product.in_stock ? "Add to cart" : "Notify me"}
        </button>
      </div>
    </article>
  );
}

function ProductDetailPage({ productId, initialProduct, openNotifyOnLoad = false, onBack, onAdd, onBuyNow, onContact }) {
  const [product, setProduct] = useState(initialProduct || null);
  const [loading, setLoading] = useState(!initialProduct);
  const [error, setError] = useState("");
  const [selectedImage, setSelectedImage] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerImagesExpanded, setViewerImagesExpanded] = useState(false);
  const [viewerZoomed, setViewerZoomed] = useState(false);
  const availabilityAlertRef = useRef(null);
  const images = product?.images?.length ? product.images : product?.image ? [product.image] : [];
  const viewerStripStart = Math.min(Math.max(selectedImage - 3, 0), Math.max(images.length - 4, 0));
  const viewerStripImages = images.slice(viewerStripStart, viewerStripStart + 4);

  useEffect(() => {
    let active = true;
    if (initialProduct) {
      setProduct(initialProduct);
      setLoading(false);
      setError("");
      return () => { active = false; };
    }
    setLoading(true);
    setError("");
    api.product(productId).then((result) => {
      if (active) setProduct(result);
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [productId, initialProduct]);

  useEffect(() => {
    setSelectedImage(0);
    setQuantity(1);
    setViewerImagesExpanded(false);
  }, [productId]);

  useEffect(() => setViewerZoomed(false), [selectedImage]);

  useEffect(() => {
    if (!loading && !error && product && !product.in_stock && openNotifyOnLoad) {
      const timer = window.setTimeout(() => {
        availabilityAlertRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 80);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [error, loading, openNotifyOnLoad, product]);

  useEffect(() => {
    if (!viewerOpen || images.length < 2) return undefined;
    const handleKeys = (event) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setSelectedImage((index) => (index + images.length - 1) % images.length);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setSelectedImage((index) => (index + 1) % images.length);
      }
    };
    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, [viewerOpen, images.length]);

  useEffect(() => {
    if (!product) return undefined;
    const previousTitle = document.title;
    document.title = `${product.name} | TUVA`;
    return () => { document.title = previousTitle; };
  }, [product?.name]);

  if (loading) {
    return <main className="storefront product-page"><div className="product-detail-loading" role="status">Loading product details…</div></main>;
  }
  if (error || !product) {
    return <main className="storefront product-page"><section className="product-detail-error" role="alert">
      <Package size={28} /><h1>We couldn’t load this product</h1><p>{error || "This product is no longer available."}</p>
      <button className="btn" onClick={onBack}>Back to laptops</button>
    </section></main>;
  }

  const setImage = (index) => setSelectedImage((index + images.length) % images.length);
  const comparisonPrice = Number(product.price_max_kes) > Number(product.price_min_kes) ? product.price_max_kes : null;

  return (
    <main className="storefront product-page">
      <nav className="product-breadcrumbs" aria-label="Breadcrumb">
        <button type="button" onClick={onBack}><House size={14} /> Home</button><ChevronRight size={14} />
        <span>Computers &amp; Office</span><ChevronRight size={14} /><span>{product.category || "Products"}</span>
        <ChevronRight size={14} /><strong>{product.name}</strong>
      </nav>

      <div className="product-detail-layout">
        <section className="product-gallery" aria-label={`${product.name} product photos`}>
          <div className="product-gallery-thumbnails">
            {images.map((image, index) => <button key={`${image}-${index}`} type="button"
              className={index === selectedImage ? "selected" : ""} onClick={() => setImage(index)}
              aria-label={`Show product photo ${index + 1}`} aria-pressed={index === selectedImage}>
              <img src={image} alt="" />
            </button>)}
          </div>
          <div className="product-gallery-main">
            {images.length > 0 ? <button className="product-gallery-zoom" type="button"
              onClick={() => setViewerOpen(true)} aria-label="Open product photo gallery">
              <img src={images[selectedImage]} alt={product.name} />
              {images.length > 1 && <span>{selectedImage + 1} / {images.length} · View photos</span>}
            </button> : <div className="product-gallery-unavailable"><Package size={42} /><span>Product image coming soon</span></div>}
            {images.length > 1 && <>
              <button className="product-gallery-arrow previous" type="button" aria-label="Previous photo"
                onClick={() => setImage(selectedImage - 1)}><ChevronLeft size={20} /></button>
              <button className="product-gallery-arrow next" type="button" aria-label="Next photo"
                onClick={() => setImage(selectedImage + 1)}><ChevronRight size={20} /></button>
            </>}
          </div>
        </section>

        <section className="product-detail-info">
          <span className="product-category-pill">{product.category || "TUVA product"}</span>
          <h1>{product.name}</h1>
          {product.subtitle && <p className="product-detail-subtitle">{product.subtitle}</p>}
          <div className="product-detail-trust"><span><BadgeCheck size={16} /> Verified supplier</span>
            <span className={product.in_stock ? "available" : "unavailable"}><i />{product.in_stock ? "In stock" : "Currently unavailable"}</span></div>
          <div className="product-detail-price">
            <strong>{money(product.price_min_kes)}</strong>
            {comparisonPrice && <del>{money(comparisonPrice)}</del>}
            <span>Price shown in Kenyan shillings</span>
          </div>
          {product.specs?.length > 0 && <section className="product-key-features">
            <h2>Key features</h2><ul>{product.specs.slice(0, 6).map((spec) =>
              <li key={spec}><Check size={15} />{spec}</li>)}</ul>
          </section>}
          <div className="product-buy-row">
            <span>Quantity</span>
            <div className="product-quantity">
              <button type="button" aria-label="Decrease quantity" disabled={quantity <= 1}
                onClick={() => setQuantity((value) => Math.max(1, value - 1))}><Minus size={16} /></button>
              <span aria-live="polite">{quantity}</span>
              <button type="button" aria-label="Increase quantity" onClick={() => setQuantity((value) => value + 1)}><Plus size={16} /></button>
            </div>
          </div>
          <div className="product-detail-actions">
            {product.in_stock ? <>
              <button type="button" className="btn product-add-button"
                onClick={() => onAdd(product, quantity)}><ShoppingCart size={18} /> Add to cart</button>
              <button type="button" className="product-buy-button"
                onClick={() => onBuyNow(product, quantity)}>Buy now <ChevronRight size={18} /></button>
            </> : <button type="button" className="btn product-notify-button"
              aria-label={`Notify me when ${product.name} is available`}
              onClick={() => availabilityAlertRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}>
              <BellRing size={18} /> Notify me when available
            </button>}
          </div>
          {!product.in_stock && <p className="product-stock-note">Currently unavailable. Leave your email and we’ll notify you when it’s back.</p>}
          {!product.in_stock && <div ref={availabilityAlertRef} className="product-availability-alert">
            <AvailabilityAlert query={product.name} productName={product.name} userEmail={localStorage.getItem("tuva_email") || ""} />
          </div>}
          <div className="product-assurances">
            <span><ShieldCheck size={18} /><span><strong>Secure checkout</strong><small>Protected M-PESA payment</small></span></span>
            <span><Truck size={18} /><span><strong>Delivery options</strong><small>Confirmed at checkout</small></span></span>
            <span><MessageCircle size={18} /><span><strong>Need help?</strong><small>Talk to our team</small></span></span>
          </div>
        </section>

        <aside className="product-seller-card">
          <div className="product-seller-heading"><span className="product-seller-mark">T</span><span><strong>Sold by TUVA Stores</strong><small><BadgeCheck size={13} /> Verified supplier</small></span><ChevronRight size={17} /></div>
          <div className="product-seller-message"><strong>Shopping with confidence</strong><p>Our team is here to help with product questions, delivery, and checkout.</p></div>
          <button type="button" className="product-contact-button" onClick={onContact}><MessageCircle size={16} /> Contact TUVA</button>
          <div className="product-shipping-card"><strong><MapPin size={16} /> Delivery in Kenya</strong>
            <p>Available delivery and collection options are shown during checkout.</p>
            <span><Truck size={16} /> Delivery details confirmed with your order</span>
          </div>
        </aside>
      </div>

      <section className="product-more-details">
        <nav aria-label="Product information">
          <a href="#product-description">Product details</a>
          {product.specs?.length > 0 && <a href="#product-specifications">Specifications</a>}
          <a href="#product-shipping">Shipping &amp; payment</a>
        </nav>
        <div className="product-detail-columns">
          <section id="product-description"><h2>Product details</h2>
            <p>{product.subtitle || `${product.name} is available from TUVA Stores. Contact us if you need help choosing the right product.`}</p>
          </section>
          {product.specs?.length > 0 && <section id="product-specifications"><h2>Specifications</h2>
            <ul>{product.specs.map((spec) => <li key={spec}>{spec}</li>)}</ul>
          </section>}
          <section id="product-shipping"><h2>Shipping &amp; payment</h2>
            <p>Choose an available delivery or collection option during checkout. Pay securely with M-PESA.</p>
          </section>
        </div>
      </section>

      {viewerOpen && <Modal title={`${product.name} photos`} onClose={() => setViewerOpen(false)} className="product-image-dialog">
        <div className="product-viewer">
          <div className="product-viewer-rail" aria-label="Product photos">
            {images.slice(0, viewerImagesExpanded ? images.length : 6).map((image, index) => <button key={`${image}-${index}`}
              type="button" className={index === selectedImage ? "selected" : ""} onClick={() => setImage(index)}
              aria-label={`Show photo ${index + 1}`} aria-pressed={index === selectedImage}>
              <img src={image} alt="" />
            </button>)}
            {!viewerImagesExpanded && images.length > 6 && <button type="button" className="product-viewer-more"
              onClick={() => setViewerImagesExpanded(true)} aria-label={`Show ${images.length - 6} more photos`}>
              +{images.length - 6}
            </button>}
          </div>
          <div className="product-viewer-stage" onWheel={(event) => {
            if (event.deltaY !== 0) setViewerZoomed(event.deltaY < 0);
          }}>
            <img className={viewerZoomed ? "zoomed" : ""} src={images[selectedImage]}
              alt={`${product.name}, photo ${selectedImage + 1} of ${images.length}`} />
            {images.length > 1 && <>
              <button type="button" className="product-viewer-arrow previous" aria-label="Previous photo"
                onClick={() => setImage(selectedImage - 1)}><ChevronLeft size={28} /></button>
              <button type="button" className="product-viewer-arrow next" aria-label="Next photo"
                onClick={() => setImage(selectedImage + 1)}><ChevronRight size={28} /></button>
            </>}
            <button type="button" className="product-viewer-zoom" aria-pressed={viewerZoomed}
              onClick={() => setViewerZoomed((zoomed) => !zoomed)}>
              <Search size={16} /> {viewerZoomed ? "Zoom out" : "Zoom in"} <span>(or scroll)</span>
            </button>
            <span className="product-viewer-count">{selectedImage + 1} / {images.length}</span>
          </div>
          <aside className="product-viewer-details">
            <h2>{product.name}</h2>
            {images.length > 1 && <div className="product-viewer-strip" aria-label="Choose a product photo">
              {viewerStripImages.map((image, offset) => {
                const index = viewerStripStart + offset;
                return <button key={`${image}-${index}`} type="button"
                  className={index === selectedImage ? "selected" : ""} onClick={() => setImage(index)}
                  aria-label={`Show photo ${index + 1}`} aria-pressed={index === selectedImage}>
                <img src={image} alt="" />
                </button>;
              })}
            </div>}
          </aside>
        </div>
      </Modal>}
    </main>
  );
}

function AvailabilityAlert({ query, userEmail, productName = "" }) {
  const [email, setEmail] = useState(userEmail || "");
  const [consent, setConsent] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => setEmail(userEmail || ""), [userEmail, query]);
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api.alert(email, productName || query, consent);
      setMessage(productName
        ? `You're on the list. We'll email you at ${email} when ${productName} is back in stock.`
        : "You're on the list. We'll email you when a match is available.");
      setEmail(userEmail || "");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="alert-card" onSubmit={submit}>
      <div><span className="eyebrow">STOCK ALERT</span><h3>{productName ? "Get notified when it’s back" : `Still looking for “${query}”?`}</h3>
        <p>{productName ? `Leave your email and we’ll let you know when ${productName} is available.` : "Leave your email and we’ll let you know when it’s available."}</p></div>
      <div className="alert-form"><input type="email" required autoComplete="email" placeholder="Your email address" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button className="btn" disabled={busy}>{busy ? "Saving…" : "Notify me"}</button></div>
      <label className="alert-consent"><input type="checkbox" required checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Email me when a matching item is available. I can unsubscribe at any time.</label>
      {message && <p className="form-message" role="status">{message}</p>}
    </form>
  );
}

function Modal({ title, onClose, children, className = "" }) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    const focusable = () => [...dialog.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')];
    (focusable()[0] || dialog).focus();
    const handleKeys = (event) => {
      if (document.querySelectorAll('[role="dialog"]').item(document.querySelectorAll('[role="dialog"]').length - 1) !== dialog) return;
      if (event.key === "Escape") {
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) { event.preventDefault(); dialog.focus(); return; }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    };
    document.addEventListener("keydown", handleKeys);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", handleKeys);
      document.body.classList.remove("modal-open");
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, []);
  return createPortal((
    <div className={`modal-backdrop${["cart-dialog", "checkout-dialog"].includes(className) ? " cart-backdrop" : ""}${className === "product-image-dialog" ? " product-image-backdrop" : ""}`}
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section ref={dialogRef} className={`dialog ${className}`} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
        <div className="dialog-heading"><div><span className="eyebrow">TUVA</span><h2 id={titleId}>{title}</h2></div>
          <button className="icon-button close-button" aria-label="Close" onClick={onClose}><X size={19} /></button></div>
        {children}
      </section>
    </div>
  ), document.body);
}

function SignIn({ onSignedIn, onClose }) {
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "").trim();
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");
    if (mode === "register" && password !== form.get("confirmPassword")) {
      setError("Your passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = mode === "register" ? await api.register(name, email, password) : await api.login(email, password);
      localStorage.setItem("tuva_token", result.token);
      localStorage.setItem("tuva_user", result.name || result.email);
      localStorage.setItem("tuva_email", result.email || email);
      onSignedIn(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={mode === "login" ? "Welcome back" : "Create your account"} onClose={onClose} className="signin-dialog">
      <p className="dialog-copy">{mode === "login" ? "Sign in to continue to a faster, more personal checkout." : "Create an account to save your details and check out securely."}</p>
      <form className="auth-form" onSubmit={submit}>
        {mode === "register" && <label htmlFor="account-name">Your name<input id="account-name" name="name" autoComplete="name" maxLength={150} required /></label>}
        <label htmlFor="account-email">Email address<input id="account-email" name="email" type="email" autoComplete="email" maxLength={150} required /></label>
        <label htmlFor="account-password">Password<input id="account-password" name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} required /></label>
        {mode === "register" && <label htmlFor="account-confirm-password">Confirm password<input id="account-confirm-password" name="confirmPassword" type="password" autoComplete="new-password" minLength={8} required /></label>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="btn auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in with email" : "Create account"}</button>
      </form>
      <button className="auth-mode-toggle" type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
        {mode === "login" ? "New to TUVA? Create an account" : "Already have an account? Sign in"}
      </button>
      <div className="auth-divider"><span>or</span></div>
      {googleClientId ? <GoogleLogin onSuccess={async (credential) => {
        try {
          const user = await api.google(credential.credential);
          localStorage.setItem("tuva_token", user.token);
          localStorage.setItem("tuva_user", user.name || user.email);
          localStorage.setItem("tuva_email", user.email || "");
          onSignedIn(user);
        } catch (error) {
          setError(error.message);
        }
      }} onError={() => setError("Google sign-in could not be completed.")} text="continue_with" theme="outline" size="medium" shape="rectangular" logo_alignment="left" width={Math.min(400, Math.max(200, window.innerWidth - 80))} useOneTap={false} containerProps={{ className: "google-login-button" }} /> :
        <div className="setup-notice">Google sign-in is unavailable right now. You can use your email and password above.</div>}
      <p className="security-note">Your account details are protected. Choose the sign-in method that works for you.</p>
    </Modal>
  );
}

function Checkout({ product, quantity, user, userEmail, onClose, onSignIn, onPaid, whatsappNumber }) {
  const checkoutKey = useRef(crypto.randomUUID());
  const [phone, setPhone] = useState(() => {
    const token = localStorage.getItem("tuva_token");
    return token ? localStorage.getItem(`tuva_mpesa_phone:${token}`) || "" : "";
  });
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeOrder, setActiveOrder] = useState(null);
  const [paymentComplete, setPaymentComplete] = useState(false);
  const [quote, setQuote] = useState(null);
  const [quoteError, setQuoteError] = useState("");
  const [guestCheckoutEnabled, setGuestCheckoutEnabled] = useState(false);
  const [guestName, setGuestName] = useState(() => localStorage.getItem("tuva_user") || "");
  const [guestEmail, setGuestEmail] = useState(() => userEmail || localStorage.getItem("tuva_email") || "");
  const [guestAccessToken, setGuestAccessToken] = useState("");
  const [deliveryZones, setDeliveryZones] = useState([]);
  const [deliveryZone, setDeliveryZone] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const phoneStorageKey = user ? `tuva_mpesa_phone:${localStorage.getItem("tuva_token") || user.toLowerCase()}` : "";
  useEffect(() => {
    let active = true;
    api.storeConfig().then((config) => {
      if (active) setGuestCheckoutEnabled(Boolean(config.guest_checkout));
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    api.deliveryZones().then((zones) => { if (active) setDeliveryZones(zones); }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!phoneStorageKey) return;
    const savedPhone = localStorage.getItem(phoneStorageKey);
    if (savedPhone) setPhone(savedPhone);
  }, [phoneStorageKey]);
  useEffect(() => {
    let active = true;
    setQuote(null);
    setQuoteError("");
    api.quote(product.id, quantity, deliveryZone).then((result) => {
      if (active) setQuote(result);
    }).catch((error) => {
      if (active) setQuoteError(error.message);
    });
    return () => { active = false; };
  }, [product.id, quantity, deliveryZone]);
  const pay = async (event) => {
    event.preventDefault();
    if (paymentComplete) return;
    if (!quote) {
      setMessage(quoteError || "Checking the current M-PESA total…");
      return;
    }
    setBusy(true);
    setMessageType("pending");
    let order = activeOrder;
    let orderAccessToken = guestAccessToken;
    try {
      if (order) {
        setMessage("Checking the existing payment request. We will not send another prompt.");
      } else {
        setMessage("Sending a secure M-PESA prompt to your phone...");
        const result = await api.checkout(product.id, phone, quantity, checkoutKey.current, {
          full_name: user || guestName, email: user ? userEmail : guestEmail, address, city,
          delivery_zone: deliveryZone || null,
        });
        order = result.order;
        orderAccessToken = result.access_token || "";
        setGuestAccessToken(orderAccessToken);
        setActiveOrder(order);
        if (phoneStorageKey) localStorage.setItem(phoneStorageKey, phone.trim());
        setMessage(result.message || "Check your phone and enter your M-PESA PIN.");
      }
      for (let attempt = 0; attempt < 30; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        const status = await api.order(order, orderAccessToken);
        if (status.payment_status === "successful") {
          setMessageType("success");
          setMessage(status.receipt ? `Payment confirmed. M-PESA receipt ${status.receipt}.` : "Payment confirmed.");
          setPaymentComplete(true);
          onPaid(product.id);
          return;
        }
        if (status.payment_status === "cancelled") {
          setActiveOrder(null);
          checkoutKey.current = crypto.randomUUID();
          setMessageType("cancelled");
          setMessage(status.feedback || "Payment cancelled. No payment was completed.");
          return;
        }
        if (status.payment_status === "failed") {
          setActiveOrder(null);
          checkoutKey.current = crypto.randomUUID();
          setMessageType("error");
          setMessage(status.feedback || "Payment failed. Please check your M-PESA phone and try again.");
          return;
        }
        if (status.payment_status === "reconcile") {
          setMessageType("pending");
          setMessage(status.feedback || "Your payment needs review. Please contact TUVA support.");
          return;
        }
      }
      setMessage("Your payment is still processing. We’ll confirm it as soon as Safaricom responds.");
    } catch (error) {
      if (error.status && error.status < 500) checkoutKey.current = crypto.randomUUID();
      setMessageType("error");
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Secure checkout" onClose={onClose} className="checkout-dialog">
      <div className="checkout-content">
        <div className="checkout-product"><img src={product.image} alt="" /><div><strong>{product.name}</strong><span>Qty {quantity}</span></div>
          <b>{money(product.price_min_kes)}</b></div>
        <div className="kes-quote"><span>M-PESA total</span><strong>{quote ? money(quote.amount_kes) : quoteError ? "Unavailable" : "Calculating…"}</strong></div>
        {quote && <p className="security-note">Subtotal {money(quote.subtotal)}{Number(quote.delivery_fee) > 0 ? ` · delivery ${money(quote.delivery_fee)}` : ""}</p>}
        {quoteError && <p className="form-message quote-error" role="alert">{quoteError}</p>}
        {paymentComplete ? <section className="payment-confirmation" aria-live="polite">
          <div><CircleCheck size={30} aria-hidden="true" /><span><strong>Payment confirmed</strong><small>Your order is complete. You do not need to pay again.</small></span></div>
          <button className="btn" onClick={onClose}>Done</button>
        </section> : <>
          {!user && !guestCheckoutEnabled ? <div className="checkout-signin"><p>Sign in or create a TUVA account before paying by M-PESA.</p><button className="btn" onClick={onSignIn}>Sign in or create account</button></div> :
            <form className="checkout-form" onSubmit={pay}>
            {!user && <>
              <label htmlFor="guest-name">Your name</label>
              <input id="guest-name" type="text" autoComplete="name" required maxLength="150" value={guestName} onChange={(event) => setGuestName(event.target.value)} />
              <label htmlFor="guest-email">Email for order updates</label>
              <input id="guest-email" type="email" autoComplete="email" required maxLength="254" value={guestEmail} onChange={(event) => setGuestEmail(event.target.value)} />
            </>}
            {deliveryZones.length > 0 && <>
              <label htmlFor="delivery-zone">Delivery area</label>
              <select id="delivery-zone" value={deliveryZone} onChange={(event) => setDeliveryZone(event.target.value)}>
                <option value="">Choose later / arrange with TUVA</option>
                {deliveryZones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name} · {zone.is_collection ? "collection" : money(zone.fee)}{zone.eta ? ` · ${zone.eta}` : ""}</option>)}
              </select>
              <label htmlFor="delivery-address">Delivery address (optional)</label>
              <input id="delivery-address" autoComplete="street-address" value={address} onChange={(event) => setAddress(event.target.value)} />
              <label htmlFor="delivery-city">Town / city</label>
              <input id="delivery-city" autoComplete="address-level2" value={city} onChange={(event) => setCity(event.target.value)} />
            </>}
            <label htmlFor="mpesa-phone">M-PESA phone number</label>
            <input id="mpesa-phone" type="tel" inputMode="tel" autoComplete="tel" required minLength="9" placeholder="e.g. 0712 345 678" value={phone} onChange={(event) => setPhone(event.target.value)} />
            <button className="btn pay-button" disabled={busy || !quote}>{busy ? "Waiting for payment..." : activeOrder ? "Check payment status" : "Pay with M-PESA"}</button>
            <p className="security-note">Secure payment via Safaricom M-PESA STK Push. Prices are shown and charged in Kenyan shillings.</p>
            </form>}
          <div className="checkout-whatsapp"><span>Prefer to confirm details before paying?</span>
            <a className="outline-button" href={`https://wa.me/${whatsappNumber || ""}?text=${encodeURIComponent(`Hi TUVA, I would like to order ${product.name} (quantity ${quantity}) for ${money(quote?.amount_kes ?? product.price_min_kes)}. Please confirm availability and payment options.`)}`} target="_blank" rel="noreferrer">
              <Icon name="whatsapp" size={17} />Order via WhatsApp
            </a><small>Confirm stock and discuss payment options with our team.</small>
          </div>
        </>}
        {message && <p className={`form-message checkout-feedback ${messageType}`} role="status" aria-live="polite">{message}</p>}
      </div>
    </Modal>
  );
}

function CartDialog({ items, onClose, onBrowse, onRemove, onChangeQuantity, onCheckout }) {
  const subtotal = items.every((item) => item.product.price_min_kes != null)
    ? items.reduce((sum, item) => sum + Number(item.product.price_min_kes) * item.quantity, 0)
    : null;
  return (
    <Modal title={`Your bag (${items.reduce((count, item) => count + item.quantity, 0)})`} onClose={onClose} className="cart-dialog">
      <div className="cart-content">
        {items.length ? <>
          <div className="cart-items">{items.map(({ product, quantity }) => <article className={`cart-item${items.length === 1 ? " cart-item-single" : ""}`} key={product.id}>
            <img src={product.image} alt="" />
            <div className="cart-item-copy">
              <strong>{product.name}</strong><span>{money(product.price_min_kes)} each</span>
              <div className="cart-quantity" aria-label={`Quantity ${quantity}`}>
                <button type="button" aria-label={`Decrease ${product.name} quantity`} disabled={quantity <= 1}
                  onClick={() => onChangeQuantity(product.id, quantity - 1)}><Minus size={15} /></button>
                <span>{quantity}</span>
                <button type="button" aria-label={`Increase ${product.name} quantity`}
                  onClick={() => onChangeQuantity(product.id, quantity + 1)}><Plus size={15} /></button>
              </div>
              <button className="btn cart-checkout" onClick={() => onCheckout(product, quantity)}>Checkout item</button>
            </div>
            <b>{money(product.price_min_kes == null ? null : product.price_min_kes * quantity)}</b>
            <button className="cart-remove" type="button" aria-label={`Remove ${product.name} from cart`}
              onClick={() => onRemove(product.id)}><Trash2 size={17} /></button>
          </article>)}</div>
          <div className="cart-footer">
            <div className="cart-total"><span>Subtotal</span><strong>{money(subtotal)}</strong></div>
            {items.length === 1 ? <button className="btn cart-primary-checkout"
              onClick={() => onCheckout(items[0].product, items[0].quantity)}>Checkout <ChevronRight size={19} /></button> :
              <p className="security-note">Choose an item above to check out. Each item is checked for live availability before secure M-PESA checkout.</p>}
            {items.length === 1 && <p className="security-note">Secure checkout with M-PESA. Delivery options are confirmed during checkout.</p>}
          </div>
        </> : <div className="cart-empty"><span><Icon name="bag" size={30} /></span><strong>Your cart is waiting for a great laptop.</strong><p>Explore the catalogue and add your favorites.</p><button className="btn" onClick={onBrowse}>Browse laptops</button></div>}
      </div>
    </Modal>
  );
}

function Assistant({ onClose }) {
  const [messages, setMessages] = useState([{ role: "assistant", content: "Hi, I’m your TUVA shopping assistant. What will you use your laptop for, and what’s your budget?" }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);
  const send = async (event) => {
    event.preventDefault();
    const prompt = text.trim();
    if (!prompt || busy) return;
    const next = [...messages, { role: "user", content: prompt }];
    setMessages(next);
    setText("");
    setBusy(true);
    try {
      const { reply } = await api.assistant(next.slice(1));
      setMessages([...next, { role: "assistant", content: reply }]);
    } catch (error) {
      setMessages([...next, { role: "assistant", content: error.message }]);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Your AI shopping assistant" onClose={onClose} className="chat-dialog ai-dialog">
      <p className="chat-caption">Personalized laptop recommendations, comparisons, and buying advice.</p>
      <div className="message-list" aria-live="polite">{messages.map((message, index) =>
        <p key={index} className={`message ${message.role}`}>{message.content}</p>)}
        {busy && <p className="message assistant">Finding the right fit…</p>}<div ref={bottom} /></div>
      <form className="message-form" onSubmit={send}><input aria-label="Message the AI assistant" value={text} onChange={(event) => setText(event.target.value)} placeholder="Tell me what you need…" />
        <button className="btn" disabled={busy || !text.trim()}>Send</button></form>
    </Modal>
  );
}

function LiveChat({ onClose }) {
  const [conversation] = useState(() => {
    const saved = localStorage.getItem("tuva_chat_id");
    if (saved) return saved;
    const id = crypto.randomUUID();
    localStorage.setItem("tuva_chat_id", id);
    return id;
  });
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef(null);
  const refresh = useCallback(async () => {
    try {
      const result = await api.chat(conversation);
      const serverMessages = result.messages || [];
      setMessages((current) => {
        const serverIds = new Set(serverMessages.map((message) => message.id));
        const notYetPersisted = current.filter((message) => message.id && !serverIds.has(message.id));
        return [...serverMessages, ...notYetPersisted];
      });
    } catch (error) {
      setMessages((current) => current.length ? current : [{ sender: "support", message: `Chat is temporarily unavailable: ${error.message}` }]);
    }
  }, [conversation]);
  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  const submit = async (event) => {
    event.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      const sent = await api.sendChat(conversation, text.trim());
      setMessages((current) => [...current, sent]);
      setText("");
      await refresh();
    } catch (error) {
      setMessages((current) => [...current, { sender: "support", message: error.message }]);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="live-chat-panel" aria-label="Live chat support">
      <div className="live-chat-head"><div className="support-avatar">T</div><div><strong>Talk to TUVA</strong><span><i /> We’re here to help</span></div>
        <button className="icon-button" aria-label="Close chat" onClick={onClose}><X size={18} /></button></div>
      <div className="live-chat-messages" aria-live="polite">
        <p className="message support">Welcome to TUVA! Tell us what you’re looking for and our team will be with you shortly.</p>
        {messages.map((message) => <p key={message.id} className={`message ${message.sender === "customer" ? "user" : "support"}`}>{message.message}</p>)}
        <div ref={bottom} />
      </div>
      <form className="live-chat-form" onSubmit={submit}><input aria-label="Message customer support" value={text} onChange={(event) => setText(event.target.value)} placeholder="Type your message…" maxLength={2000} />
        <button className="btn" aria-label="Send message" disabled={busy || !text.trim()}><ArrowUp size={18} /></button></form>
      <p className="chat-privacy">Messages are saved securely for this conversation.</p>
    </section>
  );
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState(productIdFromPath);
  const [openProductNotify, setOpenProductNotify] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(isCatalogPath);
  const [adminOpen, setAdminOpen] = useState(isAdminPath);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [appliedMinPrice, setAppliedMinPrice] = useState("");
  const [appliedMaxPrice, setAppliedMaxPrice] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMoreProducts, setHasMoreProducts] = useState(false);
  const [totalProductCount, setTotalProductCount] = useState(0);
  const [error, setError] = useState("");
  const [cart, setCart] = useState([]);
  const [cartAnnouncement, setCartAnnouncement] = useState("");
  const [cartOpen, setCartOpen] = useState(false);
  const [checkout, setCheckout] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInError, setSignInError] = useState("");
  const [user, setUser] = useState(() => localStorage.getItem("tuva_user") || "");
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem("tuva_email") || "");
  const [installPrompt, setInstallPrompt] = useState(null);
  const [imageSearchBusy, setImageSearchBusy] = useState(false);
  const [imageSearchActive, setImageSearchActive] = useState(false);
  const [activeTab, setActiveTab] = useState("home");
  const imageInput = useRef(null);
  const liveChatPanel = useRef(null);
  const liveChatTrigger = useRef(null);
  const cartAnnouncementTimer = useRef(null);
  const logoLongPressTimer = useRef(null);
  const logoLongPressTriggered = useRef(false);
  const skipProductEffect = useRef(false);
  const searchRequestId = useRef(0);
  const resultsSection = useRef(null);
  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);
  const productFilters = {
    sort: sortOrder,
    minPrice: appliedMinPrice,
    maxPrice: appliedMaxPrice,
    inStock: inStockOnly,
  };

  useEffect(() => {
    const handlePopState = () => {
      setSelectedProductId(productIdFromPath());
      setOpenProductNotify(false);
      setCatalogOpen(isCatalogPath());
      setAdminOpen(isAdminPath());
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const openAdminShortcut = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "a" && !event.repeat) {
        const target = event.target;
        if (target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
        event.preventDefault();
        openAdmin();
      }
    };
    window.addEventListener("keydown", openAdminShortcut);
    return () => window.removeEventListener("keydown", openAdminShortcut);
  }, []);

  useEffect(() => () => window.clearTimeout(logoLongPressTimer.current), []);

  useEffect(() => {
    if (!chatOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!(event.target instanceof Node)) return;
      if (liveChatPanel.current?.contains(event.target) || liveChatTrigger.current?.contains(event.target)) return;
      setChatOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, [chatOpen]);

  const loadProducts = useCallback(async (search = query, selectedCategory = category, includeCount = catalogOpen) => {
    const requestId = ++searchRequestId.current;
    setImageSearchActive(false);
    setImageSearchBusy(false);
    setLoading(true);
    setLoadingMore(false);
    setHasMoreProducts(false);
    setTotalProductCount(0);
    setError("");
    setProducts([]);
    try {
      const response = await api.products(search, selectedCategory, 0, includeCount, productFilters);
      if (requestId === searchRequestId.current) {
        const result = includeCount ? response.results : response;
        setProducts(result);
        setTotalProductCount(includeCount ? response.count : result.length);
        setHasMoreProducts(includeCount ? response.count > result.length : result.length === PRODUCT_PAGE_SIZE);
      }
    } catch (requestError) {
      if (requestId === searchRequestId.current) setError(requestError.message);
    } finally {
      if (requestId === searchRequestId.current) setLoading(false);
    }
  }, [catalogOpen, category, query, sortOrder, appliedMinPrice, appliedMaxPrice, inStockOnly]);
  const loadMoreProducts = async () => {
    if (loading || loadingMore || !hasMoreProducts) return;
    const requestId = searchRequestId.current;
    setLoadingMore(true);
    setError("");
    try {
      const response = await api.products(query, category, products.length, true, productFilters);
      if (requestId === searchRequestId.current) {
        setProducts((current) => [...current, ...response.results]);
        setTotalProductCount(response.count);
        setHasMoreProducts(response.count > products.length + response.results.length);
      }
    } catch (requestError) {
      if (requestId === searchRequestId.current) setError(requestError.message);
    } finally {
      if (requestId === searchRequestId.current) setLoadingMore(false);
    }
  };
  const searchAndScrollToResults = async () => {
    goHome();
    await loadProducts();
    window.requestAnimationFrame(() => {
      const section = resultsSection.current;
      if (!section) return;
      const header = document.querySelector(".site-header");
      const stickyOffset = header && getComputedStyle(header).position === "sticky"
        ? header.getBoundingClientRect().height + 12
        : 12;
      const top = section.getBoundingClientRect().top + window.scrollY - stickyOffset;
      window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    });
  };
  useEffect(() => {
    if (skipProductEffect.current) {
      skipProductEffect.current = false;
      return undefined;
    }
    const timer = window.setTimeout(() => loadProducts(), 250);
    return () => window.clearTimeout(timer);
  }, [loadProducts]);
  useEffect(() => {
    const onInstall = (event) => { event.preventDefault(); setInstallPrompt(event); };
    window.addEventListener("beforeinstallprompt", onInstall);
    return () => window.removeEventListener("beforeinstallprompt", onInstall);
  }, []);
  const doInstall = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };
  const addToCart = (product, quantity = 1) => {
    setCart((items) => {
      const existing = items.find((item) => item.product.id === product.id);
      return existing
        ? items.map((item) => item.product.id === product.id ? { ...item, quantity: item.quantity + quantity } : item)
        : [...items, { product, quantity }];
    });
    setCartAnnouncement(`${quantity > 1 ? `${quantity} × ` : ""}${product.name} added to cart.`);
    window.clearTimeout(cartAnnouncementTimer.current);
    cartAnnouncementTimer.current = window.setTimeout(() => setCartAnnouncement(""), 3000);
  };
  const runImageSearch = async (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError("Choose an image file to search."); return; }
    const requestId = ++searchRequestId.current;
    setImageSearchBusy(true);
    setLoading(true);
    setError("");
    setProducts([]);
    setHasMoreProducts(false);
    if (query || category) skipProductEffect.current = true;
    setQuery("");
    setCategory("");
    setImageSearchActive(true);
    try {
      const result = await api.imageSearch(file);
      if (requestId === searchRequestId.current) {
        setProducts(result);
        setTotalProductCount(result.length);
      }
    } catch (requestError) {
      if (requestId === searchRequestId.current) {
        setError(requestError.message);
        setProducts([]);
      }
    } finally {
      if (requestId === searchRequestId.current) {
        setLoading(false);
        setImageSearchBusy(false);
      }
      if (imageInput.current) imageInput.current.value = "";
    }
  };
  const handleSignIn = (result) => {
    if (result.error) { setSignInError(result.error); return; }
    setUser(result.name || result.email || "");
    setUserEmail(result.email || "");
    setSignInOpen(false);
    setSignInError("");
  };
  const handleSignOut = async () => {
    const token = localStorage.getItem("tuva_token");
    localStorage.removeItem("tuva_token");
    localStorage.removeItem("tuva_user");
    localStorage.removeItem("tuva_email");
    setUser("");
    setUserEmail("");
    setCheckout(null);
    setSignInError("");
    if (!token) return;
    try {
      await api.logout(token);
    } catch (logoutError) {
      setSignInError(`You are signed out on this device, but the server session could not be revoked: ${logoutError.message}`);
    }
  };
  const whatsappNumber = (import.meta.env.VITE_WHATSAPP || "").replace(/\D/g, "");
  const whatsappLink = `https://wa.me/${whatsappNumber || ""}?text=${encodeURIComponent("Hi TUVA, I need help choosing a laptop.")}`;
  function openAdmin() {
    if (!isAdminPath()) window.history.pushState({ admin: true }, "", "/admin/");
    setAdminOpen(true);
    setSelectedProductId(null);
    setCatalogOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function closeAdmin() {
    if (isAdminPath()) window.history.pushState({}, "", "/");
    setAdminOpen(false);
    setSelectedProductId(null);
    setCatalogOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  const goHome = () => {
    if (window.location.pathname !== "/") window.history.pushState({}, "", "/");
    setSelectedProductId(null);
    setOpenProductNotify(false);
    setCatalogOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openCatalog = () => {
    if (!isCatalogPath()) window.history.pushState({ catalog: true }, "", "/products/");
    setSelectedProductId(null);
    setOpenProductNotify(false);
    setCatalogOpen(true);
    setImageSearchActive(false);
    setImageSearchBusy(false);
    if (query || category) {
      setQuery("");
      setCategory("");
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openProduct = (product, focusNotify = !product.in_stock) => {
    window.history.pushState({ productId: product.id }, "", `/products/${product.id}/`);
    setSelectedProductId(String(product.id));
    setOpenProductNotify(focusNotify && !product.in_stock);
    setCatalogOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const filterCatalog = (value) => {
    const sameFilter = !query && category === value;
    setQuery("");
    setCategory(value);
    setImageSearchActive(false);
    if (sameFilter && imageSearchActive) loadProducts("", value);
  };
  const clearCatalogFilters = () => {
    setQuery("");
    setCategory("");
    setSortOrder("newest");
    setMinPrice("");
    setMaxPrice("");
    setAppliedMinPrice("");
    setAppliedMaxPrice("");
    setInStockOnly(false);
  };
  const selectCategory = (value) => {
    if (selectedProductId) goHome();
    setCategory(value);
  };
  const openCart = () => {
    setCartOpen(true);
  };
  return (
    <>
      <div className="utility-bar"><div><span className="utility-action"><Icon name="location" size={14} />Delivering in Kenya</span>
        <span className="utility-action"><Icon name="languages" size={14} />Prices in KSh</span></div>
        <button className="utility-action" onClick={() => setChatOpen(true)}><Icon name="circleHelp" size={14} />Contact support</button></div>
      <header className="site-header">
        <a className="brand" href="/" aria-label="TUVA home" onPointerDown={(event) => {
          if (event.pointerType !== "touch") return;
          logoLongPressTriggered.current = false;
          window.clearTimeout(logoLongPressTimer.current);
          logoLongPressTimer.current = window.setTimeout(() => {
            logoLongPressTriggered.current = true;
            openAdmin();
          }, 700);
        }} onPointerUp={() => window.clearTimeout(logoLongPressTimer.current)} onPointerCancel={() => window.clearTimeout(logoLongPressTimer.current)} onPointerLeave={() => window.clearTimeout(logoLongPressTimer.current)} onClick={(event) => {
          if (logoLongPressTriggered.current) {
            event.preventDefault();
            logoLongPressTriggered.current = false;
          } else {
            event.preventDefault();
            goHome();
          }
        }}><img src="/logo.png" alt="TUVA" /></a>
        <button className="mobile-ai-button" aria-label="Open AI shopping assistant" onClick={() => setAiOpen(true)}><Icon name="sparkle" size={18} /></button>
        {installPrompt && <button className="mobile-install-button" aria-label="Install TUVA app" onClick={doInstall}><Icon name="download" size={18} /></button>}
        <div className="mobile-location" aria-label="Delivery destination: Kenya"><Icon name="location" size={19} /><span><small>Deliver to</small><strong>Kenya</strong></span></div>
        <div className="search-wrap"><span className="search-category">All laptops</span>
          <input aria-label="Search laptops" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && searchAndScrollToResults()} placeholder="Search laptops, models, or features" />
          <button className="image-search" title="Search by image" aria-label="Search by image" onClick={() => imageInput.current?.click()}>{imageSearchBusy ? <Icon name="loading" size={18} /> : <Icon name="camera" size={19} />}</button>
          <input ref={imageInput} hidden type="file" accept="image/*" onChange={(event) => runImageSearch(event.target.files?.[0])} />
          <button className="btn search-button" onClick={searchAndScrollToResults}><Icon className="search-button-icon" name="search" size={17} /><span>Search</span></button>
        </div>
        <div className="header-actions">
          <button className="text-action" onClick={() => setAiOpen(true)}><Icon name="sparkle" size={17} /><span>AI assistant</span></button>
          {installPrompt && <button className="text-action" onClick={doInstall}><Icon name="download" size={17} /><span>Install app</span></button>}
          {user ? <><span className="text-action account-action"><Icon name="user" size={16} /><span>Hi, {user}</span></span>
            <button className="text-action" onClick={handleSignOut}><LogOut size={16} /><span>Sign out</span></button></> :
            <button className="text-action" onClick={() => setSignInOpen(true)}><Icon name="user" size={16} /><span>Sign in</span></button>}
          <button className="cart-action" onClick={openCart} aria-label={`Cart, ${cartCount} items`}><Icon name="bag" /><span>Cart</span><b>{cartCount}</b></button>
        </div>
      </header>
      <nav className="desktop-nav" aria-label="Main navigation">
        <button onClick={openCatalog}><Icon name="menu" size={15} />All laptops</button>
        {categories.slice(0, 4).map((item) => <button key={item.id} className={category === item.id ? "selected" : ""} aria-pressed={category === item.id} onClick={() => selectCategory(item.id)}>{item.name}</button>)}
        <button onClick={() => selectCategory("accessories")}>Accessories</button><button onClick={() => { goHome(); window.setTimeout(() => document.getElementById("products")?.scrollIntoView({ behavior: "smooth" }), 0); }}>Shop</button>
      </nav>

      {selectedProductId ? <ProductDetailPage key={selectedProductId} productId={selectedProductId}
        initialProduct={products.find((item) => String(item.id) === selectedProductId)}
        openNotifyOnLoad={openProductNotify}
        onBack={goHome} onAdd={addToCart} onBuyNow={(product, quantity) => setCheckout({ product, quantity })}
        onContact={() => setChatOpen(true)} /> : catalogOpen ? <main className="storefront catalog-page">
        <nav className="product-breadcrumbs" aria-label="Breadcrumb">
          <button type="button" onClick={goHome}><House size={14} /> Home</button><ChevronRight size={14} /><strong>All products</strong>
        </nav>
        <section className="catalog-heading">
          <div><span className="eyebrow">THE TUVA COLLECTION</span>
            <h1>{query ? `Results for “${query}”` : category ? `${categories.find((item) => item.id === category)?.name || "Laptop"} laptops` : "Shop all products"}</h1>
            <p>Find the right tech for work, study, and everything in between.</p>
          </div>
          <div className="catalog-result-count" aria-live="polite"
            aria-label={`${loading ? "Loading" : totalProductCount} products`}>
            <strong>{loading ? "…" : totalProductCount}</strong><span>products</span>
          </div>
        </section>
        <nav className="catalog-categories" aria-label="Filter products by category">
          <button type="button" className={!category ? "selected" : ""} aria-pressed={!category}
            onClick={() => filterCatalog("")}>All products</button>
          {categories.map((item) => <button key={item.id} type="button"
            className={category === item.id ? "selected" : ""} aria-pressed={category === item.id}
            onClick={() => filterCatalog(item.id)}>
            <Icon name={item.icon} size={15} />{item.name}
          </button>)}
        </nav>
        <form className="catalog-filters" onSubmit={(event) => {
          event.preventDefault();
          setAppliedMinPrice(minPrice);
          setAppliedMaxPrice(maxPrice);
        }}>
          <label className="catalog-filter-field">Sort by
            <select aria-label="Sort products" value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}>
              <option value="newest">Newest arrivals</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
            </select>
          </label>
          <label className="catalog-filter-field">Min price (KSh)
            <input aria-label="Minimum price in KSh" type="number" min="0" step="1" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} placeholder="Any" />
          </label>
          <label className="catalog-filter-field">Max price (KSh)
            <input aria-label="Maximum price in KSh" type="number" min="0" step="1" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} placeholder="Any" />
          </label>
          <button className="catalog-filter-apply" type="submit">Apply price</button>
          <label className="catalog-stock-filter">
            <input type="checkbox" checked={inStockOnly} onChange={(event) => setInStockOnly(event.target.checked)} />
            In stock only
          </label>
          {(query || category || appliedMinPrice || appliedMaxPrice || inStockOnly || sortOrder !== "newest") &&
            <button className="catalog-filter-clear" type="button" onClick={clearCatalogFilters}>Clear filters</button>}
        </form>
        {error && <div className="error-banner" role="alert">{error}
          <button onClick={() => products.length && hasMoreProducts ? loadMoreProducts() : loadProducts()}>Try again</button>
        </div>}
        {loading ? <div className="product-grid catalog-product-grid" role="status" aria-label="Loading products" aria-busy="true">
          {[...Array(8)].map((_, index) => <div key={index} className="product-card skeleton" />)}
        </div> : products.length ? <div className="product-grid catalog-product-grid">
          {products.map((product) => <ProductCard key={product.id} product={product} onAdd={addToCart} onOpen={openProduct} />)}
        </div> : !error && <div className="empty-results">
          <Search className="empty-search-icon" aria-hidden="true" size={30} strokeWidth={1.6} />
          <h3>No products found</h3><p>Try a different search or category to explore our collection.</p>
          {(query || category || appliedMinPrice || appliedMaxPrice || inStockOnly || sortOrder !== "newest") && <button className="btn" onClick={clearCatalogFilters}>Clear filters</button>}
        </div>}
        {!loading && products.length > 0 && hasMoreProducts && <div className="catalog-load-more">
          <span>Showing {products.length} of {totalProductCount} products</span>
          <button className="btn" type="button" disabled={loadingMore} onClick={loadMoreProducts}>
            {loadingMore ? <><LoaderCircle size={16} className="spin" /> Loading products…</> : "Load more products"}
          </button>
        </div>}
      </main> : <main className="storefront">
        <section className="hero-layout">
          <aside className="category-panel" aria-label="Shop by category">
            {categories.map((item) => <button key={item.id} className="category-row" onClick={() => selectCategory(item.id)}>
              <span className="category-icon"><Icon name={item.icon} size={21} /></span><span className="category-copy"><strong>{item.name}</strong><small>{item.hint}</small></span><span className="category-arrow"><Icon name="chevronRight" size={16} /></span>
            </button>)}
            <button className="all-categories" onClick={() => selectCategory("")}>View all categories <Icon name="chevronRight" size={16} /></button>
          </aside>
          <div className="mobile-category-quick" id="mobile-categories" aria-label="Shop popular categories">
            {[categories[0], categories[1], categories[2], categories[4]].map((item) => <button key={item.id} className={category === item.id ? "active" : ""} aria-pressed={category === item.id} onClick={() => selectCategory(item.id)}>
              <span><Icon name={item.icon} size={28} /></span><strong>{item.name}</strong>
            </button>)}
          </div>
          <div className="hero-main"><div className="hero-copy"><span className="eyebrow">BUILT FOR WHAT’S NEXT</span><h1>Source smarter.<br />Work faster.</h1>
            <p>Reliable laptops for teams, resellers, and growing businesses.</p>
            <div className="hero-actions"><button className="btn" onClick={() => document.getElementById("products")?.scrollIntoView({ behavior: "smooth" })}>Shop laptops</button>
              <button className="outline-button" onClick={() => setAiOpen(true)}>Find my laptop</button></div></div></div>
          <aside className="promo-stack">
            <article className="promo-card quote-promo"><div><span className="eyebrow">BUYING FOR A TEAM?</span><h2>Request bulk pricing</h2><p>Tell us what you need.<br />We’ll get back fast.</p><button onClick={() => setChatOpen(true)}>Talk to our team <Icon name="message" size={13} /></button></div><span className="promo-boxes" aria-hidden="true"><Icon name="box" size={58} strokeWidth={1.4} /></span></article>
          </aside>
        </section>

        <section className="trust-strip" aria-label="Shopping benefits">
          {[["shieldCheck", "Verified suppliers", "Quality you can trust"], ["package", "Trade protection", "Your orders, protected"], ["lock", "Secure payments", "Safe & encrypted"], ["globe", "Global delivery", "Fast, reliable shipping"]].map(([icon, title, caption]) =>
            <div className="trust-item" key={title}><Icon name={icon} size={22} /><div><strong>{title}</strong><small>{caption}</small></div></div>)}
        </section>


        <section className="products-section" id="products" ref={resultsSection}>
          <div className="section-heading"><div><span className="eyebrow">{imageSearchActive ? "IMAGE SEARCH" : query || category ? "YOUR SEARCH" : "CURATED FOR YOU"}</span><h2>{imageSearchActive ? "Visually similar laptops" : query ? `Results for “${query}”` : category ? `${categories.find((item) => item.id === category)?.name || "Laptop"} laptops` : "Popular laptops"}</h2></div>
            <button className="view-all" onClick={openCatalog}>View all <Icon name="chevronRight" size={16} /></button></div>
          {error && <div className="error-banner" role="alert">{error}<button onClick={() => loadProducts()}>Try again</button></div>}
          {loading ? <div className="product-grid" role="status" aria-label="Loading products" aria-busy="true">{[1, 2, 3, 4].map((item) => <div key={item} className="product-card skeleton" />)}</div> :
            products.length ? <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={addToCart} onOpen={openProduct} />)}</div> :
              !error && <div className="empty-results"><Search className="empty-search-icon" aria-hidden="true" size={30} strokeWidth={1.6} /><h3>No matching laptops just yet</h3><p>Try a different search or get notified when something becomes available.</p></div>}
          {!loading && !error && query && (!products.length || products.every((product) => !product.in_stock)) && <AvailabilityAlert query={query} userEmail={userEmail} />}
          {!loading && !error && !products.length && !query && <button className="btn retry-button" onClick={() => loadProducts()}>Reload laptops</button>}
        </section>

      </main>}

      {cartAnnouncement && <div className="cart-added-toast" role="status" aria-live="polite"><span>{cartAnnouncement}</span>
        <button onClick={() => { setCartAnnouncement(""); openCart(); }}>View cart</button></div>}

      <footer className="site-footer"><span>© {new Date().getFullYear()} TUVA. Prices in Kenyan shillings.</span>
      </footer>

      <div className="floating-actions">
        <button ref={liveChatTrigger} className="float-button live-button" aria-label="Open live chat" aria-expanded={chatOpen} aria-controls="live-chat-panel" onClick={() => setChatOpen((open) => !open)}><Icon name="chat" size={22} /><span className="online-dot" /></button>
        <a className="float-button whatsapp-button" href={whatsappLink} target="_blank" rel="noreferrer" aria-label="Contact TUVA on WhatsApp"><Icon name="whatsapp" size={25} /></a>
      </div>
      {chatOpen && <div ref={liveChatPanel} id="live-chat-panel"><LiveChat onClose={() => setChatOpen(false)} /></div>}
      {cartOpen && <CartDialog items={cart} onClose={() => setCartOpen(false)}
        onBrowse={() => { setCartOpen(false); openCatalog(); }}
        onRemove={(id) => setCart((items) => items.filter((item) => item.product.id !== id))}
        onChangeQuantity={(id, quantity) => setCart((items) => items.map((item) => item.product.id === id ? { ...item, quantity } : item))}
        onCheckout={(product, quantity) => { setCartOpen(false); setCheckout({ product, quantity }); }} />}
      <nav className="mobile-tabs" aria-label="Mobile navigation">
        {[["home", "home", "Home"], ["categories", "grid", "Categories"], ["messages", "chat", "Messages"], ["cart", "bag", "Cart"]].map(([key, icon, label]) =>
          <button key={key} className={activeTab === key ? "active" : ""} onClick={() => {
            setActiveTab(key);
            if (key === "categories") {
              const categoriesSection = catalogOpen ? document.querySelector(".catalog-categories") : document.getElementById("mobile-categories");
              categoriesSection?.scrollIntoView({ behavior: "smooth" });
            }
            if (key === "messages") setChatOpen(true);
            if (key === "cart") openCart();
            if (key === "home") goHome();
          }}><span><Icon name={icon} size={21} /></span>{label}{key === "cart" && cartCount > 0 && <b>{cartCount}</b>}</button>)}
      </nav>
      {checkout && <Checkout product={checkout.product} quantity={checkout.quantity} user={user} userEmail={userEmail} whatsappNumber={whatsappNumber} onClose={() => setCheckout(null)}
        onSignIn={() => setSignInOpen(true)} onPaid={(id) => setCart((items) => items.filter((item) => item.product.id !== id))} />}
      {aiOpen && <Assistant onClose={() => setAiOpen(false)} />}
      {signInOpen && <SignIn onClose={() => setSignInOpen(false)} onSignedIn={handleSignIn} />}
      {adminOpen && <AdminDashboard onClose={closeAdmin} />}
      {signInError && <div className="toast-error" role="alert">{signInError}<button aria-label="Dismiss error" onClick={() => setSignInError("")}><X size={17} /></button></div>}
    </>
  );
}
