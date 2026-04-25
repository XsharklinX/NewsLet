# API — Fuentes

Base URL: `/api/v1`

---

## GET `/api/v1/sources`

Lista todas las fuentes de noticias.

**Respuesta (200):**
```json
[
  {
    "id": 1,
    "name": "El País",
    "source_type": "rss",
    "url": "https://elpais.com/rss/elpais/portada.xml",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "consecutive_failures": 0,
    "last_error": null,
    "last_success_at": "2024-01-15T10:00:00",
    "disabled_at": null,
    "article_count": 342
  }
]
```

---

## POST `/api/v1/sources`

Agrega una nueva fuente.

**Body:**
```json
{
  "name": "BBC Mundo",
  "source_type": "rss",
  "url": "https://feeds.bbci.co.uk/mundo/rss.xml"
}
```

**Tipos válidos:** `rss`, `newsapi`, `scraper`

**Para NewsAPI**, la URL es el término de búsqueda (ej: `tecnologia inteligencia artificial`).  
**Para scraper**, la URL es la página principal del sitio.

**Respuesta (201):**
```json
{
  "id": 5,
  "name": "BBC Mundo",
  "source_type": "rss",
  "url": "https://feeds.bbci.co.uk/mundo/rss.xml",
  "is_active": true,
  "created_at": "2024-01-15T12:00:00"
}
```

---

## PATCH `/api/v1/sources/{id}`

Actualiza una fuente existente.

**Body (todos los campos son opcionales):**
```json
{
  "name": "Nuevo nombre",
  "url": "https://nueva-url.com/rss.xml",
  "is_active": false
}
```

**Respuesta (200):** objeto fuente actualizado.

---

## DELETE `/api/v1/sources/{id}`

Elimina una fuente y todos sus artículos asociados.

**Respuesta (200):**
```json
{
  "deleted": true
}
```

---

## POST `/api/v1/sources/{id}/toggle`

Activa o desactiva una fuente (alterna el estado `is_active`).

**Respuesta (200):**
```json
{
  "id": 1,
  "is_active": false
}
```

---

## GET `/api/v1/sources/{id}/stats`

Estadísticas de una fuente específica.

**Respuesta (200):**
```json
{
  "id": 1,
  "name": "El País",
  "total_articles": 342,
  "articles_by_status": {
    "pending": 12,
    "approved": 280,
    "rejected": 40,
    "sent": 10
  },
  "avg_score": 6.8,
  "last_success_at": "2024-01-15T10:00:00",
  "consecutive_failures": 0
}
```

---

## POST `/api/v1/sources/import/opml`

Importa múltiples fuentes RSS desde un archivo OPML (formato estándar de lectores RSS).

**Body:** `multipart/form-data` con campo `file` conteniendo el archivo `.opml`.

**Respuesta (200):**
```json
{
  "imported": 15,
  "skipped": 3,
  "errors": []
}
```

---

## Tipos de fuente

### RSS (`source_type: "rss"`)
- La URL debe apuntar a un feed RSS/Atom válido
- Ejemplo: `https://elpais.com/rss/elpais/portada.xml`
- Soporta cualquier feed estándar RSS 1.0, 2.0 y Atom 0.3/1.0

### NewsAPI (`source_type: "newsapi"`)
- Requiere `NEWSAPI_KEY` configurado
- La URL es el término de búsqueda (no una URL real)
- Ejemplo URL: `economía latinoamérica`
- Hace 1 request por fuente cada vez que el scheduler corre

### Scraper (`source_type: "scraper"`)
- La URL es la página principal del sitio
- El sistema extrae enlaces a artículos y los procesa
- Útil para sitios sin feed RSS (ej: portales de noticias locales)
