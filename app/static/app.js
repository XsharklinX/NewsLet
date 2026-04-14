/* ═══════════════════════════════════════════════════════
   NewsLet v3.0 — Panel Editorial App
   Tiers A + B + C + D
═══════════════════════════════════════════════════════ */
const API = "/api/v1";

// ── State ─────────────────────────────────────────────
let pg = 1;
let filterStatus = "", filterSrc = "", filterCat = "", filterScore = "", filterSentiment = "";
let filterRecent = "";  // "1h", "6h", "24h", "7d" — vacío = todos
let searchQ = "", searchTmr = null;
let artView = localStorage.getItem("artView") || "list";
let dashView = localStorage.getItem("dashView") || "list";
let savedSearches = JSON.parse(localStorage.getItem("savedSearches") || "[]");
let chartDaily = null, chartCat = null, chartSentiment = null;
let readerArticleId = null;
let draggedId = null;
let wsReconnectDelay = 1000;

// Sentiment emoji map
const SENT_EMOJI = { positive: "😊", neutral: "😐", negative: "😟" };
const NOTIF_ICON = { fetch: "🔄", keyword: "🔑", digest: "📬", error: "⚠️", info: "ℹ️", article_high_score: "⭐" };

/* ══════════════════════════════════════════════════════
   API
══════════════════════════════════════════════════════ */
async function api(path, opt = {}) {
  const token = localStorage.getItem("nl_token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const r = await fetch(API + path, { headers, ...opt });
  if (r.status === 401) {
    // Token expired or invalid — redirect to login
    localStorage.removeItem("nl_token");
    window.location.replace("/login.html");
    return;
  }
  if (!r.ok) throw Object.assign(new Error(`${r.status}`), { status: r.status });
  return r.json();
}

function logout() {
  localStorage.removeItem("nl_token");
  window.location.replace("/login.html");
}

/* ══════════════════════════════════════════════════════
   TOAST
══════════════════════════════════════════════════════ */
function toast(msg, type) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  const colors = { ok: "var(--success)", err: "var(--danger)", info: "var(--primary)" };
  t.style.borderLeftColor = colors[type] || colors.info;
  t.classList.add("on");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("on"), 3500);
}

/* ══════════════════════════════════════════════════════
   SIDEBAR (mobile)
══════════════════════════════════════════════════════ */
function toggleSidebar() {
  const sb = document.getElementById("sidebar");
  const bd = document.getElementById("sidebar-backdrop");
  const open = sb.classList.toggle("mobile-open");
  bd.classList.toggle("on", open);
  document.body.style.overflow = open ? "hidden" : "";
}
function closeSidebar() {
  const sb = document.getElementById("sidebar");
  const bd = document.getElementById("sidebar-backdrop");
  sb.classList.remove("mobile-open");
  bd.classList.remove("on");
  document.body.style.overflow = "";
}

/* ══════════════════════════════════════════════════════
   NAVIGATION
══════════════════════════════════════════════════════ */
function go(v) {
  document.querySelectorAll(".view").forEach(el => el.classList.remove("on"));
  document.getElementById("v-" + v).classList.add("on");
  document.querySelectorAll(".nav-item[data-v]").forEach(n => n.classList.remove("active"));
  const b = document.querySelector(`.nav-item[data-v="${v}"]`);
  if (b) b.classList.add("active");
  closeSidebar(); // close mobile sidebar on navigation

  // Bug fix: reset time filter when leaving articles view
  if (v !== "arts") {
    filterRecent = "";
    document.querySelectorAll(".pill-time").forEach(p => p.classList.remove("on"));
  }

  if (v === "dash")     { loadStats(); loadDash(); }
  if (v === "arts")     { loadArts(); loadSrcFilter(); }
  if (v === "kanban")   loadKanban();
  if (v === "srcs")     loadSrcs();
  if (v === "charts")   loadCharts();
  if (v === "heatmap")  loadHeatmap();
  if (v === "trending") loadTrending();
  if (v === "kw")       loadKeywords();
  if (v === "webhooks") loadWebhooks();
  if (v === "cfg")      { loadDigestConfig(); loadSystemStatus(); }
  if (v === "admin")   loadAdminSettings();
}

/* ══════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════ */
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}
function fmtDate(s) {
  if (!s) return "";
  const d = new Date(s);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const diffH   = Math.floor(diffMs / 3600000);
  const diffD   = Math.floor(diffMs / 86400000);

  // Relative time for recent articles
  if (diffMin < 1)  return "ahora mismo";
  if (diffMin < 60) return `hace ${diffMin} min`;
  if (diffH   < 24) return `hace ${diffH}h`;
  if (diffD   < 2)  return `ayer ${d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`;
  if (diffD   < 7)  return d.toLocaleDateString("es-ES", { weekday: "short", hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function fmtDateFull(s) {
  if (!s) return "";
  return new Date(s).toLocaleString("es-ES", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}
function cleanTxt(t) {
  return (t || "").replace(/\[IMG:[^\]]*\]/g, "").trim();
}
function readTime(text) {
  if (!text) return null;
  const words = text.trim().split(/\s+/).length;
  const mins  = Math.max(1, Math.round(words / 200));
  return `~${mins} min`;
}
function scoreBadge(score) {
  if (score == null) return `<span class="score-badge score-na">?</span>`;
  const cls = score >= 7 ? "score-hi" : score >= 4 ? "score-mid" : "score-lo";
  return `<span class="score-badge ${cls}">${score}</span>`;
}
function sentimentTag(s) {
  if (!s) return "";
  const em = SENT_EMOJI[s] || "";
  const cls = s === "positive" ? "sentiment-pos" : s === "negative" ? "sentiment-neg" : "sentiment-neu";
  return `<span class="${cls}" title="${s}">${em}</span>`;
}
function badgeCls(s) { return "badge b-" + s; }

/* ══════════════════════════════════════════════════════
   THEME
══════════════════════════════════════════════════════ */
function toggleTheme() {
  const root = document.documentElement;
  const isDark = root.getAttribute("data-theme") !== "light";
  root.setAttribute("data-theme", isDark ? "light" : "dark");
  document.getElementById("theme-btn").textContent = isDark ? "🌙" : "☀";
  localStorage.setItem("theme", isDark ? "light" : "dark");
}
(function initTheme() {
  const saved = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  const btn = document.getElementById("theme-btn");
  if (btn) btn.textContent = saved === "light" ? "🌙" : "☀";
})();

/* ══════════════════════════════════════════════════════
   WEBSOCKET — live updates
══════════════════════════════════════════════════════ */
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    const badge = document.getElementById("live-badge");
    if (badge) { badge.classList.add("on"); badge.title = "Conectado en tiempo real"; }
    wsReconnectDelay = 1000;
    // Ping every 25s to keep alive
    ws._ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 25000);
  };

  ws.onmessage = ({ data }) => {
    try {
      const msg = JSON.parse(data);
      if (msg.event === "fetch_complete") {
        const n = msg.data?.total_new || 0;
        if (n > 0) {
          toast(`↻ ${n} artículos nuevos`, "ok");
          const currentView = document.querySelector(".view.on")?.id;
          if (currentView === "v-dash") { loadStats(); loadDash(); }
          if (currentView === "v-arts") loadArts();
          loadNotifBadge();
        }
      }
      if (msg.event === "high_score_article") {
        const d = msg.data;
        toast(`⭐ Score ${d.score}/10: ${d.title?.slice(0, 60)}…`, "ok");
        loadNotifBadge();
      }
    } catch {}
  };

  ws.onclose = () => {
    const badge = document.getElementById("live-badge");
    if (badge) badge.classList.remove("on");
    clearInterval(ws._ping);
    setTimeout(connectWS, wsReconnectDelay);
    wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
  };

  ws.onerror = () => ws.close();
}

