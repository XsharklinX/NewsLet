/* CHARTS
══════════════════════════════════════════════════════ */
async function loadCharts() {
  const days = document.getElementById("chart-days")?.value || 7;
  try {
    const d = await api(`/stats/chart?days=${days}`);

    const chartOpts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#a1a1aa", font: { size: 11 }, boxWidth: 12, padding: 10 } } },
    };
    const gridColor = "rgba(255,255,255,0.05)";
    const tickColor = "#71717a";

    // Daily
    const ctxD = document.getElementById("chart-daily").getContext("2d");
    if (chartDaily) chartDaily.destroy();
    chartDaily = new Chart(ctxD, {
      type: "line",
      data: {
        labels: d.daily.map(r => r.day),
        datasets: [{
          label: "Artículos",
          data: d.daily.map(r => r.count),
          borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.10)",
          borderWidth: 2, pointRadius: 4, pointBackgroundColor: "#6366f1",
          fill: true, tension: 0.4,
        }],
      },
      options: {
        ...chartOpts,
        plugins: { ...chartOpts.plugins, legend: { display: false } },
        scales: {
          x: { ticks: { color: tickColor, font: { size: 10 } }, grid: { color: gridColor } },
          y: { ticks: { color: tickColor, font: { size: 10 }, stepSize: 1 }, grid: { color: gridColor }, beginAtZero: true },
        },
      },
    });

    // Category doughnut
    const palette = ["#6366f1","#22c55e","#3b82f6","#eab308","#ef4444","#a855f7","#f97316","#14b8a6"];
    const ctxC = document.getElementById("chart-cat").getContext("2d");
    if (chartCat) chartCat.destroy();
    chartCat = new Chart(ctxC, {
      type: "doughnut",
      data: {
        labels: d.categories.map(r => r.category),
        datasets: [{ data: d.categories.map(r => r.count), backgroundColor: palette, borderColor: "var(--bg)", borderWidth: 2 }],
      },
      options: { ...chartOpts, cutout: "65%" },
    });

    // Sentiment bar
    const ctxS = document.getElementById("chart-sentiment").getContext("2d");
    if (chartSentiment) chartSentiment.destroy();
    const sentColors = { positive: "#22c55e", neutral: "#3b82f6", negative: "#ef4444" };
    chartSentiment = new Chart(ctxS, {
      type: "bar",
      data: {
        labels: (d.sentiments || []).map(r => r.sentiment),
        datasets: [{
          label: "Artículos",
          data: (d.sentiments || []).map(r => r.count),
          backgroundColor: (d.sentiments || []).map(r => sentColors[r.sentiment] || "#6366f1"),
          borderRadius: 6,
        }],
      },
      options: {
        ...chartOpts,
        plugins: { ...chartOpts.plugins, legend: { display: false } },
        scales: {
          x: { ticks: { color: tickColor }, grid: { display: false } },
          y: { ticks: { color: tickColor, stepSize: 1 }, grid: { color: gridColor }, beginAtZero: true },
        },
      },
    });
  } catch(e) { console.error(e); }
}

/* ══════════════════════════════════════════════════════
   HEATMAP
══════════════════════════════════════════════════════ */
async function loadHeatmap() {
  try {
    const d = await api("/stats/heatmap");

    // Hours bar chart
    const maxH = Math.max(...d.hours.map(h => h.count), 1);
    const hGrid = document.getElementById("hm-hours");
    hGrid.innerHTML = d.hours.map(h => {
      const pct = Math.round((h.count / maxH) * 100);
      const barH = Math.max(pct * 1.5, 4);
      const hue  = 240 + Math.round((pct / 100) * 60); // blue → purple
      return `<div class="hm-bar-item">
        <div class="hm-bar-val">${h.count || ""}</div>
        <div class="hm-bar-fill" style="height:${barH}px;background:hsl(${hue},70%,60%)"></div>
        <div class="hm-bar-label">${String(h.hour).padStart(2,"0")}h</div>
      </div>`;
    }).join("");

    // Days
    const maxD = Math.max(...d.days.map(d => d.count), 1);
    const wGrid = document.getElementById("hm-days");
    wGrid.innerHTML = d.days.map(day => {
      const pct = Math.round((day.count / maxD) * 100);
      return `<div class="hm-week-row">
        <span class="hm-week-label">${day.day_name}</span>
        <div class="hm-week-bar">
          <div class="hm-week-fill" style="width:${pct}%;background:linear-gradient(90deg,#6366f1,#a855f7)"></div>
        </div>
        <span class="hm-week-val">${day.count}</span>
      </div>`;
    }).join("");
  } catch(e) { console.error(e); }
}

/* ══════════════════════════════════════════════════════
   TRENDING
══════════════════════════════════════════════════════ */
async function loadTrending() {
  const hours = document.getElementById("trend-hours")?.value || 24;
  try {
    const d   = await api(`/stats/trending?hours=${hours}&limit=30`);
    const c   = document.getElementById("trending-list");
    if (!d.topics.length) {
      c.innerHTML = `<div class="empty"><span class="e-icon">📊</span><h3>Sin datos</h3><p>Aún no hay suficientes artículos</p></div>`;
      return;
    }
    const max = d.topics[0].count;
    const palette = ["#6366f1","#22c55e","#3b82f6","#eab308","#a855f7","#f97316","#14b8a6","#ef4444"];
    c.innerHTML = d.topics.map((t, i) => {
      const size = 0.75 + (t.count / max) * 0.85;
      const col  = palette[i % palette.length];
      return `<div class="trend-word" style="font-size:${size.toFixed(2)}rem;color:${col};border-color:${col}22"
        onclick="searchTrend('${esc(t.word)}')"
        title="${t.count} menciones">
        ${esc(t.word)} <span style="font-size:0.65em;opacity:0.7">${t.count}</span>
      </div>`;
    }).join("");
  } catch(e) { console.error(e); }
}

function searchTrend(word) {
  searchQ = word;
  document.getElementById("q").value = word;
  go("arts");
}