/**
 * NewsLet Service Worker v2.0
 * Strategy: Cache-first for static assets, Network-first for API calls.
 * Supports: offline fallback, push notifications, background sync.
 */
const CACHE_NAME = 'newslet-v7';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/login.html',
  '/style.css',
  '/app.js?v=7',
  '/js/api.js?v=7',
  '/js/ui.js?v=7',
  '/js/articles.js?v=7',
  '/js/kanban.js?v=7',
  '/js/sources.js?v=7',
  '/js/charts.js?v=7',
  '/js/config.js?v=7',
  '/js/health.js?v=7',
  '/manifest.json',
];

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NewsLet — Sin conexión</title>
<style>
  body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;
       display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{text-align:center;padding:40px}
  h1{font-size:2rem;margin-bottom:8px}
  p{color:#94a3b8;margin-bottom:24px}
  button{background:#6366f1;color:#fff;border:none;padding:12px 24px;
         border-radius:8px;font-size:1rem;cursor:pointer}
  button:hover{background:#818cf8}
</style></head>
<body><div class="box">
  <div style="font-size:3rem;margin-bottom:16px">📰</div>
  <h1>Sin conexión</h1>
  <p>NewsLet Pro no puede conectarse al servidor.<br>Verifica tu conexión a internet.</p>
  <button onclick="location.reload()">↻ Reintentar</button>
</div></body></html>`;

// ── Install: pre-cache static shell ──────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(STATIC_ASSETS).catch(err =>
        console.warn('[SW] Pre-cache error (non-fatal):', err)
      )
    )
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch: routing strategy ───────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET and cross-origin requests
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;

  // Network-first for API and WebSocket paths
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'Sin conexión', offline: true }), {
          headers: { 'Content-Type': 'application/json' },
          status: 503,
        })
      )
    );
    return;
  }

  // Cache-first for static assets, with offline HTML fallback
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (!response || response.status !== 200 || response.type === 'opaque') return response;
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
        return response;
      }).catch(() => {
        // Offline fallback for navigation requests
        if (event.request.destination === 'document') {
          return new Response(OFFLINE_HTML, {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
          });
        }
      });
    })
  );
});

// ── Push notifications ────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  if (!event.data) return;
  let data;
  try { data = event.data.json(); }
  catch { data = { title: 'NewsLet Pro', body: event.data.text() }; }

  const options = {
    body:    data.body    || 'Nueva notificación',
    icon:    data.icon    || '/icons/icon-192.png',
    badge:   data.badge   || '/icons/icon-192.png',
    tag:     data.tag     || 'newslet-notif',
    data:    { url: data.url || '/' },
    actions: data.actions || [],
    vibrate: [100, 50, 100],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'NewsLet Pro', options)
  );
});

// ── Notification click ────────────────────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(wcs => {
      const existing = wcs.find(wc => wc.url.includes(target));
      if (existing) return existing.focus();
      return clients.openWindow(target);
    })
  );
});

// ── Background sync ───────────────────────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-approvals') {
    console.log('[SW] Sync event: sync-approvals');
  }
});
