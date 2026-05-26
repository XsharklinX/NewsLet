# NewsLet v3.0 — AI Agent Instructions

Este archivo es para cualquier IA que tome el proyecto. Lee esto **antes** de tocar cualquier archivo.

---

## ¿Qué es este proyecto?

**NewsLet v3.0** es un sistema de agregación, análisis y distribución de noticias en español.
Recolecta artículos de RSS, NewsAPI y scrapers web, los resume con IA (Groq/OpenAI), los muestra
en un panel web editorial y los distribuye por Telegram.

**Stack:** FastAPI + SQLite + APScheduler + Vanilla JS (sin build step)

**Arrancar en local:**
```bash
cd E:/Programacion/NewsBotPro
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Panel en: http://localhost:8000
```

---

## Estructura de archivos críticos

```
NewsBotPro/
├── app/
│   ├── main.py                  ← FastAPI app + lifespan + run_db_migrations()
│   ├── config.py                ← Settings (pydantic-settings, lee .env)
│   ├── database.py              ← SQLAlchemy engine + SessionLocal + Base
│   ├── models/
│   │   ├── article.py           ← Source, Article, Summary, Subscriber
│   │   ├── digest_config.py     ← DigestConfig
│   │   ├── keyword.py           ← Keyword
│   │   ├── notification.py      ← Notification
│   │   ├── rule.py              ← Rule (IF/THEN automation)
│   │   └── webhook.py           ← Webhook
│   ├── schemas/article.py       ← Pydantic schemas (ArticleOut, SourceOut, etc.)
│   ├── api/
│   │   ├── routes.py            ← Agrega todos los routers en protected_routers[]
│   │   └── routers/
│   │       ├── articles.py      ← GET/PATCH artículos, tags, feedback
│   │       ├── sources.py       ← CRUD fuentes + /preview + /catalogue
│   │       ├── operations.py    ← /fetch/now, /summarize/all, /digest/now
│   │       ├── analytics.py     ← /stats, /heatmap, /trending
│   │       ├── config.py        ← DigestConfig CRUD, /digest/preview
│   │       ├── rules.py         ← CRUD reglas + /rules/apply-now
│   │       └── auth.py          ← JWT login/logout
│   ├── services/
│   │   ├── rss_fetcher.py       ← feedparser + hook rule_engine al final
│   │   ├── newsapi_fetcher.py   ← httpx → newsapi.org + hook rule_engine
│   │   ├── web_scraper.py       ← scraper genérico
│   │   ├── summarizer.py        ← Groq/OpenAI async, resúmenes estructurados
│   │   ├── enricher.py          ← category + relevance_score + sentiment por IA
│   │   ├── deduplicator.py      ← SHA-256 de URL normalizada
│   │   ├── rule_engine.py       ← Motor IF/THEN: evalúa reglas en cada artículo nuevo
│   │   ├── topic_clusterer.py   ← Clustering por tema (cluster_id en Article)
│   │   ├── telegram_notifier.py ← Envía artículos/digest a Telegram
│   │   ├── telegram_bot.py      ← Bot polling + comandos (/noticias, /suscribir, etc.)
│   │   ├── keyword_checker.py   ← Alertas por palabras clave
│   │   ├── notification_service.py ← Notificaciones in-app (tabla Notification)
│   │   └── auth.py              ← JWT require_auth dependency
│   ├── scheduler/jobs.py        ← APScheduler: fetch, digest, clustering, backup, cleanup
│   └── static/
│       ├── index.html           ← SPA única — SIEMPRE bump ?v=N al cambiar CSS/JS
│       ├── style.css            ← Todos los estilos en un archivo (v=11 actual)
│       ├── app.js               ← Estado global: pg, filters, shortlistIds, etc.
│       └── js/
│           ├── api.js           ← función api() wrapper de fetch
│           ├── ui.js            ← go(view), toggleSidebar, toasts, tema
│           ├── articles.js      ← Lista artículos, cards, reader modal, tags, shortlist
│           ├── sources.js       ← CRUD fuentes, preview URL, catálogo
│           ├── config.js        ← Digest config, keywords, digest preview
│           ├── rules.js         ← IF/THEN rules UI completo
│           ├── kanban.js        ← Vista kanban drag-and-drop
│           ├── charts.js        ← Gráficas (Chart.js)
│           └── health.js        ← Health check, logs view
├── seeds/default_sources.json   ← Fuentes por defecto al inicializar DB vacía
├── .env                         ← Variables de entorno (NO comitear)
├── .env.example                 ← Plantilla pública
└── requirements.txt
```

