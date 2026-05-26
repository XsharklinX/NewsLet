"""
IF/THEN automation rule engine.

Conditions evaluated against an Article object:
  keyword   — title or text contains keyword (case-insensitive)
  category  — article.category matches
  sentiment — article.sentiment matches
  score_min — article.relevance_score >= value
  score_max — article.relevance_score <= value
  source_id — article.source_id == value

Actions executed when ALL conditions match:
  approve      — set status = "approved"
  reject       — set status = "rejected"
  add_tag      — append tag to article.tags
  send_telegram — queue immediate Telegram send
  webhook      — POST JSON payload to URL
"""
import json
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.article import Article

logger = logging.getLogger(__name__)


def _match_condition(article: Article, cond: dict[str, Any]) -> bool:
    ctype = cond.get("type")
    value = cond.get("value", "")

    if ctype == "keyword":
        kw = str(value).lower()
        title = (article.title or "").lower()
        text = (article.original_text or "").lower()
        return kw in title or kw in text

    if ctype == "category":
        return (article.category or "").lower() == str(value).lower()

    if ctype == "sentiment":
        return (article.sentiment or "").lower() == str(value).lower()

    if ctype == "score_min":
        score = article.relevance_score
        return score is not None and score >= int(value)

    if ctype == "score_max":
        score = article.relevance_score
        return score is not None and score <= int(value)

    if ctype == "source_id":
        return article.source_id == int(value)

    return False


def _evaluate_rule(article: Article, rule_conditions: list[dict]) -> bool:
    """Return True if ALL conditions match (AND logic)."""
    if not rule_conditions:
        return False
    return all(_match_condition(article, c) for c in rule_conditions)


async def _execute_action(article: Article, action: dict[str, Any], db: Session) -> None:
    atype = action.get("type")

    if atype == "approve":
        if article.status == "pending":
            article.status = "approved"
            logger.info(f"Rule engine: approved article {article.id}")

    elif atype == "reject":
        if article.status == "pending":
            article.status = "rejected"
            logger.info(f"Rule engine: rejected article {article.id}")

    elif atype == "add_tag":
        tag = str(action.get("value", "")).strip().lower()
        if tag:
            existing = {t.strip() for t in (article.tags or "").split(",") if t.strip()}
            if tag not in existing:
                existing.add(tag)
                article.tags = ",".join(sorted(existing))
                logger.info(f"Rule engine: tagged article {article.id} with '{tag}'")

    elif atype == "send_telegram":
        try:
            from app.services.telegram_notifier import send_article
            await send_article(article, db)
            article.status = "sent"
            logger.info(f"Rule engine: sent article {article.id} to Telegram")
        except Exception as e:
            logger.error(f"Rule engine: Telegram send failed for {article.id}: {e}")

    elif atype == "webhook":
        url = str(action.get("value", "")).strip()
        if url:
            try:
                payload = {
                    "id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "category": article.category,
                    "score": article.relevance_score,
                    "sentiment": article.sentiment,
                    "status": article.status,
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(url, json=payload)
                logger.info(f"Rule engine: webhook fired for article {article.id} → {url}")
            except Exception as e:
                logger.error(f"Rule engine: webhook failed for {article.id}: {e}")


async def apply_rules_to_article(article: Article, db: Session) -> None:
    """
    Evaluate all active rules against a single article.
    Called right after a new article is persisted.
    """
    from app.models.rule import Rule

    rules = db.query(Rule).filter(Rule.is_active == True).order_by(Rule.priority).all()
    if not rules:
        return

    for rule in rules:
        try:
            conditions = json.loads(rule.conditions or "[]")
            actions = json.loads(rule.actions or "[]")
        except json.JSONDecodeError:
            logger.warning(f"Rule {rule.id} has invalid JSON, skipping")
            continue

        if _evaluate_rule(article, conditions):
            logger.info(f"Rule '{rule.name}' (id={rule.id}) matched article {article.id}")
            for action in actions:
                await _execute_action(article, action, db)

    db.commit()


async def apply_rules_to_pending(db: Session) -> int:
    """
    Apply rules to all pending articles in batch.
    Used by the scheduler or manual trigger endpoint.
    """
    from app.models.rule import Rule
    from app.models.article import Article

    rules = db.query(Rule).filter(Rule.is_active == True).order_by(Rule.priority).all()
    if not rules:
        return 0

    articles = db.query(Article).filter(Article.status == "pending").all()
    count = 0
    for article in articles:
        before = article.status
        for rule in rules:
            try:
                conditions = json.loads(rule.conditions or "[]")
                actions = json.loads(rule.actions or "[]")
            except json.JSONDecodeError:
                continue
            if _evaluate_rule(article, conditions):
                for action in actions:
                    await _execute_action(article, action, db)
        if article.status != before:
            count += 1

    db.commit()
    return count
