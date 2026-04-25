# Configuración — NewsLet Pro

Toda la configuración se hace a través de variables de entorno en el archivo `.env`.  
Copia `.env.example` como punto de partida y edita solo lo que necesitas.

---

## Variables de entorno

### IA — Proveedor principal

| Variable         | Por defecto               | Descripción                               |
| ---------------- | ------------------------- | ----------------------------------------- |
| `AI_PROVIDER`    | `groq`                    | Proveedor de IA: `groq` o `openai`        |
| `GROQ_API_KEY`   | _(vacío)_                 | Clave API de Groq (recomendado — gratis)  |
| `GROQ_MODEL`     | `llama-3.3-70b-versatile` | Modelo de Groq a usar                     |
| `OPENAI_API_KEY` | _(vacío)_                 | Clave API de OpenAI (alternativa de pago) |
| `OPENAI_MODEL`   | `gpt-4o-mini`             | Modelo de OpenAI a usar                   |

> Si `AI_PROVIDER=groq` y `GROQ_API_KEY` está vacío, el sistema funcionará pero sin resúmenes automáticos.

---

### NewsAPI

| Variable      | Por defecto | Descripción                                                                        |
| ------------- | ----------- | ---------------------------------------------------------------------------------- |
| `NEWSAPI_KEY` | _(vacío)_   | Clave de [newsapi.org](https://newsapi.org). Sin ella, solo se usan RSS y scrapers |

---

### Telegram

| Variable             | Por defecto | Descripción                                                                                       |
| -------------------- | ----------- | ------------------------------------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN` | _(vacío)_   | Token del bot (`@BotFather`). Sin él, no hay notificaciones                                       |
| `TELEGRAM_CHAT_ID`   | _(vacío)_   | Chat ID del administrador principal                                                               |
| `TELEGRAM_ADMIN_IDS` | _(vacío)_   | Lista de Chat IDs adicionales con acceso admin, separados por comas                               |
| `WEBHOOK_BASE_URL`   | _(vacío)_   | URL pública HTTPS para modo webhook (ej: `https://mi-app.koyeb.app`). Vacío = polling (dev local) |

---

### Base de datos

| Variable       | Por defecto              | Descripción                           |
| -------------- | ------------------------ | ------------------------------------- |
| `DATABASE_URL` | `sqlite:///./newslet.db` | URL de conexión SQLAlchemy. Ejemplos: |

**Ejemplos de `DATABASE_URL`:**

```
# SQLite local (por defecto)
DATABASE_URL=sqlite:///./newslet.db

# SQLite en volumen persistente (Fly.io)
DATABASE_URL=sqlite:////app/data/newslet.db

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

### Scheduler

| Variable                 | Por defecto                      | Descripción                                                   |
| ------------------------ | -------------------------------- | ------------------------------------------------------------- |
| `FETCH_INTERVAL_MINUTES` | `10`                             | Cada cuántos minutos se recolectan noticias                   |
| `DIGEST_HOUR`            | `8`                              | Hora del digest diario (0–23, en la zona horaria configurada) |
| `APP_TIMEZONE`           | `America/Argentina/Buenos_Aires` | Zona horaria para el digest y fechas mostradas                |

---

### Análisis con IA

| Variable              | Por defecto | Descripción                                              |
| --------------------- | ----------- | -------------------------------------------------------- |
| `RELEVANCE_THRESHOLD` | `5`         | Score mínimo (1–10) para auto-aprobar artículos          |
| `ENRICH_ARTICLES`     | `true`      | Habilitar categorización + score automático              |
| `SCRAPE_FULL_TEXT`    | `true`      | Scrapear el texto completo del artículo antes de resumir |

---

### Seguridad y autenticación

| Variable             | Por defecto                      | Descripción                                                    |
| -------------------- | -------------------------------- | -------------------------------------------------------------- |
| `ADMIN_PASSWORD`     | _(vacío)_                        | Contraseña del panel web. Vacío = sin login requerido          |
| `JWT_SECRET`         | `change-me-in-production-please` | Secreto para firmar tokens JWT. **Cambiar en producción**      |
| `JWT_EXPIRE_MINUTES` | `1440`                           | Tiempo de vida del token JWT (1440 min = 24 horas)             |
| `PANEL_PIN`          | _(vacío)_                        | PIN de 4+ dígitos para proteger el panel HTML (capa adicional) |
| `SERVICE_KEY`        | _(vacío)_                        | Clave para llamadas de servicio (CI/CD, GitHub Actions)        |

---

### Email (SMTP)

| Variable        | Por defecto      | Descripción                                     |
| --------------- | ---------------- | ----------------------------------------------- |
| `SMTP_ENABLED`  | `false`          | Habilitar envío de digest por email             |
| `SMTP_HOST`     | `smtp.gmail.com` | Servidor SMTP                                   |
| `SMTP_PORT`     | `587`            | Puerto SMTP (587 = STARTTLS, 465 = SSL)         |
| `SMTP_USER`     | _(vacío)_        | Usuario de autenticación SMTP                   |
| `SMTP_PASSWORD` | _(vacío)_        | Contraseña SMTP (para Gmail: usar App Password) |
| `SMTP_FROM`     | _(vacío)_        | Dirección de envío                              |
| `SMTP_TO`       | _(vacío)_        | Destinatarios, separados por comas              |

---

### Rate limiting y logs

| Variable                | Por defecto        | Descripción                                  |
| ----------------------- | ------------------ | -------------------------------------------- |
| `RATE_LIMIT_PER_MINUTE` | `60`               | Solicitudes por minuto por IP en la API      |
| `LOG_FILE`              | `logs/newslet.log` | Ruta del archivo de log                      |
| `LOG_MAX_BYTES`         | `10485760`         | Tamaño máximo del log antes de rotar (10 MB) |
| `LOG_BACKUP_COUNT`      | `5`                | Número de archivos de log a conservar        |

---

### Backup

| Variable     | Por defecto | Descripción                                                     |
| ------------ | ----------- | --------------------------------------------------------------- |
| `BACKUP_DIR` | _(vacío)_   | Directorio local para backups de la DB. Ej: `/app/data/backups` |

Si `BACKUP_DIR` está configurado o el directorio `/app/data` existe (Fly.io), se hacen backups automáticos a las 02:00 UTC y se envía el archivo `.db` al chat de Telegram del admin.

---

### Salud de fuentes

| Variable              | Por defecto | Descripción                                               |
| --------------------- | ----------- | --------------------------------------------------------- |
| `SOURCE_MAX_FAILURES` | `5`         | Fallos consecutivos antes de auto-deshabilitar una fuente |

---

## Ejemplo de .env mínimo funcional

```env
# IA (mínimo para tener resúmenes)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Telegram (para notificaciones)
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=987654321

# Seguridad (cambiar en producción)
JWT_SECRET=mi-secreto-super-seguro-2024
ADMIN_PASSWORD=mi_contraseña_admin
```

## Ejemplo de .env completo para producción

```env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEWSAPI_KEY=abcdef1234567890abcdef1234567890

TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=987654321
TELEGRAM_ADMIN_IDS=111111111,222222222
WEBHOOK_BASE_URL=https://mi-app.koyeb.app

DATABASE_URL=sqlite:////app/data/newslet.db

FETCH_INTERVAL_MINUTES=10
DIGEST_HOUR=8
APP_TIMEZONE=America/Argentina/Buenos_Aires

RELEVANCE_THRESHOLD=6
ADMIN_PASSWORD=mi_contraseña_segura
JWT_SECRET=cambia-esto-por-algo-random-largo

SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=mi@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=mi@gmail.com
SMTP_TO=redaccion@empresa.com

BACKUP_DIR=/app/data/backups
```
