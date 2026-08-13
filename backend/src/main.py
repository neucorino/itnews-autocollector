import logging
from src import config
from src.rss_fetcher import fetch_rss
from src.db import DatabaseManager
from src.service import NewsService
from src.mail_sender import send_daily_email
from src.exceptions import NewsSystemException, ConfigValidationError
from src.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)


def process_sources(service: NewsService, batch_id: int) -> None:
    """各RSSソースを処理する。1ソース失敗しても他を続行する。
    全ソースの記事を集約してから1回だけ分析・ランキングを行い、
    MAX_ARTICLES_PER_BATCH を「1バッチ合計の上限」として機能させる。
    """
    all_articles = []
    for rss_url, source in config.RSS_LIST:
        try:
            articles = service.process_new_articles(rss_url, source)
            if articles:
                all_articles.extend(articles)
            else:
                logger.warning(f"[{source}] から記事が取得できませんでした。")
        except Exception as e:
            logger.error(f"❌ {source} の処理中にエラーが発生しました（スキップして続行します）: {e}", exc_info=True)
    logger.info(f"全ソースの集約完了。合計 {len(all_articles)} 件の記事を分析・ランキング処理へ回します。")
    service.process_new_analyses(all_articles, batch_id)
    service.process_new_rankings(batch_id)


def run_batch(db_manager: DatabaseManager) -> None:
    """
    バッチ処理の本体。
    正常終了・異常終了いずれも finish_batch を確実に呼ぶ。
    """
    service = NewsService(db_manager)
    batch_id = db_manager.start_new_batch()
    status, notify_count = "failed", 0

    try:
        process_sources(service, batch_id)

        notify_articles = service.get_notification_targets(batch_id)
        if not notify_articles:
            logger.warning("通知対象の記事が0件でした。処理を終了します。")
            status = "success"
            return  # notify_count は 0 のまま

        logger.info(f"最終通知件数: {len(notify_articles)}件")
        send_daily_email(notify_articles, batch_id)

        notify_count = len(notify_articles)
        status = "success"

    except Exception as e:
        logger.exception(f"Batch {batch_id} 致命的エラー: {e}")
        raise

    finally:
        # return / raise どちらのパスでも必ず実行される
        _finish_batch_safely(db_manager, batch_id, status, notify_count)


def _finish_batch_safely(
    db_manager: DatabaseManager,
    batch_id: int,
    status: str,
    notify_count: int,
) -> None:
    """finish_batch 自体の失敗を握りつぶさずログだけ残す。"""
    try:
        db_manager.finish_batch(batch_id, status, notify_count)
        logger.info(f"Batch {batch_id} 完了 (status={status}, count={notify_count})")
    except Exception as e:
        logger.error(f"finish_batch 失敗 (batch_id={batch_id}): {e}")


def main() -> None:
    logger.info("★★★ main 開始 ★★★")

    try:
        config.validate_config()
    except ConfigValidationError as e:
        logger.error(f"設定検証エラー: {e}")
        return

    with DatabaseManager() as db_manager:
        run_batch(db_manager)


if __name__ == "__main__":
    main()