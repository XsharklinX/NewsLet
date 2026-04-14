"""
Telegram Bot — admin commands + public subscriber system.

Admin users (defined by TELEGRAM_CHAT_ID + TELEGRAM_ADMIN_IDS) have access
to ALL commands.  Public users can only use the read-only / subscription
commands listed in PUBLIC_COMMANDS.
"""
import asyncio
import json
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import Article, DigestConfig, Keyword, Source, Summary
from app.models.article import Subscriber
from app.services.telegram_notifier import _esc, _tg, send_message

logger = logging.getLogger(__name__)
_offset = 0

# ── Command sets ──────────────────────────────────────────────────────────
# Public users can use these commands (read-only, no moderation power)
PUBLIC_COMMANDS = {"/start", "/help", "/noticias", "/buscar",
                   "/leer", "/suscribir", "/cancelar"}

ADMIN_HELP = """<b>NewsLet Pro — Admin</b>

<b>📰 Noticias</b>
/noticias — Últimas noticias (con botones de acción)
/buscar &lt;término&gt; — Buscar artículos
/leer &lt;id&gt; — Leer artículo completo
/aprobar &lt;id&gt; — Aprobar artículo
/rechazar &lt;id&gt; — Rechazar artículo

<b>⚙️ Operaciones</b>
/fetch — Buscar y resumir noticias ahora
/digest — Enviar digest ahora
/stats — Estadísticas + salud de fuentes

<b>🔧 Configuración</b>
/fuentes — Activar/desactivar fuentes
/config — Ver configuración
/config hora=8 cantidad=10 score=5 — Cambiar"""

PUBLIC_HELP = """<b>NewsLet Pro</b> — Noticias curadas en español

/noticias — Últimas noticias
/buscar &lt;término&gt; — Buscar por tema
/leer &lt;id&gt; — Leer artículo completo
/suscribir — Recibir digest diario
/cancelar — Cancelar suscripción"""


# ── Permission helpers ─────────────────────────────────────────────────────

def is_admin(chat_id: str) -> bool:
    return chat_id in settings.get_admin_ids()


async def _deny(chat_id: str):
    await send_message(
        chat_id,
        "⛔ Este comando es solo para administradores.\n"
        "Usa /help para ver los comandos disponibles."
    )


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def cmd_start(chat_id: str, is_adm: bool):
    await send_message(chat_id, ADMIN_HELP if is_adm else PUBLIC_HELP)


async def cmd_suscribir(chat_id: str, msg: dict):
    """Register a public user as a subscriber."""
    db = SessionLocal()
    try:
        from_user = msg.get("from", {})
        existing = db.query(Subscriber).filter_by(chat_id=chat_id).first()
        if existing:
            if existing.is_active:
                await send_message(chat_id, "✅ Ya estás suscrito al digest diario de noticias.")
            else:
                existing.is_active = True
                existing.last_seen_at = datetime.utcnow()
                db.commit()
                await send_message(
                    chat_id,
                    "✅ ¡Suscripción reactivada! Vas a recibir el digest de noticias todos los días."
                )
        else:
            sub = Subscriber(
                chat_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
            )
            db.add(sub)
            db.commit()
            await send_message(
                chat_id,
                "🎉 <b>¡Suscripción activada!</b>\n\n"
                "A partir de ahora vas a recibir el digest diario de noticias curadas.\n\n"
                "Usa /cancelar para darte de baja cuando quieras."
            )
    finally:
        db.close()


async def cmd_cancelar(chat_id: str):
    db = SessionLocal()
    try:
        sub = db.query(Subscriber).filter_by(chat_id=chat_id).first()
        if not sub or not sub.is_active:
            await send_message(chat_id, "ℹ️ No tenés una suscripción activa.")
        else:
            sub.is_active = False
            db.commit()
            await send_message(
                chat_id,
                "👋 Suscripción cancelada. Ya no vas a recibir el digest.\n"
                "Podés volver cuando quieras con /suscribir."
            )
    finally:
        db.close()


