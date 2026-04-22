# 📌 NewsLet Pro — Cheat Sheet (Resumen de bolsillo)

**Imprime esta página y ten siempre a mano**

---

## ¿QUÉ ES?

Un programa que **automáticamente busca, resume y envía noticias importantes** cada día.

- ✅ Buscador automático de noticias (50+ fuentes)
- ✅ Inteligencia artificial que resume (50 palabras)
- ✅ Filtro inteligente (solo noticias importantes)
- ✅ Envío por Telegram + Email + Web
- ✅ Panel web para aprobar/rechazar noticias

---

## CÓMO USAR (Usuario Normal)

### En Telegram

```
/start             → Iniciar bot, ver comandos
/noticias          → Ver últimas 5 noticias
/buscar TEMA       → Buscar por tema (ej: /buscar economia)
/leer 123          → Leer artículo completo (número en paréntesis)
/suscribir         → Recibir resumen diario a las 8am
/cancelar          → Cancelar suscripción
```

### En la Web

```
1. Abre: http://localhost:8000  (o el link que te den)
2. Ver tabla con noticias
3. Filtrar por tema/fuente
4. Leer cualquiera
5. Eso es todo
```

---

## CÓMO ADMINISTRAR (Admin/Propietario)

### Panel Admin

```
URL: http://localhost:8000
```

#### Columna izquierda: 
```
📰 NOTICIAS
├─ Todas              (lista completa)
├─ Pendientes         (esperando aprobación)
├─ Aprobadas          (listas para enviar)
└─ Rechazadas         (no se enviarán)

📡 FUENTES
├─ Listar             (ver todas las fuentes)
├─ Agregar            (agregar nueva fuente RSS/API)
└─ Salud              (ver cuáles están rotas)

📊 ESTADÍSTICAS
├─ Total artículos
├─ Fuentes activas
├─ Suscriptores
└─ Score promedio

⚙️ CONFIGURACIÓN
├─ Hora digest        (a qué hora mandar resumen)
├─ Cantidad artículos (cuántos por digest)
├─ Score mínimo       (qué importancia mínima)
└─ API Keys           (OpenAI, NewsAPI, etc)
```

#### Qué hacer cada día:
```
1. Abre el panel
2. Mira noticias PENDIENTES
3. Lee cada una
4. Si es importante:  ✅ APROBAR
5. Si es spam:        ❌ RECHAZAR
6. Si no tiene IA:    🤖 RESUMIR
7. Listo, ¡a descansar!
```

---

## COMANDOS TELEGRAM (Admin)

**Para administrador solamente:**

```
/fetch             → Buscar noticias AHORA (no esperar 30 min)
/digest            → Enviar resumen AHORA (no esperar mañana)
/stats             → Ver estadísticas completas
/fuentes           → Ver/activar fuentes
/config            → Ver/cambiar configuración
/aprobar ID        → Aprobar noticia (ej: /aprobar 123)
/rechazar ID       → Rechazar noticia
```

---

## ESTRUCTURA DE CARPETAS (Resumen)

```
NewsLet Pro/
│
├── app/                    ← El programa
│   ├── main.py             (corazón)
│   ├── api/routers/        (formularios web)
│   ├── services/           (motor: busca, resume, envía)
│   └── static/             (panel web bonito)
│
├── .github/workflows/      ← Auto-actualizar
├── Dockerfile              ← Para la nube
├── requirements.txt        ← Qué instalar
├── fly.toml                ← Config cloud
└── .env.example            ← Variables secretas
```

---

## VARIABLES SECRETAS (QUÉ NECESITAS)

Copia `.env.example` → `.env` y llena:

```
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_CHAT_ID=987654321

# OpenAI (para resúmenes)
OPENAI_API_KEY=sk-...

# Groq (alternativa gratis)
GROQ_API_KEY=gsk_...

# NewsAPI (fuentes de noticias)
NEWSAPI_KEY=...

# Admin
ADMIN_PASSWORD=mipasswordsecreto123

# JWT (seguridad)
JWT_SECRET=miclavesecreta12345678...

# SERVICE_KEY (para GitHub Actions)
SERVICE_KEY=...

# Para la nube
WEBHOOK_BASE_URL=https://newslet-pro.fly.dev
```

**Dónde obtener:**
- 🤖 OpenAI: https://platform.openai.com/api-keys
- 🧠 Groq: https://console.groq.com
- 📰 NewsAPI: https://newsapi.org
- 📱 Telegram: @BotFather en Telegram

---

## RESOLVER PROBLEMAS

