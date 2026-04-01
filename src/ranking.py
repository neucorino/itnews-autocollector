import db
import config
import logging

logger = logging.getLogger(__name__)

# SQL を定数として定義
GET_RANKED_ARTICLES_QUERY = """
    SELECT 
        articles.id,
        articles.title,
        articles.published_at,
        article_analyses.importance
    FROM articles
    JOIN article_analyses ON articles.id = article_analyses.article_id
    WHERE articles.published_at >= datetime('now', '-7 days')
    ORDER BY article_analyses.importance DESC, articles.published_at DESC
    LIMIT 10
"""

def generete_rankings(batch_id):
    """重要度の高い記事をランキング形式で取得し、DBに保存する"""
    def generate_rankings(batch_id):
    """重要度の高い記事をランキング形式で取得し、DBに保存する"""
    db_manager = db.DatabaseManager()
    ranked_articles = db_manager.conn.execute(GET_RANKED_ARTICLES_QUERY).fetchall()

    rankings_to_save = []
    for rank, article in enumerate(ranked_articles, start=1):
        rankings_to_save.append((
            article["id"],           # article_id
            article["analysis_id"],  # analysis_id
            batch_id,
            rank,
            datetime.datetime.now().isoformat()  # created_at
        ))

    # ランキングをDBに保存
    db_manager.bulk_insert_rankings(rankings_to_save)
    logger.info(f"ランキングを生成してDBに保存しました。バッチID: {batch_id}")