async def cmd_misuscripcion(chat_id: str):
    db = SessionLocal()
    try:
        sub = db.query(Subscriber).filter_by(chat_id=chat_id).first()
        if not sub:
            await send_message(
                chat_id,
                "❌ No estás suscrito.\nUsa /suscribir para recibir el digest diario."
            )
        elif sub.is_active:
            await send_message(
                chat_id,
                f"✅ <b>Suscripción activa</b>\n"
                f"Suscripto desde: {sub.subscribed_at.strftime('%d/%m/%Y')}\n\n"
                "Usa /cancelar para darte de baja."
            )
        else:
            await send_message(
                chat_id,
                "⏸ Tu suscripción está pausada.\nUsa /suscribir para reactivarla."
            )
    finally:
        db.close()


async def cmd_noticias_public(chat_id: str):
    """Public version — shows only 'sent' articles."""
    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary), joinedload(Article.source))
            .filter(Article.status == "sent")
            .order_by(Article.fetched_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            await send_message(chat_id, "Todavía no hay noticias publicadas. ¡Volvé más tarde!")
            return

        for a in articles:
            summary = a.summary.summary_text if a.summary else a.original_text or ""
            if len(summary) > 200:
                summary = summary[:200] + "…"
            source_name = a.source.name if a.source else ""
            cat = f" · {a.category}" if a.category else ""
            text = (
                f"<b>{_esc(a.title)}</b>\n\n"
                f"{_esc(summary)}\n\n"
                f"📌 {_esc(source_name)}{cat}\n"
                f'<a href="{a.url}">Leer completo</a> · /leer {a.id}'
            )
            await send_message(chat_id, text)
            await asyncio.sleep(0.4)
    finally:
        db.close()


async def cmd_buscar_public(chat_id: str, term: str):
    """Public version — searches only sent articles."""
    if not term:
        await send_message(chat_id, "Uso: /buscar <i>termino</i>\nEjemplo: <code>/buscar economia</code>")
        return

    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary), joinedload(Article.source))
            .filter(Article.title.ilike(f"%{term}%"), Article.status == "sent")
            .order_by(Article.fetched_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            await send_message(chat_id, f"Sin resultados publicados para: <i>{_esc(term)}</i>")
            return

        lines = [f"<b>Resultados: «{_esc(term)}»</b>\n"]
        for i, a in enumerate(articles, 1):
            src = a.source.name if a.source else ""
            summary = (a.summary.summary_text[:100] + "…") if a.summary else ""
            lines.append(f"<b>{i}. {_esc(a.title)}</b>")
            lines.append(f"   <i>{_esc(src)}</i>")
            if summary:
                lines.append(f"   {_esc(summary)}")
            lines.append(f'   <a href="{a.url}">Leer</a> · /leer {a.id}\n')
        await send_message(chat_id, "\n".join(lines))
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def cmd_stats(chat_id: str):
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total    = db.query(Article).count()
        pending  = db.query(Article).filter(Article.status == "pending").count()
        approved = db.query(Article).filter(Article.status == "approved").count()
        sent     = db.query(Article).filter(Article.status == "sent").count()
        no_sum   = db.query(Article).outerjoin(Summary).filter(Summary.id == None).count()
        subs     = db.query(Subscriber).filter(Subscriber.is_active == True).count()
        avg_score = db.query(func.avg(Article.relevance_score)).filter(
            Article.relevance_score != None
        ).scalar()

        # Source health summary
        all_sources = db.query(Source).all()
        ok_srcs  = sum(1 for s in all_sources if s.is_active and not (s.consecutive_failures or 0))
        bad_srcs = sum(1 for s in all_sources if s.is_active and (s.consecutive_failures or 0) > 0)
        off_srcs = sum(1 for s in all_sources if not s.is_active)

        text = (
            "<b>Estado del sistema</b>\n\n"
            f"📰 Total artículos: <b>{total}</b>\n"
            f"⏳ Pendientes: <b>{pending}</b>  ✅ Aprobados: <b>{approved}</b>  📤 Enviados: <b>{sent}</b>\n"
            f"🤖 Sin resumen: <b>{no_sum}</b>  ⭐ Score prom: <b>{round(float(avg_score), 1) if avg_score else 'N/A'}</b>\n\n"
            f"📡 Fuentes: 🟢 {ok_srcs} ok  ⚠️ {bad_srcs} con errores  🔴 {off_srcs} desactivadas\n"
            f"👥 Suscriptores activos: <b>{subs}</b>"
        )
        await send_message(chat_id, text)
    finally:
        db.close()


async def cmd_suscriptores(chat_id: str):
    """Admin: list subscriber count and recent subscribers."""
    db = SessionLocal()
    try:
        total  = db.query(Subscriber).count()
        active = db.query(Subscriber).filter(Subscriber.is_active == True).count()
        recent = (
            db.query(Subscriber)
            .filter(Subscriber.is_active == True)
            .order_by(Subscriber.subscribed_at.desc())
            .limit(10)
            .all()
        )
        lines = [
            f"<b>Suscriptores</b>",
            f"Total: <b>{total}</b> · Activos: <b>{active}</b>\n",
        ]
        for s in recent:
            name = s.first_name or s.username or s.chat_id
            date = s.subscribed_at.strftime("%d/%m/%Y")
            lines.append(f"• {_esc(name)} — {date}")
        await send_message(chat_id, "\n".join(lines))
    finally:
        db.close()


async def cmd_noticias_admin(chat_id: str):
    """Admin version — shows all recent articles with action buttons."""
    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary), joinedload(Article.source))
            .order_by(Article.fetched_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            await send_message(chat_id, "No hay artículos. Usa /fetch para buscar.")
            return

        for a in articles:
            summary = a.summary.summary_text if a.summary else "Sin resumen"
            source_name = a.source.name if a.source else "?"
            cat   = f" · {_esc(a.category)}" if a.category else ""
            score = f" · ⭐{a.relevance_score}/10" if a.relevance_score else ""
            text = (
                f"<b>{_esc(a.title)}</b>\n\n"
                f"{_esc(summary)}\n\n"
                f"📌 {_esc(source_name)}{cat}{score}\n"
                f'<a href="{a.url}">Leer</a> · ID: {a.id}'
            )
            buttons = []
            row = []
            if not a.summary:
                row.append({"text": "🤖 Resumir", "callback_data": json.dumps({"a": "summarize", "id": a.id})})
            if a.status != "approved":
                row.append({"text": "✅ Aprobar", "callback_data": json.dumps({"a": "approve", "id": a.id})})
            if a.status != "rejected":
                row.append({"text": "❌ Rechazar", "callback_data": json.dumps({"a": "reject", "id": a.id})})
            if row:
                buttons.append(row)
            if a.summary and a.status != "sent":
                buttons.append([{"text": "📤 Enviar", "callback_data": json.dumps({"a": "send", "id": a.id})}])

            await send_message(chat_id, text, reply_markup={"inline_keyboard": buttons} if buttons else None)
            await asyncio.sleep(0.4)
    finally:
        db.close()


async def cmd_buscar_admin(chat_id: str, term: str):
    if not term:
        await send_message(chat_id, "Uso: /buscar <i>termino</i>")
        return
    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary), joinedload(Article.source))
            .filter(Article.title.ilike(f"%{term}%"))
            .order_by(Article.fetched_at.desc())
            .limit(5)
            .all()
        )
        if not articles:
            await send_message(chat_id, f"Sin resultados para: <i>{_esc(term)}</i>")
            return

        lines = [f"<b>Resultados: «{_esc(term)}»</b>\n"]
        for i, a in enumerate(articles, 1):
            src     = a.source.name if a.source else "?"
            summary = (a.summary.summary_text[:120] + "…") if a.summary else ""
            cat     = f" · {a.category}" if a.category else ""
            score   = f" · ⭐{a.relevance_score}" if a.relevance_score else ""
            lines.append(f"<b>{i}. {_esc(a.title)}</b>")
            lines.append(f"   <i>{_esc(src)}{cat}{score}</i>")
            if summary:
                lines.append(f"   {_esc(summary)}")
            lines.append(f'   <a href="{a.url}">Leer</a> · /leer {a.id}\n')
        await send_message(chat_id, "\n".join(lines))
    finally:
        db.close()


