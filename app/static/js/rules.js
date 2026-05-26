/* ═══════════════════════════════════════════════════════
   Rules (IF/THEN Automation) — NewsLet v3.0
═══════════════════════════════════════════════════════ */

let _editingRuleId = null;

const CONDITION_TYPES = [
  { value: "keyword",   label: "Título/texto contiene" },
  { value: "category",  label: "Categoría es" },
  { value: "sentiment", label: "Sentimiento es" },
  { value: "score_min", label: "Score ≥" },
  { value: "score_max", label: "Score ≤" },
  { value: "source_id", label: "Fuente ID es" },
];

const ACTION_TYPES = [
  { value: "approve",       label: "Aprobar artículo" },
  { value: "reject",        label: "Rechazar artículo" },
  { value: "add_tag",       label: "Añadir etiqueta" },
  { value: "send_telegram", label: "Enviar a Telegram" },
  { value: "webhook",       label: "Llamar webhook (URL)" },
];

const CONDITION_NEEDS_VALUE = {
  approve: false, reject: false, send_telegram: false,
};


/* ── Load & render ────────────────────────────────────── */

async function loadRules() {
  try {
    const d = await api("/rules");
    const rules = d.rules || [];
    const el = document.getElementById("rules-list");
    const cnt = document.getElementById("n-rules");
    if (cnt) cnt.textContent = rules.length;

    if (!rules.length) {
      el.innerHTML = `<div class="empty">
        <span class="e-icon">⚡</span>
        <h3>Sin reglas</h3>
        <p>Crea reglas IF/THEN para aprobar, rechazar o etiquetar artículos automáticamente</p>
      </div>`;
      return;
    }

    el.innerHTML = rules.map(r => _renderRule(r)).join("");
  } catch(e) { console.error("loadRules:", e); }
}

function _renderRule(r) {
  const conditions = (r.conditions || []).map(c => {
    const lbl = CONDITION_TYPES.find(x => x.value === c.type)?.label || c.type;
    return `<span class="rule-pill rule-pill-if">${lbl}${c.value ? `: <strong>${esc(String(c.value))}</strong>` : ""}</span>`;
  }).join("");

  const actions = (r.actions || []).map(a => {
    const lbl = ACTION_TYPES.find(x => x.value === a.type)?.label || a.type;
    return `<span class="rule-pill rule-pill-then">${lbl}${a.value ? `: <strong>${esc(String(a.value))}</strong>` : ""}</span>`;
  }).join("");

  const lastMatch = r.last_matched_at
    ? `<span class="rule-meta-item">Último match: ${fmtDate(r.last_matched_at)}</span>`
    : `<span class="rule-meta-item rule-meta-never">Nunca coincidió</span>`;

  const statusClass = r.is_active ? "rule-active" : "rule-paused";
  const statusLabel = r.is_active ? "Activa" : "Pausada";

  return `<div class="rule-card ${statusClass}" id="rule-card-${r.id}">
    <div class="rule-header">
      <div class="rule-title-row">
        <span class="rule-status-dot ${r.is_active ? "dot-active" : "dot-paused"}"></span>
        <span class="rule-name">${esc(r.name)}</span>
        <span class="rule-priority-badge">P${r.priority}</span>
        <span class="rule-match-badge">${r.match_count || 0} matches</span>
      </div>
      <div class="rule-actions-row">
        <button class="btn btn-g btn-xs" onclick="toggleRule(${r.id})" title="${r.is_active ? "Pausar" : "Activar"}">
          ${r.is_active ? "⏸" : "▶"}
        </button>
        <button class="btn btn-g btn-xs" onclick="editRule(${r.id})">✏</button>
        <button class="btn btn-d btn-xs" onclick="deleteRule(${r.id}, '${esc(r.name)}')">✕</button>
      </div>
    </div>
    <div class="rule-body">
      <div class="rule-logic-row">
        <span class="rule-logic-label if-label">SI</span>
        <div class="rule-pills">${conditions || "<em>Sin condiciones</em>"}</div>
      </div>
      <div class="rule-logic-row">
        <span class="rule-logic-label then-label">ENTONCES</span>
        <div class="rule-pills">${actions || "<em>Sin acciones</em>"}</div>
      </div>
    </div>
    <div class="rule-footer">
      ${lastMatch}
      <span class="rule-meta-item">Prioridad: ${r.priority}</span>
    </div>
  </div>`;
}


