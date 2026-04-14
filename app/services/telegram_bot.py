"""
Interactive Telegram Bot with full command set.
Runs as asyncio background task alongside FastAPI.
"""
import asyncio
import json
import logging

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import Article, DigestConfig, Keyword, Source, Summary
from app.services.telegram_notifier import _esc, _tg, send_message

logger = logging.getLogger(__name__)

OWNER_ID = settings.telegram_chat_id
_offset = 0

HELP_TEXT = """<b>NewsLet Pro</b> — Comandos disponibles:

<b>📰 Noticias</b>
/noticias — Últimas 5 noticias con resúmenes
/ultimas — Alias de /noticias
/buscar &lt;término&gt; — Buscar por palabra clave
/leer &lt;id&gt; — Leer artículo completo
/score &lt;id&gt; — Ver score, categoría y sentimiento

<b>✅ Moderación rápida</b>
/aprobar &lt;id&gt; — Aprobar artículo por ID
/rechazar &lt;id&gt; — Rechazar artículo por ID

<b>📊 Sistema</b>
/stats — Estadísticas completas
/salud — Estado de las fuentes (salud)
/fetch — Buscar noticias ahora
/resumir — Resumir artículos pendientes
/digest — Enviar digest ahora
/pdf — Recibir digest en PDF

<b>⚙️ Configuración</b>
/fuentes — Ver y gestionar fuentes
/keywords — Ver y gestionar keywords
/config — Ver configuración del digest
/config hora=8 cantidad=10 score=5 — Actualizar digest"""


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def cmd_start(chat_id: str):
    await send_message(chat_id, HELP_TEXT)


async def cmd_stats(chat_id: str):
    db = SessionLocal()
    try:
        total = db.query(Article).count()
        pending = db.query(Article).filter(Article.status == "pending").count()
        approved = db.query(Article).filter(Article.status == "approved").count()
        sent = db.query(Article).filter(Article.status == "sent").count()
        no_summary = db.query(Article).outerjoin(Summary).filter(Summary.id == None).count()
        sources = db.query(Source).filter(Source.is_active == True).count()
        keywords = db.query(Keyword).filter(Keyword.is_active == True).count()

        from sqlalchemy import func
        avg_score = db.query(func.avg(Article.relevance_score)).filter(
            Article.relevance_score != None
        ).scalar()

        text = (
            "<b>Estadísticas del sistema</b>\n\n"
            f"📰 Total artículos: <b>{total}</b>\n"
            f"⏳ Pendientes: <b>{pending}</b>\n"
            f"✅ Aprobados: <b>{approved}</b>\n"
            f"📤 Enviados: <b>{sent}</b>\n"
            f"🤖 Sin resumen: <b>{no_summary}</b>\n\n"
            f"📡 Fuentes activas: <b>{sources}</b>\n"
            f"🔔 Keywords activas: <b>{keywords}</b>\n"
            f"⭐ Score promedio: <b>{round(float(avg_score), 1) if avg_score else 'N/A'}/10</b>"
        )
        await send_message(chat_id, text)
    finally:
        db.close()