async def cmd_leer(chat_id: str, article_id_str: str, is_adm: bool):
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/leer {id}</code>")
        return

    db = SessionLocal()
    try:
        q = db.query(Article).options(joinedload(Article.summary))
        if not is_adm:
            q = q.filter(Article.status == "sent")  # public can only read published
        article = q.filter(Article.id == article_id).first()

        if not article:
            await send_message(chat_id, f"Artículo #{article_id} no encontrado.")
            return

        full = (
            article.full_text
            or (article.summary.summary_text if article.summary else None)
            or article.original_text
            or ""
        )
        if not full:
            await send_message(chat_id, "Este artículo no tiene texto disponible.")
            return

        CHUNK = 3500
        chunks = [full[i:i+CHUNK] for i in range(0, len(full), CHUNK)]
        for idx, chunk in enumerate(chunks):
            header = f"<b>{_esc(article.title[:80])}</b>"
            if len(chunks) > 1:
                header += f" ({idx+1}/{len(chunks)})"
            page_text = f"{header}\n\n{_esc(chunk)}"
            if idx == len(chunks) - 1:
                page_text += f'\n\n<a href="{article.url}">Fuente original</a>'
            await send_message(chat_id, page_text)
            await asyncio.sleep(0.5)
    finally:
        db.close()


