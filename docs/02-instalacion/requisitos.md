# Requisitos — NewsLet Pro

## Requisitos del sistema

| Componente | Mínimo                | Recomendado        |
| ---------- | --------------------- | ------------------ |
| **Python** | 3.12                  | 3.12+              |
| **RAM**    | 256 MB                | 512 MB             |
| **Disco**  | 500 MB                | 2 GB               |
| **CPU**    | 1 núcleo              | 2 núcleos          |
| **SO**     | Linux, macOS, Windows | Linux (producción) |

> Para correr con Docker no se necesita Python local, solo Docker instalado.

---

## Dependencias Python (requirements.txt)

```
fastapi
uvicorn[standard]
sqlalchemy
pydantic-settings
python-dotenv
feedparser
httpx
openai
groq
apscheduler
slowapi
python-jose[cryptography]
passlib
reportlab
Pillow
python-multipart
psycopg2-binary
```

### Descripción de dependencias clave

| Paquete             | Para qué se usa                                   |
| ------------------- | ------------------------------------------------- |
| `fastapi`           | Framework web y API REST                          |
| `uvicorn[standard]` | Servidor ASGI con soporte WebSocket               |
| `sqlalchemy`        | ORM para SQLite / PostgreSQL                      |
| `pydantic-settings` | Lectura de `.env` con validación de tipos         |
| `feedparser`        | Parsing de feeds RSS y Atom                       |
| `httpx`             | Cliente HTTP async (NewsAPI, Telegram, scrapers)  |
| `openai`            | SDK oficial de OpenAI (GPT-4o-mini)               |
| `groq`              | SDK oficial de Groq (Llama 3.3 70B, gratuito)     |
| `apscheduler`       | Scheduler de jobs en segundo plano                |
| `slowapi`           | Rate limiting para endpoints de la API            |
| `python-jose`       | Generación y verificación de tokens JWT           |
| `reportlab`         | Generación de PDF para el digest                  |
| `psycopg2-binary`   | Driver PostgreSQL (opcional si se usa PostgreSQL) |

---

## Dependencias del sistema (para Docker slim)

El `Dockerfile` instala automáticamente:

- `gcc` — compilación de extensiones Python
- `libpq-dev` — soporte PostgreSQL (incluso si se usa SQLite)

---

## Cuentas y claves necesarias

### Obligatorio para funciones básicas

| Servicio         | Obtención                                               | Gratis                     |
| ---------------- | ------------------------------------------------------- | -------------------------- |
| **Groq API Key** | [console.groq.com](https://console.groq.com) → API Keys | Sí (con límites generosos) |

### Recomendado para funciones completas

| Servicio               | Obtención                                            | Gratis                            |
| ---------------------- | ---------------------------------------------------- | --------------------------------- |
| **Telegram Bot Token** | `@BotFather` en Telegram → `/newbot`                 | Sí (siempre)                      |
| **NewsAPI Key**        | [newsapi.org/register](https://newsapi.org/register) | Sí (100 req/día en plan gratuito) |

### Opcional

| Servicio           | Obtención                                          | Gratis                |
| ------------------ | -------------------------------------------------- | --------------------- |
| **OpenAI API Key** | [platform.openai.com](https://platform.openai.com) | No (pago por uso)     |
| **Servidor SMTP**  | Gmail, Sendgrid, Mailgun, etc.                     | Depende del proveedor |

---

## Obtener el Chat ID de Telegram

1. Crea el bot con `@BotFather` y copia el token
2. Envía cualquier mensaje a tu bot desde tu cuenta de Telegram
3. Visita: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Busca el campo `"chat": { "id": 123456789 }` — ese es tu Chat ID

---

## Instalación local (sin Docker)

```bash
# Clonar o descargar el proyecto
cd NewsLet

# Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env
# Editar .env con tus claves

# Arrancar
uvicorn app.main:app --reload --port 8000
```

El panel estará en: `http://localhost:8000`
La documentación interactiva de la API: `http://localhost:8000/docs`
