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
  if (v === "heatmap")  loadHeatmap();
  if (v === "trending") loadTrending();
  if (v === "kw")       loadKeywords();
  if (v === "webhooks") loadWebhooks();
  if (v === "cfg")      { loadDigestConfig(); loadSystemStatus(); }
  if (v === "logs")    loadLogs();
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
  if (key === "4")  { e.preventDefault(); go("trending"); return; }
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