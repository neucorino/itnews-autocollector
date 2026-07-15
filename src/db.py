import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
from src import config
from src import queries
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = str(config.DB_PATH)) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON") #外部キー制約を有効にする(SQLiteの設定)
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

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """CRUD用に接続を返す。成功時は commit、失敗時は rollback する。"""
        self.conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield self.conn
        except Exception:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    # ── セットアップ ──────────────────────────────────────────

    def _create_tables(self) -> None:
        """起動時に必要なテーブルをまとめて作成する（既存テーブルはスキップ）。"""
        ddl_list = (
            queries.CREATE_BATCHES,
            queries.CREATE_ARTICLES,
            queries.CREATE_ARTICLE_ANALYSES,
            queries.CREATE_ARTICLE_ANALYSES_UNIQUE_INDEX,
            queries.CREATE_RANKINGS,
            queries.CREATE_USERS,
            queries.CREATE_USER_PREFERENCES,
            queries.CREATE_ARTICLE_FEEDBACKS,
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
