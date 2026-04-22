"""
Summarization pipeline: scrape → AI enrich → auto-approve → high-score alert.
"""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article, Summary

logger = logging.getLogger(__name__)

HIGH_SCORE_THRESHOLD = 9  # Immediate Telegram alert if score >= this


async def summarize_article(article: Article, db: Session) -> Summary | None:
    """
    Full enrichment pipeline for a single article:
    1. Scrape full text (if enabled and not already scraped)
    2. Single AI call → summary + category + score + sentiment
    3. Auto-approve if score >= relevance_threshold
    4. Immediate Telegram alert if score >= HIGH_SCORE_THRESHOLD
    5. Persist all results

    Returns the Summary object or None on failure.
    """
    if article.summary:
        return article.summary

    # Step 1: Scrape full article text + thumbnail
    if settings.scrape_full_text and not article.full_text:
        try:
            from app.services.article_scraper import scrape_article
            full, thumbnail = await scrape_article(article.url)
            if full:
                article.full_text = full
                logger.debug(f"Scraped {len(full)} chars for article {article.id}")
            if thumbnail and not article.thumbnail_url:
                article.thumbnail_url = thumbnail
                logger.debug(f"Thumbnail extracted for article {article.id}: {thumbnail[:60]}")
            if full or thumbnail:
                db.flush()
        except Exception as e:
            logger.warning(f"Full-text scrape failed for article {article.id}: {e}")

    # Best available text for AI
    ai_text = article.full_text or article.original_text or article.title
    if len(ai_text.strip()) < 20:
        logger.warning(f"Article {article.id} has too little text, skipping")
        return None

    # Step 2: Single AI call (summary + structured fields + category + score + sentiment)
    summary_text, key_point, context_note, impact, category, score, sentiment = (
        None, None, None, None, None, None, None
    )
    if settings.enrich_articles:
        try:
            from app.services.enricher import enrich_article
            summary_text, key_point, context_note, impact, category, score, sentiment = (
                await enrich_article(article.title, ai_text)
            )
        except Exception as e:
            logger.error(f"Enrichment failed for article {article.id}: {e}")

    # Fallback: plain summary without enrichment
    if not summary_text:
        try:
            summary_text = await _plain_summary(article.title, ai_text)
        except Exception as e:
            logger.error(f"Plain summary also failed for article {article.id}: {e}")
            return None

    if not summary_text:
        return None

    # Step 3: Persist enrichment data
    if category:
        article.category = category
    if score is not None:
        article.relevance_score = score
    if sentiment:
        article.sentiment = sentiment

    # Step 4: Auto-approve by relevance threshold
    if score is not None and score >= settings.relevance_threshold:
        if article.status == "pending":
            article.status = "approved"
            logger.info(f"Auto-approved article {article.id} (score={score})")

    model_name = settings.groq_model if settings.ai_provider == "groq" else settings.openai_model
    summary = Summary(
        article_id=article.id,
        summary_text=summary_text,
        key_point=key_point,
        context_note=context_note,
        impact=impact,
        model_used=model_name,
        tokens_used=0,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    logger.info(
        f"Article {article.id} → score={score} cat={category} "
        f"sentiment={sentiment} status={article.status}"
    )

    # Step 5: Immediate high-score alert
    if score is not None and score >= HIGH_SCORE_THRESHOLD:
        try:
            db.refresh(article)
            from app.services.telegram_notifier import send_article
            await send_article(article, db)
            logger.info(f"High-score alert sent for article {article.id} (score={score})")

            # WS broadcast
            from app.api.websocket import manager
            await manager.broadcast("high_score_article", {
                "id": article.id,
                "title": article.title,
                "score": score,
            })
        except Exception as e:
            logger.warning(f"High-score alert failed: {e}")

    return summary


async def _plain_summary(title: str, text: str) -> str | None:
    """Fallback: plain summary without category/score."""
    prompt = (
        "Eres un editor de noticias. Resume en español en 2-3 oraciones concisas. "
        "Incluye: quién, qué, cuándo, dónde. Solo los hechos."
    )
    content = f"Título: {title}\n\nTexto: {text[:4000]}"
    try:
        if settings.ai_provider == "groq":
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.groq_api_key)
            resp = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": content},
                ],
                max_tokens=300, temperature=0.3,
            )
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": content},
                ],
                max_tokens=300, temperature=0.3,
            )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Plain summary AI error: {e}")
        return None


async def summarize_pending(db: Session, limit: int = 20) -> int:
    """Summarize up to `limit` articles without summaries. Returns count processed."""
    articles = (
        db.query(Article)
        .outerjoin(Summary)
        .filter(Summary.id == None)
        .order_by(Article.fetched_at.desc())
        .limit(limit)
        .all()
    )

    count = 0
    for article in articles:
        result = await summarize_article(article, db)
        if result:
            count += 1

    logger.info(f"Batch summarization: {count}/{len(articles)} processed")
    return count


async def reenrich_articles(db: Session, limit: int = 50) -> int:
    """Re-enrich articles that are missing sentiment or category. Returns count updated."""
    articles = (
        db.query(Article)
        .filter(
            (Article.sentiment == None) | (Article.category == None)
        )
        .order_by(Article.fetched_at.desc())
        .limit(limit)
        .all()
    )

    count = 0
    for article in articles:
        ai_text = article.full_text or article.original_text or article.title
        if len(ai_text.strip()) < 20:
            continue
        try:
            from app.services.enricher import enrich_article
            _, _, _, _, category, score, sentiment = await enrich_article(article.title, ai_text)

            updated = False
            if category and not article.category:
                article.category = category
                updated = True
            if score is not None and article.relevance_score is None:
                article.relevance_score = score
                # Auto-approve
                if score >= settings.relevance_threshold and article.status == "pending":
                    article.status = "approved"
                updated = True
            if sentiment and not article.sentiment:
                article.sentiment = sentiment
                updated = True

            if updated:
                db.commit()
                count += 1
        except Exception as e:
            logger.warning(f"Re-enrich failed for article {article.id}: {e}")

    logger.info(f"Re-enrichment: {count}/{len(articles)} articles updated")
    return count
