# 🗺️ ROADMAP — NewsLet Pro
## Qué mejorar, agregar, quitar y cómo

**Enfoque:** 100% realista. Solo lo que podemos hacer con nuestro stack actual.  
**Stack:** FastAPI · SQLAlchemy · SQLite/PostgreSQL · Telegram · Fly.io · GitHub Actions

---

## CÓMO LEER ESTE ROADMAP

```
⏱️ = Tiempo estimado de implementación
💥 = Impacto en el usuario final
🔧 = Dificultad técnica
✅ = Ya existe
🆕 = Nuevo
🔄 = Mejorar lo que hay
🗑️ = Eliminar
```

---

## FASE 0 — QUICK WINS (Esta semana · cada item 1-4 horas)

Cosas que se hacen rápido y mejoran mucho.

### 🗑️ ELIMINAR (Limpieza)

| Item | Por qué quitarlo |
|------|-----------------|
| `DOCUMENTACION_RESUMEN.txt` | Redundante, ya está en .md |
| Archivo `Analisis` (sin extensión) | Raro, meterlo bien en ANALISIS_PROFESIONAL.md |
| `app/services/article_scraper.py` y `web_scraper.py` | ¿Duplicado? Verificar y consolidar en uno |
| Imports sin usar en routers | Código muerto que confunde |
| Logs de debug en producción | Exposición de datos internos |

### 🔄 MEJORAR (Sin código nuevo)

**1. El `app.js` tiene 1476 líneas en un solo archivo**
```
PROBLEMA: Monstruo de archivo
SOLUCIÓN: Dividir en módulos:
  app/static/js/
  ├── api.js         (fetch, auth)
  ├── articles.js    (tabla, filtros)
  ├── reader.js      (modal lector)
  ├── charts.js      (analytics)
  ├── config.js      (panel settings)
  └── main.js        (init, navigation)

TIEMPO: 3-4 horas
IMPACTO: Mantenimiento 3x más fácil
```

**2. El `style.css` tiene 3737 líneas**
```
PROBLEMA: CSS difícil de mantener
SOLUCIÓN: Variables CSS + estructura:
  app/static/css/
  ├── variables.css   (colores, fuentes, spacing)
  ├── layout.css      (sidebar, grid)
  ├── components.css  (botones, badges, cards)
  ├── articles.css    (tabla, modal)
  └── mobile.css      (responsive)

TIEMPO: 2-3 horas
IMPACTO: Cambios de estilo en segundos
```

**3. Mensajes de error genéricos**
```python
# ACTUAL:
"Error al cargar" # ¿Qué falló? ¿Por qué?

# MEJOR:
"No hay noticias pendientes en este momento"
"Fuente BBC no responde (intento 3/5)"
"La IA está tardando más de lo habitual, reintentando..."
```

**4. Confimación antes de acciones destructivas**
```
ACTUAL: Click "rechazar" → borrado inmediato
MEJOR:  Click "rechazar" → modal confirmación → confirmar
```

**5. `.env.example` actualizado**
```
Agregar todas las variables nuevas:
SERVICE_KEY, WEBHOOK_BASE_URL, BACKUP_DIR
Con comentarios explicativos en cada una
```

---

## FASE 1 — PRIORIDAD ALTA (Semanas 1-3)

### 🆕 1.1 MODO LECTURA MEJORADO (2-3 días)
**Impacto: Alto · Dificultad: Baja**

El modal reader actual muestra texto plano. Mejorar:

```
AGREGAR:
├── Imagen de portada full-width
├── Tiempo estimado de lectura ("3 min")
├── Fuente original con favicon
├── Botón "Compartir" (copiar link)
├── Botón "Guardar para después"
├── Modo focus (sin distracciones)
├── Font size adjustable (A- A+)
├── Highlight de keywords automático
└── "Artículos relacionados" al final

QUITAR:
└── Scroll infinito en el modal (confuso)
```

### 🆕 1.2 SISTEMA DE NOTIFICACIONES EN TIEMPO REAL (2-3 días)
**Impacto: Alto · Dificultad: Media**

Ya tienen WebSocket. Usarlo mejor:

```
ACTUAL: WebSocket existe pero hace poco

AGREGAR:
├── Toast cuando llega noticia con score 9+
│   "⭐ Noticia importante: Tesla anuncia..."
├── Badge en el ícono del browser
├── Sonido opcional (configurable)
├── Notificación del browser (Push API)
└── Contador de pendientes en tiempo real

TÉCNICO:
El sw.js ya existe (Service Worker).
Solo falta conectar el WebSocket a Push Notifications.
```

