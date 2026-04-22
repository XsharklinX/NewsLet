/* KEYWORDS
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

  // Auto-refresh dashboard + stats every 10 minutes
  setInterval(() => {
    const currentView = document.querySelector(".view.on")?.id;
    if (currentView === "v-dash") { loadStats(); loadDash(); }
    else loadStats();
  }, 10 * 60 * 1000);
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