async def cmd_score(chat_id: str, article_id_str: str):
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/score {id}</code>")
        return

    db = SessionLocal()
    try:
        article = db.query(Article).options(
            joinedload(Article.summary), joinedload(Article.source)
        ).get(article_id)
        if not article:
            await send_message(chat_id, f"Artículo #{article_id} no encontrado.")
            return

        filled = round(article.relevance_score / 10 * 10) if article.relevance_score else 0
        score_bar = "█" * filled + "░" * (10 - filled)
        sentiment_icon = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(
            article.sentiment or "neutral", "😐"
        )
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌", "sent": "📤"}.get(
            article.status, "❓"
        )
        src     = article.source.name if article.source else "?"
        preview = f"\n\n<i>{_esc(article.summary.summary_text[:300])}</i>" if article.summary else ""

        text = (
            f"<b>#{article_id} · {_esc(article.title[:80])}</b>\n\n"
            f"⭐ Score: <b>{article.relevance_score}/10</b>  {score_bar}\n"
            f"🏷 Categoría: <b>{_esc(article.category or 'N/A')}</b>\n"
            f"{sentiment_icon} Sentimiento: <b>{article.sentiment or 'N/A'}</b>\n"
            f"{status_icon} Estado: <b>{article.status}</b>\n"
            f"📡 Fuente: <b>{_esc(src)}</b>"
            f"{preview}\n\n"
            f'<a href="{article.url}">Leer original</a>'
        )
        buttons = []
        if article.status == "pending":
            buttons.append([
                {"text": "✅ Aprobar", "callback_data": json.dumps({"a": "approve", "id": article.id})},
                {"text": "❌ Rechazar", "callback_data": json.dumps({"a": "reject", "id": article.id})},
            ])
        if not article.summary:
            buttons.append([{"text": "🤖 Resumir", "callback_data": json.dumps({"a": "summarize", "id": article.id})}])
        await send_message(chat_id, text, reply_markup={"inline_keyboard": buttons} if buttons else None)
    finally:
        db.close()


