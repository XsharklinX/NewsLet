# API — Analíticas y estadísticas

Base URL: `/api/v1`

---

## GET `/api/v1/stats`

Estadísticas generales del sistema en tiempo real. Usado por el dashboard.

**Respuesta (200):**

```json
{
  "total_articles": 1250,
  "total_sources": 12,
  "pending": 23,
  "approved": 845,
  "rejected": 312,
  "sent": 70,
  "articles_today": 34,
  "avg_score": 6.4,
  "unread_notifications": 5,
  "scheduler_running": true,
  "db_size_kb": 2048
}
```

---

## GET `/api/v1/analytics/articles-by-day`

Artículos recolectados por día en los últimos N días.

**Query params:**

| Param  | Por defecto | Descripción                |
| ------ | ----------- | -------------------------- |
| `days` | `30`        | Número de días hacia atrás |

**Respuesta (200):**

```json
[
  { "date": "2024-01-14", "count": 45 },
  { "date": "2024-01-15", "count": 38 }
]
```

---

## GET `/api/v1/analytics/articles-by-category`

Distribución de artículos por categoría.

**Respuesta (200):**

```json
[
  { "category": "Tecnología", "count": 320 },
  { "category": "Política", "count": 280 },
  { "category": "Economía", "count": 190 }
]
```

---

## GET `/api/v1/analytics/articles-by-sentiment`

Distribución por sentimiento.

**Respuesta (200):**

```json
[
  { "sentiment": "neutral", "count": 650 },
  { "sentiment": "negative", "count": 380 },
  { "sentiment": "positive", "count": 220 }
]
```

---

## GET `/api/v1/analytics/score-distribution`

Histograma de scores de relevancia (1-10).

**Respuesta (200):**

```json
[
  { "score": 1, "count": 12 },
  { "score": 2, "count": 34 },
  { "score": 5, "count": 180 },
  { "score": 8, "count": 95 },
  { "score": 10, "count": 22 }
]
```

---

## GET `/api/v1/analytics/heatmap`

Mapa de actividad: cantidad de artículos publicados por día de la semana y hora del día.

**Respuesta (200):**

```json
[
  { "day": 0, "hour": 8, "count": 23 },
  { "day": 0, "hour": 9, "count": 45 },
  { "day": 1, "hour": 14, "count": 18 }
]
```

`day`: 0=Lunes, 6=Domingo. `hour`: 0-23.

---

## GET `/api/v1/analytics/trending`

Palabras más mencionadas en los títulos de los últimos N artículos.

**Query params:**

| Param   | Por defecto | Descripción                   |
| ------- | ----------- | ----------------------------- |
| `hours` | `24`        | Ventana temporal en horas     |
| `top`   | `20`        | Número de palabras a devolver |

**Respuesta (200):**

```json
[
  { "word": "inteligencia", "count": 45 },
  { "word": "artificial", "count": 43 },
  { "word": "gobierno", "count": 38 }
]
```

---

## GET `/api/v1/analytics/source-performance`

Rendimiento de cada fuente: artículos aportados, score promedio, tasa de aprobación.

**Respuesta (200):**

```json
[
  {
    "source_id": 1,
    "source_name": "El País",
    "total": 342,
    "approved": 280,
    "avg_score": 7.2,
    "approval_rate": 0.82
  }
]
```

---

## GET `/api/v1/logs`

Últimas líneas del archivo de log del sistema.

**Query params:**

| Param   | Por defecto | Descripción                                   |
| ------- | ----------- | --------------------------------------------- |
| `lines` | `100`       | Número de líneas a devolver                   |
| `level` | _(todos)_   | Filtrar por nivel: `INFO`, `WARNING`, `ERROR` |

**Respuesta (200):**

```json
{
  "logs": [
    "2024-01-15 10:00:01 [INFO    ] app.scheduler.jobs: Scheduler: fetch cycle starting",
    "2024-01-15 10:00:05 [INFO    ] app.scheduler.jobs: Scheduler: fetched 12 new articles"
  ],
  "total_lines": 100
}
```

---

## GET `/api/v1/health`

Health check del sistema. No requiere autenticación.

**Respuesta (200):**

```json
{
  "status": "ok",
  "version": "3.0.0",
  "db": "ok",
  "scheduler": "running",
  "uptime_seconds": 86400
}
```

---

## GET `/api/v1/notifications`

Lista las notificaciones internas del sistema.

**Query params:**

| Param         | Por defecto | Descripción                   |
| ------------- | ----------- | ----------------------------- |
| `limit`       | `50`        | Máximo de notificaciones      |
| `unread_only` | `false`     | Solo notificaciones no leídas |

---

## POST `/api/v1/notifications/read-all`

Marca todas las notificaciones como leídas.

---

## DELETE `/api/v1/notifications`

Elimina todo el historial de notificaciones.
