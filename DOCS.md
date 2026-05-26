# NewsLet v3.0 — Documentación técnica completa

## Visión general

NewsLet es un **panel editorial de agregación de noticias** personal. Recoge artículos
de múltiples fuentes, los analiza con IA, los muestra en un panel web y los distribuye
por Telegram. Diseñado para ser ejecutado por una sola persona (o equipo pequeño) como
servicio autoalojado.

**Proyecto en:** `E:/Programacion/NewsBotPro/`

---

## Cómo ejecutar

```bash
# Requisitos: Python 3.11+, pip
cd E:/Programacion/NewsBotPro
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate       # Linux/Mac

pip install -r requirements.txt
cp .env.example .env             # editar con tus claves

uvicorn app.main:app --reload --port 8000
# → Panel en http://localhost:8000
# → API docs en http://localhost:8000/docs
```

La DB SQLite se crea automáticamente en `newslet.db` al primer arranque.
Las migraciones de columnas se aplican automáticamente en `run_db_migrations()`.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    PANEL WEB                        │
│          HTML + Vanilla JS (no build step)          │
│  Vistas: Dashboard, Artículos, Kanban, Fuentes,     │
│  Análisis, Automatización, Configuración...         │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP + WebSocket
┌──────────────────▼──────────────────────────────────┐
│                   FASTAPI                           │
│  Routers: articles, sources, operations,            │
│  analytics, config, rules, auth, websocket          │
└──────────────────┬──────────────────────────────────┘
         ┌─────────┼─────────┐
┌────────▼──┐ ┌────▼────┐ ┌──▼──────────┐
│  SQLite   │ │APSchedul│ │  Servicios  │
│ newslet.db│ │  Jobs   │ │ rss_fetcher │
│           │ │fetch 10m│ │ summarizer  │
│ SQLAlchemy│ │digest 8h│ │ rule_engine │
│           │ │cluster  │ │ telegram    │
└───────────┘ └─────────┘ └─────────────┘
```

---

## Pipeline de un artículo nuevo

```
1. Fuente RSS/NewsAPI/scraper → rss_fetcher.py
2. Deduplicación → deduplicator.py (SHA-256 de URL normalizada)
3. INSERT en tabla articles (status="pending")
4. rule_engine.py aplica reglas IF/THEN automáticamente
5. summarizer.py genera resumen estructurado (Groq/OpenAI)
6. enricher.py asigna category, relevance_score (1-10), sentiment
7. topic_clusterer.py agrupa artículos por tema (cluster_id)
8. keyword_checker.py envía alertas Telegram por keywords
9. Panel web muestra artículo en lista
10. Usuario aprueba → telegram_notifier.py envía a Telegram
    O regla IF/THEN hace auto-approve → envío automático