---

## Base de Datos — Modelos y columnas

### Article
```
id, source_id (FK→Source), title, url (UNIQUE), url_hash (SHA-256),
original_text, full_text (scraped), category, relevance_score (1-10),
sentiment (positive/neutral/negative), published_at, fetched_at,
status (pending/approved/rejected/sent), enrich_attempts,
thumbnail_url, cluster_id, feedback (-1/0/1), is_recurring,
tags (TEXT, coma-separados)
```

### Source
```
id, name, source_type (rss/newsapi/scraper), url, is_active,
created_at, consecutive_failures, last_error, last_success_at, disabled_at
```

### Summary
```
id, article_id (FK, UNIQUE), summary_text, key_point, context_note,
impact, model_used, tokens_used, created_at
```

### Rule
```
id, name, conditions (JSON TEXT), actions (JSON TEXT),
is_active, priority (lower=first), created_at, last_matched_at, match_count
```

### DigestConfig
```
id, hour, count, min_score, categories, is_active,
recipients, sort_by, send_weekly, weekly_day, weekly_hour
```

### Keyword | Notification | Webhook | Subscriber — ver archivos en models/

---

## Convenciones CRÍTICAS — No romper

### 1. Migraciones de DB
**NUNCA** hagas `Base.metadata.drop_all()`. Las columnas nuevas van en `run_db_migrations()`
en `main.py`. Patrón:
```python
_new_cols = [
    ("nombre_columna", "ALTER TABLE tabla ADD COLUMN nombre_columna TEXT"),
]
for col, sql in _new_cols:
    if col not in existing_cols:
        conn.execute(text(sql))
```
Las tablas nuevas se crean automáticamente vía `Base.metadata.create_all()`.

### 2. Cache busting — SIEMPRE bump la versión
Cuando cambies cualquier `.js` o `.css`, aumenta `?v=N` en `index.html`:
```html
<!-- Actual: v=11 -->
<link rel="stylesheet" href="style.css?v=11">
<script src="app.js?v=11"></script>
<script src="js/rules.js?v=11"></script>
```
Todos los scripts deben tener la **misma** versión.

### 3. Agregar un nuevo router
1. Crear `app/api/routers/mi_router.py` con `router = APIRouter(prefix="/api/v1", ...)`
2. Importar en `app/api/routes.py` y agregar a `protected_routers[]`
3. El modelo debe importarse en `run_db_migrations()` para que `create_all()` lo registre

### 4. Tags de artículos
Se guardan como `TEXT` coma-separado en `Article.tags`. Filtrar con:
```python
Article.tags.ilike(f"%{tag}%")
```
Normalizar siempre: `.strip().lower()`. El endpoint es `PATCH /api/v1/articles/{id}/tags`.

### 5. Pydantic v2
Todos los schemas usan `model_config = {"from_attributes": True}` (no `orm_mode`).

---

