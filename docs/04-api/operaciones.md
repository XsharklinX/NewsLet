# API — Operaciones manuales

Base URL: `/api/v1`

Estos endpoints permiten disparar manualmente acciones que normalmente ocurren de forma automática.

---

## Recolección de noticias

### POST `/api/v1/fetch/now`

Dispara un ciclo completo de recolección de noticias inmediatamente, sin esperar al scheduler.

Incluye: fetch de todas las fuentes activas → deduplicación → auto-resumen con IA → alertas de keywords → notificación WebSocket.

**Respuesta (200):**

```json
{
  "started": true,
  "message": "Fetch iniciado en segundo plano"
}
```

> El fetch corre de forma asíncrona. La respuesta llega de inmediato; el resultado se emite por WebSocket cuando termina.

---

## Digest diario

### POST `/api/v1/digest/now`

Envía el digest diario a Telegram inmediatamente, usando la configuración actual (hora, cantidad, categorías, score mínimo).

**Respuesta (200):**

```json
{
  "sent": 10,
  "articles": [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]
}
```

---

### POST `/api/v1/digest/email`

Envía el digest por email a los destinatarios configurados en `SMTP_TO`.  
Requiere `SMTP_ENABLED=true` en `.env`.

**Respuesta (200):**

```json
{
  "sent": 2,
  "recipients": ["redaccion@empresa.com", "editor@empresa.com"]
}
```

**Error (si SMTP no está configurado):**

```json
{
  "sent": 0,
  "error": "SMTP no configurado"
}
```

---

## Resumen con IA

### POST `/api/v1/summarize/pending`

Resumir todos los artículos pendientes que aún no tienen resumen.

**Query params:**

| Param   | Por defecto | Descripción                    |
| ------- | ----------- | ------------------------------ |
| `limit` | `20`        | Máximo de artículos a procesar |

**Respuesta (200):**

```json
{
  "summarized": 15,
  "failed": 0,
  "skipped": 5
}
```

---

## PDF

### GET `/api/v1/digest/pdf`

Genera y descarga el digest actual en formato PDF.

**Query params:**

| Param       | Descripción                                     |
| ----------- | ----------------------------------------------- |
| `count`     | Número de artículos a incluir (por defecto: 10) |
| `min_score` | Score mínimo                                    |

**Respuesta:** archivo PDF con el encabezado `Content-Disposition: attachment; filename="newslet_digest_YYYY-MM-DD.pdf"`.

El PDF incluye: encabezado con logo y fecha, tabla de artículos con título/fuente/score/categoría, y el resumen de cada artículo.

---

## Limpieza

### POST `/api/v1/cleanup/now`

Ejecuta la limpieza de artículos antiguos manualmente:

- Artículos con estado `rejected` de más de 30 días
- Artículos con estado `sent` de más de 60 días

**Respuesta (200):**

```json
{
  "deleted_rejected": 45,
  "deleted_sent": 12,
  "total_deleted": 57
}
```

---

## Clustering temático

### POST `/api/v1/cluster/now`

Agrupa artículos similares por tema manualmente.

**Respuesta (200):**

```json
{
  "updated": 23,
  "clusters_found": 8
}
```
