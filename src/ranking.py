import db
from models import Ranking
import config
import logging

logger = logging.getLogger(__name__)

# 修正版：最新のランキング（batch_idが最大のもの）に紐づくデータだけを取る
# 修正後のクエリ
GET_RANKED_ARTICLES_QUERY = """
    SELECT 
        articles.id,
        articles.title,
        articles.published_at,
        article_analyses.importance,
        article_analyses.ai_summary, -- 👈 これを追加！
        article_analyses.id AS analyses_id
    FROM articles
    INNER JOIN article_analyses ON articles.id = article_analyses.article_id
    WHERE articles.published_at >= datetime('now', ?)
    ORDER BY article_analyses.importance DESC, articles.published_at DESC
    LIMIT 10
"""


def generate_rankings(batch_id):
    """重要度の高い記事をランキング形式で取得"""
    db_manager = db.DatabaseManager()
    since = f"-{config.NOTIFICATION_LOOKBACK_DAYS} days"
    ranked_articles = db_manager.conn.execute(
        GET_RANKED_ARTICLES_QUERY, (since,)
    ).fetchall()

    rankings_to_save = []
    for rank, article in enumerate(ranked_articles, start=1):
        #current_article_id = getattr(article, 'id', None)
       
        rankings= Ranking(
            article_id=article['id'],
            analyses_id=article['analyses_id'],
            batch_id=batch_id,
            rank=rank
        )
        rankings_to_save.append(rankings)

    logger.info(f"ランキングを生成してDBに保存しました。バッチID: {batch_id}")
    return rankings_to_save