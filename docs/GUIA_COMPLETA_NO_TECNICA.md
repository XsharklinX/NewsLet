# 📖 NewsLet Pro — Guía Completa para No Técnicos

**Escrito para:** Personas sin conocimiento de programación que compren, usen o mantengan este sistema.

**Objetivo:** Explicar qué es, cómo funciona, y para qué sirve cada archivo.

---

## 🎯 PARTE 1: QUÉ ES NEWSLET PRO (En palabras simples)

### La idea básica

Imagina que tienes 50 periódicos y revistas en tu escritorio. Todos los días quieres leer las noticias importantes, pero **no tienes tiempo**. NewsLet Pro hace lo siguiente:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. Lee automáticamente noticias de múltiples fuentes (periódicos,│
│     revistas online, blogs)                                      │
│                                                                 │
│  2. Elimina duplicados (misma noticia en varios periódicos)      │
│                                                                 │
│  3. Las ordena por importancia (usa inteligencia artificial)     │
│                                                                 │
│  4. Crea un resumen de cada una en español claro y corto        │
│                                                                 │
│  5. Te las envía por Telegram cuando están listas                │
│                                                                 │
│  6. También tiene un panel web donde puedes ver y aprobar/      │
│     rechazar noticias                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### ¿Quién lo usa?

- **Profesionales ocupados** (abogados, médicos, ejecutivos) que necesitan estar informados pero no tienen 3 horas/día
- **Empresas** que quieren monitorear noticias de su industria
- **Investigadores** que necesitan seguimiento de temas específicos
- **Productores de contenido** que necesitan ideas para artículos

---

## 🔄 PARTE 2: CÓMO FUNCIONA (El flujo paso a paso)

### El viaje de una noticia desde que nace hasta tu celular

```
PASO 1: BÚSQUEDA (Search)
├─ El sistema busca en 3 lugares automáticamente:
│  ├─ RSS Feeds (blogs, noticias online)
│  ├─ NewsAPI (base de datos de noticias)
│  └─ Sitios web (tecnología, finanzas, etc)
│
└─ Frecuencia: Cada 30 minutos
   (Como si alguien leyera 3 periódicos cada media hora)

                           ↓

PASO 2: VERIFICAR DUPLICADOS
├─ Si la misma noticia aparece en 2 fuentes:
│  ├─ El sistema la detecta
│  └─ Guarda solo 1 copia (sin spam)
│
└─ Tecnología: Compara URLs después de limpiarlas
   (Remueve cosas como "?utm_source=facebook" que son basura)

                           ↓

PASO 3: ENRIQUECIMIENTO (Agregar información)
├─ El sistema automáticamente:
│  ├─ Asigna un score de importancia (1-10)
│  ├─ Identifica el tema (política, tecnología, deportes, etc)
│  ├─ Analiza si es noticia positiva o negativa
│  └─ Guarda imágenes si las hay
│
└─ Tecnología: Usa Inteligencia Artificial (OpenAI o Groq)

                           ↓

PASO 4: RESUMEN AUTOMÁTICO
├─ La IA lee el artículo completo (500-1000 palabras)
│  ├─ Extrae los puntos clave
│  └─ Crea un resumen en español (50-100 palabras)
│
└─ Tiempo: 2-3 segundos por artículo
   (En comparación: un humano tarda 5 minutos)

                           ↓

PASO 5: APROBACIÓN
├─ El sistema:
│  ├─ Si score < 5: rechaza automáticamente (poco relevante)
│  ├─ Si score 5-8: envía a panel para revisión humana
│  └─ Si score > 8: aprueba automáticamente
│
├─ Aquí el administrador puede:
│  ├─ Ver la noticia completa
│  ├─ Aprobarla (enviar a usuarios)
│  ├─ Rechazarla (no enviar)
│  └─ Editarla (cambiar resumen)
│
└─ Interface: Panel web intuitivo (ver imágenes abajo)

                           ↓

PASO 6: ENVÍO
├─ La noticia aprobada se envía por:
│  ├─ Telegram Bot (mensaje directo)
│  └─ Opcionalmente: Email (resumen diario)
│
├─ Formato:
│  ├─ Título
│  ├─ Resumen (50-100 palabras)
│  ├─ Fuente
│  ├─ Tema
│  └─ Link al artículo original
│
└─ Timing: Inmediato o en digest diario (configurable)

                           ↓

PASO 7: USUARIO LEE Y REACCIONA
├─ El usuario (en Telegram o web) puede:
│  ├─ Leer el resumen
│  ├─ Clickear para leer artículo completo
│  └─ Reaccionar (guardar, compartir, etc)
│
└─ Feedback: El sistema aprende qué noticiass gustan
```

