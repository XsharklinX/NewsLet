"""
Email digest via SMTP (async using aiosmtplib).
Enabled when SMTP_ENABLED=true in .env.
Supports Gmail, Outlook, and any STARTTLS/SSL server.
"""
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _build_html(articles: list) -> str:
    """Build an HTML email body from a list of Article ORM objects."""
    date_str = datetime.utcnow().strftime("%d de %B de %Y")
    count = len(articles)

    rows = []
    for a in articles:
        summary_text = ""
        if a.summary:
            summary_text = a.summary.summary_text
        category = a.category or ""
        score = f"⭐ {a.relevance_score}/10" if a.relevance_score else ""
        sentiment_color = {
            "positive": "#22c55e",
            "negative": "#ef4444",
            "neutral":  "#64748b",
        }.get(a.sentiment or "neutral", "#64748b")
        sentiment_label = {"positive": "Positivo", "negative": "Negativo", "neutral": "Neutral"}.get(
            a.sentiment or "neutral", ""
        )
        src_name = a.source.name if a.source else ""

        thumbnail = ""
        if getattr(a, "thumbnail_url", None):
            thumbnail = f'<img src="{a.thumbnail_url}" style="width:100%;max-height:180px;object-fit:cover;border-radius:8px;margin-bottom:12px;" alt="">'

        rows.append(f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:16px;border-left:4px solid #818cf8;">
          {thumbnail}
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
            {"" if not category else f'<span style="background:#312e81;color:#a5b4fc;padding:2px 8px;border-radius:20px;font-size:12px;">{category}</span>'}
            {"" if not score else f'<span style="background:#1e3a5f;color:#93c5fd;padding:2px 8px;border-radius:20px;font-size:12px;">{score}</span>'}
            {"" if not sentiment_label else f'<span style="color:{sentiment_color};font-size:12px;">{sentiment_label}</span>'}
          </div>
          <h3 style="margin:0 0 8px;color:#e2e8f0;font-size:16px;line-height:1.4;">
            <a href="{a.url}" style="color:#a5b4fc;text-decoration:none;">{a.title}</a>
          </h3>
          {"" if not summary_text else f'<p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 12px;">{summary_text}</p>'}
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#64748b;">
            <span>📡 {src_name}</span>
            <a href="{a.url}" style="color:#818cf8;text-decoration:none;">Leer artículo →</a>
          </div>
        </div>
        """)

    body_rows = "\n".join(rows)

    return f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:640px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="text-align:center;padding:32px 0 24px;">
      <div style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:16px;padding:12px 20px;margin-bottom:16px;">
        <span style="color:white;font-size:24px;">📰</span>
      </div>
      <h1 style="margin:0;color:#e2e8f0;font-size:28px;font-weight:700;">NewsLet</h1>
      <p style="color:#64748b;margin:8px 0 0;font-size:14px;">Digest diario · {date_str}</p>
    </div>

    <!-- Summary bar -->
    <div style="background:#1e293b;border-radius:12px;padding:16px;margin-bottom:20px;text-align:center;">
      <span style="color:#94a3b8;font-size:14px;">
        📊 <strong style="color:#e2e8f0;">{count}</strong> artículos en este digest
      </span>
    </div>

    <!-- Articles -->
    {body_rows}

    <!-- Footer -->
    <div style="text-align:center;padding:24px 0;border-top:1px solid #1e293b;margin-top:8px;">
      <p style="color:#475569;font-size:12px;margin:0;">
        NewsLet Pro · Generado el {datetime.utcnow().strftime("%d/%m/%Y %H:%M")} UTC
      </p>
    </div>
  </div>
</body>
</html>
"""


async def send_email_digest(articles: list) -> dict:
    """
    Send an HTML digest email to all configured recipients.
    Returns a dict with sent count and any errors.
    """
    if not settings.smtp_enabled:
        return {"sent": 0, "error": "SMTP_ENABLED is false — set it in .env to enable email digest"}

    if not settings.smtp_user or not settings.smtp_password:
        return {"sent": 0, "error": "SMTP credentials not configured"}

    recipients = [r.strip() for r in settings.smtp_to.split(",") if r.strip()]
    if not recipients:
        return {"sent": 0, "error": "SMTP_TO is empty — set recipient addresses in .env"}

    try:
        import aiosmtplib
    except ImportError:
        return {"sent": 0, "error": "aiosmtplib not installed. Run: pip install aiosmtplib"}

    date_str = datetime.utcnow().strftime("%d/%m/%Y")
    subject = f"📰 NewsLet Digest — {len(articles)} artículos · {date_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = ", ".join(recipients)

    html_content = _build_html(articles)
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    errors = []
    sent = 0
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        sent = len(recipients)
        logger.info(f"Email digest sent to {len(recipients)} recipients ({len(articles)} articles)")
    except Exception as e:
        errors.append(str(e))
        logger.error(f"Email digest failed: {e}")

    return {"sent": sent, "recipients": recipients, "errors": errors}