## API Endpoints completos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/articles` | Lista con filtros: status, source_id, category, sentiment, tag, min_score, search, date_from, date_to, page, page_size |
| GET | `/api/v1/articles/{id}` | Artículo + resumen |
| PATCH | `/api/v1/articles/{id}/status` | Aprobar/rechazar |
| POST | `/api/v1/articles/{id}/summarize` | Resumir manualmente |
| POST | `/api/v1/articles/{id}/send` | Enviar a Telegram |
| PATCH | `/api/v1/articles/{id}/tags` | Body: `{"tags": ["tag1", "tag2"]}` |
| PATCH | `/api/v1/articles/{id}/feedback` | Body: `{"value": 1}` (-1/0/1) |
| GET | `/api/v1/tags` | Todos los tags únicos de la DB |
| GET | `/api/v1/sources` | Lista fuentes |
| POST | `/api/v1/sources` | Crear fuente |
| PUT | `/api/v1/sources/{id}` | Actualizar fuente |
| DELETE | `/api/v1/sources/{id}` | Eliminar fuente |
| POST | `/api/v1/sources/preview` | Previsualizar feed/URL antes de agregar |
| GET | `/api/v1/sources/catalogue` | Fuentes populares precargadas |
| GET | `/api/v1/sources/{id}/stats` | Stats de una fuente |
| POST | `/api/v1/fetch/now` | Fetch manual inmediato |
| POST | `/api/v1/summarize/all` | Resumir todos los pendientes |
| POST | `/api/v1/digest/now` | Enviar digest ahora |
| GET | `/api/v1/digest/preview` | Preview del digest sin enviar |
| GET | `/api/v1/stats` | Dashboard stats |
| GET | `/api/v1/analytics/heatmap` | Heatmap actividad por hora/día |
| GET | `/api/v1/analytics/trending` | Términos trending |
| GET | `/api/v1/keywords` | Lista keywords |
| POST | `/api/v1/keywords` | Crear keyword |
| PATCH | `/api/v1/keywords/{id}/toggle` | Activar/pausar |
| DELETE | `/api/v1/keywords/{id}` | Eliminar |
| GET | `/api/v1/rules` | Lista reglas |
| POST | `/api/v1/rules` | Crear regla |
| GET | `/api/v1/rules/{id}` | Ver regla |
| PUT | `/api/v1/rules/{id}` | Actualizar regla |
| PATCH | `/api/v1/rules/{id}/toggle` | Activar/pausar |
| DELETE | `/api/v1/rules/{id}` | Eliminar |
| POST | `/api/v1/rules/apply-now` | Aplicar reglas a pendientes |
| GET | `/api/v1/notifications` | Notificaciones in-app |
| PATCH | `/api/v1/notifications/read-all` | Marcar todas leídas |
| GET/POST | `/api/v1/digest/config` | Config del digest |
| GET | `/api/v1/webhooks` | Lista webhooks |
| POST | `/api/v1/webhooks` | Crear webhook |
| DELETE | `/api/v1/webhooks/{id}` | Eliminar |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/logs` | Últimas líneas del log |
| GET | `/api/v1/export/csv` | Exportar artículos en CSV |
| GET | `/feed/rss` | RSS feed público de artículos aprobados |
| POST | `/api/v1/auth/login` | JWT login |
| WS | `/ws` | WebSocket para actualizaciones en tiempo real |

---

## Motor de Reglas IF/THEN

Archivo: `app/services/rule_engine.py`

**Tipos de condición** (campo `conditions` en Rule, JSON array):
```json
[
  {"type": "keyword",   "value": "inteligencia artificial"},
  {"type": "category",  "value": "Tecnología"},
  {"type": "sentiment", "value": "positive"},
  {"type": "score_min", "value": "7"},
  {"type": "score_max", "value": "5"},
  {"type": "source_id", "value": "3"}
]
```

**Tipos de acción** (campo `actions` en Rule, JSON array):
```json
[
  {"type": "approve"},
  {"type": "reject"},
  {"type": "add_tag",       "value": "destacado"},
  {"type": "send_telegram"},
  {"type": "webhook",       "value": "https://ejemplo.com/hook"}
]
```

**Integración:** Después de insertar artículos nuevos en `rss_fetcher.py` y `newsapi_fetcher.py`,
se llama `await apply_rules_to_article(art, db)` para cada artículo nuevo.

**TODO pendiente importante:** La lógica actual usa AND implícito en condiciones.
Falta agregar campo `"logic": "and"|"or"` al JSON de condiciones y actualizar
`_evaluate_rule()` para respetar ese campo.

**TODO pendiente:** Actualizar `Rule.match_count` y `Rule.last_matched_at` dentro de
`rule_engine.py` cuando una regla coincide (los campos ya existen en el modelo,
solo falta escribirlos).

---

## Frontend — Vistas disponibles

| Vista | ID | JS cargado | Función de init |
|-------|----|-----------|-----------------|
| Dashboard | `v-dash` | articles.js | `loadDash()`, `loadStats()` |
| Artículos | `v-arts` | articles.js | `loadArts()` |
| Kanban | `v-kanban` | kanban.js | `loadKanban()` |
| Fuentes | `v-srcs` | sources.js | `loadSrcs()` |
| Mapa calor | `v-heatmap` | charts.js | `loadHeatmap()` |
| Tendencias | `v-trending` | charts.js | `loadTrending()` |
| Keywords | `v-kw` | config.js | `loadKeywords()` |
| Automatización | `v-rules` | rules.js | `loadRules()` |
| Webhooks | `v-webhooks` | config.js | `loadWebhooks()` |
| Configuración | `v-cfg` | config.js | `loadDigestConfig()` |
| Logs | `v-logs` | health.js | `loadLogs()` |
| Administración | `v-admin` | config.js | `loadAdminSettings()` |

**Navegación:** función `go(viewName)` en `ui.js` — muestra la vista y llama la función de init.

**Estado global** en `app.js`:
- `pg` — página actual de artículos
- `filterStatus`, `filterSrc`, `filterCat`, `filterScore`, `filterSentiment`, `filterRecent` — filtros activos
- `searchQ` — búsqueda de texto
- `artView` / `dashView` — "list" | "grid" | "compact"
- `shortlistIds` — Set de IDs en shortlist (localStorage `shortlistIds`)
- `savedArticles` — artículos guardados (localStorage)
- `filterShortlist` — boolean, filtro de shortlist activo
- `filterDateFrom` / `filterDateTo` — filtro por fecha

---

## Scheduler — Jobs programados

| Job | Frecuencia | Qué hace |
|-----|-----------|----------|
| `job_fetch_all` | Cada N min (config `FETCH_INTERVAL_MINUTES`, default 10) | Fetch RSS + NewsAPI + scrapers en paralelo → keywords → auto-resumir |
| `job_daily_digest` | Cron a hora config (default 08:00) | Digest a Telegram owner + broadcast a suscriptores |
| `_job_cluster` | Cada 2 horas | Clustering de artículos por tema |
| `job_backup_db` | Cron 02:00 UTC | Copia DB a directorio + envía a Telegram |
| `job_weekly_report` | Lunes 08:00 | Informe semanal por Telegram + email opcional |
| `job_cleanup` | Domingo 03:00 | Elimina rejected >30d y sent >60d |

---

## Variables de entorno (.env)

```env
# IA — usa Groq GRATIS o OpenAI
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
OPENAI_API_KEY=sk-...          # fallback

