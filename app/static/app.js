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
let savedSearches  = JSON.parse(localStorage.getItem("savedSearches") || "[]");
let savedArticles  = JSON.parse(localStorage.getItem("savedArticles")  || "[]");
let filterDateFrom = "";
let filterDateTo   = "";
let readerArticleId = null;
let draggedId = null;
let wsReconnectDelay = 1000;

// Sentiment emoji map
const SENT_EMOJI = { positive: "😊", neutral: "😐", negative: "😟" };
const NOTIF_ICON = { fetch: "🔄", keyword: "🔑", digest: "📬", error: "⚠️", info: "ℹ️", article_high_score: "⭐" };


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