---

## 📁 PARTE 3: ESTRUCTURA DE ARCHIVOS (Qué es cada cosa)

### Los directorios principales

```
NewsLet Pro/
│
├── 📄 README.md
│   └─ "Hola, soy NewsLet Pro, esto es lo que hago"
│
├── 📄 INSTALL.md
│   └─ Instrucciones para instalar el programa
│
├── 📄 ANALISIS_PROFESIONAL.md
│   └─ Análisis para gente que quiera comprar/vender
│
├── 📄 PROXIMO_PASO.md
│   └─ Qué hacer después de tenerlo instalado
│
├── 📄 requirements.txt
│   └─ Lista de "ingredientes" que necesita el programa
│      (Como lista de compras para hacer una torta)
│
├── 🐳 Dockerfile
│   └─ "Receta" para empacar el programa en un contenedor
│      (Como un tupper hermético que funciona en cualquier lado)
│
├── 📋 fly.toml
│   └─ Configuración para cuando está en la nube
│
├── 📁 .env.example
│   └─ "Ejemplo" de qué información secreta necesitas
│      (Tokens, contraseñas, keys de API)
│
└── 📁 app/  ← AQUÍ ESTÁ TODO EL CÓDIGO
   │
   ├── 📄 main.py
   │   └─ El "corazón" del programa
   │      (Aquí se inicia todo y se coordinan los procesos)
   │
   ├── 📄 config.py
   │   └─ Configuración global (timezones, límites, etc)
   │      (Como los "settings" de un programa)
   │
   ├── 📄 database.py
   │   └─ Conexión a la base de datos
   │      (La "bodega" donde guarda información)
   │
   ├── 📁 api/
   │   │   └─ Todos los "endpoints" (formularios web que reciben datos)
   │   │
   │   ├── articles.py
   │   │   └─ "Endpoints" para leer/aprobar/rechazar noticias
   │   │      GET /articles → dame las noticias
   │   │      PATCH /articles/123 → cambiar estado de noticia
   │   │
   │   ├── sources.py
   │   │   └─ "Endpoints" para gestionar fuentes
   │   │      POST /sources → agregar una fuente nueva
   │   │      GET /sources → ver todas las fuentes
   │   │
   │   ├── operations.py
   │   │   └─ "Endpoints" para operaciones manuales
   │   │      POST /fetch/now → buscar noticias AHORA
   │   │      POST /digest/now → enviar resumen AHORA
   │   │
   │   ├── config.py
   │   │   └─ "Endpoints" para cambiar configuración
   │   │
   │   ├── auth.py
   │   │   └─ "Endpoints" de seguridad
   │   │      POST /login → acceso al panel
   │   │      POST /telegram/webhook → recibe mensajes de Telegram
   │   │
   │   └── analytics.py
   │       └─ "Endpoints" de estadísticas
   │          GET /stats → cuántas noticias, fuentes activas, etc
   │
   ├── 📁 services/  ← EL "MOTOR" DEL SISTEMA
   │   │
   │   ├── rss_fetcher.py
   │   │   └─ Busca noticias en blogs/sitios RSS
   │   │      (RSS = un formato estándar que usan muchos blogs)
   │   │
   │   ├── newsapi_fetcher.py
   │   │   └─ Busca noticias en NewsAPI (gigante base de datos)
   │   │
   │   ├── web_scraper.py
   │   │   └─ Lee noticias de sitios específicos
   │   │      (Si un sitio no tiene RSS, lo "raspa" directamente)
   │   │
   │   ├── deduplicator.py
   │   │   └─ "Elimina duplicados" inteligentemente
   │   │      (Detecta que BBC.com y El País hablan de la misma noticia)
   │   │
   │   ├── summarizer.py
   │   │   └─ Usa IA para resumir artículos
   │   │      (Conecta con OpenAI o Groq)
   │   │
   │   ├── enricher.py
   │   │   └─ Agrega información (score, categoría, sentimiento)
   │   │      (Usa IA)
   │   │
   │   ├── telegram_bot.py
   │   │   └─ El "cervecito" del bot en Telegram
   │   │      (Responde a comandos: /start, /noticias, /buscar, etc)
   │   │
   │   ├── telegram_notifier.py
   │   │   └─ Envía mensajes a usuarios por Telegram
   │   │
   │   ├── telegram_webhook.py
   │   │   └─ "Conexión" para que Telegram le avise cuando hay mensajes
   │   │
   │   ├── email_notifier.py
   │   │   └─ Envía emails con resúmenes diarios
   │   │
   │   ├── pdf_generator.py
   │   │   └─ Crea un PDF con las noticias (para imprimir)
   │   │
   │   ├── keyword_checker.py
   │   │   └─ Filtra noticias por palabras clave
   │   │      (Si el usuario dice "solo tecnología", filtra)
   │   │
   │   └── [otros servicios...]
   │
   ├── 📁 models/
   │   │   └─ "Moldes" para guardar información en la base de datos
   │   │      (Como plantillas de Excel)
   │   │
   │   ├── article.py
   │   │   └─ Estructura de: Artículo, Fuente, Resumen, Suscriptor
   │   │
   │   ├── digest_config.py
   │   │   └─ Configuración del resumen diario
   │   │      (a qué hora, cuántas noticias, etc)
   │   │
   │   ├── keyword.py
   │   │   └─ Palabras clave para filtrar noticias
   │   │
   │   └── [otros modelos...]
   │
   ├── 📁 static/
   │   │   └─ Los archivos del PANEL WEB
   │   │      (HTML, CSS, JavaScript)
   │   │
   │   ├── index.html
   │   │   └─ "Página principal" del panel
   │   │      (Lo que ves cuando abres http://localhost:8000)
   │   │
   │   ├── app.js
   │   │   └─ "Lógica" del panel en JavaScript
   │   │      (Qué pasa cuando clickeas un botón, etc)
   │   │
   │   └── style.css
   │       └─ "Estilos" (colores, tamaños, posición de cosas)
   │
   └── 📁 scheduler/
       └─ Tareas automáticas que se ejecutan periódicamente
       │
       └── jobs.py
           └─ Define:
              - Buscar noticias cada 30 min
              - Enviar resumen diario a las 8am
              - Revisar salud de fuentes
              - Hacer backups

└── 📁 .github/workflows/
    └─ Automatización en GitHub
    │
    ├── deploy.yml
    │   └─ "Receta" para publicar cambios automáticamente
    │      (Cuando haces push, GitHub automáticamente actualiza la nube)
    │
    └── scheduler.yml
        └─ "Receta" para ejecutar tareas en la nube
           (Buscar noticias cada 30 min, enviar digest cada mañana)
```

