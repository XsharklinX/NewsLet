# Roadmap NewsLet Pro — Mejoras y fixes

> Generado el 2026-04-25 — basado en el estado actual del código y los problemas detectados durante la sesión.
> Versión actual: v3.0 → próxima: v3.1 (fixes y refinamiento) → v3.2 (calidad de vida) → v4.0 (cambios mayores).

---

## v3.1 — Fixes y deuda técnica (prioridad ALTA)

Cosas que **ya nos rompieron** o están a punto de hacerlo. Hacer primero.

### 🔴 1. Eliminar el sistema de cache-busting `?v=N` manual

**Problema:** cada vez que tocamos un JS, hay que actualizar `?v=N` en `index.html` Y en `sw.js`. Olvidar uno solo deja a los usuarios con código viejo.

**Solución:** generar el hash automáticamente en build/startup. Opciones:
- Endpoint `/api/v1/static-version` que devuelve un hash basado en `os.path.getmtime` de los archivos JS, y `index.html` lo lee al cargar
- O migrar a un Service Worker con estrategia **network-first** para los `.js` y mantener cache-first solo para CSS/imágenes

**Impacto:** elimina toda una clase de bugs ("a mí no me funciona, recargá con Ctrl+F5").

---

### 🔴 2. Bloque comentario JS frágil

**Problema:** los archivos en `js/` empiezan con `/* SECCION ════ */` pero si alguien edita y borra el `/*` por error, todo el módulo deja de cargar (ya pasó dos veces).

**Solución:** cambiar los headers de comentarios bloque a `// SECCION` simples (single-line). No se rompen al cortar/pegar.

**Esfuerzo:** 10 minutos. Sed por todos los archivos.

---

### 🔴 3. Service Worker no excluye `/login.html` de cache

**Problema:** si el usuario tiene token expirado, el SW puede servir `index.html` cacheado en vez de redirigir a login → confusión.

**Solución:** verificar que `/login.html` está en `STATIC_ASSETS` (sí lo está) pero asegurar que las llamadas a `/api/v1/auth/*` siempre van a la red (sí lo hacen). Falta: invalidar caché del HTML cuando el token expira.

---

### 🟡 4. Pérdida de DB en Koyeb free tier

**Problema:** Koyeb plan gratuito no tiene volúmenes persistentes. La DB se pierde al redesplegar.

**Solución actual:** backup diario por Telegram (ya está implementado).

**Mejora:** agregar comando `/restore` en el bot que reciba un archivo `.db` adjunto y lo restaure automáticamente al volver a desplegar. Hoy hay que hacerlo a mano por SSH/console.

---

### 🟡 5. Validación de startup falla silenciosamente

**Problema:** `startup_validator.py` corre al inicio pero los errores solo van al log. Si configuraste mal la API key, te enterás cuando el primer fetch falle 30 minutos después.

**Solución:** crear notificación in-app crítica al detectar config inválida + emitir un campo `health_warnings` en `/api/v1/health` que el dashboard muestre como banner rojo.

---

## v3.2 — Calidad de vida (prioridad MEDIA)

### 🟢 6. Modo oscuro / claro toggleable

**Problema:** el panel solo tiene tema oscuro fijo.

**Solución:** variables CSS con `data-theme="light|dark"` en `<html>`, toggle en el sidebar, persistido en `localStorage`. ~2h de trabajo.

---

### 🟢 7. Búsqueda en el bot de Telegram

**Estado actual:** `/buscar <término>` solo busca en títulos.

**Mejora:** buscar también en `summary_text` y `full_text` con `ILIKE`. Útil para encontrar noticias por palabras del cuerpo.

---

### 🟢 8. Filtro "no leídos" para artículos

**Problema:** no hay forma de saber qué artículos ya viste y cuáles no.

**Solución:** agregar columna `viewed_at` en `articles` (nullable). Marcar al abrir el lector. Agregar filtro "Solo no leídos" en la vista.

---

### 🟢 9. Bulk actions en la vista de artículos

**Problema:** aprobar 50 artículos = 50 clics individuales.

**Solución:** checkboxes en cada artículo + barra flotante "Aprobar seleccionados / Rechazar / Eliminar". Endpoint nuevo: `POST /api/v1/articles/bulk` con array de IDs y action.

---

### 🟢 10. Reintento manual de fuente caída

**Estado actual:** una fuente con 5 fallos consecutivos se desactiva automáticamente y queda esperando intervención manual.

**Mejora:** botón "Reactivar" que resetee `consecutive_failures` y `disabled_at`, y dispare un fetch inmediato de esa sola fuente para validar.

---

### 🟢 11. Dashboard: gráficas con rango configurable

**Estado actual:** "artículos por día" siempre muestra 30 días fijos.

**Mejora:** selector 7d / 30d / 90d / 12m. Mismo endpoint, solo cambia el query param `days`.

---

### 🟢 12. Exportar a Markdown (no solo CSV/PDF)

