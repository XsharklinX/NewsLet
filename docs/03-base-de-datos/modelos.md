# Base de datos — Modelos ORM

NewsLet Pro usa **SQLAlchemy 2.x** con **SQLite** por defecto (también soporta PostgreSQL).  
Las tablas se crean automáticamente al iniciar. Las columnas nuevas se agregan mediante un sistema de migraciones seguras en `app/main.py`.

---

## Modelos

### Source — Fuentes de noticias

**Tabla:** `sources`

| Campo                  | Tipo        | Descripción                                        |
| ---------------------- | ----------- | -------------------------------------------------- |
| `id`                   | Integer PK  | Identificador único                                |
| `name`                 | String(200) | Nombre descriptivo de la fuente                    |
| `source_type`          | String(20)  | `rss`, `newsapi` o `scraper`                       |
| `url`                  | String(500) | URL del feed RSS, query de NewsAPI o URL del sitio |
| `is_active`            | Boolean     | Si la fuente está habilitada                       |
| `created_at`           | DateTime    | Cuándo se agregó                                   |
| `consecutive_failures` | Integer     | Fallos consecutivos sin éxito                      |
| `last_error`           | Text        | Último mensaje de error                            |
| `last_success_at`      | DateTime    | Última vez que devolvió artículos                  |
| `disabled_at`          | DateTime    | Cuándo fue deshabilitada automáticamente           |

**Relaciones:** una fuente tiene muchos artículos (`articles`).

**Comportamiento:** si `consecutive_failures` llega a `SOURCE_MAX_FAILURES` (por defecto 5), la fuente se desactiva automáticamente y se muestra una alerta en el panel.

---

### Article — Artículos recolectados

**Tabla:** `articles`  
**Índice:** `ix_articles_url_hash` (sobre `url_hash` para búsqueda rápida de duplicados)

| Campo             | Tipo                | Descripción                                                          |
| ----------------- | ------------------- | -------------------------------------------------------------------- |
| `id`              | Integer PK          | Identificador único                                                  |
| `source_id`       | Integer FK          | Fuente que lo publicó                                                |
| `title`           | String(500)         | Título del artículo                                                  |
| `url`             | String(1000) UNIQUE | URL original                                                         |
| `url_hash`        | String(64)          | SHA-256 de la URL normalizada (para deduplicación rápida)            |
| `original_text`   | Text                | Texto del feed (descripción o snippet)                               |
| `full_text`       | Text                | Texto completo scrapeado del artículo                                |
| `category`        | String(50)          | Categoría asignada por IA                                            |
| `relevance_score` | Integer             | Score de relevancia 1-10 asignado por IA                             |
| `sentiment`       | String(20)          | `positive`, `neutral` o `negative`                                   |
| `published_at`    | DateTime            | Fecha de publicación original                                        |
| `fetched_at`      | DateTime            | Cuándo lo recolectó el sistema                                       |
| `status`          | String(20)          | `pending`, `approved`, `rejected` o `sent`                           |
| `enrich_attempts` | Integer             | Cuántas veces se intentó enriquecer con IA                           |
| `thumbnail_url`   | String(1000)        | URL de imagen de portada (si existe)                                 |
| `cluster_id`      | Integer             | ID del grupo temático (topic clustering)                             |
| `feedback`        | Integer             | Valoración del editor: `-1` = dislike, `0` = sin valorar, `1` = like |
| `is_recurring`    | Boolean             | Si el artículo trata un tema recurrente                              |

**Flujo de estados:**

```
pending → approved → sent
        ↘ rejected
```

**Categorías válidas:** Política, Economía, Tecnología, Deportes, Internacional, Entretenimiento, Salud, Ciencia.

---

### Summary — Resúmenes generados por IA

**Tabla:** `summaries`

| Campo          | Tipo              | Descripción                                     |
| -------------- | ----------------- | ----------------------------------------------- |
| `id`           | Integer PK        | Identificador único                             |
| `article_id`   | Integer FK UNIQUE | Artículo al que pertenece (1:1)                 |
| `summary_text` | Text              | Resumen en español (2-3 oraciones)              |
| `key_point`    | Text              | Punto clave (el hecho central)                  |
| `context_note` | Text              | Contexto o antecedente relevante                |
| `impact`       | Text              | Impacto o consecuencia potencial                |
| `model_used`   | String(50)        | Modelo IA usado (ej: `llama-3.3-70b-versatile`) |
| `tokens_used`  | Integer           | Tokens consumidos en la generación              |
| `created_at`   | DateTime          | Cuándo se generó el resumen                     |

