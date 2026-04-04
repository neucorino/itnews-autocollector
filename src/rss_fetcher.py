import feedparser
from models import Article
import config
import logging

logger = logging.getLogger(__name__)

def fetch_rss(rss_url, source):
    logger.info(f"RSS取得開始: {rss_url}")
    feed = feedparser.parse(rss_url)
    articles = []
    if feed.bozo:
        raise Exception("RSSの形式が壊れています")
    else:
        logger.info(f"{len(articles)} 件の記事取得")

    for entry in feed.entries:
        logger.info(f"記事取得: {entry.title}")

        article = Article(
            title=entry.title,
            url=entry.link,
            source=source,
            summary=entry.get("summary", ""),
            published_at=entry.get("published", ""),

        )

        articles.append(article)

    return articles