/* KANBAN
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