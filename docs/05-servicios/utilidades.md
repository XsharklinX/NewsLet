# Servicios — Utilidades

---

## Email Notifier (`services/email_notifier.py`)

Envía el digest diario por correo electrónico vía SMTP.

**Activación:** `SMTP_ENABLED=true` en `.env`.

### Configuración necesaria

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=mi@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # App Password de Gmail
SMTP_FROM=mi@gmail.com
SMTP_TO=destinatario1@email.com,destinatario2@email.com
```

### Uso con Gmail

Gmail requiere una **App Password** (no la contraseña normal):
1. Google Account → Seguridad → Verificación en 2 pasos (debe estar activa)
2. Seguridad → Contraseñas de aplicaciones → Crear
3. Copiar la contraseña de 16 caracteres a `SMTP_PASSWORD`

### Función: `send_email(subject, body)`

Envía un email HTML a todos los destinatarios en `SMTP_TO`. El contenido es el digest formateado en HTML con tabla de artículos.

---

## PDF Generator (`services/pdf_generator.py`)

Genera documentos PDF con el digest de artículos.

**Biblioteca:** `reportlab` + `Pillow`

### Función: `generate_digest_pdf(articles) → bytes`

Retorna el PDF como bytes para ser descargado vía la API (`GET /api/v1/digest/pdf`).

### Estructura del PDF

- **Encabezado:** logo del sistema + nombre + fecha de generación
- **Tabla de artículos:** número, título, fuente, categoría, score, sentimiento
- **Sección de resúmenes:** para cada artículo: título, resumen, punto clave, impacto, enlace

---

## Webhook Dispatcher (`services/webhook_dispatcher.py`)

Envía notificaciones HTTP POST a URLs externas cuando ocurren eventos en el sistema.

### Eventos disponibles

| Evento | Cuándo se dispara |
|---|---|
| `fetch` | Al completar un ciclo de recolección |
| `keyword` | Al detectar un artículo con keyword activa |
| `digest` | Al enviar el digest diario |
| `approved` | Al aprobar un artículo manualmente |

### Payload enviado

```json
{
  "event": "fetch",
  "timestamp": "2024-01-15T10:00:00Z",
  "data": {
    "total_new": 12,
    "summarized": 10
  }
}
```

Para eventos `keyword` y `approved`, `data` incluye el artículo completo.

### Verificación con secreto (HMAC)

Si el webhook tiene configurado un `secret`, se incluye el header:
```
X-Webhook-Signature: sha256=<hmac-sha256-del-body>
```

El receptor puede verificar la autenticidad del payload calculando el HMAC con el mismo secreto.

---

## Notification Service (`services/notification_service.py`)

Crea notificaciones internas que aparecen en el panel web (campana de notificaciones).

### Función: `push(db, type, title, message)`

```python
push(db, "fetch", "Fetch completado", "12 artículos nuevos · 10 resumidos")
push(db, "keyword", "Alerta: IA", "Artículo: 'Nueva IA de OpenAI...'")
push(db, "error", "Error en fetch", "Timeout en fuente El País")
push(db, "digest", "Digest enviado", "10 artículos enviados por Telegram")
push(db, "info", "Limpieza", "57 artículos antiguos eliminados")
```

Los tipos tienen iconos distintos en el panel:
- `fetch` → 📡
- `keyword` → 🔔
- `digest` → 📰
- `error` → ❌
- `info` → ℹ️

---

## Startup Validator (`services/startup_validator.py`)

Se ejecuta una vez al arrancar el servidor y verifica que la configuración es válida.

### Validaciones

- Si `GROQ_API_KEY` está configurado: hace una llamada de prueba a la API de Groq
- Si `TELEGRAM_BOT_TOKEN` está configurado: verifica que el token es válido con `getMe`
- Si `NEWSAPI_KEY` está configurado: hace una petición de prueba
- Si `SMTP_ENABLED=true`: verifica que todos los campos SMTP están presentes

Los errores de configuración se muestran en los logs al inicio pero no impiden que el servidor arranque.
