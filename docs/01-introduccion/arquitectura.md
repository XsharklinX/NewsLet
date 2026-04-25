# Arquitectura — NewsLet Pro

## Stack tecnológico

| Capa              | Tecnología                                  | Rol                                                   |
| ----------------- | ------------------------------------------- | ----------------------------------------------------- |
| **Backend**       | FastAPI 0.115+                              | Servidor HTTP + WebSocket + API REST                  |
| **ORM / DB**      | SQLAlchemy 2.x + SQLite                     | Persistencia de datos                                 |
| **Scheduler**     | APScheduler 3.x                             | Jobs automáticos (fetch, digest, backup)              |
| **IA**            | Groq (Llama 3.3 70B) / OpenAI (GPT-4o-mini) | Resúmenes, scores, categorías                         |
| **HTTP client**   | httpx (async)                               | NewsAPI, Telegram Bot API, scrapers                   |
| **RSS**           | feedparser                                  | Parsing de feeds RSS/Atom                             |
| **Frontend**      | HTML + JS Vanilla + Chart.js                | Panel editorial (sin build step)                      |
| **Bot**           | Telegram Bot API                            | Polling (dev) / Webhook (producción)                  |
| **Autenticación** | JWT (PyJWT)                                 | Login de administrador                                |
| **Rate limiting** | slowapi                                     | Protección de endpoints                               |
| **Deploy**        | Docker                                      | Contenedor único, compatible con Koyeb/Fly.io/Railway |

---

## Estructura de directorios

```
NewsBotPro/
├── app/
│   ├── main.py                  # Punto de entrada FastAPI + lifespan
│   ├── config.py                # Configuración via pydantic-settings (.env)
│   ├── database.py              # Engine SQLAlchemy, sesión, Base
│   ├── limiter.py               # Instancia de slowapi
│   │
│   ├── models/
│   │   └── article.py           # Modelos ORM: Source, Article, Summary, Subscriber, …
│   │
│   ├── schemas/                 # Pydantic schemas (request / response)
│   │
│   ├── api/
│   │   ├── routes.py            # Registro de todos los routers
│   │   ├── websocket.py         # Gestor de conexiones WebSocket
│   │   ├── articles.py          # Endpoints de artículos
│   │   ├── sources.py           # Endpoints de fuentes
│   │   ├── analytics.py         # Estadísticas y logs
│   │   ├── config_router.py     # Keywords, digest config, webhooks
│   │   ├── operations.py        # Fetch manual, digest manual, PDF
│   │   └── auth.py              # Login, JWT, tokens de servicio
│   │
│   ├── services/
│   │   ├── rss_fetcher.py       # Parser RSS/Atom
│   │   ├── newsapi_fetcher.py   # Integración NewsAPI
│   │   ├── web_scraper.py       # Scraping de sitios sin RSS
│   │   ├── deduplicator.py      # SHA-256 + fuzzy matching
│   │   ├── summarizer.py        # Pipeline IA (resumen + score + categoría)
│   │   ├── telegram_bot.py      # Comandos del bot (polling)
│   │   ├── telegram_notifier.py # Envío de mensajes a Telegram
│   │   ├── telegram_webhook.py  # Registro de webhook en producción
│   │   ├── keyword_checker.py   # Alertas por palabras clave
│   │   ├── topic_clusterer.py   # Agrupación de noticias similares
│   │   ├── notification_service.py # Notificaciones in-app
│   │   ├── email_notifier.py    # Digest por SMTP
│   │   ├── pdf_generator.py     # Export a PDF
│   │   ├── webhook_dispatcher.py # POST a webhooks externos
│   │   └── startup_validator.py # Validación de config al arrancar
│   │
│   ├── scheduler/
│   │   └── jobs.py              # Todos los jobs automáticos
│   │
│   └── static/                  # Panel web (servido como StaticFiles)
│       ├── index.html           # SPA principal
│       ├── login.html           # Página de login JWT
│       ├── style.css            # Estilos globales
│       ├── app.js               # Variables globales + helpers
│       ├── sw.js                # Service Worker (PWA)
│       ├── manifest.json        # PWA manifest
│       └── js/
│           ├── api.js           # Cliente HTTP + WebSocket
│           ├── ui.js            # Navegación + sidebar + toasts
│           ├── articles.js      # Vista de artículos
│           ├── kanban.js        # Vista Kanban
│           ├── sources.js       # Gestión de fuentes
│           ├── charts.js        # Gráficas y estadísticas
│           ├── config.js        # Configuración + notificaciones
│           └── health.js        # Logs y estado del sistema
│
├── seeds/
│   └── default_sources.json     # Fuentes RSS precargadas al iniciar
│
├── logs/                        # Logs rotativos (auto-creado)
├── data/                        # Base de datos SQLite (auto-creado)
│
├── Dockerfile
├── requirements.txt
└── .env                         # Variables de entorno (no commitear)
```

