/* ══════════════════════════════════════════════════════
   BULK SELECTION
══════════════════════════════════════════════════════ */
const selectedIds = new Set();

function toggleSelect(id, cb) {
  if (cb.checked) selectedIds.add(id);
  else selectedIds.delete(id);
  updateBulkBar();
}

function updateBulkBar() {
  const bar = document.getElementById("bulk-bar");
  const cnt = document.getElementById("bulk-count");
  if (!bar) return;
  if (selectedIds.size > 0) {
    bar.style.display = "flex";
    if (cnt) cnt.textContent = selectedIds.size;
  } else {
    bar.style.display = "none";
  }
}

function clearSelection() {
  selectedIds.clear();
  document.querySelectorAll(".a-check input").forEach(cb => cb.checked = false);
  updateBulkBar();
}

async function bulkApprove() {
  if (!selectedIds.size) return;
  const ids = [...selectedIds];
  try {
    const d = await api("/articles/bulk-approve", { method: "POST", body: JSON.stringify(ids) });
    toast(`✓ ${d.approved} artículos aprobados`, "ok");
    clearSelection();
    loadArts(); loadStats(); loadDash();
  } catch(e) { toast("Error al aprobar en lote", "err"); }
}

async function bulkReject() {
  if (!selectedIds.size) return;
  const ids = [...selectedIds];
  try {
    const d = await api("/articles/bulk-reject", { method: "POST", body: JSON.stringify(ids) });
    toast(`✕ ${d.rejected} artículos rechazados`, "ok");
    clearSelection();
    loadArts(); loadStats(); loadDash();
  } catch(e) { toast("Error al rechazar en lote", "err"); }
}

