# Servicios — Pipeline de IA

El enriquecimiento con IA es el proceso central que convierte artículos crudos en contenido listo para publicar.

---

## Summarizer (`services/summarizer.py`)

### Función principal: `summarize_pending(db, limit=20)`

Busca artículos sin resumen con `status = "pending"` y los procesa con IA.

### Proveedor de IA

Configurado con `AI_PROVIDER` en `.env`:

| Proveedor | Variable | Modelo por defecto | Costo |
|---|---|---|---|
| **Groq** | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | Gratis (con límites) |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` | ~$0.0001 por artículo |

### Proceso de enriquecimiento por artículo

1. **Preparar contexto:** usa `full_text` si está disponible; si no, usa `original_text`
2. **Llamada a la API de IA** con el prompt de enriquecimiento
3. **Parsear respuesta JSON** con los campos estructurados
4. **Guardar en `summaries`:** resumen, punto clave, contexto, impacto
5. **Actualizar `articles`:** category, relevance_score, sentiment
6. **Auto-aprobación:** si `relevance_score >= RELEVANCE_THRESHOLD`, cambia status a `approved`

### Prompt de enriquecimiento

El prompt instruye al modelo a responder en JSON con esta estructura:

```json
{
  "summary": "Resumen en 2-3 oraciones concisas en español",
  "key_point": "El hecho central de la noticia en una oración",
  "context_note": "Antecedente o contexto relevante",
  "impact": "Consecuencia potencial o relevancia",
  "category": "Política|Economía|Tecnología|Deportes|Internacional|Entretenimiento|Salud|Ciencia",
  "relevance_score": 7,
  "sentiment": "positive|neutral|negative"
}
```

### Score de relevancia (1-10)

El modelo asigna un score según:
- **1-3:** Noticia menor, local, sin impacto amplio
- **4-6:** Noticia de interés moderado
- **7-8:** Noticia importante con impacto significativo
- **9-10:** Noticia de impacto mayor, urgente o viral

### Auto-aprobación

Cuando `ENRICH_ARTICLES=true` y el artículo recibe un score ≥ `RELEVANCE_THRESHOLD` (por defecto: 5), su estado cambia automáticamente a `approved`, sin intervención del editor.

Esto permite que las noticias más relevantes lleguen al digest sin revisión manual.

### Manejo de errores

- Si la IA falla, se incrementa `enrich_attempts` en el artículo
- Los artículos con 3+ intentos fallidos se marcan para no reintentar
- Si la respuesta JSON está malformada, se guarda el texto crudo como resumen

---

## Keyword Checker (`services/keyword_checker.py`)

Analiza los artículos nuevos en busca de palabras clave configuradas.

### Función: `run_keyword_checks(articles, db)`

Para cada artículo nuevo:
1. Normaliza el título (minúsculas, sin acentos)
2. Verifica si alguna keyword activa aparece en el título
3. Si hay coincidencia → envía alerta inmediata a Telegram con el título y enlace
4. Dispara webhooks con evento `keyword`

Las alertas de keywords llegan **fuera del digest** — son mensajes individuales inmediatos.

---

## Topic Clusterer (`services/topic_clusterer.py`)

Agrupa artículos sobre el mismo tema.

### Función: `cluster_articles(db)`

1. Obtiene artículos recientes sin cluster asignado
2. Calcula similaridad entre títulos (TF-IDF o similitud simple)
3. Asigna un `cluster_id` a artículos que hablan del mismo tema
4. Los artículos con `is_recurring=true` son temas que aparecen repetidamente

El clustering se ejecuta automáticamente cada 2 horas.  
En el panel, los artículos del mismo cluster se pueden identificar visualmente.

---

## Flujo completo post-fetch

```
Artículo nuevo (status: pending)
    │
    ├─ ¿Tiene keywords? → Alerta inmediata a Telegram
    │
    ▼
Summarizer
    │
    ├─ Texto completo disponible? → usar full_text
    │                              → si no: usar original_text
    │
    ▼
API de IA (Groq / OpenAI)
    │
    ▼
Guardar en DB:
    ├─ summaries: summary_text, key_point, context_note, impact
    └─ articles:  category, relevance_score, sentiment
    │
    ▼
Score >= umbral?
    ├─ Sí → status = "approved"
    └─ No → status = "pending" (queda para revisión manual)
```
