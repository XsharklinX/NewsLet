# Design Research: News Aggregation & Curation Platforms
**Date:** 2026-05-09 | **Platform:** NewsLet Pro (NewsBotPro)

---

## TL;DR

Las mejores plataformas de 2025-2026 se diferencian en tres ejes: **automatización inteligente** (reglas "si esto → entonces aquello"), **captura de conocimiento** (highlights, notas, anotaciones que persisten), y **estadísticas de lectura personales**. NewsLet ya tiene una base sólida; los próximos movimientos de mayor impacto son una **cola de lectura + modo focus**, un **motor de reglas de automatización**, y **deduplicación cruzada entre fuentes**.

---

## Estado actual de NewsLet Pro

NewsLet ya implementa:
- ✅ Dashboard con widgets, Kanban, vista lista/grid/compacto
- ✅ Resumenes con IA (Groq/OpenAI), enriquecimiento (categoría, sentimiento, score)
- ✅ Keywords de alerta, heatmap de actividad, trending topics
- ✅ Mapa de calor, tendencias, estadísticas por fuente
- ✅ Envío automático a Telegram, digest diario/semanal
- ✅ Etiquetas manuales, historial de búsqueda, catálogo de fuentes
- ✅ Vista previa de fuentes (Tier 1.1), deduplicación SHA-256
- ✅ Webhooks, RSS feed público, exportación CSV/MD/PDF
- ✅ Source health monitoring con fallos consecutivos

---

## Recomendaciones / Próximos pasos (priorizadas)

### 1. Cola de lectura + modo focus (Leer más tarde)
**Impacto: Alto | Esfuerzo: Medio**

Readwise Reader y Matter definen el estándar: artículos tienen tres estados — inbox, para_luego, archivado. El modo focus muestra solo el artículo, sin sidebar, con controles tipográficos (tamaño, fuente, espaciado).

```
┌─────────────────────────────────────────────────────┐
│  [← Volver]   Tecnología · ⭐ 8/10        [☰] [Aa] │
├─────────────────────────────────────────────────────┤
│                                                     │
│          TÍTULO DEL ARTÍCULO                        │
│          El País · hace 2h · 4 min lectura          │
│                                                     │
│  🎯 Punto clave: ...                                │
│  📌 Contexto: ...                                   │
│                                                     │
│  ─────────────────────────────────────────          │
│                                                     │
│  Texto completo con tipografía cómoda...            │
│  [seleccionar texto → highlights aparecen]          │
│                                                     │
│  ─────────────────────────────────────────          │
│  [✓ Aprobar] [✉ Enviar] [🔖 Guardar] [→ Siguiente] │
└─────────────────────────────────────────────────────┘
```

### 2. Motor de reglas de automatización
**Impacto: Alto | Esfuerzo: Alto**

Inoreader lidera esto. Las reglas son el principal motivo por el que los usuarios de poder pagan. Modelo simple: IF (condición) THEN (acción).

Condiciones disponibles:
- `keyword contiene X` / `score >= N` / `fuente es X` / `categoría es X` / `sentimiento es X`

Acciones disponibles:
- auto-aprobar / auto-rechazar / auto-enviar a Telegram / añadir etiqueta / notificar / webhook

```
┌─────────────────────────────────────────────┐
│  ✦ Nueva regla                              │
│                                             │
│  CUANDO  [score] [>=] [8]                   │
│  Y       [categoría] [es] [Tecnología]      │
│                                             │
│  ENTONCES  [✓] Auto-aprobar                 │
│            [✉] Enviar a Telegram            │
│            [🏷] Añadir etiqueta: "destacado" │
│                                             │
│  [Guardar regla]  [Probar con artículos]    │
└─────────────────────────────────────────────┘
```

### 3. Highlights y anotaciones en el reader
**Impacto: Medio-Alto | Esfuerzo: Medio**

Readwise Reader es el referente aquí. Al seleccionar texto en el reader modal, aparece un mini-toolbar con opciones de highlight y nota. Las anotaciones se guardan y se pueden exportar.

```
 "La inflación cayó un 2% en marzo..."
  ╔══════════════════════════════════╗
  ║  [🟡 Amarillo] [🔴 Rojo] [📝 Nota] ║
  ╚══════════════════════════════════╝
```

En el futuro: página de "Mis highlights" que agrupa todo lo subrayado, exportable a Notion/Obsidian.

