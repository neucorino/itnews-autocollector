import config
import db
import logging

logger = logging.getLogger(__name__)

# DB保存
def save_articles(articles: list) -> None:
    """記事リストをDB保存の専門家（db.py）に丸投げする"""
    try:
        # まとめてドカンと保存！
        db.bulk_insert_articles(articles)
    except Exception as e:
        logger.error(f"保存に失敗しました。通知処理を中断します: {e}")
        # ここで処理を止めるか、リトライするかの判断ができる

# メール通知対象の記事をDBから取得
def get_notification_targets(target_count=config.MAX_NOTIFICATION_COUNT) -> list:
    # 1. まずは「今日」の重要な記事を狙い撃ちで取得
    today_articles = db.fetch_articles(
        limit=target_count, 
        min_importance=config.IMPORTANCE_THRESHOLD, 
        days_ago=config.RETENTION_DAYS_TODAY
        )

    targets = today_articles

    # 2. 足りない場合は「過去7日」から補填
    if len(targets) < target_count:
        needed = target_count - len(targets)
        # すでに取得済みのURLを除外するために全件多めに取ってからフィルタするか、
        # SQLで NOT IN を使うなどの工夫ができます
        weekly_articles = db.fetch_articles(
            limit=target_count, 
            min_importance=config.IMPORTANCE_THRESHOLD, 
            days_ago=config.RETENTION_DAYS_WEEKLY
            )
        
        existing_urls = {a["url"] for a in targets}
        extra = [a for a in weekly_articles if a["url"] not in existing_urls]
        
        targets = (targets + extra)[:target_count]

    logger.info(f"通知対象: {[a['title'] for a in targets]}")
    return targets