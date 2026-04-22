/* ══════════════════════════════════════════════════════
   API
══════════════════════════════════════════════════════ */
async function api(path, opt = {}) {
  const token = localStorage.getItem("nl_token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const r = await fetch(API + path, { headers, ...opt });
  if (r.status === 401) {
    // Token expired or invalid — redirect to login and stop execution
    localStorage.removeItem("nl_token");
    window.location.replace("/login.html");
    // Throw so callers don't try to use undefined result
    throw new Error("401");
  }
  if (!r.ok) throw Object.assign(new Error(`${r.status}`), { status: r.status });
  return r.json();
}

function logout() {
  localStorage.removeItem("nl_token");
  window.location.replace("/login.html");
}
