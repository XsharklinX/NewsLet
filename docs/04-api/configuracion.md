# API — Configuración

Base URL: `/api/v1`

---

## Palabras clave (Keywords)

### GET `/api/v1/keywords`

Lista todas las palabras clave de alerta.

**Respuesta (200):**

```json
[
  {
    "id": 1,
    "keyword": "inteligencia artificial",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

---

### POST `/api/v1/keywords`

Agrega una nueva palabra clave.

**Body:**

```json
{
  "keyword": "cambio climático"
}
```

**Respuesta (201):** objeto keyword creado.  
**Error (409):** la keyword ya existe.

---

### PATCH `/api/v1/keywords/{id}/toggle`

Activa o desactiva una keyword.

---

### DELETE `/api/v1/keywords/{id}`

Elimina una keyword.

---

## Configuración del Digest

### GET `/api/v1/digest/config`

Obtiene la configuración actual del digest diario.

**Respuesta (200):**

```json
{
  "id": 1,
  "hour": 8,
  "count": 10,
  "min_score": 5,
  "categories": "Política,Economía",
  "is_active": true
}
```

---

### PATCH `/api/v1/digest/config`

Actualiza la configuración del digest.

**Body (todos los campos son opcionales):**

```json
{
  "hour": 9,
  "count": 15,
  "min_score": 6,
  "categories": "Tecnología,Ciencia",
  "is_active": true
}
```

- `hour`: 0-23, hora de envío (en la zona horaria de `APP_TIMEZONE`)
- `count`: número máximo de artículos
- `min_score`: score mínimo para incluir artículos (0 = todos)
- `categories`: categorías separadas por comas (vacío = todas)
- `is_active`: si el digest automático está habilitado

Al actualizar `hour`, el scheduler se reprograma automáticamente sin necesidad de reiniciar.

---

## Webhooks

### GET `/api/v1/webhooks`

Lista todos los webhooks configurados.

**Respuesta (200):**

```json
[
  {
    "id": 1,
    "name": "n8n Workflow",
    "url": "https://mi-n8n.com/webhook/abc123",
    "events": "fetch,approved",
    "is_active": true,
    "last_fired_at": "2024-01-15T10:00:00"
  }
]
```

---

### POST `/api/v1/webhooks`

Crea un nuevo webhook.

**Body:**

```json
{
  "name": "Zapier",
  "url": "https://hooks.zapier.com/hooks/catch/xxx/yyy/",
  "events": "fetch,keyword,approved",
  "secret": "mi-secreto-hmac"
}
```

**Eventos disponibles:**

- `fetch` — se dispara cuando se completa un ciclo de recolección de noticias
- `keyword` — cuando un artículo coincide con una keyword activa
- `digest` — cuando se envía el digest diario
- `approved` — cuando un artículo es aprobado manualmente

`secret` es opcional. Si se configura, el sistema envía un header `X-Webhook-Signature` con el HMAC-SHA256 del body para verificar autenticidad.

---

### PATCH `/api/v1/webhooks/{id}/toggle`

Activa o desactiva un webhook.

---

### DELETE `/api/v1/webhooks/{id}`

Elimina un webhook.

---

## Configuración de administrador

### GET `/api/v1/admin/settings`

Devuelve los valores actuales de configuración del sistema (variables de entorno).  
Los campos sensibles (claves API, contraseñas) se muestran como `••••••••`.

**Respuesta (200):**

```json
{
  "settings": {
    "AI_PROVIDER": { "value": "groq", "type": "select", "options": ["groq", "openai"] },
    "GROQ_API_KEY": { "value": "••••••••", "type": "password" },
    "FETCH_INTERVAL_MINUTES": { "value": "10", "type": "number" },
    "DIGEST_HOUR": { "value": "8", "type": "number" }
  }
}
```

---

### POST `/api/v1/admin/settings`

Actualiza una o más variables de configuración. Los cambios se escriben en el archivo `.env` y se aplican en tiempo real cuando es posible.

**Body:**

```json
{
  "updates": {
    "FETCH_INTERVAL_MINUTES": "15",
    "RELEVANCE_THRESHOLD": "7"
  }
}
```

**Respuesta (200):**

```json
{
  "message": "3 configuraciones actualizadas",
  "restart_needed": false,
  "updated": ["FETCH_INTERVAL_MINUTES", "RELEVANCE_THRESHOLD"]
}
```

`restart_needed: true` indica que algún cambio requiere reiniciar el servidor (ej: `DATABASE_URL`, `JWT_SECRET`).

> Las claves API y contraseñas solo se actualizan si se envían con un valor no vacío.
