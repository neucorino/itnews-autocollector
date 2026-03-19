from rss_fetcher import fetch_rss
from db import create_table
from gemini_analyzer import (
    analyze_article_with_gemini,
    analyze_articles
)
from service import (
    save_articles,
    get_notification_targets
)
import config
from logger import setup_logger

logger = setup_logger()

RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

def main():

    create_table()

    for rss_url, source in RSS_LIST:

        # RSSから記事を取得
        articles = fetch_rss(rss_url, source)

        # 取得した記事をGeminiで分析
        analyzed_articles = analyze_articles(articles)

        # 重要な記事をDBに保存
        save_articles(analyzed_articles)

    # 通知対象決定
    notify_articles = get_notification_targets()

    logger.info(f"最終通知件数: {len(notify_articles)}件")

if __name__ == "__main__":
    main()