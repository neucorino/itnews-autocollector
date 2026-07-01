from typing import List
from src.exceptions import RSSFetchError
import feedparser
from src.models import Article
from src import config
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

def parse_rss_date(published_str: str) -> datetime:
    """様々なRSSの日付フォーマット（RFC 822 / ISO 8601）を安全に datetime オブジェクトに変換する。
    パースに失敗した場合は、システムを落とさず現在時刻をフォールバックとして返す防御設計。
    """
    if not published_str:
        return datetime.now(timezone.utc)

    # 標準的な RSS 形式 (RFC 822: Wed, 30 Jun 2026 ... など) を試みる
    try:
        return parsedate_to_datetime(published_str)
    except ValueError:
        pass

    #失敗した場合、ISO 8601 形式 ("2026-06-30T20:51:03-04:00") を試みる
    try:
        return datetime.fromisoformat(published_str)
    except ValueError:
        pass

    # どちらのフォーマットでもなければ、警告ログを出して現在時刻を返し、全体の収集を止めない
    logger.warning(
        f"未知の日付フォーマットを検出したため現在時刻を適用します: '{published_str}'"
    )
    return datetime.now(timezone.utc)


def fetch_rss(rss_url: str, source: str) -> List[Article]:
    logger.info(f"RSS取得開始: {rss_url}")
    feed = feedparser.parse(rss_url)
    articles = []
    if feed.bozo:
        raise RSSFetchError(f"RSSの形式が壊れています: {rss_url}") 

    for entry in feed.entries[:config.SOURCE_FETCH_LIMIT]:
        logger.info(f"記事取得: {entry.title}")

        # entry から日付文字列を安全に取得
        published_str = entry.get("published") or entry.get("updated")
        
        # 日付文字列をdatetimeオブジェクトに変換
        published_dt = parse_rss_date(published_str)
        
       # データベース保存用に指定の文字フォーマットに成形
        formatted_date = published_dt.strftime("%Y-%m-%d %H:%M:%S")

        article = Article(
            title=entry.title,
            url=entry.link,
            source=source,
            summary=entry.get("summary", ""),
            published_at=formatted_date,
        )
        
        articles.append(article)

    return articles