async def cmd_noticias(chat_id: str):
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
            await send_message(chat_id, "No hay artículos aún. Usa /fetch para buscar.")
            return

        for a in articles:
            summary = a.summary.summary_text if a.summary else "Sin resumen — usa el botón para generarlo"
            source_name = a.source.name if a.source else "?"
            cat = f" · {_esc(a.category)}" if a.category else ""
            score = f" · ⭐{a.relevance_score}/10" if a.relevance_score else ""

            text = (
                f"<b>{_esc(a.title)}</b>\n\n"
                f"{_esc(summary)}\n\n"
                f"📌 {_esc(source_name)}{cat}{score}\n"
                f'<a href="{a.url}">Leer completo</a> · ID: {a.id}'
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
                buttons.append([{"text": "📤 Enviar a canal", "callback_data": json.dumps({"a": "send", "id": a.id})}])

            await send_message(chat_id, text, reply_markup={"inline_keyboard": buttons} if buttons else None)
            await asyncio.sleep(0.4)
    finally:
        db.close()


async def cmd_buscar(chat_id: str, term: str):
    if not term:
        await send_message(chat_id, "Uso: /buscar <i>termino</i>\nEjemplo: <code>/buscar economia</code>")
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
            src = a.source.name if a.source else "?"
            summary = (a.summary.summary_text[:120] + "...") if a.summary else ""
            cat = f" · {a.category}" if a.category else ""
            score = f" · ⭐{a.relevance_score}" if a.relevance_score else ""
            lines.append(f"<b>{i}. {_esc(a.title)}</b>")
            lines.append(f"   <i>{_esc(src)}{cat}{score}</i>")
            if summary:
                lines.append(f"   {_esc(summary)}")
            lines.append(f'   <a href="{a.url}">Leer</a> · /leer {a.id}\n')

        await send_message(chat_id, "\n".join(lines))
    finally:
        db.close()


async def cmd_leer(chat_id: str, article_id_str: str):
    """Send article full text in paginated chunks."""
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/leer {id}</code>\nEjemplo: <code>/leer 42</code>")
        return

    db = SessionLocal()
    try:
        article = db.query(Article).options(joinedload(Article.summary)).get(article_id)
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
        total = len(chunks)

        for idx, chunk in enumerate(chunks):
            header = f"<b>{_esc(article.title)}</b>"
            if total > 1:
                header += f" ({idx+1}/{total})"
            page_text = f"{header}\n\n{_esc(chunk)}"
            if idx == total - 1:
                page_text += f'\n\n<a href="{article.url}">Fuente original</a>'
            await send_message(chat_id, page_text)
            await asyncio.sleep(0.5)
    finally:
        db.close()


async def cmd_fetch(chat_id: str):
    await send_message(chat_id, "🔄 Buscando noticias en todas las fuentes...")
    db = SessionLocal()
    try:
        from app.services.rss_fetcher import fetch_all_rss
        from app.services.newsapi_fetcher import fetch_all_newsapi
        from app.services.web_scraper import fetch_all_scrapers
        rss = await fetch_all_rss(db)
        newsapi = await fetch_all_newsapi(db)
        scraped = await fetch_all_scrapers(db)
        total = rss + newsapi + scraped
        await send_message(chat_id,
            f"✅ <b>{total}</b> noticias nuevas\n"
            f"RSS: {rss} · API: {newsapi} · Scraper: {scraped}"
        )
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_resumir(chat_id: str):
    await send_message(chat_id, "🤖 Resumiendo artículos pendientes (scrape + IA)...")
    db = SessionLocal()
    try:
        from app.services.summarizer import summarize_pending
        count = await summarize_pending(db, limit=10)
        await send_message(chat_id, f"✅ <b>{count}</b> artículos procesados")
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_digest(chat_id: str):
    db = SessionLocal()
    try:
        from app.services.telegram_notifier import send_digest
        cfg = db.query(DigestConfig).first()
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
    except Exception as e:
        await send_message(chat_id, f"❌ Error: {_esc(str(e))}")
    finally:
        db.close()


async def cmd_pdf(chat_id: str):
    await send_message(chat_id, "📄 Generando PDF del digest...")
    db = SessionLocal()
    try:
        cfg = db.query(DigestConfig).first()
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
                files={"document": ("newsbot_digest.pdf", pdf_bytes, "application/pdf")},
            )
        if not resp.json().get("ok"):
            await send_message(chat_id, f"❌ Error enviando PDF: {resp.json().get('description')}")
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
            icon = "🟢" if s.is_active else "🔴"
            buttons.append([{
                "text": f"{icon} {s.name} ({count}) [{s.source_type}]",
                "callback_data": json.dumps({"a": "toggle_src", "id": s.id}),
            }])
        buttons.append([{"text": "🔄 Actualizar", "callback_data": json.dumps({"a": "refresh_fuentes"})}])
        await send_message(
            chat_id,
            "<b>Fuentes de noticias</b>\nToca para activar/desactivar:",
            reply_markup={"inline_keyboard": buttons},
        )
    finally:
        db.close()


async def cmd_keywords(chat_id: str):
    db = SessionLocal()
    try:
        keywords = db.query(Keyword).order_by(Keyword.keyword).all()
        if not keywords:
            await send_message(
                chat_id,
                "<b>Keywords de alerta</b>\n\nNo hay keywords configuradas.\n\n"
                "Agrega una desde el panel web o el API.",
            )
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
            f"<b>Keywords de alerta</b>\n{active}/{len(keywords)} activas\nToca para activar/desactivar:",
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
            # Parse key=value pairs
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
                cfg.updated_at = __import__("datetime").datetime.utcnow()
                db.commit()
                from app.scheduler.jobs import reschedule_digest
                reschedule_digest(cfg.hour)
                await send_message(chat_id, f"✅ Configuración actualizada: {', '.join(changed)}")
                return

        # Show current config
        cats = cfg.categories or "Todas"
        text = (
            "<b>Configuración del Digest</b>\n\n"
            f"🕐 Hora de envío: <b>{cfg.hour:02d}:00</b>\n"
            f"📰 Artículos por digest: <b>{cfg.count}</b>\n"
            f"⭐ Score mínimo: <b>{cfg.min_score}/10</b>\n"
            f"🏷 Categorías: <b>{_esc(cats)}</b>\n\n"
            "<i>Para cambiar: /config hora=8 cantidad=10 score=5</i>"
        )
        await send_message(chat_id, text)
    finally:
        db.close()


