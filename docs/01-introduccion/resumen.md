# NewsLet Pro — Introducción

## ¿Qué es?

NewsLet Pro es un sistema de agregación y distribución de noticias diseñado para editores, periodistas y equipos de comunicación que necesitan monitorear múltiples fuentes de información, filtrarlas con inteligencia artificial y distribuirlas por Telegram o email de forma automática.

El sistema corre 24/7 en un servidor propio, recolecta noticias cada 10 minutos, las analiza con IA y las presenta en un panel web para su revisión y aprobación editorial.

---

## ¿Para qué sirve?

| Problema | Solución |
|---|---|
| Revisar 20+ sitios de noticias a mano | El sistema las recolecta solo, cada 10 minutos |
| No saber qué noticias son importantes | La IA puntúa cada artículo del 1 al 10 |
| Distribuir noticias a un equipo por Telegram | Envío automático con resumen en español |
| Perder noticias relevantes | Alertas por palabras clave configurables |
| No tener estadísticas de cobertura | Panel con gráficas, tendencias y mapas de actividad |

---

## Características principales

### Recolección automática
- **RSS feeds** — Cualquier sitio web con feed RSS/Atom
- **NewsAPI** — API de noticias con búsqueda por términos
- **Web scraping** — Sitios sin RSS (WordPress, sitios custom)
- **Detección de duplicados** — Por URL y por similitud de título (fuzzy matching)
- **Extracción de texto completo** — Scraping del artículo original

### Análisis con inteligencia artificial
- **Resumen en español** — 2-3 oraciones concisas
- **Punto clave** — El hecho central de la noticia
- **Contexto** — Antecedente relevante
- **Impacto** — Consecuencia potencial
- **Categoría** — Política, Economía, Tecnología, etc.
- **Score de relevancia** — 1 al 10 (calibrado con ejemplos)
- **Sentimiento** — Positivo, neutral o negativo
- **Auto-aprobación** — Artículos con score alto se aprueban solos

### Distribución
- **Bot de Telegram** — Comandos para admins y suscriptores públicos
- **Noticias diarias** — Digest automático cada día a la hora configurada
- **Envío individual** — Artículo específico a demanda
- **Email SMTP** — Digest por correo electrónico
- **RSS de salida** — Feed RSS de artículos aprobados
- **Webhooks** — POST a n8n, Zapier, Make u otros servicios
- **PDF** — Digest exportable en formato PDF

### Panel editorial web
- **Dashboard** — Estadísticas en tiempo real vía WebSocket
- **Artículos** — Lista con filtros por estado, categoría, score, fecha, sentimiento
- **Kanban** — Vista de flujo editorial (pendiente → aprobado → enviado)
- **Gráficas** — Artículos por día, por categoría, por sentimiento
- **Mapa de actividad** — A qué hora y qué día publican más las fuentes
- **Tendencias** — Las palabras más mencionadas en las últimas N horas
- **Logs** — Actividad del sistema en tiempo real
- **Modo PWA** — Instalable como app en móvil

---

## Flujo de trabajo típico

```
Cada 10 min (automático)
    │
    ▼
Recolección de fuentes RSS + NewsAPI + Scraper
    │
    ▼
Deduplicación (¿ya tenemos este artículo?)
    │
    ▼
Análisis IA (resumen + score + categoría + sentimiento)
    │
    ├─ Score alto (≥ umbral) → Auto-aprobado
    │
    └─ Score bajo → Queda pendiente para revisión manual
              │
              ▼
        Editor revisa en el panel
              │
              ▼
        Aprueba / Rechaza
              │
              ▼
08:00 AM → Digest diario a Telegram + Email
```

---

## Versión actual

| Componente | Versión |
|---|---|
| NewsLet Pro | v3.0 |
| Python | 3.12 |
| FastAPI | 0.115+ |
| IA por defecto | Groq (Llama 3.3 70B) |
| Base de datos | SQLite (producción) / PostgreSQL (opcional) |
