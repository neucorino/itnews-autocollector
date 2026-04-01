import config
import db
import gemini_analyzer
import logging

logger = logging.getLogger(__name__)

db_manager = DatabaseManager()

# RSSからデータを受け取ってリストを作る
def process_new_articles(rss_data):
    # データを (値, 値, ...) のタプルのリストに変換する
    data_to_save = [
        (item.title, item.url, item.source, item.summary, item.published_at)
        for item in rss_data
    ]
    
    # 一括保存！
    db_manager.bulk_insert_articles(data_to_save)

def process_new_analyses(articles,batch_id):
    # Geminiで分析して、分析結果を辞書で受け取る
    analyzed_articles = gemini_analyzer.analyze_articles(articles, batch_id)
    
    # 分析結果をDBに保存する
    db_manager.bulk_insert_article_analyses(analyzed_articles)

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