---

## 🎮 PARTE 4: CÓMO SE USA (El día a día)

### Para el administrador

```
FLUJO TÍPICO:

1. Abre http://localhost:8000 en el navegador
   ↓
2. Ve una tabla con noticias pendientes
   ↓
3. Lee cada una:
   - Si es importante: clickea ✅ APROBAR
   - Si es spam: clickea ❌ RECHAZAR
   - Si no tiene resumen: clickea 🤖 RESUMIR
   ↓
4. Las aprobadas se envían automáticamente a usuarios Telegram
   ↓
5. El resumen diario se envía todos los días a las 8am
   ↓
6. Las fuentes que fallan muchas veces se desactivan automáticamente
   (El sistema avisa en el panel)
```

### Para el usuario final (No necesita hacer nada)

```
OPCIÓN 1: Bot de Telegram (Lo más simple)
├─ Usuario: /start
├─ Bot: "¡Hola! Aquí recibirás noticias cada día"
├─ Automáticamente: Llegan noticias aprobadas por el admin
├─ Usuario puede: Buscar (/buscar economia), leer (/leer 123)
└─ Eso es todo

OPCIÓN 2: Web Panel (Si quiere más control)
├─ Usuario entra a http://newslet-pro.fly.dev
├─ Ve todas las noticias aprobadas
├─ Puede filtrar por tema
└─ Eso es todo
```

---

## ⚙️ PARTE 5: CÓMO FUNCIONA INTERNAMENTE (Explicado simple)

### Base de datos (La "bodega" de información)

Imagina 3 archivos Excel gigantes:

**Archivo 1: ARTICLES (Noticias)**
```
ID  │ Título                      │ Resumen        │ Estado    │ Score
──────────────────────────────────────────────────────────────────────
1   │ "Nueva ley de impuestos"   │ "El gobierno..." │ approved  │ 8
2   │ "Gato trepa a árbol"       │ "Un gato..."     │ rejected  │ 2
3   │ "Avance en tecnología IA"  │ "Los científicos"│ pending   │ 7
```

**Archivo 2: SOURCES (Fuentes)**
```
ID  │ Nombre      │ Tipo     │ URL                    │ Activa?
────────────────────────────────────────────────────────────
1   │ El País     │ RSS      │ elpais.com/rss        │ ✅
2   │ BBC Español │ RSS      │ bbc.com/mundo/rss     │ ✅
3   │ TechCrunch  │ NewsAPI  │ techcrunch.com        │ ❌ (caída)
```

