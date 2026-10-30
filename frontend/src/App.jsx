import { useCallback, useEffect, useId, useRef, useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import {
  ArrowUp,
  BadgeCheck,
  Box,
  BriefcaseBusiness,
  Building2,
  Camera,
  Check,
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
  Package,
  PackageCheck,
  Percent,
  Search,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Star,
  Store,
  Tag,
  Tablet,
  Truck,
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
const money = (value) => value == null ? "Price unavailable" : `KSh ${Number(value).toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

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

function ProductCard({ product, onAdd }) {
  return (
    <article className="product-card">
      {product.badge && <span className="badge">{product.badge}</span>}
      <div className="product-image">
        <img src={product.image} alt={product.name} loading="lazy" />
      </div>
      <div className="product-info">
        <div className="product-title"><h3>{product.name}</h3><span className="supplier-check" title="Verified supplier"><Check size={10} strokeWidth={3} /></span></div>
        <p className="product-subtitle">{product.subtitle}</p>
        <p className="rating"><span aria-label={`${product.rating} out of 5 stars`}>{Array.from({ length: 5 }, (_, index) =>
          <Star key={index} size={12} strokeWidth={1.7} fill={index < Math.round(product.rating || 0) ? "currentColor" : "none"} />)}</span><small>{product.rating} / 5</small></p>
        <p className="price">{money(product.price_min_kes)}</p>
        <p className="verified"><BadgeCheck size={12} aria-hidden="true" /> Verified supplier</p>
      </div>
      <div className="specs">{(product.specs || []).slice(0, 4).map((spec) => <span key={spec}>{spec}</span>)}</div>
      <div className="card-bottom">
        <span className={product.in_stock ? "stock-label" : "stock-label unavailable"}>
          {product.in_stock ? "In stock" : "Currently unavailable"}
        </span>
        <button className="btn card-cta" disabled={!product.in_stock} onClick={() => onAdd(product)}>
          {product.in_stock ? "Add to cart" : "Out of stock"}
        </button>
      </div>
    </article>
  );
}

function AvailabilityAlert({ query }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api.alert(email, query);
      setMessage("You're on the list. We'll email you when a match is available.");
      setEmail("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="alert-card" onSubmit={submit}>
      <div><span className="eyebrow">STOCK ALERT</span><h3>Still looking for “{query}”?</h3>
        <p>Leave your email and we’ll let you know when it’s available.</p></div>
      <div className="alert-form"><input type="email" required placeholder="Your email address" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button className="btn" disabled={busy}>{busy ? "Saving…" : "Notify me"}</button></div>
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
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section ref={dialogRef} className={`dialog ${className}`} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
        <div className="dialog-heading"><div><span className="eyebrow">TUVA</span><h2 id={titleId}>{title}</h2></div>
          <button className="icon-button close-button" aria-label="Close" onClick={onClose}><X size={19} /></button></div>
        {children}
      </section>
    </div>
  );
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

function Checkout({ product, quantity, user, onClose, onSignIn, onPaid, whatsappNumber }) {
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
  const phoneStorageKey = user ? `tuva_mpesa_phone:${localStorage.getItem("tuva_token") || user.toLowerCase()}` : "";
  useEffect(() => {
    if (!phoneStorageKey) return;
    const savedPhone = localStorage.getItem(phoneStorageKey);
    if (savedPhone) setPhone(savedPhone);
  }, [phoneStorageKey]);
  useEffect(() => {
    let active = true;
    api.quote(product.id, quantity).then((result) => {
      if (active) setQuote(result);
    }).catch((error) => {
      if (active) setQuoteError(error.message);
    });
    return () => { active = false; };
  }, [product.id, quantity]);
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
    try {
      if (order) {
        setMessage("Checking the existing payment request. We will not send another prompt.");
      } else {
        setMessage("Sending a secure M-PESA prompt to your phone...");
        const result = await api.checkout(product.id, phone, quantity);
        order = result.order;
        setActiveOrder(order);
        if (phoneStorageKey) localStorage.setItem(phoneStorageKey, phone.trim());
        setMessage(result.message || "Check your phone and enter your M-PESA PIN.");
      }
      for (let attempt = 0; attempt < 30; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        const status = await api.order(order);
        if (status.status === "paid") {
          setMessageType("success");
          setMessage(status.receipt ? `Payment confirmed. M-PESA receipt ${status.receipt}.` : "Payment confirmed.");
          setPaymentComplete(true);
          onPaid(product.id);
          return;
        }
        if (status.status === "cancelled") {
          setActiveOrder(null);
          setMessageType("cancelled");
          setMessage(status.feedback || "Payment cancelled. No payment was completed.");
          return;
        }
        if (status.status === "failed") {
          setActiveOrder(null);
          setMessageType("error");
          setMessage(status.feedback || "Payment failed. Please check your M-PESA phone and try again.");
          return;
        }
      }
      setMessage("Your payment is still processing. We’ll confirm it as soon as Safaricom responds.");
    } catch (error) {
      setMessageType("error");
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Secure checkout" onClose={onClose} className="checkout-dialog">
      <div className="checkout-product"><img src={product.image} alt="" /><div><strong>{product.name}</strong><span>Qty {quantity}</span></div>
        <b>{money(product.price_min_kes)}</b></div>
      <div className="kes-quote"><span>M-PESA total</span><strong>{quote ? money(quote.amount_kes) : quoteError ? "Unavailable" : "Calculating…"}</strong></div>
      {quoteError && <p className="form-message quote-error" role="alert">{quoteError}</p>}
      {paymentComplete ? <section className="payment-confirmation" aria-live="polite">
        <div><CircleCheck size={30} aria-hidden="true" /><span><strong>Payment confirmed</strong><small>Your order is complete. You do not need to pay again.</small></span></div>
        <button className="btn" onClick={onClose}>Done</button>
      </section> : <>
        {!user ? <div className="checkout-signin"><p>Sign in or create a TUVA account before paying by M-PESA.</p><button className="btn" onClick={onSignIn}>Sign in or create account</button></div> :
          <form className="checkout-form" onSubmit={pay}>
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
    </Modal>
  );
}

function CartDialog({ items, onClose, onBrowse, onRemove, onCheckout }) {
  const subtotal = items.every((item) => item.product.price_min_kes != null)
    ? items.reduce((sum, item) => sum + Number(item.product.price_min_kes) * item.quantity, 0)
    : null;
  return (
    <Modal title="Your cart" onClose={onClose} className="cart-dialog">
      {items.length ? <>
        <div className="cart-items">{items.map(({ product, quantity }) => <article className="cart-item" key={product.id}>
          <img src={product.image} alt="" /><div className="cart-item-copy"><strong>{product.name}</strong><span>Qty {quantity} · {money(product.price_min_kes)} each</span>
            <button onClick={() => onRemove(product.id)}>Remove</button></div><b>{money(product.price_min_kes == null ? null : product.price_min_kes * quantity)}</b>
          <button className="btn cart-checkout" onClick={() => onCheckout(product, quantity)}>Checkout item</button>
        </article>)}</div>
        <div className="cart-total"><span>Estimated subtotal</span><strong>{money(subtotal)}</strong></div>
        <p className="security-note">Each item is checked for live availability before secure M-PESA checkout.</p>
      </> : <div className="cart-empty"><span><Icon name="bag" size={30} /></span><strong>Your cart is waiting for a great laptop.</strong><p>Explore the latest deals and add your favorites.</p><button className="btn" onClick={onBrowse}>Browse deals</button></div>}
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
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cart, setCart] = useState([]);
  const [cartAnnouncement, setCartAnnouncement] = useState("");
  const [cartOpen, setCartOpen] = useState(false);
  const [checkout, setCheckout] = useState(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);
  const [signInError, setSignInError] = useState("");
  const [user, setUser] = useState(() => localStorage.getItem("tuva_user") || "");
  const [installPrompt, setInstallPrompt] = useState(null);
  const [imageSearchBusy, setImageSearchBusy] = useState(false);
  const [imageSearchActive, setImageSearchActive] = useState(false);
  const [activeTab, setActiveTab] = useState("home");
  const imageInput = useRef(null);
  const liveChatPanel = useRef(null);
  const liveChatTrigger = useRef(null);
  const cartAnnouncementTimer = useRef(null);
  const skipProductEffect = useRef(false);
  const searchRequestId = useRef(0);
  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);

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

  const loadProducts = useCallback(async (search = query, selectedCategory = category) => {
    const requestId = ++searchRequestId.current;
    setImageSearchActive(false);
    setImageSearchBusy(false);
    setLoading(true);
    setError("");
    setProducts([]);
    try {
      const result = await api.products(search, selectedCategory);
      if (requestId === searchRequestId.current) setProducts(result);
    } catch (requestError) {
      if (requestId === searchRequestId.current) setError(requestError.message);
    } finally {
      if (requestId === searchRequestId.current) setLoading(false);
    }
  }, [category, query]);
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
  const addToCart = (product) => {
    setCart((items) => {
      const existing = items.find((item) => item.product.id === product.id);
      return existing
        ? items.map((item) => item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
        : [...items, { product, quantity: 1 }];
    });
    setCartAnnouncement(`${product.name} added to cart.`);
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
    if (query || category) skipProductEffect.current = true;
    setQuery("");
    setCategory("");
    setImageSearchActive(true);
    try {
      const result = await api.imageSearch(file);
      if (requestId === searchRequestId.current) setProducts(result);
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
    setSignInOpen(false);
    setSignInError("");
  };
  const handleSignOut = async () => {
    const token = localStorage.getItem("tuva_token");
    localStorage.removeItem("tuva_token");
    localStorage.removeItem("tuva_user");
    setUser("");
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
  const openCart = () => {
    setCartOpen(true);
  };
  return (
    <>
      <div className="utility-bar"><div><span className="utility-action"><Icon name="location" size={14} />Delivering in Kenya</span>
        <span className="utility-action"><Icon name="languages" size={14} />Prices in KSh</span></div>
        <button className="utility-action" onClick={() => setChatOpen(true)}><Icon name="circleHelp" size={14} />Contact support</button></div>
      <header className="site-header">
        <a className="brand" href="/" aria-label="TUVA home"><img src="/logo.png" alt="TUVA" /></a>
        <button className="mobile-ai-button" aria-label="Open AI shopping assistant" onClick={() => setAiOpen(true)}><Icon name="sparkle" size={18} /></button>
        {installPrompt && <button className="mobile-install-button" aria-label="Install TUVA app" onClick={doInstall}><Icon name="download" size={18} /></button>}
        <div className="mobile-location" aria-label="Delivery destination: Kenya"><Icon name="location" size={19} /><span><small>Deliver to</small><strong>Kenya</strong></span></div>
        <div className="search-wrap"><span className="search-category">All laptops</span>
          <input aria-label="Search laptops" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && loadProducts()} placeholder="Search laptops, models, or features" />
          <button className="image-search" title="Search by image" aria-label="Search by image" onClick={() => imageInput.current?.click()}>{imageSearchBusy ? <Icon name="loading" size={18} /> : <Icon name="camera" size={19} />}</button>
          <input ref={imageInput} hidden type="file" accept="image/*" onChange={(event) => runImageSearch(event.target.files?.[0])} />
          <button className="btn search-button" onClick={() => loadProducts()}><Icon className="search-button-icon" name="search" size={17} /><span>Search</span></button>
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
        <button onClick={() => setCategory("")}><Icon name="menu" size={15} />All laptops</button>
        {categories.slice(0, 4).map((item) => <button key={item.id} className={category === item.id ? "selected" : ""} aria-pressed={category === item.id} onClick={() => setCategory(item.id)}>{item.name}</button>)}
        <button onClick={() => setCategory("accessories")}>Accessories</button><button onClick={() => document.getElementById("deals")?.scrollIntoView({ behavior: "smooth" })}>Deals</button>
      </nav>

      <main className="storefront">
        <section className="hero-layout">
          <aside className="category-panel" aria-label="Shop by category">
            {categories.map((item) => <button key={item.id} className="category-row" onClick={() => setCategory(item.id)}>
              <span className="category-icon"><Icon name={item.icon} size={21} /></span><span className="category-copy"><strong>{item.name}</strong><small>{item.hint}</small></span><span className="category-arrow"><Icon name="chevronRight" size={16} /></span>
            </button>)}
            <button className="all-categories" onClick={() => setCategory("")}>View all categories <Icon name="chevronRight" size={16} /></button>
          </aside>
          <div className="mobile-category-quick" id="mobile-categories" aria-label="Shop popular categories">
            {[categories[0], categories[1], categories[2], categories[4]].map((item) => <button key={item.id} className={category === item.id ? "active" : ""} aria-pressed={category === item.id} onClick={() => setCategory(item.id)}>
              <span><Icon name={item.icon} size={28} /></span><strong>{item.name}</strong>
            </button>)}
          </div>
          <div className="hero-main"><div className="hero-copy"><span className="eyebrow">BUILT FOR WHAT’S NEXT</span><h1>Source smarter.<br />Work faster.</h1>
            <p>Reliable laptops for teams, resellers, and growing businesses.</p>
            <div className="hero-actions"><button className="btn" onClick={() => document.getElementById("deals")?.scrollIntoView({ behavior: "smooth" })}>Explore laptop deals</button>
              <button className="outline-button" onClick={() => setAiOpen(true)}>Find my laptop</button></div></div></div>
          <aside className="promo-stack">
            <article className="promo-card deals-promo"><div><span className="eyebrow">BUSINESS-READY DEALS</span><h2>Save up to 18%</h2><p>On bulk orders.</p><button onClick={() => document.getElementById("deals")?.scrollIntoView({ behavior: "smooth" })}>View deals <Icon name="chevronRight" size={13} /></button></div><span className="deal-discount"><Icon name="percent" size={18} /></span><img src="/products/ultrabook.png" alt="" /></article>
            <article className="promo-card quote-promo"><div><span className="eyebrow">BUYING FOR A TEAM?</span><h2>Request bulk pricing</h2><p>Tell us what you need.<br />We’ll get back fast.</p><button onClick={() => setChatOpen(true)}>Talk to our team <Icon name="message" size={13} /></button></div><span className="promo-boxes" aria-hidden="true"><Icon name="box" size={58} strokeWidth={1.4} /></span></article>
          </aside>
        </section>

        <section className="trust-strip" aria-label="Shopping benefits">
          {[["shieldCheck", "Verified suppliers", "Quality you can trust"], ["package", "Trade protection", "Your orders, protected"], ["lock", "Secure payments", "Safe & encrypted"], ["globe", "Global delivery", "Fast, reliable shipping"]].map(([icon, title, caption]) =>
            <div className="trust-item" key={title}><Icon name={icon} size={22} /><div><strong>{title}</strong><small>{caption}</small></div></div>)}
        </section>


        <section className="products-section" id="deals">
          <div className="section-heading"><div><span className="eyebrow">{imageSearchActive ? "IMAGE SEARCH" : query || category ? "YOUR SEARCH" : "CURATED FOR YOU"}</span><h2>{imageSearchActive ? "Visually similar laptops" : query ? `Results for “${query}”` : category ? `${categories.find((item) => item.id === category)?.name || "Laptop"} laptops` : "Top laptop deals"}</h2></div>
            <button className="view-all" onClick={() => { setQuery(""); setCategory(""); }}>View all deals <Icon name="chevronRight" size={16} /></button></div>
          {error && <div className="error-banner" role="alert">{error}<button onClick={() => loadProducts()}>Try again</button></div>}
          {loading ? <div className="product-grid" role="status" aria-label="Loading products" aria-busy="true">{[1, 2, 3, 4].map((item) => <div key={item} className="product-card skeleton" />)}</div> :
            products.length ? <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={addToCart} />)}</div> :
              !error && <div className="empty-results"><Search className="empty-search-icon" aria-hidden="true" size={30} strokeWidth={1.6} /><h3>No matching laptops just yet</h3><p>Try a different search or get notified when something becomes available.</p></div>}
          {!loading && !error && query && (!products.length || products.every((product) => !product.in_stock)) && <AvailabilityAlert query={query} />}
          {!loading && !error && !products.length && !query && <button className="btn retry-button" onClick={() => loadProducts()}>Reload laptops</button>}
        </section>

      </main>

      {cartAnnouncement && <div className="cart-added-toast" role="status" aria-live="polite"><span>{cartAnnouncement}</span>
        <button onClick={() => { setCartAnnouncement(""); openCart(); }}>View cart</button></div>}

      <footer className="site-footer"><span>© {new Date().getFullYear()} TUVA. Prices in Kenyan shillings.</span>
        <button onClick={() => setAdminOpen(true)}>Store management</button>
      </footer>

      <div className="floating-actions">
        <button ref={liveChatTrigger} className="float-button live-button" aria-label="Open live chat" aria-expanded={chatOpen} aria-controls="live-chat-panel" onClick={() => setChatOpen((open) => !open)}><Icon name="chat" size={22} /><span className="online-dot" /></button>
        <a className="float-button whatsapp-button" href={whatsappLink} target="_blank" rel="noreferrer" aria-label="Contact TUVA on WhatsApp"><Icon name="whatsapp" size={25} /></a>
      </div>
      {chatOpen && <div ref={liveChatPanel} id="live-chat-panel"><LiveChat onClose={() => setChatOpen(false)} /></div>}
      {cartOpen && <CartDialog items={cart} onClose={() => setCartOpen(false)}
        onBrowse={() => { setCartOpen(false); document.getElementById("deals")?.scrollIntoView({ behavior: "smooth" }); }}
        onRemove={(id) => setCart((items) => items.filter((item) => item.product.id !== id))}
        onCheckout={(product, quantity) => { setCartOpen(false); setCheckout({ product, quantity }); }} />}
      <nav className="mobile-tabs" aria-label="Mobile navigation">
        {[["home", "home", "Home"], ["categories", "grid", "Categories"], ["messages", "chat", "Messages"], ["cart", "bag", "Cart"]].map(([key, icon, label]) =>
          <button key={key} className={activeTab === key ? "active" : ""} onClick={() => {
            setActiveTab(key);
            if (key === "categories") document.getElementById("mobile-categories")?.scrollIntoView({ behavior: "smooth" });
            if (key === "messages") setChatOpen(true);
            if (key === "cart") openCart();
            if (key === "home") window.scrollTo({ top: 0, behavior: "smooth" });
          }}><span><Icon name={icon} size={21} /></span>{label}{key === "cart" && cartCount > 0 && <b>{cartCount}</b>}</button>)}
      </nav>
      {checkout && <Checkout product={checkout.product} quantity={checkout.quantity} user={user} whatsappNumber={whatsappNumber} onClose={() => setCheckout(null)}
        onSignIn={() => setSignInOpen(true)} onPaid={(id) => setCart((items) => items.filter((item) => item.product.id !== id))} />}
      {aiOpen && <Assistant onClose={() => setAiOpen(false)} />}
      {signInOpen && <SignIn onClose={() => setSignInOpen(false)} onSignedIn={handleSignIn} />}
      {adminOpen && <AdminDashboard onClose={() => setAdminOpen(false)} />}
      {signInError && <div className="toast-error" role="alert">{signInError}<button aria-label="Dismiss error" onClick={() => setSignInError("")}><X size={17} /></button></div>}
    </>
  );
}