### 4. Deduplicación y clustering visual cross-source
**Impacto: Medio-Alto | Esfuerzo: Medio**

Readwise Reader hace "cross-source article synthesis" — muestra cuando múltiples fuentes cubren el mismo evento. NewsLet ya tiene `cluster_id`, pero no hay UI visible.

```
┌──────────────────────────────────────────────┐
│  📰 El BCE sube tipos al 3.5%                │
│  ⭐ 9/10  · Economía  · 🔗 4 fuentes         │
│                                              │
│  También cubierto por:                       │
│  • El País  • Reuters ES  • Expansión  [+1] │
└──────────────────────────────────────────────┘
```

Esto da muchísimo contexto sin duplicar el contenido en la lista.

### 5. Estadísticas personales de lectura
**Impacto: Medio | Esfuerzo: Bajo**

Ningun competidor hace esto excepcionalmente bien, lo cual es una oportunidad. Los datos ya existen (readIds en localStorage, artículos enviados, scores).

```
┌──────────────────────────────────────────────────┐
│  📊 Tu actividad editorial esta semana           │
│                                                  │
│  Artículos leídos:     47    ████████░░  +12%   │
│  Aprobados:            23    ██████░░░░           │
│  Tiempo estimado:    1h 40m                      │
│  Categoría favorita: Tecnología (40%)            │
│  Mejor hora:         10:00 – 12:00               │
└──────────────────────────────────────────────────┘
```

### 6. Integraciones de salida adicionales (Slack, Discord, Notion)
**Impacto: Medio | Esfuerzo: Medio**

Feedly Pro conecta con Slack, MS Teams, Notion, Trello, HubSpot. NewsLet tiene Telegram + webhooks, pero una integración nativa de Slack (simple: POST a Slack Webhook) aumentaría mucho el valor para equipos pequeños.

```
Distribución del digest → [Telegram ✓] [Slack □] [Discord □] [Email ✓] [Webhook ✓]
```

### 7. Entrenamiento implícito del algoritmo de relevancia
**Impacto: Medio | Esfuerzo: Medio**

NewsBlur aprende de los likes/dislikes. Feedly Leo se entrena con los artículos que marcas como prioritarios. NewsLet ya tiene el campo `feedback` (+1/-1). El siguiente paso es usar eso para ajustar automáticamente el score de artículos similares o pesos por fuente.

### 8. Ingesta de newsletters por email
**Impacto: Bajo-Medio | Esfuerzo: Alto**

Feedbin y Inoreader dan una dirección de email única para suscribir newsletters. Muy potente pero requiere infraestructura de email (Mailgun, etc.). Dejarlo para más adelante.

---

## Patrones comunes en las mejores plataformas

| Patrón | Feedly | Inoreader | Readwise | NewsLet actual |
|--------|--------|-----------|----------|---------------|
| Cola de lectura (inbox/later/archive) | ✓ | ✓ | ✓ | Parcial (guardados) |
| Modo focus/lectura | ✓ | ✓ | ✓ | ✓ Reader modal |
| AI summaries | ✓ Pro | ✓ Pro | ✓ | ✓ Gratis |
| Reglas de automatización | Básico | ✓✓✓ | ✗ | Solo keywords |
| Highlights / anotaciones | ✗ | ✓ | ✓✓✓ | ✗ |
| Keyboard shortcuts | ✓ | ✓✓ | ✓✓ | ✓ |
| Filtros avanzados | ✓ | ✓✓✓ | ✓✓ | ✓✓ |
| Source health monitoring | ✗ | ✗ | ✗ | ✓✓ |
| Heatmap / analytics | ✗ | ✗ | ✗ | ✓ |
| Digest configurable | Básico | ✓ | ✓ | ✓✓ |
| Webhooks salida | ✗ | ✓ | ✗ | ✓ |
| Deduplicación | ✗ | Básico | ✓ | ✓ (sin UI) |
| Etiquetas manuales | ✓ | ✓✓ | ✓✓ | ✓ (Tier 1.4) |
| Multi-formato (YouTube, PDF) | ✗ | ✓ | ✓✓✓ | ✗ |

---

## Anti-patterns a evitar

1. **Demasiadas opciones visibles a la vez** — Inoreader sufre de esto. El panel de poder puede abrumar al usuario casual. NewsLet debe mantener la simplicidad como ventaja.