async def cmd_aprobar(chat_id: str, article_id_str: str):
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/aprobar {id}</code>")
        return
    db = SessionLocal()
    try:
        article = db.query(Article).get(article_id)
        if not article:
            await send_message(chat_id, f"Artículo #{article_id} no encontrado.")
            return
        if article.status == "approved":
            await send_message(chat_id, f"ℹ️ El artículo #{article_id} ya está aprobado.")
            return
        article.status = "approved"
        db.commit()
        await send_message(chat_id, f"✅ Aprobado: <b>{_esc(article.title[:80])}</b>")
    finally:
        db.close()


async def cmd_rechazar(chat_id: str, article_id_str: str):
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/rechazar {id}</code>")
        return
    db = SessionLocal()
    try:
        article = db.query(Article).get(article_id)
        if not article:
            await send_message(chat_id, f"Artículo #{article_id} no encontrado.")
            return
        if article.status == "rejected":
            await send_message(chat_id, f"ℹ️ El artículo #{article_id} ya está rechazado.")
            return
        article.status = "rejected"
        db.commit()
        await send_message(chat_id, f"❌ Rechazado: <b>{_esc(article.title[:80])}</b>")
    finally:
        db.close()


async def cmd_fetch(chat_id: str):
    await send_message(chat_id, "🔄 Buscando y procesando noticias...")
    db = SessionLocal()
    try:
        from app.services.rss_fetcher import fetch_all_rss
        from app.services.newsapi_fetcher import fetch_all_newsapi
        from app.services.web_scraper import fetch_all_scrapers
        rss, newsapi, scraped = await asyncio.gather(
            fetch_all_rss(db), fetch_all_newsapi(db), fetch_all_scrapers(db),
            return_exceptions=True,
        )
        rss     = rss     if isinstance(rss,     int) else 0
        newsapi = newsapi if isinstance(newsapi, int) else 0
        scraped = scraped if isinstance(scraped, int) else 0
        total_new = rss + newsapi + scraped

        # Auto-summarize pending after fetch
        from app.services.summarizer import summarize_pending
        summarized = await summarize_pending(db, limit=15)

        await send_message(chat_id,
            f"✅ <b>{total_new}</b> noticias nuevas · <b>{summarized}</b> resumidas\n"
            f"RSS: {rss} · API: {newsapi} · Scraper: {scraped}"
        )
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_digest(chat_id: str):
    db = SessionLocal()
    try:
        from app.services.telegram_notifier import send_digest
        cfg   = db.query(DigestConfig).first()
        count = cfg.count if cfg else 10
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary))
            .filter(Article.status.in_(["approved", "pending"]))
            .order_by(Article.fetched_at.desc())
            .limit(count)
            .all()
        )
        await send_digest(articles)
        await send_message(chat_id, f"📬 Digest enviado: {len(articles)} artículos")
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_pdf(chat_id: str):
    await send_message(chat_id, "📄 Generando PDF...")
    db = SessionLocal()
    try:
        cfg   = db.query(DigestConfig).first()
        count = cfg.count if cfg else 10
        articles = (
            db.query(Article)
            .options(joinedload(Article.summary), joinedload(Article.source))
            .filter(Article.status.in_(["approved", "pending", "sent"]))
            .order_by(Article.fetched_at.desc())
            .limit(count)
            .all()
        )
        from app.services.pdf_generator import generate_digest_pdf
        pdf_bytes = generate_digest_pdf(articles)
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendDocument"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                data={"chat_id": chat_id, "caption": f"📰 Digest — {len(articles)} artículos"},
                files={"document": ("newslet_digest.pdf", pdf_bytes, "application/pdf")},
            )
        if not resp.json().get("ok"):
            await send_message(chat_id, f"❌ Error: {resp.json().get('description')}")
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_fuentes(chat_id: str):
    db = SessionLocal()
    try:
        sources = db.query(Source).order_by(Source.name).all()
        if not sources:
            await send_message(chat_id, "No hay fuentes configuradas.")
            return
        buttons = []
        for s in sources:
            count = db.query(Article).filter(Article.source_id == s.id).count()
            icon  = "🟢" if s.is_active else "🔴"
            buttons.append([{
                "text": f"{icon} {s.name} ({count}) [{s.source_type}]",
                "callback_data": json.dumps({"a": "toggle_src", "id": s.id}),
            }])
        buttons.append([{"text": "🔄 Actualizar", "callback_data": json.dumps({"a": "refresh_fuentes"})}])
        await send_message(
            chat_id, "<b>Fuentes de noticias</b>\nToca para activar/desactivar:",
            reply_markup={"inline_keyboard": buttons},
        )
    finally:
        db.close()


