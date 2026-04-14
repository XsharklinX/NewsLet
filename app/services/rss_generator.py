"""
Generates a valid RSS 2.0 feed from approved/sent articles.
"""
from datetime import datetime
from email.utils import formatdate
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.article import Article


def _cdata(text: str) -> str:
    return f"<![CDATA[{text}]]>"


def _rfc822(dt: datetime | None) -> str:
    if dt is None:
        return formatdate()
    return formatdate(dt.timestamp())


def generate_rss_feed(articles: list["Article"], base_url: str = "http://localhost:8000") -> str:
    """Returns a complete RSS 2.0 XML string."""
    now = _rfc822(datetime.utcnow())

    items_xml = []
    for a in articles:
        summary_text = ""
        if a.summary:
            summary_text = a.summary.summary_text
        elif a.original_text:
            summary_text = (a.original_text or "")[:500]

        category_tag = f"<category>{a.category}</category>" if a.category else ""
        score_tag = f"<newslet:score>{a.relevance_score}</newslet:score>" if a.relevance_score else ""

        items_xml.append(f"""    <item>
      <title>{_cdata(a.title)}</title>
      <link>{a.url}</link>
      <guid isPermaLink="true">{a.url}</guid>
      <pubDate>{_rfc822(a.published_at or a.fetched_at)}</pubDate>
      <description>{_cdata(summary_text)}</description>
      {category_tag}
      {score_tag}
      <source url="{base_url}">{_cdata(a.source.name if a.source else "NewsLet")}</source>
    </item>""")

    items_block = "\n".join(items_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:newslet="https://newslet.app/rss/1.0">
  <channel>
    <title>NewsLet — Noticias curadas</title>
    <link>{base_url}</link>
    <description>Feed de noticias curadas y resumidas por NewsLet</description>
    <language>es</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{base_url}/api/v1/feed/rss" rel="self" type="application/rss+xml"/>
{items_block}
  </channel>
</rss>"""
