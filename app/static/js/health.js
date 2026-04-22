/* HEALTH CHECK
══════════════════════════════════════════════════════ */
async function checkHealth() {
  const dot   = document.getElementById("health-dot");
  const label = document.getElementById("health-label");
  const navDot = document.getElementById("health-dot-nav");
  try {
    const h = await api("/health");
    const ok = h.status === "ok";
    const color = ok ? "#22c55e" : "#ef4444";
    if (dot)    { dot.style.background = color; }
    if (navDot) { navDot.style.background = color; }
    if (label)  { label.textContent = ok ? "Sistema OK" : "Degradado"; }

    // Update logs view badge too
    const statusDot  = document.getElementById("health-status-dot");
    const statusText = document.getElementById("health-status-text");
    if (statusDot)  statusDot.style.background = color;
    if (statusText) statusText.textContent = ok ? "Sistema OK" : "Sistema degradado";

    // Render health checks grid
    const grid = document.getElementById("health-checks-grid");
    if (grid && h.checks) {
      grid.innerHTML = Object.entries(h.checks).map(([k, v]) => {
        const isOk = v === "ok" || typeof v === "number";
        const icon = isOk ? "🟢" : "🔴";
        const val  = typeof v === "number" ? v : (v === "ok" ? "OK" : v);
        return `<div class="health-check-card">
          <div class="hc-icon">${icon}</div>
          <div class="hc-key">${k.replace(/_/g," ")}</div>
          <div class="hc-val">${val}</div>
        </div>`;
      }).join("");
    }
  } catch {
    const color = "#ef4444";
    if (dot)    dot.style.background = color;
    if (navDot) navDot.style.background = color;
    if (label)  label.textContent = "Sin conexión";
  }
}

// Start health polling every 30s
checkHealth();
setInterval(checkHealth, 30000);

/* ══════════════════════════════════════════════════════
   LOGS
══════════════════════════════════════════════════════ */
async function loadLogs() {
  const lines = document.getElementById("log-lines")?.value || 100;
  const pre   = document.getElementById("log-output");
  if (!pre) return;
  pre.textContent = "Cargando...";
  try {
    const d = await api(`/logs?lines=${lines}`);
    pre.textContent = d.lines.join("\n") || "Sin logs disponibles.";
    // Auto-scroll to bottom
    pre.scrollTop = pre.scrollHeight;
    // Also update health checks
    checkHealth();
  } catch(e) {
    pre.textContent = "Error al cargar logs: " + e.message;
  }
}