2. **Onboarding vacío sin guía** — El empty state de "Sin artículos" no debe ser solo texto. Debe ofrecer un CTA inmediato: "Probar fuentes populares →".

3. **AI como excusa de paywall** — Feedly pone casi todo lo útil en Pro+. NewsLet tiene AI gratis lo cual es una ventaja diferencial enorme. Mantenerlo.

4. **Diseño que envejece** — NewsBlur es el ejemplo de lo que pasa cuando no se actualiza el look & feel. El dark theme moderno de NewsLet es un activo.

5. **Sync solo en una dirección** — Las integraciones que solo exportan (sin feedback) tienen menos retención. Cuando se pueda, cerrar el loop (ej: si un artículo es aprobado en Notion → marcarlo como enviado en NewsLet).

---

## Ángulos únicos (oportunidades de diferenciación)

### "Source Intelligence Dashboard"
Ningún competidor muestra health scores, failure rates, rejection rates y average relevance en una sola vista de fuentes. NewsLet ya lo tiene parcialmente — ampliarlo con gráficas de evolución temporal sería genuinamente único.

### "Editorial workflow" como identidad
Feedly es para business intelligence, Inoreader es para power users individuales, Readwise es para lectores que quieren retener conocimiento. **NewsLet puede ser la herramienta editorial para equipos pequeños y creadores de newsletters** — ese nicho está poco servido.

### "Digest como producto"
El flujo Aprobar → Editar → Enviar (Telegram + Email + RSS) ya existe en NewsLet. Añadir un editor visual sencillo del digest (drag para reordenar artículos, añadir intro personalizada) lo haría genuinamente competitivo para newsletter creators.

```
┌─────────────────────────────────────────────────────┐
│  📧 Editor del Digest — Miércoles 8 mayo            │
│                                                     │
│  Introducción:  [Hoy en tecnología y economía...]   │
│                                                     │
│  ① ═══ El BCE sube tipos ══════════════════ [✕][↕] │
│  ② ═══ Apple lanza nuevo iPad ══════════════ [✕][↕] │
│  ③ ═══ Meta cierra acuerdo con... ══════════ [✕][↕] │
│                          [+ Añadir artículo]        │
│                                                     │
│  [Vista previa] [Enviar ahora] [Programar]          │
└─────────────────────────────────────────────────────┘
```

---

## Roadmap sugerido (Tier 2)

| Prioridad | Feature | Complejidad | Diferenciación |
|-----------|---------|-------------|---------------|
| 🔴 Alta | Cola de lectura (inbox/later) | Media | Media |
| 🔴 Alta | Motor de reglas (IF/THEN) | Alta | Muy alta |
| 🟡 Media | Highlights en reader | Media | Alta |
| 🟡 Media | Clustering UI (cross-source) | Baja | Alta |
| 🟡 Media | Stats personales de lectura | Baja | Media |
| 🟡 Media | Integración Slack/Discord | Media | Media |
| 🟢 Baja | Editor visual del digest | Alta | Muy alta |
| 🟢 Baja | Entrenamiento implícito IA | Alta | Alta |
| 🟢 Baja | Ingesta newsletters por email | Muy alta | Media |

---

## Fuentes

- [Best RSS Readers 2026 — Readless Blog](https://www.readless.app/blog/best-rss-readers-2026)
- [Inoreader 2025: Intelligence and Automation](https://www.inoreader.com/blog/2025/12/inoreader-2025-intelligence-and-automation-in-one-content-hub.html)
- [Feedly AI Features — Siteefy](https://siteefy.com/tools/feedly)
- [The 3 best RSS reader apps in 2026 — Zapier](https://zapier.com/blog/best-rss-feed-reader-apps/)
- [Readwise Reader — Official](https://readwise.io/read)
- [Feedly vs Inoreader vs NewsBlur 2026 — Readless](https://www.readless.app/blog/feedly-vs-inoreader-vs-newsblur-2026)
- [Dashboard Design Best Practices 2025 — 5of10](https://5of10.com/articles/dashboard-design-best-practices/)
- [Matter Reading App — Robert Breen](https://robertbreen.com/2025/02/27/elevate-your-online-reading-with-matter/)
- [Empty State UX — Eleken](https://www.eleken.co/blog-posts/empty-state-ux)