/* ── Modal open/close ─────────────────────────────────── */

function openRuleModal(prefill) {
  _editingRuleId = null;
  document.getElementById("rule-modal-title").textContent = "Nueva regla";
  document.getElementById("rule-name").value = prefill?.name || "";
  document.getElementById("rule-priority").value = prefill?.priority || 10;
  document.getElementById("rule-active").checked = prefill?.is_active !== false;
  document.getElementById("rule-conditions").innerHTML = "";
  document.getElementById("rule-actions").innerHTML = "";

  if (prefill?.conditions?.length) {
    prefill.conditions.forEach(c => addCondition(c));
  } else {
    addCondition();
  }
  if (prefill?.actions?.length) {
    prefill.actions.forEach(a => addAction(a));
  } else {
    addAction();
  }

  document.getElementById("overlay-rule").style.display = "flex";
}

function closeRuleModal() {
  document.getElementById("overlay-rule").style.display = "none";
  _editingRuleId = null;
}

async function editRule(id) {
  try {
    const r = await api(`/rules/${id}`);
    _editingRuleId = id;
    document.getElementById("rule-modal-title").textContent = "Editar regla";
    document.getElementById("rule-name").value = r.name;
    document.getElementById("rule-priority").value = r.priority;
    document.getElementById("rule-active").checked = r.is_active;
    document.getElementById("rule-conditions").innerHTML = "";
    document.getElementById("rule-actions").innerHTML = "";

    (r.conditions || []).forEach(c => addCondition(c));
    (r.actions    || []).forEach(a => addAction(a));

    if (!r.conditions?.length) addCondition();
    if (!r.actions?.length)    addAction();

    document.getElementById("overlay-rule").style.display = "flex";
  } catch(e) { toast("Error al cargar la regla", "err"); }
}


/* ── Condition / Action builders ──────────────────────── */

function _condSelect(selected) {
  return `<select class="cond-type" onchange="_updateCondValueField(this)">
    ${CONDITION_TYPES.map(ct =>
      `<option value="${ct.value}" ${selected === ct.value ? "selected" : ""}>${ct.label}</option>`
    ).join("")}
  </select>`;
}

function _actionSelect(selected) {
  return `<select class="act-type" onchange="_updateActValueField(this)">
    ${ACTION_TYPES.map(at =>
      `<option value="${at.value}" ${selected === at.value ? "selected" : ""}>${at.label}</option>`
    ).join("")}
  </select>`;
}

function _valueInput(val, placeholder) {
  return `<input type="text" class="part-value" placeholder="${placeholder || "Valor"}" value="${esc(String(val || ""))}">`;
}

function addCondition(prefill) {
  const container = document.getElementById("rule-conditions");
  const div = document.createElement("div");
  div.className = "rule-part-row";
  const type = prefill?.type || "keyword";
  const showVal = !["approve","reject","send_telegram"].includes(type);
  div.innerHTML = `
    ${_condSelect(type)}
    ${showVal ? _valueInput(prefill?.value, _condPlaceholder(type)) : `<span class="part-no-value"></span>`}
    <button class="btn btn-d btn-xs part-rm" onclick="this.closest('.rule-part-row').remove()">✕</button>
  `;
  container.appendChild(div);
}

function addAction(prefill) {
  const container = document.getElementById("rule-actions");
  const div = document.createElement("div");
  div.className = "rule-part-row";
  const type = prefill?.type || "approve";
  const showVal = !["approve","reject","send_telegram"].includes(type);
  div.innerHTML = `
    ${_actionSelect(type)}
    ${showVal ? _valueInput(prefill?.value, _actPlaceholder(type)) : `<span class="part-no-value"></span>`}
    <button class="btn btn-d btn-xs part-rm" onclick="this.closest('.rule-part-row').remove()">✕</button>
  `;
  container.appendChild(div);
}