---

## Diagrama de flujo de datos

```
┌─────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                         │
│  RSS feeds   │  NewsAPI   │  Web Scraper  │  (cada 10 minutos)  │
└──────┬───────┴─────┬──────┴──────┬────────┘                     │
       │             │             │                               │
       └─────────────┴─────────────┘                               │
                           │                                       │
                    ┌──────▼──────┐                                │
                    │ Deduplicador│  SHA-256 de URL normalizada     │
                    │  (fuzzy)    │  Descarta artículos ya vistos   │
                    └──────┬──────┘                                │
                           │ artículos nuevos                      │
                    ┌──────▼──────┐                                │
                    │  Pipeline   │  Groq / OpenAI                 │
                    │    de IA    │  → resumen en español          │
                    │             │  → score 1-10                  │
                    │             │  → categoría                   │
                    │             │  → sentimiento                 │
                    └──────┬──────┘                                │
                           │                                       │
              ┌────────────┼────────────┐                          │
              │            │            │                          │
       score ≥ umbral  score < umbral  siempre                     │
              │            │            │                          │
       ┌──────▼──────┐ ┌───▼──────┐ ┌──▼──────────────┐          │
       │ Auto-aprobado│ │ Pendiente│ │  Keyword alerts  │          │
       └──────┬──────┘ └───┬──────┘ └─────────────────┘          │
              │            │                                       │
              │     ┌──────▼──────┐                               │
              │     │  Editor web │  Panel editorial               │
              │     │  revisa y   │  Aprueba / Rechaza             │
              │     │  aprueba    │                                │
              └─────┴──────┬──────┘                               │
                           │ artículos aprobados                   │
              ┌────────────┼────────────┐                          │
              │            │            │                          │
       ┌──────▼──────┐ ┌───▼──────┐ ┌──▼──────────┐              │
       │   Telegram  │ │  Email   │ │  Webhooks   │              │
       │  (digest +  │ │  (SMTP)  │ │  (n8n, etc) │              │
       │  individual)│ │          │ │             │              │
       └─────────────┘ └──────────┘ └─────────────┘              │
```

---

## Arranque del servidor (lifespan)

Al iniciar, FastAPI ejecuta en orden:

1. **Logging** — Configura logger rotativo en `logs/newslet.log`
2. **Base de datos** — `create_all()` crea tablas si no existen
3. **Migraciones** — Agrega columnas nuevas sin romper datos existentes
4. **Seed** — Carga fuentes por defecto si la DB está vacía
5. **Validación de startup** — Verifica claves API configuradas
6. **Scheduler** — Inicia todos los jobs automáticos (APScheduler)
7. **Bot de Telegram** — Polling (dev) o registro de webhook (producción)

---

## Comunicación en tiempo real

El panel web mantiene una conexión **WebSocket** con el servidor (`/ws`).  
Cuando el scheduler completa un fetch, emite `fetch_complete` → el dashboard se actualiza sin necesidad de recargar la página.

---

## Autenticación

| Modo               | Descripción                                                                             |
| ------------------ | --------------------------------------------------------------------------------------- |
| **Sin contraseña** | `ADMIN_PASSWORD` vacío → panel accesible sin login                                      |
| **JWT**            | `ADMIN_PASSWORD` configurado → login en `/login.html`, token en `Authorization: Bearer` |
| **PIN**            | `PANEL_PIN` configurado → middleware bloquea acceso al panel HTML                       |
| **Service Key**    | `SERVICE_KEY` → header `X-Service-Key` para llamadas programáticas (CI/CD)              |
