from rss_fetcher import fetch_rss
from db import DatabaseManager
from gemini_analyzer import (
    analyze_article_with_gemini,
    analyze_articles
)
from service import NewsService
from mail_sender import send_daily_email
import config
import logging
from logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

def main():
    logger.info("★★★ main開始 ★★★")    

    db_manager = DatabaseManager()
    service = NewsService(db_manager)
    
    batch_id = db_manager.start_new_batch()

    for rss_url, source in RSS_LIST:
        # 重要な記事をDBに保存
        articles= service.process_new_articles(rss_url, source)
        save_analyses = service.process_new_analyses(articles, batch_id)
        save_rankings = service.process_new_rankings(batch_id)

    # 通知対象決定
    notify_articles = service.get_notification_targets(batch_id)

    if notify_articles is None: # 万が一 None が返ってきても大丈夫なように
        notify_articles = []
        
    if not notify_articles:
        logger.warning("通知対象の記事が0件でした。処理を終了します。")
        return # ここで安全に止める

    logger.info(f"最終通知件数: {len(notify_articles)}件")
    
    # メール送信
    send_daily_email(notify_articles, batch_id)

if __name__ == "__main__":
    main()