| Problema | Solución |
|----------|----------|
| **Bot no responde** | Abre http://localhost:8000 / Si carga = servidor ok |
| **Telegram caído** | Sistema sigue funcionando, envía cuando vuelva |
| **Fuente no trae noticias** | Click en 🟢/🔴 para activar/desactivar |
| **Costo OpenAI alto** | Cambiar a Groq (gratis, más lento) |
| **Panel lento** | Reducir número de artículos guardados |
| **No envía digest** | Ver en CONFIGURACIÓN la hora correcta |
| **No resume automático** | Resumir manualmente: [🤖 RESUMIR] botón |

---

## ESTADÍSTICAS RÁPIDAS

```
Artículos por mes:      500-1000
Duplicados eliminados:  30-40%
Tiempo lectura ahorrado: 3-5 min por noticia
Costo mensual:          $0-20 (mostly IA)
Uptime esperado:        99.9%
```

---

## ACCIONES RÁPIDAS (Botones principales)

### En panel:

```
[🔄 Buscar ahora]     → Fetch noticias INMEDIATAMENTE
[📬 Digest ahora]     → Enviar resumen AHORA
[📊 Estadísticas]     → Ver estado del sistema
[⚙️ Config]           → Cambiar parámetros
[💾 Backup]           → Descargar copia de seguridad
```

### En artículo:

```
[✅ Aprobar]          → Marcar como importante
[❌ Rechazar]         → No enviar
[🤖 Resumir]          → Generar resumen IA
[👁️ Leer]            → Ver artículo completo
```

---

## SEGURIDAD (No olvides)

```
✅ HACER:
├─ Cambiar ADMIN_PASSWORD regularmente
├─ Guardar .env en lugar seguro (no en GitHub)
├─ Hacer backup del sistema cada semana
└─ Actualizar API keys si es necesario

❌ NO HACER:
├─ Compartir .env file
├─ Poner contraseñas en código
├─ Usar mismo password en múltiples servicios
└─ Dejar credenciales en el servidor
```

---

## COSTOS MENSUALES

```
Hosting (Fly.io):        GRATIS ($0)
Base de datos (Supabase): GRATIS ($0)
IA (OpenAI):             ~$0.15-20 según uso
Email:                   GRATIS ($0)
API keys:                GRATIS-10 ($0-10)

TOTAL TÍPICO:            $5-25/mes
POR USUARIO (100 users): $0.05-0.25
```

---

## LINKS IMPORTANTES

```
📖 Documentación:
   - GUIA_COMPLETA_NO_TECNICA.md
   - DIAGRAMA_VISUAL.md
   - README.md

🚀 Producción:
   - https://newslet-pro.fly.dev

🤖 Bot Telegram:
   - @NewsLetProBot (si está publicado)

💬 Soporte:
   - GitHub Issues
   - Email: [contact]

📊 Dashboard:
   - https://fly.io (monitoreo)
   - https://github.com (código)
```

---

## QUICK START (30 minutos)

```
1. (5 min)  Clonar código: git clone ...
2. (5 min)  Instalar: pip install -r requirements.txt
3. (10 min) Configurar .env (copiar de .env.example)
4. (5 min)  Ejecutar: python -m uvicorn app.main:app --reload
5. (5 min)  Abrir: http://localhost:8000

✅ ¡Listo!
```

---

## MANTENIMIENTO SEMANAL (Checklist)

```
Lunes:
  □ ¿Panel carga rápido?
  □ ¿Bot responde?
  □ ¿Hay noticias nuevas?

Miércoles:
  □ Ver /stats en Telegram
  □ Desactivar fuentes muertas (🔴)
  □ Revisar logs

Viernes:
  □ Hacer backup: GET /backup
  □ Revisar costo OpenAI
  □ Actualizar lista de fuentes si es necesario
```

---

## MANTENIMIENTO MENSUAL

```
Primera semana:
  □ Security audit (cambiar passwords)
  □ Dependency updates (npm/pip)
  □ Logs review
  
Segunda semana:
  □ Performance analysis (speed, uptime)
  
Tercera semana:
  □ Backup verification (descargar, verificar)
  
Cuarta semana:
  □ Planning: nuevas features/fuentes
```

---

## MONETIZACIÓN (Si vendes como SaaS)

```
Tier GRATIS:         2 sources, 50 articles/mes
Tier PRO ($2/mes):   10 sources, unlimited articles
Tier EMPRESA:        Custom pricing + soporte 24/7

Proyección:
  100 users × $2/mes = $200/mes
  1000 users × $2/mes = $2000/mes (ingreso pasivo)

Costo:
  Hosting:      $50/mes
  IA:           $200/mes (scaling)
  Total:        $250/mes

Margen:  80% (muy rentable)
```

---

**¿Necesitas más ayuda?** Lee `GUIA_COMPLETA_NO_TECNICA.md` (completa) o `DIAGRAMA_VISUAL.md` (diagramas)

**Última actualización:** Abril 2026
**Versión:** NewsLet Pro 3.0