async def cmd_keywords(chat_id: str):
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).order_by(Keyword.keyword).all()
        if not keywords:
            await send_message(chat_id, "<b>Keywords</b>\n\nNo hay keywords.\nAgregalas desde el panel web.")
            return
        buttons = []
        for kw in keywords:
            icon = "🟢" if kw.is_active else "🔴"
            buttons.append([{
                "text": f"{icon} {kw.keyword}",
                "callback_data": json.dumps({"a": "toggle_kw", "id": kw.id}),
            }])
        active = sum(1 for kw in keywords if kw.is_active)
        await send_message(
            chat_id,
            f"<b>Keywords de alerta</b>\n{active}/{len(keywords)} activas:",
            reply_markup={"inline_keyboard": buttons},
        )
    finally:
        db.close()


async def cmd_config(chat_id: str, args: str):
    db = SessionLocal()
    try:
        cfg = db.query(DigestConfig).first()
        if not cfg:
            cfg = DigestConfig()
            db.add(cfg)
            db.commit()

        if args.strip():
            changed = []
            for part in args.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    k = k.strip().lower()
                    if k in ("hora", "hour") and v.isdigit():
                        cfg.hour = min(23, max(0, int(v)))
                        changed.append(f"hora={cfg.hour}")
                    elif k in ("cantidad", "count") and v.isdigit():
                        cfg.count = min(50, max(1, int(v)))
                        changed.append(f"cantidad={cfg.count}")
                    elif k in ("score", "min_score") and v.isdigit():
                        cfg.min_score = min(10, max(0, int(v)))
                        changed.append(f"score_min={cfg.min_score}")
            if changed:
                cfg.updated_at = datetime.utcnow()
                db.commit()
                from app.scheduler.jobs import reschedule_digest
                reschedule_digest(cfg.hour)
                await send_message(chat_id, f"✅ Configuración: {', '.join(changed)}")
                return

        cats = cfg.categories or "Todas"
        await send_message(chat_id,
            "<b>Configuración del Digest</b>\n\n"
            f"🕐 Hora: <b>{cfg.hour:02d}:00</b>\n"
            f"📰 Artículos: <b>{cfg.count}</b>\n"
            f"⭐ Score mínimo: <b>{cfg.min_score}/10</b>\n"
            f"🏷 Categorías: <b>{_esc(cats)}</b>\n\n"
            "<i>/config hora=8 cantidad=10 score=5</i>"
        )
    finally:
        db.close()


