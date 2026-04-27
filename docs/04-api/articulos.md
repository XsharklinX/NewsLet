# API — Artículos

Base URL: `/api/v1`  
Todos los endpoints requieren autenticación JWT cuando `ADMIN_PASSWORD` está configurado.

---

## GET `/api/v1/articles`

Lista artículos con filtros y paginación.

**Query params (todos opcionales):**

| Param       | Tipo         | Descripción                                                   |
| ----------- | ------------ | ------------------------------------------------------------- |
| `status`    | string       | Filtrar por estado: `pending`, `approved`, `rejected`, `sent` |
| `source_id` | int          | Filtrar por fuente                                            |
| `category`  | string       | Filtrar por categoría (ej: `Tecnología`)                      |
| `sentiment` | string       | `positive`, `neutral`, `negative`                             |
| `min_score` | int (1-10)   | Score mínimo de relevancia                                    |
| `search`    | string       | Búsqueda en título + texto (máx 200 chars)                    |
| `date_from` | ISO datetime | Artículos recolectados después de esta fecha                  |
| `date_to`   | ISO datetime | Artículos recolectados antes de esta fecha                    |
| `page`      | int (≥1)     | Página actual (por defecto: 1)                                |
| `page_size` | int (1-100)  | Artículos por página (por defecto: 20)                        |

**Respuesta (200):**

```json
{
  "items": [
    {
      "id": 42,
      "title": "Título del artículo",
      "url": "https://ejemplo.com/noticia",
      "status": "pending",
      "category": "Tecnología",
      "relevance_score": 8,
      "sentiment": "positive",
      "published_at": "2024-01-15T10:30:00",
      "fetched_at": "2024-01-15T10:45:00",
      "source": { "id": 1, "name": "El País" },
      "summary": {
        "summary_text": "Resumen en español...",
        "key_point": "El punto clave es...",
        "context_note": "El contexto es...",
        "impact": "El impacto potencial es..."
      }
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

---

## GET `/api/v1/articles/{id}`

Obtiene un artículo específico con su resumen completo.

**Respuesta (200):** objeto `ArticleOut` (igual que cada item de la lista).  
**Error (404):** artículo no encontrado.

---

## PATCH `/api/v1/articles/{id}/status`

Cambia el estado de un artículo.

**Body:**

```json
{
  "status": "approved"
}
```

Valores válidos: `pending`, `approved`, `rejected`, `sent`.

**Respuesta (200):**

```json
{
  "id": 42,
  "status": "approved"
}
```

---

## POST `/api/v1/articles/{id}/summarize`

Genera o regenera el resumen de un artículo específico mediante IA.

**Respuesta (200):**

```json
{
  "summary": "Resumen generado...",
  "key_point": "El punto clave...",
  "context_note": "El contexto...",
  "impact": "El impacto...",
  "model": "llama-3.3-70b-versatile",
  "tokens": 450
}
```

---

## POST `/api/v1/articles/{id}/send`

Envía un artículo específico a Telegram inmediatamente.

**Respuesta (200):**

```json
{
  "sent": true,
  "article_id": 42
}
```

**Error (400):** si el bot de Telegram no está configurado.

---

## POST `/api/v1/articles/{id}/feedback`

Registra la valoración del editor sobre un artículo.

**Body:**

```json
{
  "value": 1
}
```

Valores: `1` (like), `-1` (dislike), `0` (resetear).

**Respuesta (200):**

```json
{
  "id": 42,
  "feedback": 1
}
```

---

## DELETE `/api/v1/articles/{id}`

Elimina un artículo y su resumen asociado.

**Respuesta (200):**

```json
{
  "deleted": true
}
```

---

## GET `/api/v1/articles/export/csv`

Exporta todos los artículos filtrados en formato CSV.

**Query params:** mismos que `GET /articles` (sin paginación).

**Respuesta:** archivo `.csv` con columnas: id, title, url, status, category, score, sentiment, published_at, fetched_at, source, summary.

---

## GET `/api/v1/feed/rss`

Feed RSS público de los artículos aprobados. No requiere autenticación.

**Respuesta:** XML RSS 2.0 con los últimos artículos con estado `approved`.
