# Panel web — Vistas

El panel web es una SPA (Single Page Application) construida en HTML + JavaScript vanilla, sin bundler ni framework. Toda la lógica está modularizada en archivos JS que se cargan en orden específico.

---

## Arquitectura del frontend

```
index.html          — SPA principal, contiene toda la estructura HTML
app.js              — Variables globales, helpers, estado de la app (carga PRIMERO)
js/api.js           — Cliente HTTP (función api()), cliente WebSocket
js/ui.js            — Navegación, sidebar, toasts, lector de artículo
js/articles.js      — Vista de artículos (lista + filtros + búsqueda)
js/kanban.js        — Vista Kanban (drag & drop entre columnas)
js/sources.js       — Gestión de fuentes RSS/NewsAPI/Scraper
js/charts.js        — Gráficas con Chart.js (estadísticas)
js/config.js        — Configuración del sistema, keywords, digest, webhooks
js/health.js        — Logs del sistema y estado de salud
```

**Orden de carga crítico:** `app.js` debe cargarse antes que cualquier módulo porque define variables globales (`API`, `artView`, etc.) que los IIFEs de los módulos usan al inicializarse.

---

## Vistas del sidebar

### Inicio (Dashboard)

**Archivo:** `js/charts.js` + partes de `app.js`

Muestra en tiempo real:
- **Tarjetas de resumen:** total artículos, pendientes, aprobados, enviados hoy
- **Últimas noticias:** lista de artículos recientes con título, score y estado
- **Gráfica de artículos por día:** barras de los últimos 30 días
- **Distribución por categoría:** gráfica de dona
- **Distribución por sentimiento:** gráfica de dona

Se actualiza automáticamente:
- Al recibir el evento `fetch_complete` por WebSocket
- Cada 10 minutos (timer cliente)

---

### Artículos

**Archivo:** `js/articles.js`

Vista principal de gestión de artículos. Incluye:

**Filtros:**
- Por estado: Todos / Pendiente / Aprobado / Rechazado / Enviado
- Por fuente (select)
- Por categoría (select)
- Por sentimiento
- Score mínimo
- Rango de fechas
- Búsqueda por texto libre

**Vistas de lista:** 3 modos alternables
- **Lista** — Una fila por artículo, compacta
- **Cuadrícula** — Cards con thumbnail si está disponible
- **Compacta** — Máxima densidad, solo título y acciones

**Acciones por artículo:**
- Aprobar / Rechazar
- Leer el artículo completo (modal con resumen IA)
- Enviar a Telegram
- Ver artículo original (nueva pestaña)
- Like / Dislike
- Eliminar

**Búsquedas guardadas:** el usuario puede guardar filtros frecuentes con un nombre y recuperarlos en un clic.

**Exportar CSV:** descarga un CSV con todos los artículos filtrados.

---

### Kanban

**Archivo:** `js/kanban.js`

Vista de flujo editorial con columnas:
- **Pendiente** — artículos por revisar
- **Aprobado** — artículos aprobados, listos para el digest
- **Enviado** — artículos ya enviados a Telegram

Los artículos se mueven entre columnas con drag & drop o con los botones de cada tarjeta.

---

### Estadísticas

**Archivo:** `js/charts.js`

Sección dedicada a análisis y gráficas avanzadas:
- **Artículos por día** (barras, últimos 30 días)
- **Distribución por categoría** (dona)
- **Distribución por sentimiento** (dona)
- **Histograma de scores** (barras, 1-10)
- **Mapa de actividad** (heatmap día × hora)
- **Rendimiento por fuente** (tabla)
- **Tendencias** — las palabras más mencionadas en las últimas 24h (configurable)

---

### Fuentes

**Archivo:** `js/sources.js`

Gestión de fuentes de noticias:
- Lista de fuentes con estado de salud (failures, última actualización)
- Agregar fuente RSS / NewsAPI / Scraper
- Importar fuentes desde archivo OPML
- Activar / desactivar fuentes
- Ver estadísticas por fuente
- Eliminar fuentes

Fuentes con fallos consecutivos se muestran con indicador visual de alerta.

---

### Noticias diarias (Digest)

**Archivo:** `js/config.js`

Configuración del digest diario:
- Hora de envío (0-23)
- Número máximo de artículos
- Score mínimo
- Categorías a incluir
- Activar / desactivar

También incluye botones para:
- Enviar digest ahora
- Enviar email de prueba
- Descargar digest en PDF

---

### Palabras clave

**Archivo:** `js/config.js`

Gestión de keywords para alertas:
- Lista de keywords activas/pausadas
- Agregar nueva keyword
- Activar / pausar / eliminar

---

### Integraciones (Webhooks)

**Archivo:** `js/config.js`

Gestión de webhooks externos:
- Lista de webhooks con URL, eventos y último disparo
- Agregar webhook (nombre, URL, eventos, secreto opcional)
- Activar / desactivar / eliminar

---

### Registros (Logs)

**Archivo:** `js/health.js`

Visor de logs del sistema en tiempo real:
- Últimas N líneas del archivo de log
- Filtro por nivel (INFO, WARNING, ERROR)
- Botón de actualizar
- Estado del sistema (DB, scheduler, versión)

---

### Configuración

**Archivo:** `js/config.js`

Panel de administración del sistema:
- Edición de todas las variables de entorno (.env) desde el panel
- Campos sensibles (claves API, contraseñas) nunca se pre-rellenan
- Aviso de "reinicio necesario" para cambios que lo requieran

---

## Comunicación en tiempo real (WebSocket)

El panel mantiene una conexión WebSocket permanente con `/ws`.

**Eventos que recibe:**
| Evento | Acción en el panel |
|---|---|
| `fetch_complete` | Actualiza contadores y lista de artículos |
| `keyword_alert` | Muestra toast de alerta |
| `ping` | Mantiene viva la conexión |

El cliente reconecta automáticamente si la conexión se pierde (con backoff exponencial).

---

## Sistema de toasts

Los toasts son notificaciones visuales temporales que aparecen en la esquina inferior derecha.

```javascript
toast("Artículo aprobado", "ok");    // Verde
toast("Error al guardar", "err");    // Rojo
toast("Procesando...", "info");      // Azul
```

---

## Modo de vistas (List / Grid / Compact)

El estado de la vista (`artView`) se guarda en `localStorage` y persiste entre sesiones. Se puede cambiar con los botones de toggle en la barra de herramientas de artículos.
