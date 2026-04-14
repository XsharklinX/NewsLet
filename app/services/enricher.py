"""
AI enrichment: summary + category + score + sentiment in one call.
Includes few-shot calibration examples to prevent score compression.
"""
import json
import logging

from app.config import settings
from app.models.article import VALID_CATEGORIES

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = {"positive", "neutral", "negative"}

_PROMPT = f"""Eres un editor de noticias profesional latinoamericano. Analiza el artículo y responde SOLO con JSON válido.

CALIBRACIÓN DE SCORE (usa toda la escala):
- 1-2: Contenido trivial, entretenimiento menor, sin impacto real
- 3-4: Noticias locales de interés limitado, eventos rutinarios
- 5-6: Relevante para la región, impacto moderado en ciudadanos
- 7-8: Importante, afecta a muchas personas, requiere atención
- 9-10: URGENTE, crisis nacional/regional, impacto masivo inmediato

EJEMPLOS:
- "Celebridades se reúnen en evento de moda" → score: 2, sentiment: positive
- "Municipio aprueba nuevo reglamento de tránsito" → score: 4, sentiment: neutral
- "Banco central sube tasas de interés 0.5%" → score: 6, sentiment: neutral
- "Gobierno anuncia reforma fiscal que afecta salarios" → score: 8, sentiment: negative
- "Terremoto magnitude 7.2 sacude la capital, víctimas" → score: 10, sentiment: negative

Formato de respuesta:
{{
  "summary": "<resumen en español, 2-3 oraciones directas: quién, qué, cuándo, dónde, impacto>",
  "category": "<categoría>",
  "score": <entero 1-10>,
  "sentiment": "<positive|neutral|negative>"
}}

Categorías válidas: {", ".join(VALID_CATEGORIES)}

Responde SOLO el JSON. Sin texto antes ni después. Sin markdown."""


async def enrich_article(
    title: str, text: str
) -> tuple[str | None, str | None, int | None, str | None]:
    """Single AI call → (summary, category, score, sentiment). All can be None."""
    content = f"Título: {title}\n\nTexto: {text[:6000]}"

    try:
        if settings.ai_provider == "groq":
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.groq_api_key)
            resp = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _PROMPT},
                    {"role": "user",   "content": content},
                ],
                max_tokens=500,
                temperature=0.3,
            )
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": _PROMPT},
                    {"role": "user",   "content": content},
                ],
                max_tokens=500,
                temperature=0.3,
            )

        raw = resp.choices[0].message.content.strip()

        # Strip markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        summary   = (data.get("summary") or "").strip() or None
        category  = data.get("category")
        score     = data.get("score")
        sentiment = data.get("sentiment", "neutral")

        if category not in VALID_CATEGORIES:
            category = None
        try:
            score = int(score)
            if not 1 <= score <= 10:
                score = None
        except (TypeError, ValueError):
            score = None

        if sentiment not in VALID_SENTIMENTS:
            sentiment = "neutral"

        logger.debug(f"Enriched: cat={category} score={score} sentiment={sentiment}")
        return summary, category, score, sentiment

    except json.JSONDecodeError as e:
        logger.warning(f"enricher JSON parse error: {e}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"enricher AI call failed: {e}")
        return None, None, None, None
