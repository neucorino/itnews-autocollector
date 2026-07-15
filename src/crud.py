import logging
import sqlite3
from datetime import datetime
from typing import List

from src import config
from src import queries
from src.db import DatabaseManager
from src.exceptions import DatabaseError
from src.models import (
    Article,
    ArticleAnalysis,
    ArticleFeedback,
    Ranking,
    UserPreference,
)

logger = logging.getLogger(__name__)
db = DatabaseManager()


# ── 記事の一括保存 ──────────────────────────────────────────────────

def bulk_insert_articles(db: DatabaseManager, articles: List[Article]) -> List[Article]:
    """記事を一括保存し、id を付与して返す。URL重複はスキップし既存idを取得する。"""
    with db.get_connection() as conn:
        for article in articles:
            cursor = conn.execute(queries.INSERT_ARTICLE, article.to_dict())
            # INSERT OR IGNORE でスキップされた場合、lastrowid は直前の INSERT の id のまま
            # 残るため rowcount で判定し、重複時は URL から正しい id を引く
            if cursor.rowcount > 0:
                article.id = cursor.lastrowid
            else:
                article.id = _fetch_article_id_by_url(conn, article.url)
    logger.info(f"{len(articles)}件の記事を保存しました")
    return articles


def _fetch_article_id_by_url(conn: sqlite3.Connection, url: str) -> int:
    """INSERT OR IGNORE でスキップされた記事の id を URL で引く。"""
    row = conn.execute(
        "SELECT id FROM articles WHERE url = ?", (url,)
    ).fetchone()
    if row is None:
        raise DatabaseError(f"記事が見つかりません: url={url}")
    return row[0]


# ── 分析結果 ──────────────────────────────────────────────

def bulk_insert_analyses(db: DatabaseManager, analyses: List[ArticleAnalysis]) -> None:
    """分析結果を一括保存する。analyzed_at が未設定の場合は現在時刻を補完する。"""
    now = datetime.now().isoformat()
    records = [
        {**a.to_dict(), "analyzed_at": a.to_dict().get("analyzed_at") or now}
        for a in analyses
    ]
    try:
        with db.get_connection() as conn:
            conn.executemany(queries.INSERT_ANALYSES, records)
        logger.info(f"{len(records)}件の分析結果を保存しました")
    except Exception as e:
        raise DatabaseError(f"分析結果の保存に失敗しました: {e}") from e


# ── ランキング ────────────────────────────────────────────

def bulk_insert_rankings(db: DatabaseManager, rankings: List[Ranking]) -> None:
    """ランキングを一括保存する。"""
    if not rankings:
        logger.warning("保存するランキングデータがありません")
        return
    records = [r.to_dict() for r in rankings]
    try:
        with db.get_connection() as conn:
            conn.executemany(queries.INSERT_RANKING, records)
        logger.info(f"{len(rankings)}件のランキングを保存しました")
    except Exception as e:
        raise DatabaseError(f"ランキングの保存に失敗しました: {e}") from e


# ── 通知対象の取得 ─────────────────────────────────────────

def fetch_notification_targets(
    db: DatabaseManager,
    batch_id: int,
    lookback_days: int = None,
    limit: int = None,
    min_importance: int = None,
):
    """重要度・期間フィルタを適用し、通知対象記事を取得する。"""
    limit = limit if limit is not None else getattr(config, 'NOTIFICATION_LIMIT', 5)
    lookback_days = lookback_days if lookback_days is not None else getattr(config, 'NOTIFICATION_LOOKBACK_DAYS', 7)
    min_importance = min_importance if min_importance is not None else getattr(config, 'IMPORTANCE_THRESHOLD', 6)

    params = {
        "batch_id": batch_id,
        "min_importance": min_importance,
        "lookback_days": lookback_days,
        "limit": limit,
    }
    try:
        with db.get_connection() as conn:
            rows = conn.execute(queries.GET_NOTIFICATION_TARGETS, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise DatabaseError(f"通知対象の取得に失敗しました: {e}") from e


def get_news_from_db(db: DatabaseManager, params: dict):
    """通知対象の取得（API用）"""
    try:
        with db.get_connection() as conn:
            rows = conn.execute(queries.GET_NOTIFICATION_TARGETS, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise


def get_user_preferences(db: DatabaseManager, user_id: int) -> List[UserPreference]:
    """
    現在のユーザー（user_id）の興味分野リストを取得する(画面の初期表示に使用)
    """
    with db.get_connection() as conn:
        try:
            rows = conn.execute(queries.GET_PREFERENCES, {"user_id": user_id}).fetchall()

            #取得データをUserPreferenceオブジェクトに変換
            return [
                UserPreference(
                    user_id=row['user_id'],
                    category=row['category'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get preferences for user {user_id}: {e}")
            raise


def update_user_preferences_list(
    db: DatabaseManager, user_id: int, categories: List[str]
) -> None:
    """
    興味分野を一括保存（既存は全削除してから新規保存）
    """
    now = datetime.now().isoformat()
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, user_id)
            conn.execute(queries.DELETE_PREFERENCES, {"user_id": user_id})
            for category in categories:
                conn.execute(
                    queries.INSERT_PREFERENCE,
                    {"user_id": user_id, "category": category, "updated_at": now},
                )
            conn.commit()
            logger.info(f"User preferences updated for user {user_id}: {categories}")
        except Exception as e:
            logger.error(f"Failed to update preferences for user {user_id}: {e}")
            raise


def save_user_preferences(db: DatabaseManager, pref: UserPreference) -> None:
    """
    興味分野を1件保存（既存は全削除してから新規保存）
    """
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, pref.user_id)  # ユーザーが存在しなければ追加
            conn.execute(queries.DELETE_PREFERENCES, {"user_id": pref.user_id})
            conn.execute(queries.INSERT_PREFERENCE, pref.to_dict())
            conn.commit()
            logger.info(f"User preferences updated for user {pref.user_id}: {pref.category}")
        except Exception as e:
            logger.error(f"Failed to update preferences for user {pref.user_id}: {e}")
            raise


def add_user_preference(db: DatabaseManager, pref: UserPreference) -> None:
    """
    興味分野を1件追加（既存は消さずに追加）
    """
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, pref.user_id)
            conn.execute(queries.INSERT_PREFERENCE, pref.to_dict())
            conn.commit()
            logger.info(f"User preference added for user {pref.user_id}: {pref.category}")
        except Exception as e:
            logger.error(f"Failed to add preference for user {pref.user_id}: {e}")
            raise


def _ensure_user(conn, user_id: int):
    """
    サブ関数: user_idがusersテーブルに存在しなければ追加（なければスキップ）
    """
    now = datetime.now().isoformat()
    conn.execute(queries.ENSURE_USER, {"id": user_id, "created_at": now})


def save_article_feedback(db: DatabaseManager, feedback: ArticleFeedback):
    """いいね👍を保存する"""
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, feedback.user_id)
            conn.execute(queries.INSERT_FEEDBACK, feedback.to_dict())
            conn.commit()
            logger.info(f"Article Feedback saved: article={feedback.article_id}, user={feedback.user_id}")
        except Exception as e:
            logger.error(f"Article Feedback save failed: {e}")
            raise