async def cmd_salud(chat_id: str):
    db = SessionLocal()
    try:
        sources = db.query(Source).order_by(Source.consecutive_failures.desc()).all()
        if not sources:
            await send_message(chat_id, "No hay fuentes.")
            return

        lines    = ["<b>Salud de las Fuentes</b>\n"]
        disabled = [s for s in sources if not s.is_active]
        warning  = [s for s in sources if s.is_active and (s.consecutive_failures or 0) > 0]
        healthy  = [s for s in sources if s.is_active and (s.consecutive_failures or 0) == 0]

        if disabled:
            lines.append("🔴 <b>Desactivadas:</b>")
            for s in disabled:
                lines.append(f"  • {_esc(s.name)} — {_esc((s.last_error or '')[:60])}")
        if warning:
            lines.append("\n⚠️ <b>Con errores:</b>")
            for s in warning:
                lines.append(f"  • {_esc(s.name)} — {s.consecutive_failures} fallos")
        if healthy:
            lines.append(f"\n🟢 <b>OK:</b> {len(healthy)} fuentes sin errores")

        buttons = [
            [{"text": f"🔄 Reactivar: {s.name}",
              "callback_data": json.dumps({"a": "reenable_src", "id": s.id})}]
            for s in disabled
        ]
        await send_message(
            chat_id, "\n".join(lines),
            reply_markup={"inline_keyboard": buttons} if buttons else None,
        )
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER (inline buttons) — admin-only actions
# ═══════════════════════════════════════════════════════════════════════════

async def handle_callback(cb: dict):
    data     = cb.get("data", "")
    chat_id  = str(cb["message"]["chat"]["id"])
    msg_id   = cb["message"]["message_id"]
    cb_id    = cb["id"]
    adm      = is_admin(chat_id)

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return

    action  = payload.get("a")
    item_id = payload.get("id")

    # Moderation callbacks are admin-only
    ADMIN_ACTIONS = {"approve", "reject", "send", "summarize",
                     "toggle_src", "toggle_kw", "refresh_fuentes", "reenable_src"}

    if action in ADMIN_ACTIONS and not adm:
        await _tg("answerCallbackQuery", callback_query_id=cb_id,
                  text="⛔ Solo administradores")
        return

    db = SessionLocal()
    try:
        if action == "approve":
            article = db.query(Article).get(item_id)
            if article:
                article.status = "approved"
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="✅ Aprobado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
                          reply_markup={"inline_keyboard": []})

        elif action == "reject":
            article = db.query(Article).get(item_id)
            if article:
                article.status = "rejected"
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="❌ Rechazado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
                          reply_markup={"inline_keyboard": []})

        elif action == "send":
            article = db.query(Article).options(joinedload(Article.summary)).get(item_id)
            if article:
                from app.services.telegram_notifier import send_article
                await send_article(article, db)
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="📤 Enviado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
                          reply_markup={"inline_keyboard": []})

        elif action == "summarize":
            await _tg("answerCallbackQuery", callback_query_id=cb_id, text="🤖 Procesando...")
            article = db.query(Article).options(joinedload(Article.summary)).get(item_id)
            if article:
                from app.services.summarizer import summarize_article
                result = await summarize_article(article, db)
                cat   = f" · {article.category}" if article.category else ""
                score = f" · ⭐{article.relevance_score}/10" if article.relevance_score else ""
                if result:
                    await send_message(chat_id,
                        f"<b>Artículo #{item_id}</b>{cat}{score}\n\n{_esc(result.summary_text)}")
                else:
                    await send_message(chat_id, "❌ No se pudo generar el resumen")

        elif action == "toggle_src":
            source = db.query(Source).get(item_id)
            if source:
                source.is_active = not source.is_active
                db.commit()
                status_txt = "activada 🟢" if source.is_active else "desactivada 🔴"
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text=f"Fuente {status_txt}")
                await cmd_fuentes(chat_id)

        elif action == "toggle_kw":
            kw = db.query(Keyword).get(item_id)
            if kw:
                kw.is_active = not kw.is_active
                db.commit()
                status_txt = "activada 🟢" if kw.is_active else "desactivada 🔴"
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text=f"Keyword {status_txt}")
                await cmd_keywords(chat_id)

        elif action == "refresh_fuentes":
            await _tg("answerCallbackQuery", callback_query_id=cb_id, text="🔄 Actualizado")
            await cmd_fuentes(chat_id)

        elif action == "reenable_src":
            source = db.query(Source).get(item_id)
            if source:
                source.is_active          = True
                source.consecutive_failures = 0
                source.last_error         = None
                source.disabled_at        = None
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id,
                          text=f"🟢 {source.name} reactivada")
                await cmd_salud(chat_id)

    except Exception as e:
        logger.error(f"Callback error [{action}]: {e}")
        await _tg("answerCallbackQuery", callback_query_id=cb_id, text="❌ Error")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# UPDATE DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════