**Caso de uso:** redactor quiere copiar el digest a un editor Markdown (Notion, Obsidian, blog).

**Solución:** `GET /api/v1/digest/markdown` — formato plano, fácil de pegar.

---

## v3.3 — Performance y observabilidad (prioridad MEDIA)

### 🟡 13. Métrica de uso de IA por día

**Problema:** no sabemos cuántos tokens consumimos/día. Si nos pasamos del free tier de Groq, se rompe sin aviso.

**Solución:** agregar tabla `ai_usage_daily` (date, tokens, requests, errors). Endpoint `/api/v1/analytics/ai-usage`. Gráfica en estadísticas.

---

### 🟡 14. Cache de requests duplicadas

**Problema:** si dos fuentes apuntan al mismo dominio, hacemos dos requests HTTP idénticos.

**Solución:** cache HTTP de 5 minutos en `httpx` (vía `hishel` o cache simple en memoria con TTL).

---

### 🟢 15. Logs estructurados (JSON)

**Estado actual:** logs en formato texto, difíciles de parsear.

**Solución:** opción `LOG_FORMAT=json` que use `python-json-logger`. Útil si en algún momento agregamos Loki/Grafana.

---

### 🟢 16. Endpoint de métricas Prometheus

**Solución:** `GET /metrics` con métricas estándar (request count, latency, fetch_total, ai_tokens_total). Útil para integrar con Grafana sin escribir código.

---

## v4.0 — Mejoras mayores (prioridad BAJA, requieren rediseño)

### 🔵 17. Multi-tenancy

**Problema:** la app es single-user. Si querés que tu equipo tenga cuentas separadas, no se puede.

**Solución:** modelo `User`, columna `user_id` en `articles`, `sources`, `keywords`. JWT con `sub: user_id`. Roles: admin / editor / viewer.

**Esfuerzo:** ~1 semana. Migración no trivial.

---

### 🔵 18. Migrar frontend a Vue/Svelte

**Problema:** los 1646 líneas de JS vanilla empiezan a ser difíciles de mantener. Acoplamiento alto entre módulos por variables globales (`API`, `artView`).

**Solución:** Svelte (más cercano a vanilla, sin build complejo) o Vue 3 con `<script setup>`. Mantener "no build step" usando ESM via CDN si es posible.

**Riesgo:** romper la PWA. Hacer en branch aparte.

---

### 🔵 19. Soporte de idiomas en la UI

**Problema:** todo está en español hardcoded.

**Solución:** archivo `i18n/es.json`, `i18n/en.json`, función `t("key")` en JS. Selector de idioma en el sidebar.

---

### 🔵 20. Modo "agente IA" para responder preguntas

**Caso de uso:** "¿qué se dijo esta semana sobre el dólar?" → la IA responde con resumen de los artículos relevantes.

**Solución:** endpoint `/api/v1/ask` que tome la pregunta, busque artículos relevantes (vector search con embeddings), y pase a la IA como contexto.

**Costo:** requiere agregar pgvector o un índice vectorial (ChromaDB local). No trivial.

---

## Resumen ordenado por ROI (impacto / esfuerzo)

| # | Item | Impacto | Esfuerzo |
|---|---|---|---|
| 2 | Headers JS con `//` en vez de `/* */` | Alto | Mínimo |
| 6 | Modo claro/oscuro | Alto | Bajo |
| 9 | Bulk actions en artículos | Alto | Medio |
| 10 | Botón reactivar fuente | Medio | Bajo |
| 11 | Rango configurable en gráficas | Medio | Bajo |
| 8 | Filtro "no leídos" | Medio | Medio |
| 1 | Auto cache-busting | Alto | Medio |
| 5 | Banner de health warnings | Medio | Bajo |
| 13 | Métrica de uso IA | Alto | Medio |
| 4 | Restore por Telegram | Medio | Medio |
| 12 | Export Markdown | Bajo | Bajo |
| 7 | Búsqueda en cuerpo (bot) | Bajo | Mínimo |
| 14 | Cache HTTP | Medio | Medio |
| 15 | Logs JSON | Bajo | Bajo |
| 16 | Endpoint Prometheus | Bajo | Bajo |
| 3 | SW + login | Bajo | Bajo |
| 17 | Multi-tenancy | Alto | Muy alto |
| 18 | Frontend framework | Medio | Muy alto |
| 19 | i18n | Medio | Alto |
| 20 | Agente IA | Alto | Muy alto |

---

## Recomendación de orden de ejecución

**Sprint 1 (1-2 días):** items 2, 6, 10, 11, 12, 7 — quick wins de alto valor.
**Sprint 2 (3-4 días):** items 1, 5, 9, 13 — fixes estructurales de la UX y observabilidad.
**Sprint 3 (1 semana):** items 8, 4, 14 — funcionalidad nueva concreta.
**Backlog:** items 17-20 — esperar feedback real antes de invertir tanto trabajo.
