import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List
from src import config
from src import models 
from src import queries
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = str(config.DB_PATH)) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"DB接続を開始: {db_path}")
        self._create_tables()

    # ── context manager ──────────────────────────────────────

    def __enter__(self) -> "DatabaseManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """例外の有無に関わらずコネクションを閉じる。例外は呼び出し元に伝播させる。"""
        try:
            self.conn.close()
            logger.info("DB接続を閉じました")
        except Exception as e:
            logger.error(f"DB接続クローズ時にエラー: {e}")
        return None  # 例外を握りつぶさない（False と同義だが意図を明示）

    # ── セットアップ ──────────────────────────────────────────

    def _create_tables(self) -> None:
        """起動時に必要なテーブルをまとめて作成する（既存テーブルはスキップ）。"""
        ddl_list = (
            queries.CREATE_BATCHES,
            queries.CREATE_ARTICLES,
            queries.CREATE_ARTICLE_ANALYSES,
            queries.CREATE_ARTICLE_ANALYSES_UNIQUE_INDEX,
            queries.CREATE_RANKINGS,
        )
        with self.conn:
            for ddl in ddl_list:
                self.conn.execute(ddl)
        logger.info("テーブルの初期化が完了しました")

    # ── バッチ管理 ────────────────────────────────────────────

    def start_new_batch(self) -> int:
        """バッチ開始を記録し、払い出された batch_id を返す。"""
        params = {
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running",
        }
        try:
            with self.conn:
                res = self.conn.execute(queries.START_NEW_BATCH, params)
            batch_id = res.lastrowid
            logger.info(f"バッチ開始: batch_id={batch_id}")
            return batch_id
        except Exception as e:
            raise DatabaseError(f"バッチの開始に失敗しました: {e}") from e

    def finish_batch(self, batch_id: int, status: str, count: int) -> None:
        """バッチ終了ステータスを記録する。必ず呼ばれることでバッチの完全性を保証する。"""
        params = {
            "ended_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "new_articles_count": count,
            "id": batch_id,
        }
        try:
            with self.conn:
                self.conn.execute(queries.FINISH_BATCH, params)
            logger.info(f"バッチ完了: batch_id={batch_id} status={status} count={count}")
        except Exception as e:
            raise DatabaseError(f"バッチの終了に失敗しました: {e}") from e

    # ── 記事の一括保存 ──────────────────────────────────────────────────

    def bulk_insert_articles(self, articles: List[models.Article]) -> List[models.Article]:
        """記事を一括保存し、id を付与して返す。URL重複はスキップし既存idを取得する。"""
        with self.conn:
            for article in articles:
                cursor = self.conn.execute(queries.INSERT_ARTICLE, article.to_dict())
                # INSERT OR IGNORE でスキップされた場合、lastrowid は直前の INSERT の id のまま
                # 残るため rowcount で判定し、重複時は URL から正しい id を引く
                if cursor.rowcount > 0:
                    article.id = cursor.lastrowid
                else:
                    article.id = self._fetch_article_id_by_url(article.url)
        logger.info(f"{len(articles)}件の記事を保存しました")
        return articles

    def _fetch_article_id_by_url(self, url: str) -> int:
        """INSERT OR IGNORE でスキップされた記事の id を URL で引く。"""
        row = self.conn.execute(
            "SELECT id FROM articles WHERE url = ?", (url,)
        ).fetchone()
        if row is None:
            raise DatabaseError(f"記事が見つかりません: url={url}")
        return row[0]

    # ── 分析結果 ──────────────────────────────────────────────

    def bulk_insert_analyses(self, analyses: List[models.ArticleAnalysis]) -> None:
        """分析結果を一括保存する。analyzed_at が未設定の場合は現在時刻を補完する。"""
        now = datetime.now().isoformat()
        records = [
            {**a.to_dict(), "analyzed_at": a.to_dict().get("analyzed_at") or now}
            for a in analyses
        ]
        try:
            with self.conn:
                self.conn.executemany(queries.INSERT_ANALYSES, records)
            logger.info(f"{len(records)}件の分析結果を保存しました")
        except Exception as e:
            raise DatabaseError(f"分析結果の保存に失敗しました: {e}") from e

    # ── ランキング ────────────────────────────────────────────

    def bulk_insert_rankings(self, rankings: List[models.Ranking]) -> None:
        """ランキングを一括保存する。"""
        if not rankings:
            logger.warning("保存するランキングデータがありません")
            return
        records = [r.to_dict() for r in rankings]
        try:
            with self.conn:
                self.conn.executemany(queries.INSERT_RANKING, records)
            logger.info(f"{len(rankings)}件のランキングを保存しました")
        except Exception as e:
            raise DatabaseError(f"ランキングの保存に失敗しました: {e}") from e

    # ── 通知対象の取得 ─────────────────────────────────────────

    def fetch_notification_targets(
        self,
        batch_id: int,
        lookback_days: int = None, 
        limit: int = None, 
        min_importance: int = None
    ):
        
        limit = limit if limit is not None else getattr(config, 'NOTIFICATION_LIMIT', 5)
        lookback_days = lookback_days if lookback_days is not None else getattr(config, 'NOTIFICATION_LOOKBACK_DAYS', 7)
        min_importance = min_importance if min_importance is not None else getattr(config, 'IMPORTANCE_THRESHOLD', 6)

        sql = queries.GET_NOTIFICATION_TARGETS

        """重要度・期間フィルタを適用し、通知対象記事を取得する。"""
        params = {
            "batch_id": batch_id,
            "min_importance": min_importance,
            "lookback_days": lookback_days,
            "limit": limit,
        }
        try:
            with self.conn:
                rows = self.conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"通知対象の取得に失敗しました: {e}") from e

    # 通知対象の取得（API用）
    def get_news_from_db(self,params:dict):
        conn = sqlite3.connect(config.DB_PATH)
        # 辞書形式で結果を取得できるように設定
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 最新の10件を取得
            cursor.execute(queries.GET_NOTIFICATION_TARGETS, params)
            rows = cursor.fetchall()
            # Rowオブジェクトを辞書のリストに変換
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise e
        finally:
            conn.close()