---

### Subscriber — Suscriptores de Telegram

**Tabla:** `subscribers`  
Usuarios públicos que se suscribieron mediante `/suscribir` en el bot.

| Campo           | Tipo              | Descripción                            |
| --------------- | ----------------- | -------------------------------------- |
| `id`            | Integer PK        | Identificador único                    |
| `chat_id`       | String(50) UNIQUE | Chat ID de Telegram                    |
| `username`      | String(200)       | Username de Telegram (puede ser nulo)  |
| `first_name`    | String(200)       | Nombre del usuario                     |
| `is_active`     | Boolean           | Si el suscriptor recibe notificaciones |
| `subscribed_at` | DateTime          | Cuándo se suscribió                    |
| `last_seen_at`  | DateTime          | Última interacción con el bot          |

---

### DigestConfig — Configuración del digest diario

**Tabla:** `digest_config` (singleton — siempre hay una sola fila)

| Campo        | Tipo       | Descripción                                               |
| ------------ | ---------- | --------------------------------------------------------- |
| `id`         | Integer PK | Siempre 1                                                 |
| `hour`       | Integer    | Hora de envío del digest (0–23)                           |
| `count`      | Integer    | Número máximo de artículos por digest                     |
| `min_score`  | Integer    | Score mínimo para incluir un artículo                     |
| `categories` | String     | Categorías a incluir (separadas por comas, vacío = todas) |
| `is_active`  | Boolean    | Si el digest automático está habilitado                   |

---

### Keyword — Palabras clave para alertas

**Tabla:** `keywords`

| Campo        | Tipo               | Descripción                  |
| ------------ | ------------------ | ---------------------------- |
| `id`         | Integer PK         | Identificador único          |
| `keyword`    | String(200) UNIQUE | Palabra o frase a monitorear |
| `is_active`  | Boolean            | Si la keyword está activa    |
| `created_at` | DateTime           | Cuándo se agregó             |

Cuando un artículo nuevo contiene una keyword activa en su título, se envía una alerta inmediata a Telegram.

---

### Webhook — Integraciones externas

**Tabla:** `webhooks`

| Campo           | Tipo         | Descripción                                                       |
| --------------- | ------------ | ----------------------------------------------------------------- |
| `id`            | Integer PK   | Identificador único                                               |
| `name`          | String(200)  | Nombre descriptivo                                                |
| `url`           | String(1000) | URL de destino (POST)                                             |
| `events`        | String       | Eventos que lo disparan: `fetch`, `keyword`, `digest`, `approved` |
| `secret`        | String(200)  | Secreto HMAC para verificar autenticidad (opcional)               |
| `is_active`     | Boolean      | Si el webhook está habilitado                                     |
| `last_fired_at` | DateTime     | Última vez que se disparó                                         |

---

### InAppNotification — Notificaciones internas

**Tabla:** `in_app_notifications`

| Campo        | Tipo        | Descripción                                         |
| ------------ | ----------- | --------------------------------------------------- |
| `id`         | Integer PK  | Identificador único                                 |
| `type`       | String(50)  | Tipo: `fetch`, `digest`, `keyword`, `error`, `info` |
| `title`      | String(200) | Título de la notificación                           |
| `message`    | Text        | Mensaje completo                                    |
| `read`       | Boolean     | Si el editor ya la leyó                             |
| `created_at` | DateTime    | Cuándo se creó                                      |

---

## Notas de base de datos

- **Deduplicación:** la columna `url_hash` almacena el SHA-256 de la URL limpiada (sin parámetros UTM, fbclid, trailing slashes). El sistema verifica esta hash antes de insertar cualquier artículo.
- **Migraciones:** no se usa Alembic. Las columnas nuevas se agregan con `ALTER TABLE ... ADD COLUMN` al arrancar, lo que es idempotente y seguro.
- **PostgreSQL:** solo requiere cambiar `DATABASE_URL` a una cadena de conexión PostgreSQL. El resto funciona igual.