### 🆕 1.3 BÚSQUEDA AVANZADA (2-3 días)
**Impacto: Alto · Dificultad: Baja**

```
ACTUAL: Búsqueda solo por texto del título

AGREGAR:
├── Filtro por fecha (desde/hasta)
├── Filtro por score (min 7, max 10)
├── Filtro por fuente (checkbox list)
├── Filtro por sentimiento
├── Filtro por categoría
├── Búsqueda en resumen y texto completo
├── Búsquedas guardadas (LocalStorage)
└── Historial de búsquedas recientes

QUITAR:
└── Dropdown de "Categoría" que no siempre funciona
```

### 🆕 1.4 DASHBOARD MEJORADO (3-4 días)
**Impacto: Alto · Dificultad: Media**

```
AGREGAR:
├── Widget "Score promedio hoy" (con tendencia ↑↓)
├── Widget "Noticias por hora" (bar chart)
├── Widget "Top 3 fuentes del día"
├── Widget "Keyword más activa"
├── Gráfico de sentimiento (pie chart)
├── Heatmap de actividad (como GitHub)
│   (qué días/horas hay más noticias)
├── "Noticias tendencia" (top score + populares)
└── Comparación semana actual vs anterior

QUITAR:
└── Stats estáticos sin contexto
```

### 🔄 1.5 PANEL DE FUENTES MEJORADO (2 días)
**Impacto: Medio · Dificultad: Baja**

```
AGREGAR:
├── Estadísticas por fuente:
│   · Artículos/semana
│   · Score promedio de sus artículos
│   · % de artículos aprobados
│   · Última noticia exitosa (timestamp)
├── Botón "Probar fuente" (fetch manual de 1 fuente)
├── Import/Export de fuentes (JSON)
├── Detección automática de RSS:
│   User pega URL del sitio → sistema detecta el RSS
└── Preview de artículo antes de activar fuente

QUITAR:
└── URL duplicadas sin validación
```

---

## FASE 2 — TELEGRAM BOT (Semana 3-4)

### 🔄 2.1 EXPERIENCIA DE USUARIO MEJORADA (3-4 días)
**Impacto: Muy Alto · Dificultad: Media**

```
AGREGAR:
├── Inline keyboard mejorado:
│   [📚 Leer más] [⭐ Guardar] [🔗 Fuente]
│
├── Paginación de noticias:
│   "1-5 de 23 noticias [◀ Anterior] [Siguiente ▶]"
│
├── Preferencias de usuario:
│   /preferencias → elige categorías que le interesan
│   (solo tecnología, solo política, etc)
│
├── Búsqueda inline:
│   El usuario escribe y bot responde en tiempo real
│   (Telegram inline mode "@NombreBot query")
│
├── Estadísticas personales:
│   /mistats → "Leiste 45 noticias este mes"
│
├── Comando /trending:
│   Top 5 noticias más leídas/vistas esta semana
│
└── /resumen → Digest manual (sin esperar las 8am)

QUITAR:
└── Respuestas con HTML largo que Telegram corta a la mitad
└── Mensajes de error en inglés mezclados con español
```

### 🆕 2.2 GRUPOS DE TELEGRAM (2 días)
**Impacto: Muy Alto · Dificultad: Baja**

```
PROBLEMA ACTUAL: Bot funciona en chats privados

AGREGAR:
├── Bot puede ser agregado a grupos
├── Admin de grupo: /configure (configurar bot)
├── Canal Telegram dedicado (no solo privado)
│   (Admin publica en canal automáticamente)
└── Comandos silenciosos en grupos (respuesta privada)
```

### 🆕 2.3 HORARIOS PERSONALIZADOS POR USUARIO (1 día)
**Impacto: Alto · Dificultad: Baja**

```
AGREGAR:
├── /horario → configura cuándo recibir noticias
│   "Quiero noticias a las 7am y 7pm"
├── Timezone por usuario
│   "Soy de México" → timezone automático
└── Pausar notificaciones:
    /pausar 2h → silencio por 2 horas
    /pausar hoy → silencio hasta mañana
```

---

## FASE 3 — AI IMPROVEMENTS (Semanas 4-5)

### 🔄 3.1 RESÚMENES MUCHO MEJORES (2-3 días)
**Impacto: Muy Alto · Dificultad: Media**

