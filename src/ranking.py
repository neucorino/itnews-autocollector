from typing import List
from src.db import DatabaseManager
from src.models import Ranking
from src import config
from src import queries
import logging

logger = logging.getLogger(__name__)

class RankingGenerator:
    def __init__(self, db_manager: "DatabaseManager") -> None:
        self.db = db_manager

    def generate_rankings(self, batch_id: int, lookback_days: int = config.NOTIFICATION_LOOKBACK_DAYS) -> List[Ranking]:
        """重要度の高い記事をランキング形式で取得"""
        
        # SQL文のプレースホルダー名（キー）と config の設定値を合わせる
        params = {
            "batch_id": batch_id,
            "lookback_days": lookback_days,
            "ranking_limit": getattr(config, 'RANKING_LIMIT', 10) # 確実に10が渡るようにする
        }
        
        # paramsを一緒に渡すことで、SQLの :ranking_limit に 10 がカチッと入る！
        ranked_articles = self.db.conn.execute(
            queries.GET_RANKED_ARTICLES_DYNAMIC, params
        ).fetchall()

        rankings_to_save = []
        for rank, article in enumerate(ranked_articles, start=1):
            rankings = Ranking(
                article_id=article['article_id'],
                analyses_id=article['analyses_id'],
                batch_id=batch_id,
                rank=rank
            )
            rankings_to_save.append(rankings)

        logger.info(f"ランキングを生成してDBに保存しました。バッチID: {batch_id}")
        return rankings_to_save