async def _process_update(update: dict):
    if "message" in update:
        msg     = update["message"]
        chat_id = str(msg["chat"]["id"])
        text    = msg.get("text", "").strip()
        adm     = is_admin(chat_id)

        cmd  = text.split()[0].lower() if text else ""
        # Strip bot username suffix e.g. /start@MyBot
        if "@" in cmd:
            cmd = cmd.split("@")[0]
        rest = text[len(cmd):].strip()

        # Update subscriber last_seen
        if not adm and cmd in PUBLIC_COMMANDS:
            _update_last_seen(chat_id)

        if cmd in ("/start", "/help"):
            await cmd_start(chat_id, adm)

        # Public commands (available to everyone)
        elif cmd == "/noticias":
            if adm:
                await cmd_noticias_admin(chat_id)
            else:
                await cmd_noticias_public(chat_id)

        elif cmd == "/buscar":
            if adm:
                await cmd_buscar_admin(chat_id, rest)
            else:
                await cmd_buscar_public(chat_id, rest)

        elif cmd == "/leer":
            await cmd_leer(chat_id, rest, adm)

        elif cmd == "/suscribir":
            await cmd_suscribir(chat_id, msg)

        elif cmd == "/cancelar":
            await cmd_cancelar(chat_id)

        # Admin-only commands
        elif not adm:
            await send_message(
                chat_id,
                "ℹ️ Comando no disponible.\nUsa /help para ver los comandos disponibles."
            )

        elif cmd == "/aprobar":
            await cmd_aprobar(chat_id, rest)
        elif cmd == "/rechazar":
            await cmd_rechazar(chat_id, rest)
        elif cmd == "/stats":
            await cmd_stats(chat_id)
        elif cmd == "/fetch":
            await cmd_fetch(chat_id)
        elif cmd == "/digest":
            await cmd_digest(chat_id)
        elif cmd == "/fuentes":
            await cmd_fuentes(chat_id)
        elif cmd == "/config":
            await cmd_config(chat_id, rest)
        else:
            await send_message(chat_id, "Comando no reconocido. Usa /help")

    elif "callback_query" in update:
        await handle_callback(update["callback_query"])


def _update_last_seen(chat_id: str):
    """Silently update last_seen_at for a subscriber."""
    try:
        db = SessionLocal()
        sub = db.query(Subscriber).filter_by(chat_id=chat_id, is_active=True).first()
        if sub:
            sub.last_seen_at = datetime.utcnow()
            db.commit()
        db.close()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# BROADCAST helpers (used by scheduler / digest)
# ═══════════════════════════════════════════════════════════════════════════

async def broadcast_to_subscribers(text: str, reply_markup=None):
    """Send a message to all active subscribers."""
    db = SessionLocal()
    try:
        subs = db.query(Subscriber).filter(Subscriber.is_active == True).all()
        for sub in subs:
            try:
                await send_message(sub.chat_id, text, reply_markup=reply_markup)
                await asyncio.sleep(0.05)  # respect Telegram rate limits
            except Exception as e:
                logger.warning(f"Failed to send to subscriber {sub.chat_id}: {e}")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# POLLING LOOP
# ═══════════════════════════════════════════════════════════════════════════

async def poll_updates():
    global _offset
    logger.info("Telegram bot polling active")

    while True:
        try:
            result = await _tg("getUpdates", offset=_offset, timeout=30)
            if result:
                for update in result:
                    _offset = update["update_id"] + 1
                    try:
                        await _process_update(update)
                    except Exception as e:
                        logger.error(f"Update processing error: {e}")
        except asyncio.CancelledError:
            logger.info("Telegram polling stopped")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(0.5)
