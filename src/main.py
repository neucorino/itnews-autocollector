from rss_fetcher import fetch_rss
from db import DatabaseManager
from gemini_analyzer import (
    analyze_article_with_gemini,
    analyze_articles
)
from service import (
    process_new_articles,
    process_new_analyses,
    process_new_rankings,
    get_notification_targets
)
from mail_sender import send_daily_email
import config
from logger import setup_logger


logger = setup_logger()

RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

def main():

    db_manager = DatabaseManager()
    db_manager.create_tables()
    batch_id = db_manager.start_new_batch()

    for rss_url, source in RSS_LIST:

        # RSSから記事を取得
        articles = fetch_rss(rss_url, source)

        # 重要な記事をDBに保存
        articles= process_new_articles(rss_url, source)
        save_analyses = process_new_analyses(articles, batch_id)
        save_rankings = process_new_rankings(batch_id)

    # 通知対象決定
    notify_articles = get_notification_targets(batch_id)

    if notify_articles is None: # 万が一 None が返ってきても大丈夫なように
        notify_articles = []
        
    if not notify_articles:
        logger.warning("通知対象の記事が0件でした。処理を終了します。")
        return # ここで安全に止める

    logger.info(f"最終通知件数: {len(notify_articles)}件")
    
    # メール送信
    send_daily_email(batch_id)

if __name__ == "__main__":
    main()