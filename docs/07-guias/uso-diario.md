# Guía — Uso diario

Esta guía describe el flujo de trabajo típico de un editor usando NewsLet Pro.

---

## Flujo de un día normal

### Mañana — Revisar el digest automático

1. A las 08:00 (o la hora configurada), Telegram recibe el digest diario automático
2. Los artículos con mayor score ya están aprobados
3. Opcionalmente: abrir el panel web para revisar los artículos pendientes

### Durante el día — Revisar pendientes

1. Abrir el panel en `https://tu-dominio` (o desde la app instalada en el móvil)
2. Ir a **Artículos** → filtrar por estado **Pendiente**
3. Para cada artículo:
   - Leer el resumen generado por IA
   - Hacer clic en **Aprobar** o **Rechazar**
   - Opcionalmente: clic en **Enviar** para mandarlo a Telegram de inmediato

### Búsqueda de temas específicos

- Usar el campo de búsqueda en la vista de Artículos
- Filtrar por categoría o rango de fechas
- Para temas recurrentes: agregar una **Palabra clave** para recibir alertas automáticas

---

## Gestión de artículos

### Aprobar un artículo

Un artículo aprobado:
- Aparece en el próximo digest diario
- Puede enviarse manualmente a Telegram en cualquier momento
- Se mueve a la columna "Aprobado" en el Kanban

### Rechazar un artículo

Un artículo rechazado:
- No aparece en el digest
- Se elimina automáticamente tras 30 días
- No se puede enviar a Telegram

### Enviar un artículo ahora

Desde la tarjeta del artículo → botón **Enviar**:
- El artículo se envía al canal de Telegram inmediatamente
- Su estado cambia a "Enviado"
- No se incluirá en el próximo digest (ya fue enviado)

### Vista Kanban

La vista Kanban es ideal para sesiones de revisión masiva:
- Arrastra artículos de "Pendiente" a "Aprobado" o "Rechazado"
- Ver el flujo completo del contenido en un vistazo

---

## Palabras clave y alertas

Las palabras clave permiten recibir una alerta inmediata en Telegram cuando se detecta un artículo sobre un tema específico.

**Agregar una keyword:**
1. Ir a **Palabras clave** en el panel
2. Escribir la palabra o frase (ej: `terremoto`, `crisis económica`, `Apple`)
3. Clic en **Agregar**

**Cuándo se dispara la alerta:**
- El scheduler corre el fetch (cada 10 minutos)
- Se detecta que el título de un artículo nuevo contiene la keyword
- Llega un mensaje a Telegram: `🔔 Alerta: "Apple" — Título del artículo`

**Pausar una keyword:** si quieres dejar de recibir alertas temporalmente sin eliminarla, usa el botón de **Pausar**.

---

## Digest diario — Configuración

Para ajustar el digest desde el panel:

1. Ir a **Noticias diarias** en el sidebar
2. Configurar:
   - **Hora de envío:** de 0 a 23 (en la zona horaria configurada)
   - **Máx. artículos:** cuántos artículos incluir
   - **Score mínimo:** artículos con score menor se excluyen (0 = todos)
   - **Categorías:** dejar vacío para incluir todas, o escribir `Tecnología,Política`
3. Guardar — el cambio de hora se aplica inmediatamente al scheduler

Para enviar el digest ahora sin esperar: botón **Enviar ahora**.

---

## Actualizar noticias manualmente

El sistema actualiza automáticamente cada 10 minutos. Si necesitas las últimas noticias ahora:

1. En el panel → botón **Actualizar ahora** (en la barra superior)
2. O desde Telegram → enviar `/fetch` al bot

---

## Gestión de fuentes

**Agregar una fuente RSS:**
1. Ir a **Fuentes**
2. Clic en **Nueva fuente**
3. Rellenar: nombre, tipo (RSS), URL del feed
4. Guardar

**Importar múltiples fuentes:**
Si tienes un archivo OPML exportado de otro lector RSS:
1. Fuentes → **Importar OPML**
2. Seleccionar el archivo `.opml`
3. El sistema importa todas las fuentes automáticamente

**Fuente con fallos:**
Si una fuente aparece marcada en rojo con un contador de errores:
- La fuente falló N veces consecutivas (timeout, URL inválida, feed roto)
- Verifica la URL del feed manualmente en el navegador
- Si el feed está caído temporalmente: espera — se reactivará sola cuando vuelva a funcionar
- Si la URL cambió: editar la fuente con la nueva URL

---

## Estadísticas y análisis

**Ver tendencias recientes:**
1. Ir a **Estadísticas**
2. Ver la sección **Tendencias** — palabras más mencionadas en las últimas 24h
3. Útil para identificar temas en auge

**Mapa de actividad:**
El heatmap muestra a qué horas y días publican más las fuentes configuradas. Útil para saber cuándo revisar el panel.

**Rendimiento por fuente:**
La tabla de fuentes muestra cuáles aportan más artículos de calidad (score promedio, tasa de aprobación). Considera deshabilitar fuentes con score promedio muy bajo.

---

## Atajos de productividad

| Acción | Cómo |
|---|---|
| Aprobar todos los artículos de una sesión rápida | Usar la vista Kanban: arrastra en masa |
| Encontrar artículos sobre un tema | Búsqueda de texto en la vista Artículos |
| Ver solo lo importante | Filtrar por score ≥ 7 |
| Exportar para análisis externo | Artículos → Exportar CSV |
| Ver en móvil | Instalar como PWA desde el navegador |
| Recibir alertas urgentes | Configurar keywords relevantes |
