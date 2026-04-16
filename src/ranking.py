import db
from models import Ranking
import config
import logging

logger = logging.getLogger(__name__)

# 最新のAI分析結果を参照し重要度が高い順ぬTOP10を抽出する
GET_RANKED_ARTICLES_QUERY = """
    SELECT 
        a.id AS article_id, 
        aa.id AS analyses_id,
        aa.importance
    FROM articles a
    INNER JOIN article_analyses aa ON a.id = aa.article_id
    -- 「記事ごとの最新の分析レコードID」のリストを作る
    WHERE aa.id IN (
        SELECT MAX(id)
        FROM article_analyses 
        GROUP BY article_id
    )
    ORDER BY aa.importance DESC, a.published_at DESC
    LIMIT 10
"""

class RankingGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def generate_rankings(self, batch_id: int):
        """重要度の高い記事をランキング形式で取得"""
        ranked_articles = self.db.conn.execute(
            GET_RANKED_ARTICLES_QUERY
        ).fetchall()

        rankings_to_save = []
        for rank, article in enumerate(ranked_articles, start=1):
        
            rankings= Ranking(
                article_id=article['article_id'],
                analyses_id=article['analyses_id'],
                batch_id=batch_id,
                rank=rank
            )
            rankings_to_save.append(rankings)

        logger.info(f"ランキングを生成してDBに保存しました。バッチID: {batch_id}")
        return rankings_to_save