async def cmd_score(chat_id: str, article_id_str: str):
    """Show score, category, sentiment and summary for a specific article."""
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/score {id}</code>\nEjemplo: <code>/score 42</code>")
        return

    db = SessionLocal()
    try:
        article = db.query(Article).options(joinedload(Article.summary), joinedload(Article.source)).get(article_id)
        if not article:
            await send_message(chat_id, f"Artículo #{article_id} no encontrado.")
            return

        score_bar = ""
        if article.relevance_score:
            filled = round(article.relevance_score / 10 * 10)
            score_bar = "█" * filled + "░" * (10 - filled)

        sentiment_icon = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(
            article.sentiment or "neutral", "😐"
        )
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌", "sent": "📤"}.get(
            article.status, "❓"
        )
        cat = article.category or "Sin categoría"
        src = article.source.name if article.source else "?"
        summary_preview = ""
        if article.summary:
            summary_preview = f"\n\n<i>{_esc(article.summary.summary_text[:300])}</i>"

        text = (
            f"<b>#{article_id} · {_esc(article.title[:80])}</b>\n\n"
            f"⭐ Score: <b>{article.relevance_score}/10</b>  {score_bar}\n"
            f"🏷 Categoría: <b>{_esc(cat)}</b>\n"
            f"{sentiment_icon} Sentimiento: <b>{article.sentiment or 'N/A'}</b>\n"
            f"{status_icon} Estado: <b>{article.status}</b>\n"
            f"📡 Fuente: <b>{_esc(src)}</b>"
            f"{summary_preview}\n\n"
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
    """Approve an article by ID via text command."""
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/aprobar {id}</code>\nEjemplo: <code>/aprobar 42</code>")
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
        await send_message(
            chat_id,
            f"✅ Artículo #{article_id} aprobado: <b>{_esc(article.title[:80])}</b>"
        )
    finally:
        db.close()


async def cmd_rechazar(chat_id: str, article_id_str: str):
    """Reject an article by ID via text command."""
    try:
        article_id = int(article_id_str.strip())
    except ValueError:
        await send_message(chat_id, "Uso: <code>/rechazar {id}</code>\nEjemplo: <code>/rechazar 42</code>")
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
        await send_message(
            chat_id,
            f"❌ Artículo #{article_id} rechazado: <b>{_esc(article.title[:80])}</b>"
        )
    finally:
        db.close()


async def cmd_salud(chat_id: str):
    """Show source health status — consecutive failures, last error, disabled sources."""
    db = SessionLocal()
    try:
        sources = db.query(Source).order_by(Source.consecutive_failures.desc()).all()
        if not sources:
            await send_message(chat_id, "No hay fuentes configuradas.")
            return

        lines = ["<b>Salud de las Fuentes</b>\n"]
        disabled = [s for s in sources if not s.is_active]
        healthy = [s for s in sources if s.is_active and (s.consecutive_failures or 0) == 0]
        warning = [s for s in sources if s.is_active and (s.consecutive_failures or 0) > 0]

        if disabled:
            lines.append("🔴 <b>Desactivadas:</b>")
            for s in disabled:
                err = (s.last_error or "")[:60]
                lines.append(f"  • {_esc(s.name)} — {_esc(err)}")

        if warning:
            lines.append("\n⚠️ <b>Con errores:</b>")
            for s in warning:
                lines.append(f"  • {_esc(s.name)} — {s.consecutive_failures} fallos consecutivos")

        if healthy:
            lines.append(f"\n🟢 <b>OK:</b> {len(healthy)} fuentes sin errores")

        # Offer re-enable buttons for disabled sources
        buttons = []
        for s in disabled:
            buttons.append([{
                "text": f"🔄 Reactivar: {s.name}",
                "callback_data": json.dumps({"a": "reenable_src", "id": s.id}),
            }])

        await send_message(
            chat_id,
            "\n".join(lines),
            reply_markup={"inline_keyboard": buttons} if buttons else None,
        )
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER (inline buttons)
# ═══════════════════════════════════════════════════════════════════════════

async def handle_callback(cb: dict):
    data = cb.get("data", "")
    chat_id = str(cb["message"]["chat"]["id"])
    message_id = cb["message"]["message_id"]
    cb_id = cb["id"]

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return

    action = payload.get("a")
    item_id = payload.get("id")

    db = SessionLocal()
    try:
        if action == "approve":
            article = db.query(Article).get(item_id)
            if article:
                article.status = "approved"
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="✅ Aprobado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                           reply_markup={"inline_keyboard": []})

        elif action == "reject":
            article = db.query(Article).get(item_id)
            if article:
                article.status = "rejected"
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="❌ Rechazado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                           reply_markup={"inline_keyboard": []})

        elif action == "send":
            article = db.query(Article).options(joinedload(Article.summary)).get(item_id)
            if article:
                from app.services.telegram_notifier import send_article
                await send_article(article, db)
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text="📤 Enviado")
                await _tg("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                           reply_markup={"inline_keyboard": []})

        elif action == "summarize":
            await _tg("answerCallbackQuery", callback_query_id=cb_id, text="🤖 Procesando...")
            article = db.query(Article).options(joinedload(Article.summary)).get(item_id)
            if article:
                from app.services.summarizer import summarize_article
                result = await summarize_article(article, db)
                if result:
                    cat = f" · {article.category}" if article.category else ""
                    score = f" · ⭐{article.relevance_score}/10" if article.relevance_score else ""
                    await send_message(
                        chat_id,
                        f"<b>Artículo #{item_id}</b>{cat}{score}\n\n{_esc(result.summary_text)}"
                    )
                else:
                    await send_message(chat_id, "❌ No se pudo generar el resumen")

        elif action == "toggle_src":
            source = db.query(Source).get(item_id)
            if source:
                source.is_active = not source.is_active
                db.commit()
                status = "activada 🟢" if source.is_active else "desactivada 🔴"
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text=f"Fuente {status}")
                await cmd_fuentes(chat_id)

        elif action == "toggle_kw":
            kw = db.query(Keyword).get(item_id)
            if kw:
                kw.is_active = not kw.is_active
                db.commit()
                status = "activada 🟢" if kw.is_active else "desactivada 🔴"
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text=f"Keyword {status}")
                await cmd_keywords(chat_id)

        elif action == "refresh_fuentes":
            await _tg("answerCallbackQuery", callback_query_id=cb_id, text="🔄 Actualizado")
            await cmd_fuentes(chat_id)

        elif action == "reenable_src":
            source = db.query(Source).get(item_id)
            if source:
                source.is_active = True
                source.consecutive_failures = 0
                source.last_error = None
                source.disabled_at = None
                db.commit()
                await _tg("answerCallbackQuery", callback_query_id=cb_id, text=f"🟢 {source.name} reactivada")
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
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "").strip()

        if chat_id != OWNER_ID:
            return  # Silently ignore unauthorized

        cmd = text.split()[0] if text else ""
        rest = text[len(cmd):].strip()

        if cmd in ("/start", "/help"):
            await cmd_start(chat_id)
        elif cmd == "/stats":
            await cmd_stats(chat_id)
        elif cmd in ("/noticias", "/ultimas"):
            await cmd_noticias(chat_id)
        elif cmd == "/buscar":
            await cmd_buscar(chat_id, rest)
        elif cmd == "/leer":
            await cmd_leer(chat_id, rest)
        elif cmd == "/score":
            await cmd_score(chat_id, rest)
        elif cmd == "/aprobar":
            await cmd_aprobar(chat_id, rest)
        elif cmd == "/rechazar":
            await cmd_rechazar(chat_id, rest)
        elif cmd == "/salud":
            await cmd_salud(chat_id)
        elif cmd == "/fetch":
            await cmd_fetch(chat_id)
        elif cmd == "/resumir":
            await cmd_resumir(chat_id)
        elif cmd == "/digest":
            await cmd_digest(chat_id)
        elif cmd == "/pdf":
            await cmd_pdf(chat_id)
        elif cmd == "/fuentes":
            await cmd_fuentes(chat_id)
        elif cmd == "/keywords":
            await cmd_keywords(chat_id)
        elif cmd == "/config":
            await cmd_config(chat_id, rest)
        else:
            await send_message(chat_id, "Comando no reconocido. Usa /help")

    elif "callback_query" in update:
        await handle_callback(update["callback_query"])


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