/* ══════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS
══════════════════════════════════════════════════════ */
document.addEventListener("keydown", e => {
  // Skip if typing in input
  if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;

  // Close any open modal/panel first
  if (e.key === "Escape") {
    closeModal(); closeWebhookModal(); closeReader();
    closeNotifications(); closeShortcutHelp();
    return;
  }

  const key = e.key.toLowerCase();
  if (key === "?")  { e.preventDefault(); openShortcutHelp(); return; }
  if (key === "f")  { e.preventDefault(); doFetch(); return; }
  if (key === "r")  { e.preventDefault(); doSummarize(); return; }
  if (key === "d")  { e.preventDefault(); doDigest(); return; }
  if (key === "n")  { e.preventDefault(); openNotifications(); return; }
  if (key === "t")  { e.preventDefault(); toggleTheme(); return; }
  if (key === "1")  { e.preventDefault(); go("dash"); return; }
  if (key === "2")  { e.preventDefault(); go("arts"); return; }
  if (key === "3")  { e.preventDefault(); go("kanban"); return; }
  if (key === "4")  { e.preventDefault(); go("charts"); return; }
  if (key === "5")  { e.preventDefault(); go("trending"); return; }
  if (key === "g")  { e.preventDefault(); cycleArtView(); return; }
});

function openShortcutHelp()  { document.getElementById("shortcut-help").classList.add("on"); }
function closeShortcutHelp() { document.getElementById("shortcut-help").classList.remove("on"); }

/* ══════════════════════════════════════════════════════
   ANIMATED COUNTER
══════════════════════════════════════════════════════ */
function animateCount(el, target, suffix = "") {
  if (!el) return;
  const prev = parseFloat(el.dataset.prev) || 0;
  const start = performance.now();
  const dur = 600;
  el.dataset.prev = target;

  function step(now) {
    const p = Math.min((now - start) / dur, 1);
    // ease-out cubic
    const ease = 1 - Math.pow(1 - p, 3);
    const current = prev + (target - prev) * ease;
    el.textContent = (Number.isInteger(target) ? Math.round(current) : current.toFixed(1)) + suffix;
    if (p < 1) requestAnimationFrame(step);
    else el.classList.add("stat-count-up");
  }
  requestAnimationFrame(step);
}

/* ══════════════════════════════════════════════════════
   STATS
══════════════════════════════════════════════════════ */
async function loadStats() {
  try {
    const d = await api("/stats");
    animateCount(document.getElementById("s-total"),    d.total_articles);
    animateCount(document.getElementById("s-pending"),   d.pending);
    animateCount(document.getElementById("s-approved"),  d.approved);
    animateCount(document.getElementById("s-sent"),      d.sent);
    animateCount(document.getElementById("s-kw"),        d.total_keywords);
    animateCount(document.getElementById("s-cat"),       d.articles_with_category);
    animateCount(document.getElementById("s-sum"),       d.articles_with_summary);
    const scoreEl = document.getElementById("s-score");
    if (scoreEl) {
      if (d.avg_score != null) animateCount(scoreEl, d.avg_score);
      else scoreEl.textContent = "—";
    }
    const nTotal = document.getElementById("n-total");
    const nKw    = document.getElementById("n-kw");
    if (nTotal) animateCount(nTotal, d.total_articles);
    if (nKw)    animateCount(nKw, d.total_keywords);
    updateNotifBadge(d.unread_notifications);
  } catch(e) { console.error(e); }
}

/* ══════════════════════════════════════════════════════
   SCORE RING
══════════════════════════════════════════════════════ */
function scoreRing(score) {
  if (score == null) {
    return `<div class="score-badge score-na" title="Sin puntuación">?</div>`;
  }
  const CIRCUMFERENCE = 2 * Math.PI * 20; // r=20
  const pct = score / 10;
  const dash = CIRCUMFERENCE * pct;
  const cls = score >= 9 ? "s9" : score >= 7 ? "s7" : score >= 5 ? "s5" : score >= 3 ? "s3" : "s1";
  return `<svg class="score-ring ${cls}" viewBox="0 0 48 48" title="Score ${score}/10" style="width:40px;height:40px;flex-shrink:0">
    <circle class="track" cx="24" cy="24" r="20" stroke-dasharray="${CIRCUMFERENCE}" stroke-dashoffset="0"/>
    <circle class="progress" cx="24" cy="24" r="20"
      stroke-dasharray="${CIRCUMFERENCE}"
      stroke-dashoffset="${CIRCUMFERENCE - dash}"
      style="transition:stroke-dashoffset 0.7s cubic-bezier(0.4,0,0.2,1)"/>
    <text x="24" y="28" text-anchor="middle" font-size="12" font-weight="800"
      fill="currentColor" font-family="Inter,system-ui,sans-serif">${score}</text>
  </svg>`;
}

