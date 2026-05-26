/* SOURCES
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
    c.innerHTML = list.map(s => {
      const isDead = s.disabled_at || (!s.is_active && s.consecutive_failures > 0);
      const healthBadge = isDead
        ? `<span class="src-health-err" title="${esc(s.last_error || '')}">⚠ ${s.consecutive_failures} fallos</span>`
        : s.consecutive_failures > 0
          ? `<span class="src-health-warn" title="${esc(s.last_error || '')}">⚡ ${s.consecutive_failures}</span>`
          : "";
      const reactivarBtn = isDead
        ? `<button class="btn btn-s btn-xs" onclick="reenableSrc(${s.id})" title="Resetea fallos y reactiva">↺ Reactivar</button>`
        : `<button class="btn ${s.is_active ? "btn-warn" : "btn-s"} btn-xs" onclick="toggleSrc(${s.id})">
             ${s.is_active ? "⏸ Pausar" : "▶ Activar"}
           </button>`;
      return `<div class="src-card${s.is_active ? "" : " src-inactive"}${isDead ? " src-dead" : ""}" id="src-${s.id}">
        <div class="src-top">
          <span class="src-name">${esc(s.name)}</span>
          <div style="display:flex;gap:4px;align-items:center">
            ${healthBadge}
            <span class="src-type">${s.source_type}</span>
          </div>
        </div>
        <div class="src-url" title="${esc(s.url)}">${esc(s.url)}</div>
        <div class="src-stats" id="src-stats-${s.id}">
          <div class="src-stat"><span>Artículos</span><strong>—</strong></div>
          <div class="src-stat"><span>Score avg</span><strong>—</strong></div>
        </div>
        <div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center">
          ${reactivarBtn}
          <button class="btn btn-d btn-xs" onclick="delSrc(${s.id},'${esc(s.name)}')">Eliminar</button>
        </div>
      </div>`;
    }).join("");

    document.getElementById("n-srcs").textContent = list.length;

    // Fetch stats per source
    list.forEach(async s => {
      try {
        const stats = await api(`/sources/${s.id}/stats`);
        const el = document.getElementById(`src-stats-${s.id}`);
        if (!el) return;
        el.innerHTML = `
          <div class="src-stat"><span>Total</span><strong>${stats.total_articles}</strong></div>
          <div class="src-stat"><span>Esta semana</span><strong>${stats.articles_week}</strong></div>
          <div class="src-stat"><span>Score avg</span><strong>${stats.avg_score ?? "—"}</strong></div>
          <div class="src-stat"><span>Rechazo</span><strong>${stats.rejection_rate}%</strong></div>`;
      } catch {}
    });
  } catch(e) { console.error(e); }
}

async function toggleSrc(id) {
  try { await api(`/sources/${id}/toggle`, { method: "PATCH" }); loadSrcs(); }
  catch(e) { toast("Error", "err"); }
}

async function reenableSrc(id) {
  try {
    await api(`/sources/${id}/reenable`, { method: "POST" });
    toast("✓ Fuente reactivada", "ok");
    loadSrcs();
  } catch(e) { toast("Error al reactivar", "err"); }
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
   SOURCE PREVIEW (Tier 1.1)
══════════════════════════════════════════════════════ */
async function previewSource() {
  const url  = document.getElementById("f-url").value.trim();
  const type = document.getElementById("f-type").value;
  if (!url) { toast("Ingresa una URL primero", "err"); return; }

  const btn  = document.getElementById("preview-btn");
  const area = document.getElementById("preview-area");
  btn.disabled = true;
  btn.textContent = "Probando...";
  area.style.display = "block";
  area.innerHTML = `<div class="preview-loading">⟳ Conectando con la fuente...</div>`;

  try {
    const d = await api("/sources/preview", {
      method: "POST",
      body: JSON.stringify({ url, source_type: type }),
    });

    const ytBadge = d.is_youtube
      ? `<span class="src-type" style="background:rgba(239,68,68,0.15);color:#f87171;margin-left:6px">▶ YouTube RSS</span>`
      : "";
    area.innerHTML = `
      <div class="preview-head">
        <span class="preview-feed-title">${esc(d.feed_title || "Feed sin título")}</span>
        ${ytBadge}
        <span class="preview-count">${d.total_entries} entradas</span>
      </div>
      ${d.resolved_url !== url ? `<div class="preview-resolved">→ URL resuelta: <code>${esc(d.resolved_url)}</code></div>` : ""}
      <div class="preview-articles">
        ${(d.articles || []).map(a => `<div class="preview-art">
          <div class="preview-art-title">${esc(a.title)}</div>
          ${a.summary ? `<div class="preview-art-sum">${esc(a.summary)}</div>` : ""}
          ${a.published_at ? `<div class="preview-art-date">${new Date(a.published_at).toLocaleDateString("es")}</div>` : ""}
        </div>`).join("")}
      </div>`;

    // Auto-fill resolved URL (YouTube) and name
    if (d.is_youtube && d.resolved_url) document.getElementById("f-url").value = d.resolved_url;
    if (d.feed_title && !document.getElementById("f-name").value.trim())
      document.getElementById("f-name").value = d.feed_title.slice(0, 100);

  } catch(e) {
    area.innerHTML = `<div class="preview-err">✕ ${esc(e.message || "Error al conectar con la fuente")}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Probar URL";
  }
}

/* ══════════════════════════════════════════════════════
   POPULAR SOURCES CATALOGUE (Tier 1.1)
══════════════════════════════════════════════════════ */
async function showCatalogue() {
  const overlay = document.getElementById("overlay-catalogue");
  overlay.classList.add("on");
  const list = document.getElementById("catalogue-list");
  list.innerHTML = `<div class="preview-loading">Cargando catálogo...</div>`;

  try {
    const d = await api("/sources/catalogue");
    const byCategory = {};
    d.sources.forEach(s => {
      if (!byCategory[s.category]) byCategory[s.category] = [];
      byCategory[s.category].push(s);
    });
    list.innerHTML = Object.entries(byCategory).map(([cat, srcs]) => `
      <div class="catalogue-cat">
        <div class="catalogue-cat-name">${esc(cat)}</div>
        <div class="catalogue-items">
          ${srcs.map(s => `<div class="catalogue-item">
            <div class="catalogue-item-name">${esc(s.name)}</div>
            <button class="btn btn-s btn-xs cat-add-btn" onclick="addCatalogueSource('${esc(s.name)}','${s.source_type}','${esc(s.url)}',this)">+ Agregar</button>
          </div>`).join("")}
        </div>
      </div>`).join("");
  } catch(e) {
    list.innerHTML = `<div class="preview-err">Error al cargar el catálogo</div>`;
  }
}

async function addCatalogueSource(name, type, url, btn) {
  btn.disabled = true;
  btn.textContent = "...";
  try {
    await api("/sources", { method: "POST", body: JSON.stringify({ name, source_type: type, url }) });
    btn.textContent = "✓ Agregado";
    btn.className = "btn btn-ok btn-xs cat-add-btn";
    loadSrcs(); loadSrcFilter();
  } catch(e) {
    if (e.status === 409 || (e.message && e.message.includes("UNIQUE"))) {
      btn.textContent = "Ya existe";
    } else {
      btn.textContent = "Error";
      btn.disabled = false;
    }
  }
}

function closeCatalogue() { document.getElementById("overlay-catalogue").classList.remove("on"); }