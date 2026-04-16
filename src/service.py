import config
import db
import rss_fetcher
import gemini_analyzer
from ranking import RankingGenerator
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, db_manager):
        self.db = db_manager
        self.ranking = RankingGenerator(db_manager)

    # RSSからデータを受け取ってDBに保存する処理
    def process_new_articles(self, rss_url, source):
        articles = rss_fetcher.fetch_rss(rss_url, source)
        logger.info(f"記事をDBに保存しました。: {len(articles)}件")
        return self.db.bulk_insert_articles(articles)


    def process_new_analyses(self, articles, batch_id):
        # Geminiで分析して、分析結果を辞書で受け取る
        analyzed_articles = gemini_analyzer.analyze_articles(articles, batch_id)
        logger.info(f"分析結果をDBに保存しました。: {len(analyzed_articles)}件")
        return self.db.bulk_insert_analyses(analyzed_articles)


    def process_new_rankings(self, batch_id):
        # ランキングを生成してDBに保存する
        ranked_articles = self.ranking.generate_rankings(batch_id)

        if ranked_articles is None:
            logger.exception(f"ランキングの生成に失敗しました（batch_id: {batch_id}）")
            return False
        
        if len(ranked_articles) == 0:
            logger.warning("ランキング対象の記事がありませんでした。")
            return False

        logger.info(f"ランキングをDBに保存しました。: {len(ranked_articles)}件")
        return self.db.bulk_insert_rankings(ranked_articles)


    def get_notification_targets(self, batch_id:int) -> list:
        """
        設定値に基づいて通知対象を絞り込み、リストを返す。
        過去N日・重要度しきい値以上から、重要度順で最大M件。
        """
        batch_id = batch_id
        threshold = getattr(config, "IMPORTANCE_THRESHOLD", 7)
        lookback = getattr(config, "NOTIFICATION_LOOKBACK_DAYS", 7)
        max_count = getattr(config, "MAX_NOTIFICATION_COUNT", 5)

        targets = self.db.fetch_notification_targets(
            batch_id,
            min_importance=threshold,
            lookback_days=lookback,
            limit=max_count,
        )
        for row in targets:
            logger.info(f"title: {row['title']}, ai_summary: {row['ai_summary'][:30]}")

        if not targets:
            logger.info(
                f"通知対象の記事はありませんでした（過去{lookback}日・重要度{threshold}以上・最大{max_count}件）。"
            )
        else:
            titles = [t["title"] for t in targets]
            logger.info(
                f"通知対象確定: {len(targets)}件（過去{lookback}日・重要度{threshold}以上・最大{max_count}件） / {titles}"
            )
        return targets