**Archivo 3: SUMMARIES (Resúmenes)**
```
Article_ID │ Resumen_texto            │ Fecha creado
────────────────────────────────────────────
1          │ "El gobierno implementó..."│ 2026-04-15
2          │ "Un felino fue rescatado..." │ 2026-04-15
```

El programa lee estos archivos, los actualiza, y muestra en el panel web.

### Inteligencia Artificial (La "magia")

El sistema usa **dos inteligencias artificiales** que hacen trabajos específicos:

```
OPENAI (Modelo: GPT-4o-mini)
├─ Costo: $0.00015 por resumen
├─ Velocidad: 3 segundos
├─ Precisión: 95%
└─ Ideal para: Resúmenes de calidad, análisis de sentimiento

GROQ (Modelo: Llama 3.3)
├─ Costo: GRATIS
├─ Velocidad: 1 segundo (más rápido)
├─ Precisión: 90%
└─ Ideal para: Fallback si OpenAI está caída
   (Si OpenAI dice "no tengo cuota", usa Groq automáticamente)
```

Cada noticia se resume con IA en ~2 segundos. El AI:
1. Lee el artículo completo
2. Extrae puntos clave
3. Crea resumen de 50-100 palabras
4. Asigna score de relevancia (1-10)
5. Identifica tema (Tecnología, Política, Deportes, etc)
6. Analiza sentimiento (Positivo, Negativo, Neutral)

---

## 🌐 PARTE 6: DÓNDE ESTÁ ALOJADO (En la nube)

### ¿Dónde vive el programa?

```
Tu computadora (desarrollo)
   ↓
GitHub (repositorio del código)
   ↓
Fly.io (servidor en la nube, donde está "vivo")
   ↓
Usuarios acceden vía:
   - https://newslet-pro.fly.dev (web panel)
   - Telegram Bot (mensajes)
```

### ¿Qué cuesta?

```
Desarrollo local: GRATIS
   └─ Lo corres en tu PC

Hosting en Fly.io: GRATIS (free tier)
   ├─ 3 máquinas pequeñas
   └─ Perfect para 1-1000 usuarios

AI (resúmenes):
   ├─ OpenAI: $0.00015 por resumen
   │   └─ 100 artículos/mes = $1.50
   │   └─ 1000 artículos/mes = $15
   │
   └─ Groq: GRATIS
       └─ Fallback si OpenAI cae

Base de datos:
   ├─ SQLite (local): GRATIS
   └─ PostgreSQL (Supabase): GRATIS (free tier)

**Total costo mensual: $0-20 (mostly IA)**
```

---

## 🚨 PARTE 7: MANTENIMIENTO BÁSICO (Para no técnicos)

### Qué revisar cada semana

```
□ ¿El panel web carga rápido? (http://localhost:8000)
□ ¿Telegram bot responde? (/help en el bot)
□ ¿Hay noticias nuevas? (Ver en panel)
□ ¿Alguna fuente está caída? (/stats en Telegram)
```

### Qué revisar cada mes

```
□ ¿El almacenamiento no está lleno? (Si local)
□ ¿Las noticias siguen siendo relevantes?
□ ¿Hay sources que deberían ser actualizadas?
```

### Si algo se "rompe"

```
PROBLEMA: El bot no responde en Telegram
SOLUCIÓN: 
  1. Abre http://localhost:8000/api/v1/auth/status
  2. Si dice "ok", el servidor está vivo
  3. Si no, reinicia el programa

PROBLEMA: Las noticias no se envían
SOLUCIÓN:
  1. Busca las fuentes en el panel
  2. Si alguna tiene 🔴 rojo = está caída
  3. Haz click en reactivar

PROBLEMA: Costo de OpenAI muy alto
SOLUCIÓN:
  1. Cambiar a Groq (gratis pero más lento)
  2. Reducir número de artículos resumidos
  3. Resumir solo los artículos aprobados (no todos)
```

---

## ❓ PARTE 8: PREGUNTAS FRECUENTES

### ¿Puedo usarlo sin internet?
**No.** Necesita internet para:
- Buscar noticias online
- Enviar mensajes por Telegram
- Procesar con IA en la nube

### ¿Qué pasa si Telegram cae?
El sistema sigue funcionando pero no envía mensajes. Cuando Telegram vuelve, envía mensajes pendientes.

