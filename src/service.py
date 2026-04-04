import config
import db
import rss_fetcher
import gemini_analyzer
import ranking
import logging

logger = logging.getLogger(__name__)

db_manager = db.DatabaseManager()

# RSSからデータを受け取ってDBに保存する処理
def process_new_articles(rss_url, source):
    articles = rss_fetcher.fetch_rss(rss_url, source)
    # db_manager.bulk_insert_articles(articles)
    return db_manager.bulk_insert_articles(articles) 

def process_new_analyses(articles,batch_id):
    # Geminiで分析して、分析結果を辞書で受け取る
    analyzed_articles = gemini_analyzer.analyze_articles(articles, batch_id)
    # 分析結果をDBに保存する
    # db_manager.bulk_insert_analyses(analyzed_articles)
    return db_manager.bulk_insert_analyses(analyzed_articles)

def process_new_rankings(batch_id):
    # ランキングを生成してDBに保存する
    ranked_articles = ranking.generate_rankings(batch_id)

    if ranked_articles is None:
        logger.error(f"ランキングの生成に失敗しました（batch_id: {batch_id}）")
        return False
    
    if len(ranked_articles) == 0:
        logger.warning("ランキング対象の記事がありませんでした。")
        return False

    #db_manager.bulk_insert_rankings(ranked_articles)
    return db_manager.bulk_insert_rankings(ranked_articles)

def get_notification_targets() -> list:
    """
    設定値に基づいて通知対象を絞り込み、リストを返す
    """
    # 1. 設定ファイルからしきい値を取得
    threshold = getattr(config, 'IMPORTANCE_THRESHOLD', 7)
    
    # 2. DBマネージャーにデータ取得を依頼
    targets = db_manager.fetch_notification_targets(threshold)
    
    # 3. ログ出力などの加工処理
    if not targets:
        logger.info("通知対象の記事はありませんでした。")
    else:
        titles = [t['title'] for t in targets]
        logger.info(f"通知対象確定: {len(targets)}件 / {titles}")
        
    return targets