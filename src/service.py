from typing import List, Dict, Any, Optional
from src import config
from src import crud
from src.db import DatabaseManager
from src import rss_fetcher
from src import gemini_analyzer
from src.ranking import RankingGenerator
from src.models import Article, ArticleAnalysis
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, db_manager: "DatabaseManager") -> None:
        self.db = db_manager
        self.ranking = RankingGenerator(db_manager)

    # RSSからデータを受け取ってDBに保存する処理
    def process_new_articles(self, rss_url: str, source: str) -> List[Article]:
        # 1. まずRSSから記事を全件フェッチする
        articles = rss_fetcher.fetch_rss(rss_url, source)
        
        # 2. 💡 config.SOURCE_FETCH_LIMIT (20件) を使って、ソースごとに最大件数を制限する
        limit = getattr(config, "SOURCE_FETCH_LIMIT", 20)
        if articles:
            articles = articles[:limit]
            
        logger.info(f"[{source}] から最大 {len(articles)} 件の記事をDBに保存します。")
        return crud.bulk_insert_articles(self.db, articles)


    def process_new_analyses(self, articles: List[Article], batch_id: int) -> List[ArticleAnalysis]:
        # Geminiで分析して、分析結果を辞書で受け取る
        analyzed_articles = gemini_analyzer.analyze_articles(articles, batch_id)
        logger.info(f"分析結果をDBに保存しました。: {len(analyzed_articles)}件")
        return crud.bulk_insert_analyses(self.db, analyzed_articles)


    def process_new_rankings(self, batch_id: int) -> bool:
        # ランキングを生成してDBに保存する
        ranked_articles = self.ranking.generate_rankings(batch_id)

        if ranked_articles is None:
            logger.exception(f"ランキングの生成に失敗しました（batch_id: {batch_id}）")
            return False
        
        if len(ranked_articles) == 0:
            logger.warning("ランキング対象の記事がありませんでした。")
            return False

        logger.info(f"ランキングをDBに保存しました。: {len(ranked_articles)}件")
        crud.bulk_insert_rankings(self.db, ranked_articles)
        return True

    # 通知対象の絞り込みと取得
    def get_notification_targets(
            self, 
            batch_id: int, 
            lookback_days: int = None, 
            limit: int = None, 
            min_importance: int = None
        ) -> List[Dict[str, Any]]:
        """
        設定値に基づいて通知対象を絞り込み、リストを返す。
        過去N日・重要度しきい値以上から、重要度順で最大M件。
        """
        targets = crud.fetch_notification_targets(
            self.db,
            batch_id,
            min_importance=min_importance if min_importance is not None else config.IMPORTANCE_THRESHOLD,
            lookback_days=lookback_days if lookback_days is not None else config.NOTIFICATION_LOOKBACK_DAYS,
            limit=limit if limit is not None else config.NOTIFICATION_LIMIT,
        )
        for row in targets:
            logger.info(f"title: {row['title']}, ai_summary: {row['ai_summary'][:30]}")

        if not targets:
            logger.info(
                f"通知対象の記事はありませんでした（過去{config.NOTIFICATION_LOOKBACK_DAYS}日・重要度{config.IMPORTANCE_THRESHOLD}以上・最大{config.NOTIFICATION_LIMIT}件）。"
            )
        else:
            titles = [t["title"] for t in targets]
            logger.info(
                f"通知対象確定: {len(targets)}件（過去{config.NOTIFICATION_LOOKBACK_DAYS}日・重要度{config.IMPORTANCE_THRESHOLD}以上・最大{config.NOTIFICATION_LIMIT}件） / {titles}"
            )
        return targets