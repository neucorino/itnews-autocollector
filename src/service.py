import config
import db
import rss_fetcher
import gemini_analyzer
import logging

logger = logging.getLogger(__name__)

db_manager = db.DatabaseManager()

# RSSからデータを受け取ってDBに保存する処理
def process_new_articles(url, source_name):
    articles = rss_fetcher.fetch_rss(url, source_name)
    db_manager.bulk_insert_articles(articles)

def process_new_analyses(articles,batch_id):
    # Geminiで分析して、分析結果を辞書で受け取る
    analyzed_articles = gemini_analyzer.analyze_articles(articles, batch_id)
    return db_manager.bulk_insert_article_analyses(analyzed_articles)

    # 分析結果をDBに保存する
    db_manager.bulk_insert_article_analyses(analyzed_articles)

def process_new_rankings(batch_id):
    # ランキングを生成してDBに保存する
    ranked_articles = ranking.generate_rankings(batch_id)
    return db_manager.bulk_insert_rankings(ranked_articles)

    db_manager.bulk_insert_rankings(ranked_articles)

def get_notification_targets(min_importance=config.IMPORTANCE_THRESHOLD) -> list:
    """
    rankingsテーブルから通知対象を絞り込む
    """
    targets = db_manager.get_notification_targets(min_importance)
    
    logger.info(f"通知対象: {len(targets)}件 / {[a['title'] for a in targets]}")
    return targets