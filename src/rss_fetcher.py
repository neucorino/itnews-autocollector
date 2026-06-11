from typing import List
from src.exceptions import RSSFetchError
import feedparser
from src.models import Article
from src import config
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

def fetch_rss(rss_url: str, source: str) -> List[Article]:
    logger.info(f"RSS取得開始: {rss_url}")
    feed = feedparser.parse(rss_url)
    articles = []
    if feed.bozo:
        raise RSSFetchError(f"RSSの形式が壊れています: {rss_url}") 

    for entry in feed.entries:
        logger.info(f"記事取得: {entry.title}")

        published_str = entry.get("published")
        
        if published_str:
            published = parsedate_to_datetime(published_str)
        else:
            # publishedがないRSSへのフォールバック
            published = datetime.now(timezone.utc)

        article = Article(
            title=entry.title,
            url=entry.link,
            source=source,
            summary=entry.get("summary", ""),
            published_at=published.strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        articles.append(article)

    return articles