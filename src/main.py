from rss_fetcher import fetch_rss
from db import DatabaseManager
from gemini_analyzer import (
    analyze_article_with_gemini,
    analyze_articles
)
from service import NewsService
from mail_sender import send_daily_email
from exceptions import NewsSystemException, ConfigValidationError
import config
import logging
from logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

def main() -> None:
    logger.info("★★★ main開始 ★★★")
    
    # 設定検証
    try:
        config.validate_config()
    except ConfigValidationError as e:
        logger.error(f"設定検証エラー: {e}")
        return

    db_manager = DatabaseManager()
    service = NewsService(db_manager)
    
    batch_id = db_manager.start_new_batch()

    try:
        for rss_url, source in RSS_LIST:
            try:
                # 重要な記事をDBに保存
                articles = service.process_new_articles(rss_url, source)
                save_analyses = service.process_new_analyses(articles, batch_id)
                save_rankings = service.process_new_rankings(batch_id)
            except NewsSystemException as e:
                logger.error(f"処理中にエラー ({source}): {e}")
                # 1つのソース失敗でも続行

        # 通知対象決定
        notify_articles = service.get_notification_targets(batch_id)

        if not notify_articles:
            logger.warning("通知対象の記事が0件でした。処理を終了します。")
            db_manager.finish_batch(batch_id, 'success', 0)
            return # ここで安全に止める

        logger.info(f"最終通知件数: {len(notify_articles)}件")
        
        # メール送信
        send_daily_email(notify_articles, batch_id)
        db_manager.finish_batch(batch_id, 'success', len(notify_articles))
        
    except Exception as e:
        logger.exception(f"Batch {batch_id} 致命的エラー")
        db_manager.finish_batch(batch_id, 'failed', 0)
        raise

if __name__ == "__main__":
    main()