# Fuentes
NEWSAPI_KEY=...                # newsapi.org plan gratis = 100 req/día

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...           # tu chat ID personal
TELEGRAM_ADMIN_IDS=id1,id2    # IDs adicionales con acceso admin

# Scheduler
FETCH_INTERVAL_MINUTES=10
DIGEST_HOUR=8
APP_TIMEZONE=America/Argentina/Buenos_Aires

# IA settings
RELEVANCE_THRESHOLD=5          # score mínimo para auto-enviar
ENRICH_ARTICLES=true
SCRAPE_FULL_TEXT=true

# Seguridad del panel
PANEL_PIN=                     # vacío = sin PIN
ADMIN_PASSWORD=                # vacío = sin login JWT
JWT_SECRET=cambia-esto-en-prod

# Email (SMTP)
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=...
SMTP_TO=correo1@x.com,correo2@x.com

# Backup DB
BACKUP_DIR=                    # vacío = solo Telegram backup

# Producción
WEBHOOK_BASE_URL=              # vacío = polling local
SERVICE_KEY=                   # para GitHub Actions
```

---

## Features completados (Tier 1 + Tier 2)

### Tier 1.1 — Estadísticas de fuentes
- 4 métricas por fuente: Total artículos, Esta semana, Score promedio, Tasa de rechazo %
- Health monitoring con auto-deshabilitación tras N fallos consecutivos

### Tier 1.2 — Preview de URL al agregar fuente
- Botón "Probar URL" en el modal → POST `/sources/preview`
- Detecta tipo de feed, extrae artículos, auto-rellena nombre
- Soporte de URLs de canal de YouTube → convierte a RSS automáticamente

### Tier 1.3 — Config avanzada de digest
- Destinatarios extra (email), ordenamiento, envío semanal (día + hora)
- Vista previa del digest antes de enviar (`/digest/preview`)

### Tier 1.4 — Sistema de Tags
- Tags coma-separados en Article.tags (texto plano, no tabla de relación)
- GET `/api/v1/tags` — lista todos los tags únicos
- PATCH `/api/v1/articles/{id}/tags` — actualizar tags
- Filtro por tag en la lista de artículos
- Tags clickeables en cards → activan filtro
- Gestión de tags en el reader modal

### Tier 1.5 — Historial de búsqueda
- Guardado en localStorage (`nlSearchHistory`)
- Dropdown bajo el input de búsqueda al hacer focus
- Límite de 10 búsquedas recientes

### Tier 2.1 — Shortlist "Para leer"
- `shortlistIds` como Set en localStorage
- Botón 🔖 en cada card
- Pill "Para leer" en toolbar con contador
- Filtro activo muestra solo artículos en shortlist

### Tier 2.2 — UI de Clustering
- Badge clickeable "🔗 N fuentes" en cards agrupados
- `filterByCluster(id)` muestra artículos del mismo cluster
- Banner de filtro activo con botón para limpiar

### Tier 2.3 — Stats personales en Dashboard
- Widget "📖 Tu actividad": total leídos, en shortlist, minutos estimados de lectura
- Lee de localStorage (`readIds`, `shortlistIds`)

### Tier 2.4 — Motor de Reglas IF/THEN (completado en última sesión)
- Modelo `Rule` con conditions/actions en JSON
- `rule_engine.py` con evaluador de condiciones y ejecutor de acciones
- 6 tipos de condición: keyword, category, sentiment, score_min, score_max, source_id
- 5 tipos de acción: approve, reject, add_tag, send_telegram, webhook
- Hook automático en rss_fetcher.py y newsapi_fetcher.py
- Vista completa en panel: lista de reglas, modal editor, toggle, delete
- Endpoint `POST /rules/apply-now` para aplicar en batch

---

## Features pendientes (próximas sesiones)

### Alta prioridad
1. **Match counter en reglas** — Actualizar `Rule.match_count` y `Rule.last_matched_at`
   en `rule_engine.py` cuando una regla coincide. Ya están en el modelo, solo escribirlos.

2. **Lógica AND/OR en condiciones** — Agregar toggle en el modal de reglas.
   En `rule_engine.py`: campo `logic` en el JSON → `any()` vs `all()`.

3. **Tiempo de lectura estimado** — `len(text.split()) / 200` al ingestar artículo.
   Guardar como `estimated_read_minutes` (nueva columna). Mostrar en cards.

### Media prioridad
4. **Editor de digest drag-and-drop** — Bloques: Article Card (de la DB), texto libre,
   divider. Ghost usa slash-command + blocks. Ningún competidor tiene Article Card nativo
   de su propia DB.

5. **Resaltados y anotaciones en el reader** — Selección de texto → toolbar debajo
   (NO encima) → guardar en tabla `Highlight(article_id, text, note, tag, color)`.

6. **Separación Feed/Cola** — Vista "Para leer" separada del stream principal.
   Vistas automáticas: Rápidas (<5 min), Largas (>20 min), Continuar leyendo.

### Baja prioridad
7. **Gmail clip warning en digest** — Alertar si el digest supera 102KB.
8. **Ordenamiento "Lindy"** — Artículos más antiguos primero en la cola.
9. **Entrenamiento implícito** — Usar approve/reject para ajustar scoring por fuente.

---

## Observaciones importantes para la IA siguiente

1. **El proyecto NO usa React ni ningún bundler.** Todo el frontend es HTML + JS vanilla
   servido directamente por FastAPI `StaticFiles`. No hay `npm run build`, no hay `package.json`.

2. **SQLite, no PostgreSQL.** La migración de columnas se hace manualmente en `run_db_migrations()`
   de `main.py`. Si agregas una columna nueva al modelo, DEBES agregar el ALTER TABLE ahí.

3. **Pydantic v2** — usa `from_attributes=True` no `orm_mode=True`.

4. **El AI provider por defecto es Groq** (gratis). El code maneja fallback a OpenAI.
   Ver `config.py` y `summarizer.py`.

5. **WebSocket** en `/ws` para actualizaciones en tiempo real. El manager está en
   `app/api/websocket.py`. Se usa para notificar al panel cuando hay nuevos artículos.

6. **Telegram Bot** tiene dos modos: polling (local dev, background task) y
   webhook (producción con `WEBHOOK_BASE_URL` configurado).

7. **El CSS está EN UN SOLO ARCHIVO** `style.css`. Hay también un directorio `css/`
   con archivos separados que son los que **realmente se usan** (el style.css es legacy
   que también se mantiene). Verificar cuál importa el index.html antes de editar.

8. **Cache busting es obligatorio.** Si olvidas cambiar `?v=N`, el navegador servirá
   archivos viejos y los cambios no se verán.
