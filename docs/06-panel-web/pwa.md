# Panel web — PWA (Progressive Web App)

NewsLet Pro puede instalarse como aplicación nativa en dispositivos móviles y de escritorio gracias a su implementación como PWA.

---

## Qué es una PWA

Una Progressive Web App es un sitio web que el navegador puede instalar como si fuera una app nativa. El usuario puede:
- Agregar el panel a la pantalla de inicio del móvil
- Abrir el panel como ventana independiente (sin barra de dirección)
- Acceder a funciones básicas sin conexión (si el Service Worker lo permite)

---

## Archivos involucrados

| Archivo | Rol |
|---|---|
| `app/static/sw.js` | Service Worker — gestiona caché y actualización |
| `app/static/manifest.json` | Define nombre, ícono y comportamiento de la app instalada |

---

## Service Worker (`sw.js`)

### Estrategia de caché

El Service Worker usa una estrategia **cache-first con fallback a red**:

1. Al instalar: descarga y guarda en caché todos los assets estáticos
2. Al recibir una request: sirve desde caché si existe → si no, va a la red
3. Las llamadas a `/api/` siempre van a la red (nunca se cachean)

### Cache name

```javascript
const CACHE_NAME = 'newslet-v4';
```

El número de versión se incrementa cada vez que hay cambios importantes en los archivos estáticos. Al cambiar la versión, el Service Worker elimina el caché anterior y descarga la versión nueva.

### Assets cacheados

```javascript
const STATIC_ASSETS = [
  '/', '/index.html', '/login.html', '/style.css',
  '/app.js?v=4', '/js/api.js?v=4', '/js/ui.js?v=4',
  '/js/articles.js?v=4', '/js/kanban.js?v=4', '/js/sources.js?v=4',
  '/js/charts.js?v=4', '/js/config.js?v=4', '/js/health.js?v=4',
  '/manifest.json',
];
```

### Actualización del caché

Cuando se actualiza el código del panel, se deben hacer dos cambios:
1. Incrementar el número de versión en `CACHE_NAME` (ej: `newslet-v5`)
2. Actualizar los `?v=N` en los scripts de `index.html` y en `STATIC_ASSETS`

Esto fuerza al navegador a descargar los archivos nuevos incluso si tenía los viejos cacheados.

### URLs excluidas del caché

Cualquier path que empiece con `/api/` nunca se sirve desde caché:
```javascript
if (event.request.url.includes('/api/')) {
  return fetch(event.request);
}
```

---

## Manifest (`manifest.json`)

Define cómo se ve la app cuando está instalada:

```json
{
  "name": "NewsLet Pro",
  "short_name": "NewsLet",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#3b82f6",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- `display: "standalone"` — se abre como ventana sin barra de navegación del browser
- `start_url: "/"` — siempre abre el dashboard principal

---

## Instalar el panel como app

### En Android (Chrome)
1. Abrir el panel en Chrome
2. Tocar el menú ⋮ → "Agregar a pantalla de inicio"
3. El panel aparece como ícono en el launcher

### En iOS (Safari)
1. Abrir el panel en Safari
2. Tocar el botón de compartir ↑
3. "Agregar a pantalla de inicio"

### En escritorio (Chrome/Edge)
1. Abrir el panel
2. Click en el ícono de instalación ⊕ en la barra de dirección
3. "Instalar"

---

## Funcionalidad offline

El panel puede mostrarse sin conexión si ya fue visitado antes (el Service Worker sirve el HTML y CSS desde caché). Sin embargo, los datos (artículos, estadísticas) requieren conexión al servidor — se mostrarán vacíos o con el último estado cacheado.

Las llamadas a la API siempre van a la red y fallan sin conectividad. El panel muestra mensajes de error apropiados en ese caso.
