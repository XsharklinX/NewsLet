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