```
ACTUAL: Resumen genérico de 50 palabras

MEJORAR:
├── Resúmenes con estructura:
│   🔑 PUNTO CLAVE: [1 línea]
│   📋 CONTEXTO: [2-3 líneas]
│   💡 IMPACTO: [1-2 líneas]
│
├── Prompt mejorado con context:
│   "Eres un periodista experto. Resume para ejecutivos ocupados."
│
├── Detectar tipo de noticia:
│   · Breaking news → resumen urgente
│   · Feature story → análisis profundo
│   · Opinion → distinguir opinion de hecho
│
├── Citas importantes extraídas:
│   💬 "La inflación llegará al 3%" - Banco Central
│
└── TL;DR automático (1 oración):
    "Lo que necesitas saber: X anunció Y afectando Z"
```

### 🆕 3.2 CATEGORIZACIÓN INTELIGENTE (2 días)
**Impacto: Alto · Dificultad: Baja**

```
AGREGAR:
├── Subcategorías:
│   Tecnología → IA, Ciberseguridad, Startups, Gadgets
│   Economía → Mercados, Criptomonedas, Empresa, Personal
│
├── Tags automáticos:
│   Personas: "Elon Musk"
│   Empresas: "Tesla"
│   Lugares: "Argentina"
│   Eventos: "Copa del Mundo 2026"
│
├── Clustering de noticias relacionadas:
│   "3 artículos relacionados con este tema"
│
└── Trending topics:
    "Tecnología IA tendencia esta semana (+40%)"
```

### 🆕 3.3 RELEVANCIA PERSONALIZADA (3-4 días)
**Impacto: Muy Alto · Dificultad: Alta**

```
AGREGAR:
├── Aprendizaje de preferencias:
│   Cuando admin aprueba → +1 a ese tipo
│   Cuando admin rechaza → -1 a ese tipo
│
├── Score personalizado por usuario:
│   Score base (AI) × Factor usuario = Score final
│
├── Historial de engagement:
│   ¿Qué noticias leen hasta el final?
│   ¿En cuáles clickean "leer más"?
│
└── Recomendador:
    "Basado en lo que leíste, esto te puede interesar"
```

---

## FASE 4 — FEATURES NUEVOS (Semanas 5-7)

### 🆕 4.1 SISTEMA DE ALERTAS POR KEYWORDS (2 días)
**Impacto: Muy Alto · Dificultad: Baja**

```
MEJORAR EL ACTUAL:
├── Alertas por keyword en TIEMPO REAL (no cada 30 min)
├── Keywords con sinónimos:
│   "IA" también detecta "Inteligencia Artificial"
├── Keywords negativas:
│   "Tecnología" pero NO "Videojuegos"
├── Alertas por entidad:
│   "Cualquier noticia sobre Elon Musk"
├── Alertas por fuente específica:
│   "Solo noticias de Reuters sobre economía"
└── Email inmediato cuando hay keyword match
```

### 🆕 4.2 EXPORTACIÓN Y REPORTES (3 días)
**Impacto: Alto · Dificultad: Baja**

```
AGREGAR:
├── Exportar CSV (ya existe, mejorar)
├── PDF mejorado:
│   · Logo personalizable
│   · Header/footer con fecha
│   · Tabla de contenidos
│   · Imágenes de portada
│   · Gráficos de sentiment
│
├── Newsletter HTML:
│   Diseño profesional de email
│   (Como Substack o Morning Brew)
│   Enviable por email con layout bonito
│
├── Informe semanal automático:
│   · Los 10 temas más cubiertos
│   · Fuentes más activas
│   · Score promedio de la semana
│   · Comparación con semana anterior
│
└── OPML export/import
    (Para cambiar de aggregador sin perder fuentes)
```

### 🆕 4.3 PANEL MULTI-IDIOMA (2 días)
**Impacto: Alto · Dificultad: Baja**

```
AGREGAR:
├── Panel web en Español/Inglés/Portugués
├── Resúmenes en el idioma elegido por usuario
├── Detect language de artículo automáticamente
├── Traducir artículos bajo demanda
│   [🌐 Traducir al español]
└── RSS en múltiples idiomas con traducción
```

### 🆕 4.4 MODO OFFLINE / PWA COMPLETO (2 días)
**Impacto: Alto · Dificultad: Media**

```
ACTUAL: Hay manifest.json y sw.js, pero incompleto

COMPLETAR:
├── Service Worker cachea artículos
├── Panel funciona sin internet
│   (muestra últimas noticias guardadas)
├── Sincroniza cuando vuelve internet
├── Instalable en Android/iOS como app
├── Push notifications del browser
└── Modo oscuro completo (ya está a medias)
```

### 🆕 4.5 API PÚBLICA (3-4 días)
**Impacto: Muy Alto para vender · Dificultad: Media**

