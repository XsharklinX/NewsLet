# Servicios — Fetchers (Recolectores)

Los fetchers son los servicios que recolectan artículos de las distintas fuentes. Todos corren en paralelo dentro del job `job_fetch_all` del scheduler.

---

## RSS Fetcher (`services/rss_fetcher.py`)

Recolecta artículos de feeds RSS y Atom.

**Biblioteca:** `feedparser`

### Funcionamiento

1. Consulta todas las fuentes con `source_type = "rss"`
2. Descarga el feed con `httpx` (timeout configurable)
3. Parsea entradas con `feedparser`
4. Para cada entrada: extrae título, URL, texto, fecha de publicación y thumbnail
5. Llama al deduplicador — descarta artículos ya vistos
6. Guarda artículos nuevos en la DB
7. Actualiza `last_success_at` o `consecutive_failures` según el resultado

### Datos extraídos por entrada RSS

| Campo | Fuente en el feed |
|---|---|
| Título | `entry.title` |
| URL | `entry.link` |
| Texto | `entry.summary` o `entry.description` |
| Fecha | `entry.published_parsed` o `entry.updated_parsed` |
| Thumbnail | `entry.media_content` o `entry.media_thumbnail` |

### Manejo de errores

Si una fuente falla N veces consecutivas (por defecto N=5, configurable con `SOURCE_MAX_FAILURES`), se marca como deshabilitada automáticamente y aparece una alerta en el panel.

---

## NewsAPI Fetcher (`services/newsapi_fetcher.py`)

Recolecta artículos desde [newsapi.org](https://newsapi.org).

**Requiere:** `NEWSAPI_KEY` en `.env`

### Funcionamiento

1. Consulta todas las fuentes con `source_type = "newsapi"`
2. La URL de la fuente es el término de búsqueda (ej: `economía`)
3. Hace un GET a `https://newsapi.org/v2/everything?q=<termino>&language=es&pageSize=20`
4. Procesa cada artículo del resultado
5. Deduplica y guarda

### Parámetros de búsqueda en NewsAPI

| Parámetro | Valor |
|---|---|
| `q` | URL/término configurado en la fuente |
| `language` | `es` (español) |
| `sortBy` | `publishedAt` |
| `pageSize` | `20` |

### Límites del plan gratuito

- 100 requests por día
- Sin acceso a artículos de más de 30 días
- Solo titulares (no texto completo)

---

## Web Scraper (`services/web_scraper.py`)

Recolecta artículos de sitios web sin feed RSS.

### Funcionamiento

1. Consulta todas las fuentes con `source_type = "scraper"`
2. Descarga el HTML de la URL configurada
3. Extrae todos los enlaces `<a href>` que parezcan artículos (heurística por URL y texto)
4. Para cada enlace candidato: descarga la página y extrae título + texto
5. Deduplica y guarda

### Uso típico

Útil para portales de noticias locales o regionales que no publican RSS pero tienen una portada con titulares.

---

## Full Text Scraper

Cuando `SCRAPE_FULL_TEXT=true` (por defecto activado), antes de resumir un artículo el sistema descarga el HTML completo de la URL original y extrae el texto del artículo.

Esto mejora significativamente la calidad del resumen porque la IA recibe el artículo completo en lugar de solo el snippet del feed.

El texto completo se guarda en `articles.full_text`.

---

## Deduplicador (`services/deduplicator.py`)

Mecanismo para evitar guardar el mismo artículo dos veces.

### Proceso de deduplicación

1. **Normalización de URL:** elimina parámetros de tracking (`utm_*`, `fbclid`, `ref`, etc.), trailing slashes, fragmentos `#`
2. **SHA-256:** calcula el hash de la URL normalizada
3. **Lookup en DB:** verifica si ya existe un artículo con ese `url_hash`
4. Si existe → descarta el artículo
5. Si no existe → guarda con el hash para futuras verificaciones

### Parámetros eliminados en normalización

```
utm_source, utm_medium, utm_campaign, utm_term, utm_content,
fbclid, gclid, ref, source, mc_eid, mc_cid, _hsenc, _hsmi
```

El resultado es que `https://ejemplo.com/noticia?utm_source=twitter` y `https://ejemplo.com/noticia` se tratan como el mismo artículo.