function _condPlaceholder(type) {
  const map = { keyword:"ej: inteligencia artificial", category:"ej: Tecnología", sentiment:"positive / neutral / negative", score_min:"1–10", score_max:"1–10", source_id:"ID numérico" };
  return map[type] || "Valor";
}
function _actPlaceholder(type) {
  const map = { add_tag:"ej: destacado", webhook:"https://ejemplo.com/hook" };
  return map[type] || "Valor";
}

function _updateCondValueField(sel) {
  const row = sel.closest(".rule-part-row");
  const type = sel.value;
  const needsVal = !["approve","reject","send_telegram"].includes(type);
  const existing = row.querySelector(".part-value, .part-no-value");
  if (existing) existing.remove();
  const el = document.createElement(needsVal ? "input" : "span");
  if (needsVal) {
    el.type = "text"; el.className = "part-value";
    el.placeholder = _condPlaceholder(type);
  } else {
    el.className = "part-no-value";
  }
  row.insertBefore(el, row.querySelector(".part-rm"));
}

function _updateActValueField(sel) {
  const row = sel.closest(".rule-part-row");
  const type = sel.value;
  const needsVal = !["approve","reject","send_telegram"].includes(type);
  const existing = row.querySelector(".part-value, .part-no-value");
  if (existing) existing.remove();
  const el = document.createElement(needsVal ? "input" : "span");
  if (needsVal) {
    el.type = "text"; el.className = "part-value";
    el.placeholder = _actPlaceholder(type);
  } else {
    el.className = "part-no-value";
  }
  row.insertBefore(el, row.querySelector(".part-rm"));
}


/* ── Save ─────────────────────────────────────────────── */

async function saveRule() {
  const name = document.getElementById("rule-name").value.trim();
  if (!name) { toast("El nombre es obligatorio", "err"); return; }

  const priority = parseInt(document.getElementById("rule-priority").value) || 10;
  const isActive = document.getElementById("rule-active").checked;

  const conditions = [...document.querySelectorAll("#rule-conditions .rule-part-row")].map(row => {
    const type = row.querySelector(".cond-type").value;
    const valEl = row.querySelector(".part-value");
    return { type, value: valEl ? valEl.value.trim() : "" };
  }).filter(c => c.type);

  const actions = [...document.querySelectorAll("#rule-actions .rule-part-row")].map(row => {
    const type = row.querySelector(".act-type").value;
    const valEl = row.querySelector(".part-value");
    return { type, value: valEl ? valEl.value.trim() : "" };
  }).filter(a => a.type);

  if (!conditions.length) { toast("Añade al menos una condición", "err"); return; }
  if (!actions.length)    { toast("Añade al menos una acción", "err"); return; }

  const body = JSON.stringify({ name, conditions, actions, is_active: isActive, priority });

  try {
    if (_editingRuleId) {
      await api(`/rules/${_editingRuleId}`, { method: "PUT", body });
      toast("Regla actualizada", "ok");
    } else {
      await api("/rules", { method: "POST", body });
      toast("Regla creada", "ok");
    }
    closeRuleModal();
    loadRules();
  } catch(e) { toast("Error al guardar la regla", "err"); }
}


/* ── Toggle / Delete / Apply ──────────────────────────── */

async function toggleRule(id) {
  try {
    const d = await api(`/rules/${id}/toggle`, { method: "PATCH" });
    const card = document.getElementById(`rule-card-${id}`);
    if (card) {
      card.classList.toggle("rule-active",  d.is_active);
      card.classList.toggle("rule-paused", !d.is_active);
    }
    loadRules();
  } catch { toast("Error", "err"); }
}

async function deleteRule(id, name) {
  if (!confirm(`Eliminar la regla "${name}"?`)) return;
  try {
    await api(`/rules/${id}`, { method: "DELETE" });
    toast("Regla eliminada", "ok");
    loadRules();
  } catch { toast("Error", "err"); }
}

async function applyRulesNow() {
  try {
    toast("Aplicando reglas...", "info");
    const d = await api("/rules/apply-now", { method: "POST" });
    toast(`✓ ${d.affected_articles} artículos afectados`, "ok");
    loadRules();
  } catch { toast("Error al aplicar reglas", "err"); }
}
