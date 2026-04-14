"""Generates professional PDF digests using ReportLab."""
import io
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

logger = logging.getLogger(__name__)

_ACCENT = colors.HexColor("#6366f1")
_DARK = colors.HexColor("#1a1a2e")
_MUTED = colors.HexColor("#71717a")
_LIGHT_BORDER = colors.HexColor("#e4e4e7")
_SCORE_COLORS = {
    range(1, 4): colors.HexColor("#ef4444"),   # low
    range(4, 7): colors.HexColor("#eab308"),   # medium
    range(7, 11): colors.HexColor("#22c55e"),  # high
}


def _score_color(score: int | None) -> colors.Color:
    if score is None:
        return _MUTED
    for r, c in _SCORE_COLORS.items():
        if score in r:
            return c
    return _MUTED


def generate_digest_pdf(articles: list, title: str = "NewsBot Pro — Digest Diario") -> bytes:
    """Generate a professional PDF from a list of Article ORM objects. Returns bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title,
        author="NewsBot Pro",
    )

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("DocTitle", parent=styles["Title"],
        fontSize=22, textColor=_DARK, spaceAfter=4, fontName="Helvetica-Bold")
    s_meta = ParagraphStyle("DocMeta", parent=styles["Normal"],
        fontSize=9, textColor=_MUTED, spaceAfter=18)
    s_art_title = ParagraphStyle("ArtTitle", parent=styles["Normal"],
        fontSize=13, fontName="Helvetica-Bold", textColor=_DARK, spaceAfter=4, leading=16)
    s_art_meta = ParagraphStyle("ArtMeta", parent=styles["Normal"],
        fontSize=8, textColor=_MUTED, spaceAfter=6)
    s_art_body = ParagraphStyle("ArtBody", parent=styles["Normal"],
        fontSize=10, leading=15, textColor=colors.HexColor("#27272a"), spaceAfter=8)
    s_art_url = ParagraphStyle("ArtURL", parent=styles["Normal"],
        fontSize=8, textColor=_ACCENT, spaceAfter=20)

    story = []

    # Header
    story.append(Paragraph(title, s_title))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d de %B de %Y a las %H:%M')} · {len(articles)} artículos",
        s_meta
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_ACCENT, spaceAfter=16))

    if not articles:
        story.append(Paragraph("No hay artículos disponibles.", s_art_body))
    else:
        for i, article in enumerate(articles, 1):
            summary = ""
            if article.summary:
                summary = article.summary.summary_text
            elif article.original_text:
                summary = article.original_text[:500]

            source_name = article.source.name if article.source else "Desconocido"
            pub_date = ""
            if article.published_at:
                pub_date = article.published_at.strftime("%d/%m/%Y %H:%M")
            elif article.fetched_at:
                pub_date = article.fetched_at.strftime("%d/%m/%Y %H:%M")

            score = article.relevance_score
            category = article.category or "Sin categoría"

            # Article number + title
            story.append(Paragraph(f"{i}. {article.title}", s_art_title))

            # Metadata row with score badge
            meta_parts = [f"📌 {source_name}"]
            if pub_date:
                meta_parts.append(pub_date)
            meta_parts.append(f"🏷 {category}")
            if score:
                meta_parts.append(f"⭐ Relevancia: {score}/10")
            story.append(Paragraph("  ·  ".join(meta_parts), s_art_meta))

            # Summary
            if summary:
                story.append(Paragraph(summary[:800], s_art_body))

            # URL
            story.append(Paragraph(
                f'<link href="{article.url}" color="#6366f1">{article.url[:80]}{"..." if len(article.url) > 80 else ""}</link>',
                s_art_url
            ))

            # Divider (except after last article)
            if i < len(articles):
                story.append(HRFlowable(width="100%", thickness=0.5, color=_LIGHT_BORDER, spaceAfter=12))

    doc.build(story)
    logger.info(f"PDF generated: {len(articles)} articles, {buf.tell()} bytes")
    return buf.getvalue()
