# Servicios — Telegram

NewsLet Pro tiene dos componentes de Telegram: el **bot** (recibe comandos) y el **notificador** (envía mensajes).

---

## Modos de operación

| Modo | Cuándo | Configuración |
|---|---|---|
| **Polling** | Desarrollo local | `WEBHOOK_BASE_URL` vacío |
| **Webhook** | Producción | `WEBHOOK_BASE_URL=https://tu-dominio.com` |

En modo polling, el bot hace requests repetidos a la API de Telegram preguntando si hay mensajes nuevos. En modo webhook, Telegram envía los mensajes directamente a tu servidor (más eficiente, requiere HTTPS).

---

## Bot de Telegram (`services/telegram_bot.py`)

### Comandos de administrador

Solo accesibles para los chat IDs en `TELEGRAM_CHAT_ID` y `TELEGRAM_ADMIN_IDS`.

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida con lista de comandos |
| `/noticias` | Muestra las últimas 5 noticias aprobadas |
| `/pending` | Cuenta de artículos pendientes de revisión |
| `/digest` | Envía el digest diario ahora |
| `/fetch` | Dispara un ciclo de fetch manual |
| `/stats` | Estadísticas: total artículos, pendientes, sources |
| `/semanal` | Informe semanal: artículos de los últimos 7 días |
| `/fuentes` | Lista de fuentes activas |
| `/top` | Top 5 artículos con mayor score de la semana |
| `/buscar <término>` | Busca artículos por título |

### Comandos públicos (suscriptores)

Disponibles para cualquier usuario que interactúe con el bot.

| Comando | Descripción |
|---|---|
| `/suscribir` | Suscribirse al digest diario |
| `/cancelar` | Darse de baja del digest |
| `/noticias` | Ver las últimas noticias (versión pública) |

### Broadcast a suscriptores

El digest diario se envía tanto al canal del administrador como a todos los suscriptores activos. Los suscriptores reciben un resumen simplificado con los primeros 5 artículos.

---

## Notificador (`services/telegram_notifier.py`)

Envía mensajes a Telegram en nombre del bot.

### Función: `send_article(article)`

Envía un artículo individual al chat configurado en `TELEGRAM_CHAT_ID`.

**Formato del mensaje:**
```
📰 <b>Título del artículo</b>

📋 Resumen: Resumen en español...

🔑 Punto clave: El hecho central...
📚 Contexto: El antecedente...
⚡ Impacto: La consecuencia...

🏷️ Tecnología · ⭐ 8/10 · 😊 Positivo

🔗 <a href="URL">Leer artículo completo</a>
```

### Función: `send_digest(articles)`

Envía el digest diario completo al canal del administrador.

**Formato del mensaje:**
```
📰 <b>Digest diario — 10 noticias</b>
📅 Martes, 15 de enero de 2024

1. <b>Título artículo 1</b>
   Tecnología · ⭐ 9/10
   Resumen breve...
   <a href="URL">Leer más</a>

2. <b>Título artículo 2</b>
   ...
```

### Función: `send_keyword_alert(article, keyword)`

Alerta inmediata cuando un artículo nuevo coincide con una keyword.

**Formato:**
```
🔔 <b>Alerta: "inteligencia artificial"</b>

📰 Título del artículo
Fuente · Fecha

<a href="URL">Ver artículo</a>
```

---

## Webhook de Telegram (`services/telegram_webhook.py`)

En producción, registra el webhook automáticamente al iniciar el servidor.

### Función: `register_webhook(base_url)`

Llama a `https://api.telegram.org/bot<TOKEN>/setWebhook` con la URL:
```
<WEBHOOK_BASE_URL>/api/v1/telegram/webhook
```

Telegram verificará que la URL responde con `200 OK` antes de activar el webhook.

---

## Backup de DB por Telegram

El scheduler envía la base de datos como documento a `TELEGRAM_CHAT_ID` todos los días a las 02:00 UTC. Esto actúa como backup automático, especialmente útil en plataformas con almacenamiento efímero (Render free tier, etc.).

---

## Configuración mínima

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_CHAT_ID=987654321
```

Para producción con webhook:
```env
WEBHOOK_BASE_URL=https://mi-app.koyeb.app
```

Para múltiples administradores:
```env
TELEGRAM_ADMIN_IDS=111111111,222222222,333333333
```