/* STATS
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
    <label class="a-check" onclick="event.stopPropagation()" title="Seleccionar">
      <input type="checkbox" onchange="toggleSelect(${a.id},this)" ${selectedIds.has(a.id) ? "checked" : ""}>
    </label>
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

  // Load widgets in parallel
  loadDashWidgets();

  try {
    const d = await api("/articles?page=1&page_size=10");
    setViewClass(c, dashView);
    if (!d.articles.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">📰</span><h3>Sin artículos</h3><p>Usa "Actualizar ahora" para obtener noticias</p></div>`;
      return;
    }
    c.innerHTML = d.articles.map(a => card(a, dashView === "compact")).join("");
  } catch(e) {
    c.innerHTML = `<div class="empty"><span class="e-icon">⚠️</span><h3>Error al cargar</h3></div>`;
    console.error(e);
  }
}

async function loadDashWidgets() {
  // Trending mini
  try {
    const t = await api("/stats/trending?hours=24&limit=8");
    const el = document.getElementById("dash-trending-mini");
    if (el) {
      if (t.topics.length) {
        const max = t.topics[0].count;
        const palette = ["#6366f1","#22c55e","#3b82f6","#eab308","#a855f7","#f97316","#14b8a6","#ef4444"];
        el.innerHTML = t.topics.slice(0, 6).map((tp, i) =>
          `<span class="dash-trend-tag" style="border-color:${palette[i%palette.length]}44;color:${palette[i%palette.length]}"
            onclick="searchTrend('${esc(tp.word)}')" title="${tp.count} menciones">
            ${esc(tp.word)} <sup>${tp.count}</sup></span>`
        ).join("");
      } else {
        el.textContent = "Sin datos aún.";
      }
    }
  } catch {}

  // Heatmap mini (activity by hour)
  try {
    const h = await api("/stats/heatmap");
    const el = document.getElementById("dash-heatmap-mini");
    if (el && h.hours) {
      const max = Math.max(...h.hours.map(x => x.count), 1);
      el.innerHTML = h.hours.map(hr => {
        const pct  = Math.round((hr.count / max) * 100);
        const barH = Math.max(pct * 0.5, 2);
        const hue  = 240 + Math.round((pct / 100) * 60);
        return `<div class="dash-hm-bar" title="${hr.hour}h: ${hr.count} arts">
          <div class="dash-hm-fill" style="height:${barH}px;background:hsl(${hue},70%,60%)"></div>
          <div class="dash-hm-lbl">${String(hr.hour).padStart(2,"0")}</div>
        </div>`;
      }).join("");
    }
  } catch {}

  // Top articles by score (last 24h)
  try {
    const cutoff = new Date(Date.now() - 86400000).toISOString();
    const d = await api(`/articles?page=1&page_size=5&date_from=${cutoff}&min_score=5`);
    const el = document.getElementById("dash-top-mini");
    if (el) {
      if (d.articles.length) {
        const sorted = d.articles.slice().sort((a, b) => (b.relevance_score||0) - (a.relevance_score||0));
        el.innerHTML = sorted.slice(0,4).map(a =>
          `<div class="dash-top-item" onclick="openReader(${a.id})">
            <span class="dash-top-score">⭐${a.relevance_score||"?"}</span>
            <span class="dash-top-title">${esc(a.title)}</span>
          </div>`
        ).join("");
      } else {
        el.textContent = "Sin artículos relevantes hoy.";
      }
    }
  } catch {}

  // AI usage widget
  try {
    const u = await api("/stats/ai-usage?days=7");
    const el = document.getElementById("dash-ai-mini");
    if (el) {
      const todayTokens = u.daily.length ? u.daily[u.daily.length - 1].tokens : 0;
      el.innerHTML = `
        <div class="dash-ai-row">
          <span class="dash-ai-lbl">Total tokens</span>
          <span class="dash-ai-val">${u.total_tokens.toLocaleString()}</span>
        </div>
        <div class="dash-ai-row">
          <span class="dash-ai-lbl">Resúmenes</span>
          <span class="dash-ai-val">${u.total_summaries.toLocaleString()}</span>
        </div>
        <div class="dash-ai-row">
          <span class="dash-ai-lbl">Hoy</span>
          <span class="dash-ai-val">${todayTokens.toLocaleString()} tok</span>
        </div>
        <div class="dash-ai-row">
          <span class="dash-ai-lbl">Coste est.</span>
          <span class="dash-ai-val" style="color:var(--success)">$${u.estimated_cost_usd}</span>
        </div>`;
    }
  } catch {}
}

/* ══════════════════════════════════════════════════════
   ARTICLES LIST
══════════════════════════════════════════════════════ */
async function loadArts(p) {
  if (p !== undefined) { pg = p; clearSelection(); }
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
  } else {
    if (filterDateFrom) params.set("date_from", filterDateFrom + "T00:00:00");
    if (filterDateTo)   params.set("date_to",   filterDateTo   + "T23:59:59");
  }

  try {
    const d = await api("/articles?" + params);
    const c = document.getElementById("art-list");
    setViewClass(c, artView);
    if (!d.articles.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">🔍</span><h3>${searchQ ? "Sin resultados" : "Sin artículos"}</h3><p>${searchQ ? "Prueba otros términos" : "Usa Actualizar ahora"}</p></div>`;
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
function onDateFilter() {
  filterDateFrom = document.getElementById("date-from")?.value || "";
  filterDateTo   = document.getElementById("date-to")?.value   || "";
  loadArts(1);
}

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

    const rt = readTime(a.full_text || a.original_text);
    document.getElementById("r-meta").innerHTML =
      `<span title="${fmtDateFull(a.published_at || a.fetched_at)}">${fmtDate(a.published_at || a.fetched_at)}</span>` +
      (a.source?.name ? ` · ${esc(a.source.name)}` : "") +
      (a.relevance_score ? ` · ⭐ ${a.relevance_score}/10` : "") +
      (a.sentiment ? ` · ${SENT_EMOJI[a.sentiment] || ""} ${a.sentiment}` : "") +
      (rt ? ` · ⏱ ${rt} lectura` : "");

    // Thumbnail
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

    // Structured summary (key_point / context_note / impact)
    const structEl = document.getElementById("r-structured");
    const sumEl    = document.getElementById("r-summary");
    if (a.summary?.key_point) {
      document.getElementById("r-keypoint").textContent = a.summary.key_point;
      document.getElementById("r-context").textContent  = a.summary.context_note || "";
      document.getElementById("r-impact").textContent   = a.summary.impact || "";
      const ctxRow = document.getElementById("r-context").closest(".rs-item");
      const impRow = document.getElementById("r-impact").closest(".rs-item");
      if (ctxRow) ctxRow.style.display = a.summary.context_note ? "" : "none";
      if (impRow) impRow.style.display = a.summary.impact ? "" : "none";
      structEl.style.display = "block";
      sumEl.style.display    = "none";
    } else {
      structEl.style.display = "none";
      sumEl.textContent      = a.summary?.summary_text || "";
      sumEl.style.display    = a.summary ? "block" : "none";
    }

    const text = a.full_text || a.original_text || "Sin texto completo disponible.";
    document.getElementById("r-body").textContent = cleanTxt(text);

    // Send button
    const sendBtn = document.getElementById("r-send-btn");
    sendBtn.style.display = a.summary && a.status !== "sent" ? "inline-flex" : "none";

    // Save/bookmark button
    const saveBtn = document.getElementById("r-save-btn");
    const isSaved = savedArticles.some(s => s.id === a.id);
    saveBtn.textContent = isSaved ? "🔖✓" : "🔖";
    saveBtn.title = isSaved ? "Guardado" : "Guardar artículo";

    document.getElementById("overlay-reader").classList.add("on");
    loadRelated(id);
  } catch(e) { toast("Error al cargar artículo", "err"); }
}

function toggleSave() {
  if (!readerArticleId) return;
  const idx = savedArticles.findIndex(s => s.id === readerArticleId);
  if (idx >= 0) {
    savedArticles.splice(idx, 1);
    document.getElementById("r-save-btn").textContent = "🔖";
    toast("Artículo removido de guardados", "info");
  } else {
    const title = document.getElementById("r-title").textContent;
    savedArticles.push({ id: readerArticleId, title, saved_at: new Date().toISOString() });
    document.getElementById("r-save-btn").textContent = "🔖✓";
    toast("✓ Artículo guardado", "ok");
  }
  localStorage.setItem("savedArticles", JSON.stringify(savedArticles));
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
  toast("✉ Enviando noticias diarias...", "info");
  try {
    await api("/digest/now", { method: "POST" });
    toast("✉ Noticias diarias enviadas", "ok");
    loadStats(); loadNotifBadge();
  } catch(e) { toast("Error al enviar noticias diarias", "err"); }
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

function dlMarkdown() {
  const params = new URLSearchParams({ count: 30 });
  if (filterStatus) params.set("status",    filterStatus);
  if (filterCat)    params.set("category",  filterCat);
  if (filterScore)  params.set("min_score", filterScore);
  window.open(API + "/articles/export/markdown?" + params, "_blank");
}

function dlPDF() {
  const params = new URLSearchParams({ limit: 20, min_score: 0 });
  if (filterCat)   params.set("category", filterCat);
  if (filterScore) params.set("min_score", filterScore);
  window.open(API + "/digest/pdf?" + params, "_blank");
}