### ¿Puede robarse información?
**No es probable.** El sistema:
- Usa HTTPS (conexión encriptada)
- No almacena contraseñas (usa tokens)
- JWT = sistema de "credenciales temporales" seguro

### ¿Cuántas noticias puede guardar?
**Ilimitadas.** La base de datos puede guardar 1 millón de noticias sin problemas.

### ¿Qué pasa si hay 2 administradores?
Funcionan los dos. Si ambos aprueban la misma noticia, solo se envía 1 vez.

### ¿Puede customizarse?
**Sí, completamente.** El código está disponible. Puedes:
- Cambiar colores del panel
- Agregar nuevas fuentes (RSS, APIs)
- Cambiar mensaje de Telegram
- Agregar nuevos tipos de filtros

### ¿Es difícil de instalar?
**No si sigues las instrucciones.** Toma 30 minutos:
1. Descargar código
2. Instalar dependencias
3. Configurar .env (tokens)
4. Ejecutar

---

## 📚 PARTE 9: GLOSARIO (Palabras técnicas explicadas)

| Término | Significa | Ejemplo |
|---------|-----------|---------|
| **API** | "Interfaz" para que programas hablen entre sí | OpenAI API = forma de hablar con GPT |
| **RSS** | Formato para compartir noticias | elpais.com tiene un RSS feed |
| **Webhook** | "Puertal trasera" para que un servicio te avise | Telegram avisa al bot cuando hay mensaje |
| **Base de datos** | "Bodega digital" donde se guardan datos | SQLite guarda noticias, fuentes, etc |
| **JWT** | "Credencial temporal" para acceso seguro | Como un ticket de entrada que expira |
| **Endpoint** | "Puerta" en la web para pedir información | /articles = puerta para pedir noticias |
| **Deployment** | "Publicar" el programa en la nube | Fly.io es donde está "vivo" |
| **Deduplicación** | Eliminar copias | Detectar que BBC y El País hablan de lo mismo |
| **Scraping** | "Raspar" información de una página web | Leer un sitio que no tiene RSS |
| **Token** | "Contraseña temporal" para APIs | OpenAI token = acceso a GPT |

---

## 🎓 PARTE 10: RESUMEN VISUAL

```
┌────────────────────────────────────────────────────────────────┐
│                     NEWSLET PRO EN UN DIAGRAMA                │
└────────────────────────────────────────────────────────────────┘

    FUENTES DE NOTICIAS
    ├─ 🌐 RSS Feeds (50+ blogs)
    ├─ 📰 NewsAPI (10k noticias/día)
    └─ 🕷️ Web Scraping (sitios específicos)
           │
           ↓
    BÚSQUEDA (Cada 30 minutos)
    └─ "¿Hay noticias nuevas?"
           │
           ↓
    DEDUPLICACIÓN
    └─ "¿Estas 2 noticias son lo mismo?"
           │
           ↓
    ENRIQUECIMIENTO CON IA
    ├─ Score de relevancia (1-10)
    ├─ Categoría (Tech, Política, Deportes)
    └─ Sentimiento (Positivo/Negativo/Neutral)
           │
           ↓
    RESUMIDOR AUTOMÁTICO (OpenAI o Groq)
    └─ "Resumir en 50 palabras"
           │
           ↓
    FILTRO AUTOMÁTICO
    ├─ Si score < 5: ❌ Rechaza
    ├─ Si score 5-8: ⏳ Espera aprobación
    └─ Si score > 8: ✅ Aprueba
           │
           ↓
    ALMACENAMIENTO
    └─ Base de datos (Noticias, Fuentes, Resúmenes)
           │
           ↓
    ENVÍO A USUARIOS
    ├─ 📱 Telegram Bot (inmediato o digest)
    ├─ 📧 Email (resumen diario)
    └─ 🌐 Web Panel (lista completa)
           │
           ↓
    USUARIO RECIBE & LEE
    ├─ Noticia
    ├─ Resumen
    ├─ Fuente
    └─ Link a artículo original
```

---

## 🎯 CONCLUSIÓN

**En resumen, NewsLet Pro es:**

✅ Un programa que **automatiza la lectura de noticias**

✅ Usa **IA** para **entender y resumir**

✅ Envía solo las **importantes y relevantes**

✅ **Sin esfuerzo** del usuario

✅ Funciona **24/7** automáticamente

✅ Cuesta casi **nada**

✅ Fácil de **mantener y usar**

---

**¿Preguntas que no respondí? Abre un "Issue" en GitHub o contacta al desarrollador.**

---

*Documento creado para personas sin conocimiento técnico. Todos los términos complicados están explicados.*

*Última actualización: Abril 2026*
