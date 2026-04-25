# NewsLet Pro — Documentación Oficial

> Sistema profesional de agregación, análisis con IA y distribución de noticias.

---

## Estructura de la documentación

```
Docs/
├── README.md                        ← Este archivo (índice)
│
├── 01-introduccion/
│   ├── resumen.md                   ← Qué es, para qué sirve, características
│   └── arquitectura.md              ← Stack técnico y diagrama de flujo
│
├── 02-instalacion/
│   ├── requisitos.md                ← Dependencias del sistema
│   ├── configuracion.md             ← Variables de entorno (.env)
│   └── despliegue.md                ← Docker, Koyeb, Railway, Fly.io, local
│
├── 03-base-de-datos/
│   └── modelos.md                   ← Todos los modelos ORM y sus campos
│
├── 04-api/
│   ├── articulos.md                 ← CRUD artículos, búsqueda, exportación
│   ├── fuentes.md                   ← CRUD fuentes, OPML, stats
│   ├── analiticas.md                ← Estadísticas, gráficas, logs, health
│   ├── configuracion.md             ← Keywords, digest, webhooks, notificaciones
│   ├── operaciones.md               ← Fetch, summarize, digest, PDF
│   └── autenticacion.md             ← Login, JWT, tokens de servicio
│
├── 05-servicios/
│   ├── fetchers.md                  ← RSS, NewsAPI, Web Scraper
│   ├── ia-enriquecimiento.md        ← Pipeline IA: resumen, score, categoría
│   ├── telegram.md                  ← Bot (comandos) y notificador
│   ├── scheduler.md                 ← Jobs automáticos y sus intervalos
│   └── utilidades.md                ← PDF, email, clustering, deduplicación
│
├── 06-panel-web/
│   ├── vistas.md                    ← Cada vista del panel editorial
│   └── pwa.md                       ← Service Worker, manifest, offline
│
└── 07-guias/
    ├── uso-diario.md                ← Flujo de trabajo editorial
    └── extensibilidad.md            ← Cómo agregar fuentes, servicios, features
```

---

## Acceso rápido por rol

| Si eres... | Lee primero |
|---|---|
| **Usuario nuevo** | [Introducción](01-introduccion/resumen.md) → [Instalación](02-instalacion/requisitos.md) → [Uso diario](07-guias/uso-diario.md) |
| **Administrador del servidor** | [Configuración](02-instalacion/configuracion.md) → [Despliegue](02-instalacion/despliegue.md) |
| **Desarrollador** | [Arquitectura](01-introduccion/arquitectura.md) → [API](04-api/articulos.md) → [Servicios](05-servicios/fetchers.md) |
| **Integrador (webhooks/API)** | [API REST](04-api/articulos.md) → [Autenticación](04-api/autenticacion.md) |

---

## Stack en una línea

**Backend:** FastAPI + SQLAlchemy + APScheduler + Groq/OpenAI  
**Frontend:** HTML + JS Vanilla + Chart.js (sin build step)  
**Bot:** Telegram Bot API (polling en dev, webhook en producción)  
**Deploy:** Docker → Koyeb / Railway / Fly.io  
