from typing import List, Dict, Any, Optional
import sqlite3
import models
from datetime import datetime
import config
from exceptions import DatabaseError
import queries
import logging

logger = logging.getLogger(__name__)



# データベース管理クラス
class DatabaseManager:
    # __init__ 
    def __init__(self, db_path: str = str(config.DB_PATH)) -> None:
        # sqlite3はファイルパスを指定して接続
        self.conn = sqlite3.connect(db_path)
        # sqlite3で辞書形式でデータを取れるようにする設定
        self.conn.row_factory = sqlite3.Row
        logger.info(f"DB接続を開始: {db_path}")
        self.create_tables() # インスタンス化した時にテーブルがなければ作る
    
    def __enter__(self) -> "DatabaseManager":
        """context manager entry point"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """context manager exit point - コネクション安全にクローズ"""
        try:
            self.conn.close()
            logger.info("DB接続を閉じました")
        except Exception as e:
            logger.error(f"DB接続クローズ時にエラー: {e}")
        
        # 例外を伝播させる
        if exc_type is not None:
            return False
        return None
    
    def close(self) -> None:
        """明示的にコネクションを閉じる"""
        if self.conn:
            self.conn.close()
            logger.info("DB接続を明示的に閉じました")
    
    
    # テーブルを作成するメソッド（操作）
    def create_tables(self) -> None:
        """テーブルが存在しない場合に作成する。"""
        with self.conn:
            for ddl in (queries.CREATE_BATCHES, queries.CREATE_ARTICLES, queries.CREATE_ARTICLE_ANALYSES, queries.CREATE_RANKINGS):
                self.conn.execute(ddl)
        logger.info("テーブルを作成しました。")
    

    # 記事リストに一括でinsertするメソッド（操作）
    def bulk_insert_articles(self, articles_list: List[models.Article]) -> List[models.Article]:
        """記事リストを一括でinsertする。URLが重複する場合はスキップ。"""
        for article in articles_list:
            cursor = self.conn.execute(queries.INSERT_ARTICLE, article.to_dict())
            self.conn.commit()
            
            if cursor.lastrowid:
                article.id = cursor.lastrowid  # 新規保存された場合
            else:
                # INSERT OR IGNOREでスキップされた場合、URLで既存のidを取得
                row = self.conn.execute(
                    "SELECT id FROM articles WHERE url = ?", (article.url,) 
                ).fetchone()
                if row:
                    article.id = row[0] 
        logger.info(f"{len(articles_list)}件の記事を一括処理しました。")
        return articles_list  # idが入った状態で返す


    # 分析結果を一括でinsertするメソッド（操作）
    def bulk_insert_analyses(self, analyses_list: List[models.ArticleAnalysis]) -> None:
        records = []
        for a in analyses_list:
            d = a.to_dict()
            if 'analyzed_at' not in d or d['analyzed_at'] is None:
                d['analyzed_at'] = datetime.now().isoformat()
            records.append(d)
    
        try:
            with self.conn:
                self.conn.executemany(queries.INSERT_ANALYSES, records)
            logger.info(f"{len(records)}件保存成功")
        except Exception as e:
            logger.exception(f"INSERT失敗")
            raise DatabaseError(f"分析結果の保存に失敗しました: {e}") from e
    
    
    # ランキングを一括でinsertするメソッド（操作）
    def bulk_insert_rankings(self, rankings_list: List[models.Ranking]) -> None:
        if not rankings_list:
            logger.warning("保存するランキングデータがありません。")
            return
        records = [a.to_dict() for a in rankings_list]
        try:
            with self.conn:
                self.conn.executemany(queries.INSERT_RANKING, records)
            logger.info(f"{len(rankings_list)}件のランキングを一括処理しました。")
        except Exception as e:
            logger.exception(f"ランキング保存失敗")
            raise DatabaseError(f"ランキングの保存に失敗しました: {e}") from e
    

    # バッチ開始を記録するメソッド（操作）
    def start_new_batch(self) -> int:
        logger.info("バッチを開始します...")
        try:
            params = {
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "running"
            }
            res = self.conn.execute(queries.START_NEW_BATCH, params)
            self.conn.commit()
            batch_id = res.lastrowid
            logger.info(f"バッチ開始: batch_id={batch_id}")
            return batch_id
        except Exception as e:
            logger.exception(f"バッチ開始に失敗")
            raise DatabaseError(f"バッチの開始に失敗しました: {e}") from e


    # バッチ終了を記録するメソッド（操作）
    def finish_batch(self, batch_id: int, status: str, count: int) -> None:
        """バッチの結果を更新する。バッチ完全性を確保するため、
        最後に必ずこのメソッドが呼ばれて status を記録することが重要。
        """
        try:
            params = {
                "ended_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "new_articles_count": count,
                "id": batch_id
            }
            with self.conn:
                self.conn.execute(queries.FINISH_BATCH, params)
            logger.info(f"✅ バッチID:{batch_id} を完了 (status={status}, articles={count})")
        except Exception as e:
            logger.exception(f"バッチ終了に失敗 (batch_id={batch_id})")
            raise DatabaseError(f"バッチの終了に失敗しました: {e}") from e


    # 通知対象を取得するメソッド（操作）
    def fetch_notification_targets(
        self,
        batch_id: int,
        min_importance: int = config.IMPORTANCE_THRESHOLD,
        lookback_days: int = config.NOTIFICATION_LOOKBACK_DAYS,
        limit: int = config.MAX_NOTIFICATION_COUNT,
        ) -> List[Dict[str, Any]]:
        """過去N日・重要度しきい値以上を満たす記事を、記事ごとに1行（代表の分析）で取得する。"""
        params = {
            "batch_id": batch_id,
            "min_importance": min_importance,
            "limit": int(limit),
        }
        try:
            with self.conn:
                rows = self.conn.execute(queries.GET_NOTIFICATION_TARGETS, params).fetchall()
            if not rows:
                return [] # 0件なら空リストを返す
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"通知対象の取得に失敗: {e}")
            raise DatabaseError(f"通知対象の取得に失敗しました: {e}") from e