```
AGREGAR:
├── Versioning: /api/v2/
├── API keys para terceros
├── Endpoints públicos:
│   GET /api/v2/articles (paginated)
│   GET /api/v2/articles/{id}
│   GET /api/v2/sources
│   GET /api/v2/trending
│
├── Documentación automática (Swagger UI)
├── Rate limiting por API key
├── Webhooks outbound:
│   "Cuando hay noticia con score 9+, llama a este URL"
│
└── SDK básico (Python + JavaScript):
    news = NewsLetClient(api_key="xxx")
    articles = news.get_articles(score_min=8)
```

### 🆕 4.6 INTEGRACIÓN DISCORD/SLACK (3 días)
**Impacto: Alto · Dificultad: Media**

```
AGREGAR:
├── Discord bot (usando discord.py)
│   Mismo flow que Telegram pero Discord
│
├── Slack app
│   Slash commands: /noticias, /buscar
│   Notificaciones en canal
│
└── Email como canal alternativo:
    (ya existe aiosmtplib, solo falta UI para configurarlo)
```

---

## FASE 5 — OPERACIONAL (Semanas 7-8)

### 🆕 5.1 SISTEMA DE LOGS EN EL PANEL (1 día)
**Impacto: Alto · Dificultad: Baja**

```
AGREGAR:
├── Vista de logs en el panel web
│   (Sin tener que entrar a Fly.io)
│
├── Filtros:
│   · Solo errores
│   · Solo fetch events
│   · Solo Telegram
│
└── Download logs como archivo
```

### 🔄 5.2 HEALTH CHECK MEJORADO (1 día)
**Impacto: Alto · Dificultad: Baja**

```
ACTUAL: /api/v1/auth/status (solo dice OK)

MEJORAR:
├── /health → Estado completo:
│   {
│     "status": "healthy",
│     "database": "connected",
│     "telegram": "connected",
│     "openai": "ok (200ms)",
│     "last_fetch": "14 min ago",
│     "articles_today": 47,
│     "pending": 12
│   }
└── Dashboard widget de "Estado del Sistema"
    (Verde/Amarillo/Rojo visible en el panel)
```

### 🆕 5.3 BACKUP EN EL PANEL (1 día)
**Impacto: Medio · Dificultad: Baja**

```
AGREGAR:
├── Botón "Descargar backup" en el panel
├── Historial de backups (últimos 7 días)
├── Backup automático a Google Drive (opcional)
│   (Ya tienen autenticación Google disponible)
└── Restore desde backup en el panel
```

### 🆕 5.4 SISTEMA DE RATE LIMITING INTELIGENTE (1 día)
**Impacto: Medio · Dificultad: Baja**

```
ACTUAL: 60 req/min global

MEJORAR:
├── Por endpoint:
│   /fetch/now: 5 req/min (operación cara)
│   /articles: 100 req/min (lectura liviana)
│   /summarize: 10 req/min (llama a OpenAI)
│
└── Por tipo de usuario:
    Admin: sin límite (o mucho más alto)
    Público: 20 req/min
```

---

## FASE 6 — COSAS A ELIMINAR / SIMPLIFICAR 🗑️

```
ELIMINAR (reduce complejidad, no agrega valor):

├── alembic/ (carpeta de migraciones)
│   Uso: La hacemos manual (run_db_migrations en main.py)
│   Acción: Eliminar o usar uno solo, no ambos
│
├── app/services/topic_clusterer.py
│   Uso: ¿Se usa? ¿Funciona bien?
│   Acción: Si no tiene cobertura de tests → eliminar
│
├── app/services/notification_service.py
│   Uso: Overlap con telegram_notifier.py
│   Acción: Consolidar en uno
│
├── app/services/rss_generator.py
│   Uso: ¿Se usa? ¿Quién consume ese RSS?
│   Acción: Si no hay usuarios de esa feature → eliminar
│
├── app/models/notification.py y webhook.py
│   Uso: ¿Completamente implementados? ¿Se usan?
│   Acción: Verificar uso, eliminar si dead code
│
├── DOCUMENTACION_RESUMEN.txt
│   Uso: Redundante con .md files
│   Acción: Eliminar
│
└── Múltiples archivos .md en root
    Uso: Muchos archivos confunden
    Acción: Mover todo a docs/ folder
```

---

## RESUMEN VISUAL DEL ROADMAP

