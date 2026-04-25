# API — Autenticación

Base URL: `/api/v1`

---

## Modos de autenticación

NewsLet Pro soporta tres mecanismos de autenticación, activados según las variables de entorno configuradas:

| Modo | Activación | Uso |
|---|---|---|
| **Sin auth** | `ADMIN_PASSWORD` vacío | Panel y API accesibles sin credenciales |
| **JWT** | `ADMIN_PASSWORD` configurado | Login con contraseña → token Bearer |
| **Service Key** | `SERVICE_KEY` configurado | Integración con CI/CD, GitHub Actions |

---

## Endpoints

### POST `/api/v1/auth/login`

Inicia sesión con la contraseña de administrador. Devuelve un token JWT.

**Body:**
```json
{
  "password": "mi_contraseña_admin"
}
```

**Respuesta exitosa (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": "1440m"
}
```

**Respuesta si auth deshabilitada (200):**
```json
{
  "token": null,
  "message": "Auth disabled — set ADMIN_PASSWORD in .env to enable"
}
```

**Error (401):**
```json
{
  "detail": "Contraseña incorrecta"
}
```

---

### GET `/api/v1/auth/status`

Indica si la autenticación JWT está habilitada.

**Respuesta:**
```json
{
  "auth_enabled": true
}
```

---

### GET `/api/v1/auth/service-token?key=SERVICE_KEY`

Genera un token JWT de larga duración (365 días) para uso en automatizaciones.

**Query param:** `key` — debe coincidir con `SERVICE_KEY` del `.env`.

**Respuesta (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error (403):**
```json
{
  "detail": "Invalid service key"
}
```

---

## Usar el token en llamadas a la API

Una vez obtenido el token, inclúyelo en el header `Authorization` de todas las llamadas protegidas:

```bash
curl -H "Authorization: Bearer TU_TOKEN" \
     https://tu-dominio/api/v1/articles
```

Desde JavaScript (el panel web lo hace automáticamente):

```javascript
const token = localStorage.getItem("token");
fetch("/api/v1/articles", {
  headers: { "Authorization": `Bearer ${token}` }
});
```

---

## Webhook de Telegram (endpoint público)

### POST `/api/v1/telegram/webhook`

Endpoint que Telegram llama directamente cuando el bot recibe un mensaje (modo webhook en producción). **No requiere autenticación JWT** — es público por diseño.

El servidor procesa el update y responde siempre `200 OK` para evitar reintentos de Telegram.

Este endpoint se registra automáticamente al arrancar cuando `WEBHOOK_BASE_URL` está configurado.

---

## Flujo de login en el panel web

1. Usuario abre `https://tu-dominio` → panel detecta que `auth_enabled: true`
2. Redirige a `/login.html`
3. Usuario ingresa contraseña → POST a `/api/v1/auth/login`
4. Token guardado en `localStorage`
5. Todas las llamadas API incluyen `Authorization: Bearer <token>` automáticamente
6. Token expira en 24 horas (configurable con `JWT_EXPIRE_MINUTES`)

---

## PIN de panel (capa adicional)

Si `PANEL_PIN` está configurado en `.env`, el servidor agrega un middleware HTTP que bloquea el acceso a las páginas HTML del panel (no a la API ni al WebSocket).

El PIN se envía como:
- Header: `X-Panel-Pin: 1234`
- Query param: `?pin=1234`

El panel web guarda el PIN en `localStorage` y lo incluye automáticamente.
