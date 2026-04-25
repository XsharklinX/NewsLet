# Despliegue — NewsLet Pro

---

## Opción 1: Local (desarrollo)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env con tus claves

# Arrancar
uvicorn app.main:app --reload --port 8000
```

- Panel: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- El bot de Telegram usa **polling** automáticamente cuando `WEBHOOK_BASE_URL` no está configurado.

---

## Opción 2: Docker (local o servidor propio)

```bash
# Construir imagen
docker build -t newslet .

# Arrancar con .env
docker run -d \
  --name newslet \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  newslet
```

**Con Docker Compose (recomendado para servidor propio):**

```yaml
# docker-compose.yml
version: "3.9"
services:
  newslet:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

```bash
docker compose up -d
```

---

## Opción 3: Koyeb (cloud gratuito — recomendado)

Koyeb ofrece hosting gratuito con 512 MB RAM, perfecto para esta app.

### Pasos

1. Crear cuenta en [koyeb.com](https://www.koyeb.com)
2. Conectar tu repositorio de GitHub
3. **New Service → GitHub** → seleccionar el repositorio
4. Configurar el servicio:
   - **Builder**: Dockerfile
   - **Port**: `8000`
   - **Instance**: Free (nano)
5. En **Environment Variables**, agregar todas las variables de tu `.env`
6. En **Volumes** (si el plan lo permite): montar `/app/data` para persistencia de la DB
7. Hacer clic en **Deploy**

### Configuración de Telegram en Koyeb

Koyeb asigna una URL pública (ej: `https://mi-app-abc.koyeb.app`).  
Configura el webhook para que Telegram envíe updates directamente al servidor:

```env
WEBHOOK_BASE_URL=https://mi-app-abc.koyeb.app
```

El servidor registrará el webhook automáticamente al arrancar.

### Importante: persistencia de datos

En el plan gratuito de Koyeb, el sistema de archivos **no es persistente**.  
La base de datos se pierde al redesplegar. Opciones:

1. **Usar PostgreSQL externo** (Supabase free tier, Neon.tech, Railway):
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

2. **Activar backups automáticos a Telegram**: configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` — el sistema enviará la DB cada día a las 02:00 UTC.

---

## Opción 4: Fly.io

```bash
# Instalar flyctl
brew install flyctl  # o descargar desde fly.io

# Login
fly auth login

# Inicializar (la primera vez)
fly launch

# Crear volumen persistente para la DB
fly volumes create newslet_data --size 1 --region gru

# Configurar variables de entorno
fly secrets set GROQ_API_KEY=gsk_xxx
fly secrets set TELEGRAM_BOT_TOKEN=xxx:yyy
fly secrets set TELEGRAM_CHAT_ID=123456789
fly secrets set JWT_SECRET=secreto-seguro
fly secrets set DATABASE_URL=sqlite:////app/data/newslet.db

# Desplegar
fly deploy
```

**fly.toml mínimo:**
```toml
app = "mi-newslet"
primary_region = "gru"

[build]

[http_service]
  internal_port = 8000
  force_https = true

[mounts]
  source = "newslet_data"
  destination = "/app/data"
```

---

## Opción 5: Railway

1. Conectar repositorio en [railway.app](https://railway.app)
2. Railway detecta el Dockerfile automáticamente
3. Agregar variables de entorno en la sección **Variables**
4. Railway asigna `$PORT` automáticamente — el Dockerfile ya usa `${PORT:-8000}`
5. Agregar un **Volume** montado en `/app/data` para persistencia

---

## Variables de entorno críticas para producción

Siempre configurar estas en cualquier plataforma cloud:

```env
JWT_SECRET=una-cadena-aleatoria-de-al-menos-32-caracteres
ADMIN_PASSWORD=contraseña-para-el-panel
WEBHOOK_BASE_URL=https://tu-dominio.koyeb.app   # o fly.dev, railway.app, etc.
DATABASE_URL=sqlite:////app/data/newslet.db      # o PostgreSQL
```

---

## Verificar que funciona

Una vez desplegado, verifica en orden:

```bash
# 1. Health check
curl https://tu-dominio/api/v1/stats

# 2. Fetch manual de noticias
curl -X POST https://tu-dominio/api/v1/fetch/now \
  -H "Authorization: Bearer TU_TOKEN"

# 3. Abrir el panel
# Navegar a https://tu-dominio en el navegador
```
