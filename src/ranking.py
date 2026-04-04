import db
from models import Ranking
import config
import logging

logger = logging.getLogger(__name__)

# 過去7日間に公開された記事の中から、重要度の高い順にトップ10件を取得する
GET_RANKED_ARTICLES_QUERY = """
    SELECT 
        articles.id,
        articles.title,
        articles.published_at,
        article_analyses.importance,
        article_analyses.id AS analyses_id
    FROM articles
    INNER JOIN article_analyses ON articles.id = article_analyses.article_id
    WHERE articles.published_at >= datetime('now', '-7 days')
    ORDER BY article_analyses.importance DESC, articles.published_at DESC
    LIMIT 10
"""

def generate_rankings(batch_id):
    """重要度の高い記事をランキング形式で取得"""
    db_manager = db.DatabaseManager()
    ranked_articles = db_manager.conn.execute(GET_RANKED_ARTICLES_QUERY).fetchall()

    rankings_to_save = []
    for rank, article in enumerate(ranked_articles, start=1):
        #current_article_id = getattr(article, 'id', None)
       
        rankings= Ranking(
            article_id=article[0],
            analyses_id=article[4],
            batch_id=batch_id,
            rank=rank
        )
        rankings_to_save.append(rankings)

    logger.info(f"ランキングを生成してDBに保存しました。バッチID: {batch_id}")
    return rankings_to_save