```

---

## Modelos de base de datos

### Article — el átomo central del sistema
```python
id: int (PK)
source_id: int (FK → Source)
title: str
url: str (UNIQUE)
url_hash: str (SHA-256 de URL normalizada)
original_text: str | None     # texto del RSS/NewsAPI
full_text: str | None         # texto scrapeado completo
category: str | None          # asignado por IA
relevance_score: int | None   # 1-10, asignado por IA
sentiment: str | None         # positive/neutral/negative
published_at: datetime | None
fetched_at: datetime
status: str                   # pending/approved/rejected/sent
enrich_attempts: int
thumbnail_url: str | None
cluster_id: int | None        # ID del cluster temático
feedback: int                 # -1/0/1 (dislike/none/like)
is_recurring: bool            # tema recurrente
tags: str                     # "tag1,tag2,tag3" (coma-separado)
```

### Source — fuentes de noticias
```python
id, name, source_type (rss/newsapi/scraper), url, is_active,
created_at, consecutive_failures, last_error, last_success_at, disabled_at
```

### Summary — resúmenes de IA
```python
id, article_id (UNIQUE FK), summary_text, key_point, context_note,
impact, model_used, tokens_used, created_at
```

### Rule — reglas de automatización IF/THEN
```python
id, name
conditions: str  # JSON: [{"type": "keyword", "value": "AI"}, ...]
actions: str     # JSON: [{"type": "approve"}, {"type": "add_tag", "value": "destacado"}]
is_active: bool
priority: int    # menor número = se evalúa primero
created_at, last_matched_at, match_count
```

### DigestConfig
```python
id, hour (0-23), count (artículos), min_score, categories (coma-sep),
is_active, recipients, sort_by ("date"/"score"/"category"),
send_weekly, weekly_day (0-6), weekly_hour
```

### Keyword | Notification | Webhook | Subscriber
Ver archivos `app/models/*.py`

---

## Sistema de reglas IF/THEN

### Tipos de condición disponibles
| type | value | Descripción |
|------|-------|-------------|
| `keyword` | texto | Título O texto del artículo contiene el texto (case-insensitive) |
| `category` | Tecnología/Economía/etc. | Categoría asignada por IA coincide |
| `sentiment` | positive/neutral/negative | Sentimiento coincide |
| `score_min` | 1-10 | Score de relevancia >= value |
| `score_max` | 1-10 | Score de relevancia <= value |
| `source_id` | ID numérico | Artículo proviene de esa fuente |

### Tipos de acción disponibles
| type | value | Descripción |
|------|-------|-------------|
| `approve` | — | Cambia status a "approved" (solo si era pending) |
| `reject` | — | Cambia status a "rejected" (solo si era pending) |
| `add_tag` | "nombre-tag" | Añade tag al artículo |
| `send_telegram` | — | Envía inmediatamente a Telegram y marca como sent |
| `webhook` | URL | POST JSON con datos del artículo a esa URL |

### Cómo crear una regla vía API
```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Auto-aprobar Tecnología alta puntuación",
    "conditions": [
      {"type": "category", "value": "Tecnología"},
      {"type": "score_min", "value": "7"}
    ],
    "actions": [
      {"type": "approve"},
      {"type": "add_tag", "value": "destacado"}
    ],
    "is_active": true,
    "priority": 1
  }'
```

---

## Frontend — Guía de navegación

El panel es una SPA (Single Page Application) sin framework. Cada "página" es un
`<div class="view">` que se muestra/oculta con `go('nombre')`.

### Agregar una nueva vista

1. Agregar botón en el sidebar de `index.html`:
```html
<button class="nav-item" onclick="go('mi-vista')" data-v="mi-vista">
  Mi Vista
</button>
```

2. Agregar la vista en el body de `index.html`:
```html
<div class="view" id="v-mi-vista">
  <!-- contenido -->
</div>
```

3. Agregar la función de carga en `ui.js`:
```javascript
if (v === "mi-vista") loadMiVista();
```

4. Crear `app/static/js/mi-vista.js` con la lógica.

5. Incluir el script en `index.html` con la versión bumpeada:
```html
<script src="js/mi-vista.js?v=12"></script>
```

### La función `api()` (en js/api.js)
Wrapper de fetch que maneja autenticación JWT y errores:
```javascript
// GET
const data = await api("/articles?status=pending");

// POST con body
const result = await api("/articles/1/summarize", { method: "POST" });

// PATCH con JSON
await api("/articles/1/tags", {
  method: "PATCH",
  body: JSON.stringify({ tags: ["ia", "tecnología"] })
});
```

---

## Configuración de Telegram

### Bot commands disponibles (para suscriptores)
- `/start` — mensaje de bienvenida
- `/suscribir` — suscribirse al digest público
- `/cancelar` — darse de baja
- `/noticias` — últimas 5 noticias aprobadas
- `/resumen` — resumen de las últimas 24h

### Bot commands admin (solo TELEGRAM_ADMIN_IDS)
- `/fetch` — forzar fetch inmediato
- `/digest` — enviar digest ahora
- `/stats` — ver estadísticas
- `/semanal` — informe semanal
- `/fuentes` — listar fuentes activas

---

## Despliegue en producción

### Render.com (gratis)
1. Crear Web Service apuntando al repo
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configurar variables de entorno en el dashboard
5. Configurar `WEBHOOK_BASE_URL=https://tu-app.onrender.com` para Telegram webhook

### Fly.io
El código detecta automáticamente el volumen persistente en `/app/data`:
```
fly launch
fly volumes create newslet_data --size 1
fly secrets set GROQ_API_KEY=xxx TELEGRAM_BOT_TOKEN=xxx ...
fly deploy
```

### Docker
```dockerfile
# Dockerfile ya incluido en el proyecto
docker build -t newslet .
docker run -p 8000:8000 --env-file .env newslet
```

---

## Patrones de código frecuentes

### Endpoint típico
```python
@router.get("/mi-recurso")
def get_mi_recurso(db: Session = Depends(get_db)):
    items = db.query(MiModelo).filter(MiModelo.is_active == True).all()
    return {"items": [item_to_dict(i) for i in items]}
```

### Agregar columna a una tabla existente
En `main.py`, función `run_db_migrations()`:
```python
_mi_tabla_cols = [
    ("nueva_columna", "ALTER TABLE mi_tabla ADD COLUMN nueva_columna TEXT DEFAULT ''"),
]
# Obtener columnas existentes y aplicar solo las que faltan
mi_cols = existing("mi_tabla")
for col, sql in _mi_tabla_cols:
    if col not in mi_cols:
        conn.execute(text(sql))
```

### Notificación in-app
```python
from app.services.notification_service import push
push(db, "info", "Título", "Cuerpo del mensaje")
# tipos: "fetch", "keyword", "digest", "error", "info", "article_high_score"
```

### WebSocket broadcast
```python
from app.api.websocket import manager
await manager.broadcast("tipo_evento", {"dato": "valor"})
```

---

## Investigación de diseño realizada

Se realizaron dos sesiones de investigación con Lazyweb sobre:

1. **News aggregation platforms** (Feedly, Inoreader, Readwise Reader, NewsBlur):
   - NewsLet ya supera a sus competidores en: scoring por IA, resúmenes estructurados,
     health monitoring de fuentes y clustering de temas
   - Reporte: `.lazyweb/design-research/news-aggregation-platforms-2026-05-09/`

2. **Automation rules, reading queues, annotations, digest editors**:
   - Gold standard de reglas: Inoreader (con match counter por regla)
   - Arquitectura Feed/Cola: Readwise Reader es el modelo a seguir
   - Gap de mercado: ningún editor de digest tiene Article Card de su propia DB
   - Reporte: `.lazyweb/design-research/automation-editorial-ui-2026-05-10/`

---

## Estado actual del proyecto

**Versión:** 3.0.0
**Cache JS/CSS:** v=11 (en index.html)
**DB:** SQLite (`newslet.db`)
**AI:** Groq Llama 3.3 70B (gratis) con fallback a OpenAI GPT-4o-mini

### Lo que funciona completamente
- Fetch automático desde RSS, NewsAPI y scrapers web
- Deduplicación por SHA-256 de URL
- Resúmenes estructurados (punto clave / contexto / impacto)
- Categorización + scoring + sentiment por IA
- Clustering de artículos por tema
- Motor de reglas IF/THEN con 6 condiciones y 5 acciones
- Panel web completo con 12 vistas
- Tags por artículo (filtros + gestión en reader)
- Shortlist "Para leer" (localStorage)
- Historial de búsqueda (localStorage)
- Kanban drag-and-drop
- Gráficas y heatmap de actividad
- Telegram bot (polling + webhook)
- Suscriptores públicos de Telegram
- Digest configurable (hora, cantidad, score mínimo, categorías)
- Keywords con alertas
- Webhooks salientes
- RSS feed público (`/feed/rss`)
- Notificaciones in-app (WebSocket en tiempo real)
- Health monitoring de fuentes con auto-deshabilitación
- Backup automático de DB a Telegram
- PIN de acceso al panel
- JWT auth opcional
- Export CSV

### Pendiente inmediato (30 min de trabajo)
- **Match counter en reglas**: escribir `Rule.match_count` y `Rule.last_matched_at`
  en `rule_engine.py` cuando una regla coincide (los campos ya existen en el modelo)
- **Lógica AND/OR**: toggle en condiciones del modal de reglas + actualizar `_evaluate_rule()`
- **Tiempo de lectura**: calcular al ingestar, mostrar en cards de artículos

### Pendiente a mediano plazo
- Editor de digest drag-and-drop con Article Card nativo
- Resaltados y anotaciones en el reader
- Separación Feed/Cola en el panel