/* ══════════════════════════════════════════════════════
   ARTICLE CARD — multi-view
══════════════════════════════════════════════════════ */
function card(a, compact = false) {
  const sumText   = a.summary ? esc(a.summary.summary_text) : "";
  const preview   = sumText || esc(cleanTxt(a.original_text)).slice(0, 200) || "Sin contenido";
  const src       = a.source ? esc(a.source.name) : "?";
  const model     = a.summary ? a.summary.model_used : "";
  const rt        = readTime(a.full_text || a.original_text);
  const catHtml   = a.category ? `<span class="a-cat">${esc(a.category)}</span>` : "";
  const sentHtml  = sentimentTag(a.sentiment);
  const statusCls = `s-${a.status}`;

  const thumbHtml = (!compact && a.thumbnail_url)
    ? `<img class="a-thumb" src="${esc(a.thumbnail_url)}" alt="" loading="lazy" onerror="this.style.display='none'">`
    : "";

  const clusterHtml = a.cluster_id
    ? `<span title="Cluster #${a.cluster_id}" style="font-size:10px;color:var(--text-muted);background:var(--surface);padding:1px 6px;border-radius:4px;border:1px solid var(--border)">🔗 C${a.cluster_id}</span>`
    : "";

  const fb = a.feedback || 0;
  const fbHtml = !compact ? `<span class="a-feedback">
    <button onclick="doFeedback(${a.id},${fb===1?0:1},this)" title="Me gusta" style="background:none;border:none;cursor:pointer;font-size:14px;opacity:${fb===1?1:0.4}">👍</button>
    <button onclick="doFeedback(${a.id},${fb===-1?0:-1},this)" title="No me gusta" style="background:none;border:none;cursor:pointer;font-size:14px;opacity:${fb===-1?1:0.4}">👎</button>
  </span>` : "";

  const recurringBadge = a.is_recurring
    ? `<span title="Tema recurrente" style="font-size:10px;color:var(--warning)">🔁</span>`
    : "";

  return `<div class="a-card ${statusCls}" data-id="${a.id}">
    ${thumbHtml}
    <div class="a-body">
      <div class="a-title" onclick="openReader(${a.id})">
        <a href="${esc(a.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${esc(a.title)}</a>
        ${recurringBadge}
      </div>
      ${!compact ? `<div class="a-summary">${a.summary ? preview : `<em>${preview}</em>`}</div>` : ""}
      ${!compact ? `<div class="a-meta">
        <span class="a-source">${src}</span>
        ${catHtml}
        ${sentHtml}
        ${clusterHtml}
        ${rt ? `<span class="a-read-time">${rt}</span>` : ""}
        <span class="a-dot">·</span>
        <span title="${fmtDateFull(a.published_at || a.fetched_at)}" style="cursor:default">${fmtDate(a.published_at || a.fetched_at)}</span>
        ${model ? `<span class="a-dot">·</span><span style="font-style:italic;font-size:0.62rem;color:var(--text-muted)">${esc(model)}</span>` : ""}
      </div>` : ""}
      ${fbHtml}
    </div>
    <div class="a-right">
      <div style="display:flex;flex-direction:column;align-items:center;gap:6px">
        ${scoreRing(a.relevance_score)}
        <span class="${badgeCls(a.status)}">${a.status}</span>
      </div>
      <div class="a-actions">
        ${!a.summary ? `<button class="btn btn-g btn-xs" onclick="doSum1(${a.id})" title="Resumir IA">✦</button>` : ""}
        ${a.status !== "approved" ? `<button class="btn btn-s btn-xs" onclick="doStatus(${a.id},'approved')" title="Aprobar">✓</button>` : ""}
        ${a.status !== "rejected" ? `<button class="btn btn-d btn-xs" onclick="doStatus(${a.id},'rejected')" title="Rechazar">✕</button>` : ""}
        ${a.summary && a.status !== "sent" ? `<button class="btn btn-p btn-xs" onclick="doSend1(${a.id})" title="Enviar Telegram">✉</button>` : ""}
      </div>
    </div>
  </div>`;
}

