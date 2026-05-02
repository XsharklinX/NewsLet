/* ══════════════════════════════════════════════════════
   HEATMAP — Activity map by hour and weekday
══════════════════════════════════════════════════════ */
async function loadHeatmap() {
  _hmSkeleton();
  try {
    const d = await api("/stats/heatmap");
    _hmRender(d);
  } catch(e) {
    console.error("[heatmap]", e);
    document.getElementById("hm-hours").innerHTML =
      `<div style="color:var(--danger);padding:16px;font-size:13px">Error al cargar datos</div>`;
  }
}

function _hmSkeleton() {
  const hoursEl = document.getElementById("hm-hours");
  const daysEl  = document.getElementById("hm-days");
  if (hoursEl) hoursEl.innerHTML = Array.from({length:24}, () =>
    `<div class="hm-bar-item"><div class="skeleton" style="height:60px;width:100%;border-radius:4px"></div><div class="skeleton skeleton-h-12" style="width:24px;border-radius:4px;margin-top:4px"></div></div>`
  ).join("");
  if (daysEl) daysEl.innerHTML = Array.from({length:7}, () =>
    `<div class="hm-week-row"><div class="skeleton" style="width:70px;height:14px;border-radius:4px"></div><div class="skeleton" style="flex:1;height:14px;border-radius:4px;margin:0 8px"></div><div class="skeleton" style="width:28px;height:14px;border-radius:4px"></div></div>`
  ).join("");
}

function _hmRender(d) {
  const palette = (pct) => {
    if (pct === 0) return "rgba(255,255,255,0.06)";
    if (pct < 25)  return "rgba(99,102,241,0.35)";
    if (pct < 50)  return "rgba(99,102,241,0.60)";
    if (pct < 75)  return "rgba(139,92,246,0.80)";
    return "#a855f7";
  };

  // ── Hours ──────────────────────────────────────────
  const maxH = Math.max(...d.hours.map(h => h.count), 1);
  const maxBarH = 80; // px — the tallest bar gets this height
  const hoursEl = document.getElementById("hm-hours");
  const nowH = new Date().getHours();

  hoursEl.innerHTML = d.hours.map(h => {
    const pct  = (h.count / maxH) * 100;
    const barH = h.count > 0 ? Math.max(Math.round((h.count / maxH) * maxBarH), 8) : 6;
    const bg   = palette(pct);
    const isCurrent = h.hour === nowH;
    return `<div class="hm-bar-item${isCurrent ? " hm-bar-now" : ""}">
      <div class="hm-bar-val">${h.count || ""}</div>
      <div class="hm-bar-fill" style="height:${barH}px;background:${bg};border-radius:3px 3px 0 0"></div>
      <div class="hm-bar-label">${String(h.hour).padStart(2,"0")}</div>
    </div>`;
  }).join("");

  // ── Days ───────────────────────────────────────────
  const maxD = Math.max(...d.days.map(d => d.count), 1);
  const daysEl = document.getElementById("hm-days");
  const nowDay = (new Date().getDay() + 6) % 7; // Mon-first

  daysEl.innerHTML = d.days.map(day => {
    const pct   = (day.count / maxD) * 100;
    const isNow = day.day === nowDay;
    return `<div class="hm-week-row${isNow ? " hm-day-now" : ""}">
      <span class="hm-week-label">${day.day_name}</span>
      <div class="hm-week-bar">
        <div class="hm-week-fill" style="width:${Math.max(pct,2)}%;background:${palette(pct)};transition:width .6s cubic-bezier(.4,0,.2,1)"></div>
      </div>
      <span class="hm-week-val">${day.count}</span>
    </div>`;
  }).join("");

  // ── Summary stats ──────────────────────────────────
  const peakHour = d.hours.reduce((a, b) => a.count >= b.count ? a : b, d.hours[0]);
  const peakDay  = d.days.reduce((a, b) => a.count >= b.count ? a : b, d.days[0]);
  const totalArts = d.hours.reduce((s, h) => s + h.count, 0);
  const avgDay    = totalArts > 0 ? Math.round(totalArts / 7) : 0;

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set("hm-peak-hour",  peakHour.count > 0 ? `${String(peakHour.hour).padStart(2,"0")}:00` : "—");
  set("hm-peak-day",   peakDay.count  > 0 ? peakDay.day_name : "—");
  set("hm-total-arts", totalArts.toLocaleString());
  set("hm-avg-day",    avgDay > 0 ? `~${avgDay}/día` : "—");
}