```
SEMANA 1:
  ├── QUITAR archivos redundantes
  ├── DIVIDIR app.js en módulos
  ├── Confirmaciones en acciones destructivas
  └── .env.example actualizado

SEMANA 2:
  ├── Modal lector mejorado (imagen, tiempo lectura)
  ├── Búsqueda avanzada (filtros múltiples)
  ├── Dashboard widgets nuevos
  └── Panel de fuentes mejorado

SEMANA 3:
  ├── Telegram: paginación + inline keyboard
  ├── Telegram: /trending + /resumen + /horario
  ├── Grupos de Telegram
  └── Resúmenes IA mejorados

SEMANA 4:
  ├── Categorización inteligente + tags
  ├── Sistema de alertas mejorado
  ├── Exportación: PDF mejorado + newsletter HTML
  └── Informe semanal automático

SEMANA 5:
  ├── PWA completo (offline + instalable)
  ├── Modo oscuro completo
  ├── Multi-idioma (ES/EN/PT)
  └── API pública v2 básica

SEMANA 6:
  ├── Discord/Slack integration
  ├── Webhook outbound
  ├── API keys para terceros
  └── Documentación API (Swagger mejorado)

SEMANA 7:
  ├── Logs en panel web
  ├── Health check mejorado
  ├── Backup en panel
  └── Rate limiting por endpoint

SEMANA 8:
  ├── Testing suite (cobertura 70%)
  ├── Security hardening
  ├── Load testing
  └── Release v4.0 🚀
```

---

## PRIORIDAD POR IMPACTO

### ⭐⭐⭐⭐⭐ MÁXIMA (Hacer primero)
1. **Limpiar código muerto** (1-2 días) · reduce confusión
2. **Modal lector mejorado** (2-3 días) · uso diario
3. **Telegram: paginación + botones** (3 días) · uso diario
4. **Resúmenes IA mejorados** (2-3 días) · valor principal
5. **Dashboard útil** (3-4 días) · admin usa siempre

### ⭐⭐⭐⭐ ALTA (Mes 2)
6. Búsqueda avanzada (filtros reales)
7. Grupos de Telegram
8. Alertas keyword en tiempo real
9. PWA completo (offline)
10. Newsletter HTML export

### ⭐⭐⭐ MEDIA (Mes 3)
11. API pública v2
12. Discord/Slack
13. Horarios personalizados
14. Logs en panel
15. Informe semanal automático

### ⭐⭐ BAJA (Si queda tiempo)
16. Multi-idioma
17. Relevancia personalizada (ML básico)
18. Google Drive backup
19. Restore desde backup

---

## LO QUE NO VALE LA PENA HACER AHORA

```
❌ Machine Learning complejo
   → Demasiado costo/tiempo. Groq/OpenAI ya hace el trabajo.

❌ App nativa iOS/Android
   → PWA es suficiente. Desarrollo nativo = 3-6 meses mínimo.

❌ Elasticsearch
   → SQLite/PostgreSQL con índices es suficiente para nuestro volumen.

❌ Microservicios
   → Somos un solo equipo. Monolito bien estructurado es mejor ahora.

❌ Kubernetes
   → Fly.io maneja el deployment. K8s es overkill.

❌ GraphQL API
   → REST es suficiente y más simple para nuestro caso de uso.

❌ Redis cluster (alta disponibilidad)
   → Redis single node es suficiente hasta 10k usuarios.

❌ Blockchain/Web3
   → No agrega valor real al problema que resolvemos.
```

---

## ESTIMADO TOTAL

| Fase | Semanas | Costo estimado | Impacto |
|------|---------|---------------|---------|
| Limpieza + Quick wins | 1 | $0 (propio) | +20% calidad |
| Lectores + Dashboard | 1.5 | $0 | +40% UX |
| Telegram mejorado | 1.5 | $0 | +50% engagement |
| AI improvements | 1.5 | $0-5/mes más | +60% valor |
| Features nuevos | 2 | $10/mes más | +80% valor |
| Operacional | 1 | $0 | +99% confiabilidad |
| Testing + Security | 2 | $0 | -80% bugs |

**Total: 10-12 semanas | Costo incremental: $15-20/mes**  
**Resultado: NewsLet Pro v4.0 — Producto Enterprise-grade**

---

## PRÓXIMO PASO INMEDIATO

Siendo realistas con el tiempo disponible:

```
ESTA SEMANA (sin excusas):
  □ Eliminar archivos redundantes y dead code
  □ Arreglar confirmaciones destructivas
  □ Mejorar mensajes de error
  □ Actualizar .env.example

PRÓXIMA SEMANA:
  □ Modal lector + imagen portada
  □ Dashboard con widgets reales
  □ Telegram: paginación de noticias

Resultado en 2 semanas: UX +40%, sin bugs nuevos.
```

---

*Roadmap creado: Abril 2026 · Revisión recomendada: Cada 6 semanas*