async function doFeedback(articleId, value, btn) {
  try {
    await api(`/articles/${articleId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ value }),
    });
    // Update both buttons' opacity in the same .a-feedback container
    const container = btn.closest(".a-feedback");
    if (container) {
      const [likeBtn, dislikeBtn] = container.querySelectorAll("button");
      likeBtn.style.opacity    = value === 1  ? 1 : 0.4;
      dislikeBtn.style.opacity = value === -1 ? 1 : 0.4;
    }
  } catch (e) {
    toast("Error al guardar feedback", "err");
  }
}

function setViewClass(container, view) {
  container.classList.remove("view-list", "view-grid", "view-compact");
  container.classList.add(`view-${view}`);
}

/* ── Dash view ── */
function setDashView(v, el) {
  dashView = v;
  localStorage.setItem("dashView", v);
  document.querySelectorAll("#dash-view-toggle .vt-btn").forEach(b => b.classList.remove("on"));
  el.classList.add("on");
  setViewClass(document.getElementById("dash-list"), v);
}

/* ── Art view ── */
function setArtView(v, el) {
  artView = v;
  localStorage.setItem("artView", v);
  document.querySelectorAll("#art-view-toggle .vt-btn").forEach(b => b.classList.remove("on"));
  el.classList.add("on");
  setViewClass(document.getElementById("art-list"), v);
}

function cycleArtView() {
  const views = ["list", "grid", "compact"];
  const next  = views[(views.indexOf(artView) + 1) % views.length];
  const btn   = document.querySelector(`#art-view-toggle .vt-btn:nth-child(${views.indexOf(next) + 1})`);
  if (btn) setArtView(next, btn);
}

/* ══════════════════════════════════════════════════════
   SKELETON LOADING
══════════════════════════════════════════════════════ */
function skeletonCards(n = 5) {
  return Array.from({ length: n }, () => `
    <div class="a-card" style="pointer-events:none">
      <div class="a-body" style="display:flex;flex-direction:column;gap:10px;flex:1">
        <div class="skeleton skeleton-h-16 skeleton-w-2\/3" style="border-radius:6px;width:70%"></div>
        <div class="skeleton skeleton-h-12" style="border-radius:6px;width:100%"></div>
        <div class="skeleton skeleton-h-12" style="border-radius:6px;width:85%"></div>
        <div style="display:flex;gap:8px;margin-top:4px">
          <div class="skeleton skeleton-h-12" style="border-radius:100px;width:80px"></div>
          <div class="skeleton skeleton-h-12" style="border-radius:100px;width:60px"></div>
        </div>
      </div>
      <div class="a-right" style="align-items:center;gap:8px">
        <div class="skeleton" style="width:40px;height:40px;border-radius:50%"></div>
        <div class="skeleton skeleton-h-12" style="border-radius:100px;width:55px"></div>
      </div>
    </div>`
  ).join("");
}

/* ══════════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════════ */
async function loadDash() {
  const c = document.getElementById("dash-list");
  c.innerHTML = skeletonCards(5);
  setViewClass(c, dashView);
  try {
    const d = await api("/articles?page=1&page_size=10");
    setViewClass(c, dashView);
    if (!d.articles.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">📰</span><h3>Sin artículos</h3><p>Usa "Fetch ahora" para obtener noticias</p></div>`;
      return;
    }
    c.innerHTML = d.articles.map(a => card(a, dashView === "compact")).join("");
  } catch(e) {
    c.innerHTML = `<div class="empty"><span class="e-icon">⚠️</span><h3>Error al cargar</h3></div>`;
    console.error(e);
  }
}

/* ══════════════════════════════════════════════════════
   ARTICLES LIST
══════════════════════════════════════════════════════ */
async function loadArts(p) {
  if (p !== undefined) pg = p;
  const params = new URLSearchParams({ page: pg, page_size: 20 });
  if (filterStatus)    params.set("status",    filterStatus);
  if (filterSrc)       params.set("source_id", filterSrc);
  if (filterCat)       params.set("category",  filterCat);
  if (filterScore)     params.set("min_score", filterScore);

  // Show skeleton immediately
  const c = document.getElementById("art-list");
  if (c) { c.innerHTML = skeletonCards(8); setViewClass(c, artView); }
  if (filterSentiment) params.set("sentiment", filterSentiment);
  if (searchQ)         params.set("search",    searchQ);
  if (filterRecent) {
    const map = { "1h": 1, "6h": 6, "24h": 24, "7d": 168 };
    const hours = map[filterRecent];
    if (hours) {
      const from = new Date(Date.now() - hours * 3600000).toISOString();
      params.set("date_from", from);
    }
  }

  try {
    const d = await api("/articles?" + params);
    const c = document.getElementById("art-list");
    setViewClass(c, artView);
    if (!d.articles.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">🔍</span><h3>${searchQ ? "Sin resultados" : "Sin artículos"}</h3><p>${searchQ ? "Prueba otros términos" : "Usa Fetch ahora"}</p></div>`;
      document.getElementById("paging").innerHTML = "";
      return;
    }
    c.innerHTML = d.articles.map(a => card(a, artView === "compact")).join("");

    const tp = Math.ceil(d.total / d.page_size);
    let h = "";
    if (tp > 1) {
      if (pg > 1) h += `<button class="btn btn-g btn-sm" onclick="loadArts(${pg - 1})">← Anterior</button>`;
      h += `<span>${pg} / ${tp} · ${d.total} artículos</span>`;
      if (pg < tp) h += `<button class="btn btn-g btn-sm" onclick="loadArts(${pg + 1})">Siguiente →</button>`;
    }
    document.getElementById("paging").innerHTML = h;
  } catch(e) { console.error(e); }
}

function onSearch() {
  clearTimeout(searchTmr);
  searchTmr = setTimeout(() => {
    searchQ = document.getElementById("q").value.trim();
    loadArts(1);
  }, 350);
}

function filRecent(v, el) {
  filterRecent = filterRecent === v ? "" : v;  // toggle
  document.querySelectorAll(".pill-time").forEach(p => p.classList.remove("on"));
  if (filterRecent && el) el.classList.add("on");
  loadArts(1);
}

function fil(s, el) {
  filterStatus = s;
  document.querySelectorAll(".pill").forEach(p => p.classList.remove("on"));
  if (el) el.classList.add("on");
  loadArts(1);
}

function onSrcFilter()       { filterSrc       = document.getElementById("src-filter").value;       loadArts(1); }
function onCatFilter()       { filterCat       = document.getElementById("cat-filter").value;       loadArts(1); }
function onScoreFilter()     { filterScore     = document.getElementById("score-filter").value;     loadArts(1); }
function onSentimentFilter() { filterSentiment = document.getElementById("sentiment-filter").value; loadArts(1); }

/* ══════════════════════════════════════════════════════
   SAVED SEARCHES
══════════════════════════════════════════════════════ */
function saveSearch() {
  const filters = { status: filterStatus, src: filterSrc, cat: filterCat, score: filterScore, sentiment: filterSentiment, q: searchQ };
  const hasFilter = Object.values(filters).some(v => v);
  if (!hasFilter) { toast("No hay filtros activos para guardar", "err"); return; }

  const name = prompt("Nombre para este filtro:");
  if (!name) return;

  savedSearches.push({ name, filters });
  localStorage.setItem("savedSearches", JSON.stringify(savedSearches));
  renderSavedSearches();
  toast(`Filtro "${name}" guardado`, "ok");
}

function applySearch(idx) {
  const ss = savedSearches[idx];
  if (!ss) return;
  filterStatus    = ss.filters.status || "";
  filterSrc       = ss.filters.src    || "";
  filterCat       = ss.filters.cat    || "";
  filterScore     = ss.filters.score  || "";
  filterSentiment = ss.filters.sentiment || "";
  searchQ         = ss.filters.q      || "";

  document.getElementById("q").value = searchQ;
  document.getElementById("src-filter").value       = filterSrc;
  document.getElementById("cat-filter").value       = filterCat;
  document.getElementById("score-filter").value     = filterScore;
  document.getElementById("sentiment-filter").value = filterSentiment;
  document.querySelectorAll(".pill").forEach(p => p.classList.remove("on"));
  loadArts(1);
}

function deleteSearch(idx) {
  savedSearches.splice(idx, 1);
  localStorage.setItem("savedSearches", JSON.stringify(savedSearches));
  renderSavedSearches();
}

function renderSavedSearches() {
  const bar = document.getElementById("saved-searches-bar");
  if (!bar) return;
  bar.innerHTML = savedSearches.map((ss, i) =>
    `<div class="ss-chip" onclick="applySearch(${i})">
      ${esc(ss.name)}
      <button onclick="event.stopPropagation();deleteSearch(${i})" title="Eliminar">✕</button>
    </div>`
  ).join("");
}

/* ══════════════════════════════════════════════════════
   ARTICLE READER MODAL
══════════════════════════════════════════════════════ */
async function openReader(id) {
  readerArticleId = id;
  try {
    const a = await api(`/articles/${id}`);
    document.getElementById("r-cat").textContent   = a.category || "";
    document.getElementById("r-title").textContent = a.title;
    document.getElementById("r-link").href         = a.url;
    document.getElementById("r-meta").innerHTML =
      `<span title="${fmtDateFull(a.published_at || a.fetched_at)}">${fmtDate(a.published_at || a.fetched_at)}</span>` +
      (a.source?.name ? ` · ${esc(a.source.name)}` : "") +
      (a.relevance_score ? ` · ⭐ ${a.relevance_score}/10` : "") +
      (a.sentiment ? ` · ${SENT_EMOJI[a.sentiment] || ""} ${a.sentiment}` : "") +
      (readTime(a.full_text || a.original_text) ? ` · ${readTime(a.full_text || a.original_text)} lectura` : "");

    // Bug fix: show thumbnail in reader
    const thumbEl = document.getElementById("r-thumb");
    if (thumbEl) {
      if (a.thumbnail_url) {
        thumbEl.src = a.thumbnail_url;
        thumbEl.style.display = "block";
        thumbEl.onerror = () => { thumbEl.style.display = "none"; };
      } else {
        thumbEl.style.display = "none";
      }
    }

    const sumEl = document.getElementById("r-summary");
    sumEl.textContent = a.summary?.summary_text || "";
    sumEl.style.display = a.summary ? "block" : "none";

    const text = a.full_text || a.original_text || "Sin texto completo disponible.";
    document.getElementById("r-body").textContent = cleanTxt(text);

    const sendBtn = document.getElementById("r-send-btn");
    sendBtn.style.display = a.summary && a.status !== "sent" ? "inline-flex" : "none";

    document.getElementById("overlay-reader").classList.add("on");
    loadRelated(id);
  } catch(e) { toast("Error al cargar artículo", "err"); }
}

async function loadRelated(id) {
  try {
    const list = await api(`/articles/${id}/related`);
    // Could display in reader footer — simplified here
  } catch {}
}

function closeReader() {
  document.getElementById("overlay-reader").classList.remove("on");
  readerArticleId = null;
}

async function sendFromReader() {
  if (!readerArticleId) return;
  await doSend1(readerArticleId);
  closeReader();
}

/* ══════════════════════════════════════════════════════
   ARTICLE ACTIONS
══════════════════════════════════════════════════════ */
async function doStatus(id, s) {
  try {
    await api(`/articles/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: s }) });
    toast(s === "approved" ? "✓ Aprobado" : "✕ Rechazado", "ok");
    loadArts(); loadStats(); loadDash();
  } catch(e) { toast("Error al cambiar estado", "err"); }
}

async function doSum1(id) {
  toast("Resumiendo...", "info");
  try {
    await api(`/articles/${id}/summarize`, { method: "POST" });
    toast("⭐ Resumen listo", "ok");
    loadArts(); loadDash();
  } catch(e) { toast("Error al resumir", "err"); }
}

async function doSend1(id) {
  toast("Enviando a Telegram...", "info");
  try {
    await api(`/articles/${id}/send`, { method: "POST" });
    toast("✉ Enviado", "ok");
    loadArts(); loadStats();
  } catch(e) { toast("Error al enviar", "err"); }
}

/* ══════════════════════════════════════════════════════
   GLOBAL ACTIONS
══════════════════════════════════════════════════════ */
async function doFetch() {
  toast("↻ Buscando noticias...", "info");
  try {
    const d = await api("/fetch/now", { method: "POST" });
    toast(`↻ ${d.total_new} noticias nuevas`, "ok");
    loadArts(1); loadDash(); loadStats(); loadNotifBadge();
  } catch(e) { toast("Error al buscar", "err"); }
}

async function doSummarize() {
  toast("⭐ Resumiendo pendientes...", "info");
  try {
    const d = await api("/summarize/now", { method: "POST" });
    toast(`⭐ ${d.summarized} resumidos`, "ok");
    loadArts(); loadDash();
  } catch(e) { toast("Error al resumir", "err"); }
}

async function doDigest() {
  toast("✉ Enviando digest...", "info");
  try {
    await api("/digest/now", { method: "POST" });
    toast("✉ Digest enviado", "ok");
    loadStats(); loadNotifBadge();
  } catch(e) { toast("Error al enviar digest", "err"); }
}

async function doReenrich() {
  toast("✦ Re-enriqueciendo artículos...", "info");
  try {
    const d = await api("/articles/bulk-reenrich?limit=50", { method: "POST" });
    toast(`✦ ${d.reenriched} artículos actualizados`, "ok");
    loadArts(); loadDash(); loadStats();
  } catch(e) { toast("Error al re-enriquecer", "err"); }
}

function dlCSV() {
  const params = new URLSearchParams();
  if (filterStatus) params.set("status",   filterStatus);
  if (filterCat)    params.set("category", filterCat);
  if (filterScore)  params.set("min_score", filterScore);
  window.open(API + "/articles/export/csv?" + params, "_blank");
}

function dlPDF() {
  const params = new URLSearchParams({ limit: 20, min_score: 0 });
  if (filterCat)   params.set("category", filterCat);
  if (filterScore) params.set("min_score", filterScore);
  window.open(API + "/digest/pdf?" + params, "_blank");
}

/* ══════════════════════════════════════════════════════
   KANBAN
══════════════════════════════════════════════════════ */
async function loadKanban() {
  const statuses = ["pending", "approved", "rejected", "sent"];
  try {
    for (const s of statuses) {
      const d = await api(`/articles?status=${s}&page_size=50`);
      const list = document.getElementById(`kc-list-${s}`);
      const count = document.getElementById(`kc-${s}`);
      if (count) count.textContent = d.total;
      if (!list) continue;
      if (!d.articles.length) {
        list.innerHTML = `<div class="empty" style="padding:20px"><p>Sin artículos</p></div>`;
        continue;
      }
      list.innerHTML = d.articles.map(a => `
        <div class="kb-card" draggable="true"
          data-id="${a.id}"
          ondragstart="onDragStart(event,${a.id})"
          onclick="openReader(${a.id})">
          <div class="kb-title">${esc(a.title)}</div>
          <div class="kb-meta">
            ${scoreBadge(a.relevance_score)}
            ${a.category ? `<span class="a-cat">${esc(a.category)}</span>` : ""}
            ${sentimentTag(a.sentiment)}
            <span>${a.source?.name || ""}</span>
          </div>
        </div>`).join("");
    }
  } catch(e) { console.error(e); }
}

function onDragStart(e, id) {
  draggedId = id;
  e.dataTransfer.effectAllowed = "move";
  setTimeout(() => e.target.classList.add("dragging"), 0);
}

async function onDrop(e, newStatus) {
  e.preventDefault();
  document.querySelectorAll(".kanban-col").forEach(c => c.classList.remove("drag-over"));
  if (!draggedId) return;
  try {
    await api(`/articles/${draggedId}/status`, {
      method: "PATCH", body: JSON.stringify({ status: newStatus }),
    });
    draggedId = null;
    loadKanban();
    loadStats();
  } catch { toast("Error al mover artículo", "err"); }
}

document.addEventListener("dragover", e => {
  const col = e.target.closest(".kanban-col");
  if (col) { col.classList.add("drag-over"); e.preventDefault(); }
});
document.addEventListener("dragleave", e => {
  const col = e.target.closest(".kanban-col");
  if (col && !col.contains(e.relatedTarget)) col.classList.remove("drag-over");
});
document.addEventListener("dragend", () => {
  document.querySelectorAll(".kb-card.dragging").forEach(c => c.classList.remove("dragging"));
  document.querySelectorAll(".kanban-col.drag-over").forEach(c => c.classList.remove("drag-over"));
});

/* ══════════════════════════════════════════════════════
   SOURCES
══════════════════════════════════════════════════════ */
async function loadSrcs() {
  try {
    const list = await api("/sources");
    const c    = document.getElementById("src-list");
    if (!list.length) {
      c.innerHTML = `<div class="empty" style="grid-column:1/-1"><span class="e-icon">📡</span><h3>Sin fuentes</h3><p>Agrega tu primera fuente</p></div>`;
      return;
    }

    // Load stats for each source in parallel (fire-and-forget, update cards)
    c.innerHTML = list.map(s => `<div class="src-card${s.is_active ? "" : " src-inactive"}" id="src-${s.id}">
      <div class="src-top">
        <span class="src-name">${esc(s.name)}</span>
        <span class="src-type">${s.source_type}</span>
      </div>
      <div class="src-url" title="${esc(s.url)}">${esc(s.url)}</div>
      <div class="src-stats" id="src-stats-${s.id}">
        <div class="src-stat"><span>Artículos</span><strong>—</strong></div>
        <div class="src-stat"><span>Score avg</span><strong>—</strong></div>
      </div>
      <div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center">
        <button class="btn ${s.is_active ? "btn-warn" : "btn-s"} btn-xs" onclick="toggleSrc(${s.id})">
          ${s.is_active ? "⏸ Pausar" : "▶ Activar"}
        </button>
        <button class="btn btn-d btn-xs" onclick="delSrc(${s.id},'${esc(s.name)}')">Eliminar</button>
      </div>
    </div>`).join("");

    document.getElementById("n-srcs").textContent = list.length;

    // Fetch stats per source
    list.forEach(async s => {
      try {
        const stats = await api(`/sources/${s.id}/stats`);
        const el = document.getElementById(`src-stats-${s.id}`);
        if (!el) return;
        el.innerHTML = `
          <div class="src-stat"><span>Artículos</span><strong>${stats.total_articles}</strong></div>
          <div class="src-stat"><span>Score avg</span><strong>${stats.avg_score ?? "—"}</strong></div>`;
      } catch {}
    });
  } catch(e) { console.error(e); }
}

async function toggleSrc(id) {
  try { await api(`/sources/${id}/toggle`, { method: "PATCH" }); loadSrcs(); }
  catch(e) { toast("Error", "err"); }
}

async function delSrc(id, name) {
  if (!confirm(`Eliminar "${name}"?`)) return;
  try {
    await api(`/sources/${id}`, { method: "DELETE" });
    toast("Fuente eliminada", "ok");
    loadSrcs(); loadStats(); loadSrcFilter();
  } catch(e) { toast("Error al eliminar", "err"); }
}

async function importOPML(input) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    toast("Importando OPML...", "info");
    const r = await fetch(API + "/sources/opml", { method: "POST", body: form });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    toast(`✓ ${d.added} fuentes importadas desde OPML`, "ok");
    loadSrcs(); loadSrcFilter();
  } catch(e) { toast("Error al importar OPML", "err"); }
  input.value = "";
}

function openModal()  { document.getElementById("overlay").classList.add("on"); document.getElementById("f-name").focus(); }
function closeModal() { document.getElementById("overlay").classList.remove("on"); }

async function addSrc() {
  const name = document.getElementById("f-name").value.trim();
  const type = document.getElementById("f-type").value;
  const url  = document.getElementById("f-url").value.trim();
  if (!name || !url) { toast("Completa todos los campos", "err"); return; }
  try {
    await api("/sources", { method: "POST", body: JSON.stringify({ name, source_type: type, url }) });
    toast("✓ Fuente agregada", "ok");
    closeModal(); loadSrcs(); loadStats(); loadSrcFilter();
    document.getElementById("f-name").value = "";
    document.getElementById("f-url").value  = "";
  } catch(e) { toast("Error al agregar", "err"); }
}

/* ══════════════════════════════════════════════════════
   FILTERS
══════════════════════════════════════════════════════ */
async function loadSrcFilter() {
  try {
    const list = await api("/sources");
    const sel  = document.getElementById("src-filter");
    sel.innerHTML = '<option value="">Todas las fuentes</option>';
    list.forEach(s => { sel.innerHTML += `<option value="${s.id}">${esc(s.name)}</option>`; });
  } catch {}
}

async function loadCatFilter() {
  try {
    const d   = await api("/categories");
    const sel = document.getElementById("cat-filter");
    sel.innerHTML = '<option value="">Todas las categorías</option>';
    d.categories.forEach(c => { sel.innerHTML += `<option value="${esc(c)}">${esc(c)}</option>`; });
  } catch {}
}

/* ══════════════════════════════════════════════════════
   CHARTS
══════════════════════════════════════════════════════ */
async function loadCharts() {
  const days = document.getElementById("chart-days")?.value || 7;
  try {
    const d = await api(`/stats/chart?days=${days}`);

    const chartOpts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#a1a1aa", font: { size: 11 }, boxWidth: 12, padding: 10 } } },
    };
    const gridColor = "rgba(255,255,255,0.05)";
    const tickColor = "#71717a";

    // Daily
    const ctxD = document.getElementById("chart-daily").getContext("2d");
    if (chartDaily) chartDaily.destroy();
    chartDaily = new Chart(ctxD, {
      type: "line",
      data: {
        labels: d.daily.map(r => r.day),
        datasets: [{
          label: "Artículos",
          data: d.daily.map(r => r.count),
          borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.10)",
          borderWidth: 2, pointRadius: 4, pointBackgroundColor: "#6366f1",
          fill: true, tension: 0.4,
        }],
      },
      options: {
        ...chartOpts,
        plugins: { ...chartOpts.plugins, legend: { display: false } },
        scales: {
          x: { ticks: { color: tickColor, font: { size: 10 } }, grid: { color: gridColor } },
          y: { ticks: { color: tickColor, font: { size: 10 }, stepSize: 1 }, grid: { color: gridColor }, beginAtZero: true },
        },
      },
    });

    // Category doughnut
    const palette = ["#6366f1","#22c55e","#3b82f6","#eab308","#ef4444","#a855f7","#f97316","#14b8a6"];
    const ctxC = document.getElementById("chart-cat").getContext("2d");
    if (chartCat) chartCat.destroy();
    chartCat = new Chart(ctxC, {
      type: "doughnut",
      data: {
        labels: d.categories.map(r => r.category),
        datasets: [{ data: d.categories.map(r => r.count), backgroundColor: palette, borderColor: "var(--bg)", borderWidth: 2 }],
      },
      options: { ...chartOpts, cutout: "65%" },
    });

    // Sentiment bar
    const ctxS = document.getElementById("chart-sentiment").getContext("2d");
    if (chartSentiment) chartSentiment.destroy();
    const sentColors = { positive: "#22c55e", neutral: "#3b82f6", negative: "#ef4444" };
    chartSentiment = new Chart(ctxS, {
      type: "bar",
      data: {
        labels: (d.sentiments || []).map(r => r.sentiment),
        datasets: [{
          label: "Artículos",
          data: (d.sentiments || []).map(r => r.count),
          backgroundColor: (d.sentiments || []).map(r => sentColors[r.sentiment] || "#6366f1"),
          borderRadius: 6,
        }],
      },
      options: {
        ...chartOpts,
        plugins: { ...chartOpts.plugins, legend: { display: false } },
        scales: {
          x: { ticks: { color: tickColor }, grid: { display: false } },
          y: { ticks: { color: tickColor, stepSize: 1 }, grid: { color: gridColor }, beginAtZero: true },
        },
      },
    });
  } catch(e) { console.error(e); }
}

/* ══════════════════════════════════════════════════════
   HEATMAP
══════════════════════════════════════════════════════ */
async function loadHeatmap() {
  try {
    const d = await api("/stats/heatmap");

    // Hours bar chart
    const maxH = Math.max(...d.hours.map(h => h.count), 1);
    const hGrid = document.getElementById("hm-hours");
    hGrid.innerHTML = d.hours.map(h => {
      const pct = Math.round((h.count / maxH) * 100);
      const barH = Math.max(pct * 1.5, 4);
      const hue  = 240 + Math.round((pct / 100) * 60); // blue → purple
      return `<div class="hm-bar-item">
        <div class="hm-bar-val">${h.count || ""}</div>
        <div class="hm-bar-fill" style="height:${barH}px;background:hsl(${hue},70%,60%)"></div>
        <div class="hm-bar-label">${String(h.hour).padStart(2,"0")}h</div>
      </div>`;
    }).join("");

    // Days
    const maxD = Math.max(...d.days.map(d => d.count), 1);
    const wGrid = document.getElementById("hm-days");
    wGrid.innerHTML = d.days.map(day => {
      const pct = Math.round((day.count / maxD) * 100);
      return `<div class="hm-week-row">
        <span class="hm-week-label">${day.day_name}</span>
        <div class="hm-week-bar">
          <div class="hm-week-fill" style="width:${pct}%;background:linear-gradient(90deg,#6366f1,#a855f7)"></div>
        </div>
        <span class="hm-week-val">${day.count}</span>
      </div>`;
    }).join("");
  } catch(e) { console.error(e); }
}

/* ══════════════════════════════════════════════════════
   TRENDING
══════════════════════════════════════════════════════ */
async function loadTrending() {
  const hours = document.getElementById("trend-hours")?.value || 24;
  try {
    const d   = await api(`/stats/trending?hours=${hours}&limit=30`);
    const c   = document.getElementById("trending-list");
    if (!d.topics.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">📊</span><h3>Sin datos</h3><p>Aún no hay suficientes artículos</p></div>`;
      return;
    }
    const max = d.topics[0].count;
    const palette = ["#6366f1","#22c55e","#3b82f6","#eab308","#a855f7","#f97316","#14b8a6","#ef4444"];
    c.innerHTML = d.topics.map((t, i) => {
      const size = 0.75 + (t.count / max) * 0.85;
      const col  = palette[i % palette.length];
      return `<div class="trend-word" style="font-size:${size.toFixed(2)}rem;color:${col};border-color:${col}22"
        onclick="searchTrend('${esc(t.word)}')"
        title="${t.count} menciones">
        ${esc(t.word)} <span style="font-size:0.65em;opacity:0.7">${t.count}</span>
      </div>`;
    }).join("");
  } catch(e) { console.error(e); }
}

function searchTrend(word) {
  searchQ = word;
  document.getElementById("q").value = word;
  go("arts");
}

/* ══════════════════════════════════════════════════════
   KEYWORDS
══════════════════════════════════════════════════════ */
async function loadKeywords() {
  try {
    const list = await api("/keywords");
    const c    = document.getElementById("kw-list");
    if (!list.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">🔑</span><h3>Sin keywords</h3><p>Agrega palabras clave para recibir alertas</p></div>`;
      return;
    }
    c.innerHTML = list.map(k => `<div class="kw-item${k.is_active ? "" : " kw-inactive"}">
      <span class="kw-word">#${esc(k.keyword)}</span>
      <span class="kw-date">${fmtDate(k.created_at)}</span>
      <button class="btn ${k.is_active ? "btn-warn" : "btn-s"} btn-xs" onclick="toggleKw(${k.id})">
        ${k.is_active ? "⏸ Pausar" : "▶ Activar"}
      </button>
      <button class="btn btn-d btn-xs" onclick="delKw(${k.id},'${esc(k.keyword)}')">✕</button>
    </div>`).join("");
  } catch(e) { console.error(e); }
}

async function addKw() {
  const inp = document.getElementById("kw-input");
  const kw  = inp.value.trim();
  if (!kw) return;
  try {
    await api("/keywords", { method: "POST", body: JSON.stringify({ keyword: kw }) });
    toast(`🔑 "${kw}" agregada`, "ok");
    inp.value = "";
    loadKeywords(); loadStats();
  } catch(e) {
    toast(e.status === 409 ? "Ya existe esa keyword" : "Error al agregar", "err");
  }
}

async function toggleKw(id) {
  try { await api(`/keywords/${id}/toggle`, { method: "PATCH" }); loadKeywords(); }
  catch { toast("Error", "err"); }
}

async function delKw(id, word) {
  if (!confirm(`Eliminar "#${word}"?`)) return;
  try {
    await api(`/keywords/${id}`, { method: "DELETE" });
    toast("Keyword eliminada", "ok");
    loadKeywords(); loadStats();
  } catch { toast("Error", "err"); }
}

/* ══════════════════════════════════════════════════════
   WEBHOOKS
══════════════════════════════════════════════════════ */
async function loadWebhooks() {
  try {
    const list = await api("/webhooks");
    const c    = document.getElementById("wh-list");
    if (!list.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">🔗</span><h3>Sin webhooks</h3><p>Agrega un webhook para integrar con n8n, Zapier, etc.</p></div>`;
      return;
    }
    c.innerHTML = list.map(wh => `<div class="wh-card${wh.is_active ? "" : " wh-inactive"}">
      <div class="wh-top">
        <div>
          <div class="wh-name">${esc(wh.name)}</div>
          <div class="wh-url">${esc(wh.url)}</div>
        </div>
        <div style="display:flex;gap:4px">
          <button class="btn ${wh.is_active ? "btn-warn" : "btn-s"} btn-xs" onclick="toggleWh(${wh.id})">
            ${wh.is_active ? "⏸" : "▶"}
          </button>
          <button class="btn btn-d btn-xs" onclick="delWh(${wh.id})">✕</button>
        </div>
      </div>
      <div class="wh-events">
        ${wh.events.split(",").map(ev => `<span class="wh-event-tag">${esc(ev.trim())}</span>`).join("")}
      </div>
      ${wh.last_fired_at ? `<div style="font-size:0.68rem;color:var(--text-muted);margin-top:6px">Último envío: ${fmtDate(wh.last_fired_at)}</div>` : ""}
    </div>`).join("");
  } catch(e) { console.error(e); }
}

function openWebhookModal()  { document.getElementById("overlay-wh").classList.add("on"); document.getElementById("wh-name").focus(); }
function closeWebhookModal() { document.getElementById("overlay-wh").classList.remove("on"); }

async function addWebhook() {
  const name   = document.getElementById("wh-name").value.trim();
  const url    = document.getElementById("wh-url").value.trim();
  const events = document.getElementById("wh-events").value.trim();
  const secret = document.getElementById("wh-secret").value.trim();
  if (!name || !url) { toast("Nombre y URL son obligatorios", "err"); return; }
  try {
    await api("/webhooks", { method: "POST", body: JSON.stringify({ name, url, events, secret: secret || null }) });
    toast("✓ Webhook agregado", "ok");
    closeWebhookModal();
    ["wh-name","wh-url","wh-secret"].forEach(id => document.getElementById(id).value = "");
    document.getElementById("wh-events").value = "fetch,keyword";
    loadWebhooks();
  } catch { toast("Error al agregar webhook", "err"); }
}

async function toggleWh(id) {
  try { await api(`/webhooks/${id}/toggle`, { method: "PATCH" }); loadWebhooks(); }
  catch { toast("Error", "err"); }
}

async function delWh(id) {
  if (!confirm("Eliminar este webhook?")) return;
  try { await api(`/webhooks/${id}`, { method: "DELETE" }); toast("Webhook eliminado", "ok"); loadWebhooks(); }
  catch { toast("Error", "err"); }
}

/* ══════════════════════════════════════════════════════
   NOTIFICATIONS
══════════════════════════════════════════════════════ */
function updateNotifBadge(n) {
  const badge = document.getElementById("notif-badge");
  if (!badge) return;
  if (n > 0) { badge.style.display = "inline"; badge.textContent = n > 99 ? "99+" : n; }
  else badge.style.display = "none";
}

async function loadNotifBadge() {
  try {
    const d = await api("/stats");
    updateNotifBadge(d.unread_notifications);
  } catch {}
}

function openNotifications() {
  document.getElementById("notif-panel").classList.add("on");
  const ov = document.getElementById("notif-overlay");
  if (ov) ov.classList.add("on");
  loadNotifications();
}
function closeNotifications() {
  document.getElementById("notif-panel").classList.remove("on");
  const ov = document.getElementById("notif-overlay");
  if (ov) ov.classList.remove("on");
}

async function loadNotifications() {
  try {
    const list = await api("/notifications?limit=50");
    const c    = document.getElementById("notif-list");
    if (!list.length) {
      c.innerHTML = `<div class="notif-empty">No hay notificaciones recientes</div>`;
      return;
    }
    c.innerHTML = list.map(n => `<div class="notif-item${n.read ? "" : " unread"}">
      <div class="notif-icon">${NOTIF_ICON[n.type] || "ℹ️"}</div>
      <div class="notif-content">
        <div class="notif-title">${esc(n.title)}</div>
        <div class="notif-msg">${esc(n.message)}</div>
        <div class="notif-time">${fmtDate(n.created_at)}</div>
      </div>
    </div>`).join("");
    updateNotifBadge(list.filter(n => !n.read).length);
  } catch(e) { console.error(e); }
}

async function markAllRead() {
  try {
    await api("/notifications/read-all", { method: "POST" });
    loadNotifications();
    updateNotifBadge(0);
  } catch {}
}

async function clearNotifs() {
  if (!confirm("¿Limpiar todo el historial de notificaciones?")) return;
  try {
    await api("/notifications", { method: "DELETE" });
    loadNotifications();
    updateNotifBadge(0);
  } catch {}
}

/* ══════════════════════════════════════════════════════
   DIGEST CONFIG
══════════════════════════════════════════════════════ */
async function loadDigestConfig() {
  try {
    const cfg = await api("/digest/config");
    document.getElementById("cfg-hour").value    = cfg.hour;
    document.getElementById("cfg-count").value   = cfg.count;
    document.getElementById("cfg-score").value   = cfg.min_score;
    document.getElementById("cfg-cats").value    = cfg.categories || "";
    document.getElementById("cfg-active").checked = cfg.is_active;
  } catch {}
}

async function saveCfg() {
  const body = {
    hour:       parseInt(document.getElementById("cfg-hour").value),
    count:      parseInt(document.getElementById("cfg-count").value),
    min_score:  parseInt(document.getElementById("cfg-score").value),
    categories: document.getElementById("cfg-cats").value.trim() || null,
    is_active:  document.getElementById("cfg-active").checked,
  };
  try {
    await api("/digest/config", { method: "PATCH", body: JSON.stringify(body) });
    toast("✓ Configuración guardada", "ok");
  } catch { toast("Error al guardar", "err"); }
}

/* ══════════════════════════════════════════════════════
   SYSTEM STATUS
══════════════════════════════════════════════════════ */
async function loadSystemStatus() {
  const c = document.getElementById("cfg-status");
  try {
    const d = await api("/stats");
    c.innerHTML = `
      <div class="cfg-status-item"><span>Base de datos</span><span class="status-ok">OK</span></div>
      <div class="cfg-status-item"><span>API backend</span><span class="status-ok">OK</span></div>
      <div class="cfg-status-item"><span>Artículos totales</span><span>${d.total_articles}</span></div>
      <div class="cfg-status-item"><span>Fuentes activas</span><span>${d.total_sources}</span></div>
      <div class="cfg-status-item"><span>NewsLet versión</span><span>v3.0</span></div>`;
  } catch {
    c.innerHTML = `<div class="cfg-status-item"><span>API backend</span><span class="status-err">ERROR</span></div>`;
  }
}

/* ══════════════════════════════════════════════════════
   MODAL CLICK-OUTSIDE & ESC
══════════════════════════════════════════════════════ */
document.addEventListener("click", e => {
  if (e.target.id === "overlay")    closeModal();
  if (e.target.id === "overlay-wh") closeWebhookModal();
  if (e.target.id === "overlay-reader") closeReader();
});

/* ══════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════ */
(function init() {
  // Apply saved art view
  setViewClass(document.getElementById("art-list"), artView);
  setViewClass(document.getElementById("dash-list"), dashView);

  // Mark correct view toggle buttons
  const artBtn = document.querySelector(`#art-view-toggle .vt-btn:nth-child(${["list","grid","compact"].indexOf(artView)+1})`);
  if (artBtn) { document.querySelectorAll("#art-view-toggle .vt-btn").forEach(b=>b.classList.remove("on")); artBtn.classList.add("on"); }

  loadStats();
  loadDash();
  loadSrcFilter();
  loadCatFilter();
  renderSavedSearches();
  connectWS();

  // Poll notification badge every 60s
  setInterval(loadNotifBadge, 60000);
})();

/* ══════════════════════════════════════════════════════
   ADMIN SETTINGS
══════════════════════════════════════════════════════ */

// Fields that are masked (password inputs — we never pre-fill them from API)
const _MASKED_FIELDS = new Set([
  "GROQ_API_KEY","OPENAI_API_KEY","TELEGRAM_BOT_TOKEN",
  "ADMIN_PASSWORD","JWT_SECRET","SMTP_PASSWORD","NEWSAPI_KEY","PANEL_PIN",
]);

async function loadAdminSettings() {
  // Hide restart notice whenever we (re)load the settings page
  const notice = document.getElementById("admin-restart-notice");
  if (notice) notice.style.display = "none";
  try {
    const { settings } = await api("/admin/settings");
    for (const [key, info] of Object.entries(settings)) {
      const el = document.getElementById("sf-" + key);
      if (!el) continue;
      // Never pre-fill masked/password fields
      if (_MASKED_FIELDS.has(key)) {
        el.placeholder = info.value === "••••••••" ? "••••••• (configurado)" : "Vacío";
        el.value = "";
      } else {
        if (el.tagName === "SELECT") {
          el.value = info.value;
        } else {
          el.value = info.value;
        }
      }
    }
  } catch (e) {
    toast("Error cargando configuración: " + e.message, "err");
  }
}

async function saveAdminSettings() {
  const updates = {};
  // Collect all sf-* fields
  document.querySelectorAll("[id^='sf-']").forEach(el => {
    const key = el.id.replace("sf-", "");
    const val = el.value.trim();
    // For masked fields: only include if user typed something new
    if (_MASKED_FIELDS.has(key)) {
      if (val && val !== "•••••••") updates[key] = val;
    } else {
      updates[key] = val;
    }
  });

  if (Object.keys(updates).length === 0) {
    toast("No hay cambios para guardar", "info");
    return;
  }

  try {
    const result = await api("/admin/settings", {
      method: "POST",
      body: JSON.stringify({ updates }),
    });
    toast(result.message, "ok");
    if (result.restart_needed) {
      document.getElementById("admin-restart-notice").style.display = "block";
    }
    // Clear password fields after save
    _MASKED_FIELDS.forEach(key => {
      const el = document.getElementById("sf-" + key);
      if (el) { el.value = ""; el.placeholder = "••••••• (guardado)"; }
    });
  } catch (e) {
    toast("Error guardando: " + e.message, "err");
  }
}

async function testEmail() {
  toast("Enviando email de prueba...", "info");
  try {
    const r = await api("/digest/email", { method: "POST" });
    if (r.sent > 0) {
      toast(`✅ Email enviado a ${r.recipients.join(", ")}`, "ok");
    } else {
      toast("❌ " + (r.error || JSON.stringify(r.errors)), "err");
    }
  } catch (e) {
    toast("Error: " + e.message, "err");
  }
}

/* ══════════════════════════════════════════════════════
   MOBILE — Swipe gestures
══════════════════════════════════════════════════════ */
(function initMobileGestures() {
  let touchStartX = 0, touchStartY = 0;
  const SWIPE_THRESHOLD = 60;
  const EDGE_ZONE = 30; // px from left edge to start open gesture

  document.addEventListener("touchstart", e => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  document.addEventListener("touchend", e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    // Only treat as horizontal swipe if mostly horizontal
    if (Math.abs(dy) > Math.abs(dx) * 0.8) return;

    const sb = document.getElementById("sidebar");
    const isMobile = window.innerWidth <= 700;
    if (!isMobile) return;

    // Swipe right from left edge → open sidebar
    if (dx > SWIPE_THRESHOLD && touchStartX < EDGE_ZONE && !sb.classList.contains("mobile-open")) {
      toggleSidebar();
    }
    // Swipe left while sidebar open → close sidebar
    if (dx < -SWIPE_THRESHOLD && sb.classList.contains("mobile-open")) {
      closeSidebar();
    }
  }, { passive: true });

  // Close sidebar on Escape key
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      const sb = document.getElementById("sidebar");
      if (sb && sb.classList.contains("mobile-open")) closeSidebar();
    }
  });
})();