/* ══════════════════════════════════════════════════════
   TRENDING — Word cloud + ranked list
══════════════════════════════════════════════════════ */
async function loadTrending() {
  const hours = parseInt(document.getElementById("trend-hours")?.value || "24", 10);
  const cloud = document.getElementById("trending-list");
  const rank  = document.getElementById("trending-rank");

  if (cloud) cloud.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:24px">Cargando...</div>`;
  if (rank)  rank.innerHTML  = "";

  try {
    const d = await api(`/stats/trending?hours=${hours}&limit=40`);
    _trendRender(d, hours);
  } catch(e) {
    console.error("[trending]", e);
    if (cloud) cloud.innerHTML = `<div style="color:var(--danger);font-size:13px;padding:24px">Error al cargar datos</div>`;
  }
}

function _trendRender(d, hours) {
  const cloud   = document.getElementById("trending-list");
  const rank    = document.getElementById("trending-rank");
  const summary = document.getElementById("trend-summary");

  if (!d.topics.length) {
    if (cloud) cloud.innerHTML = `<div class="empty"><span class="e-icon">📊</span><h3>Sin datos</h3><p>Aún no hay suficientes artículos en este período</p></div>`;
    if (rank)  rank.innerHTML  = "";
    if (summary) summary.style.display = "none";
    return;
  }

  const palette = ["#6366f1","#8b5cf6","#22c55e","#3b82f6","#eab308","#a855f7","#f97316","#14b8a6","#ef4444","#ec4899"];
  const max = d.topics[0].count;

  // ── Summary row ────────────────────────────────────
  if (summary) {
    summary.style.display = "flex";
    const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
    const label = {6:"6h", 24:"24h", 72:"3 días", 168:"semana"}[hours] || `${hours}h`;
    set("trend-total-words", `${d.topics.length} palabras`);
    set("trend-top-word",    `Top: "${d.topics[0].word}" ×${d.topics[0].count}`);
    set("trend-window",      `Ventana: últimas ${label}`);
  }

  // ── Word cloud ─────────────────────────────────────
  if (cloud) {
    cloud.innerHTML = d.topics.map((t, i) => {
      const ratio = t.count / max;
      const size  = (0.72 + ratio * 1.0).toFixed(2);
      const col   = palette[i % palette.length];
      const weight = ratio > 0.6 ? 700 : ratio > 0.3 ? 600 : 400;
      return `<button class="trend-word" style="font-size:${size}rem;color:${col};border-color:${col}28;font-weight:${weight}"
        onclick="searchTrend('${esc(t.word)}')"
        title="${t.count} menciones — clic para buscar">
        ${esc(t.word)}<sup class="trend-count">${t.count}</sup>
      </button>`;
    }).join("");
  }

  // ── Ranked list ────────────────────────────────────
  if (rank) {
    rank.innerHTML = d.topics.slice(0, 15).map((t, i) => {
      const pct = Math.round((t.count / max) * 100);
      const col = palette[i % palette.length];
      const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `<span class="trend-rank-num">${i+1}</span>`;
      return `<div class="trend-rank-row" onclick="searchTrend('${esc(t.word)}')" title="Buscar '${esc(t.word)}'">
        <span class="trend-rank-pos">${medal}</span>
        <span class="trend-rank-word">${esc(t.word)}</span>
        <div class="trend-rank-bar-wrap">
          <div class="trend-rank-bar" style="width:${pct}%;background:${col}"></div>
        </div>
        <span class="trend-rank-cnt" style="color:${col}">${t.count}</span>
      </div>`;
    }).join("");
  }
}

function searchTrend(word) {
  searchQ = word;
  const q = document.getElementById("q");
  if (q) q.value = word;
  go("arts");
}
