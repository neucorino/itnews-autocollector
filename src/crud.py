import logging
from datetime import datetime

from src.db import DatabaseManager
from src.models import UserPreference, ArticleFeedback
from src import queries

logger = logging.getLogger(__name__)
db = DatabaseManager()


def _ensure_user(conn, user_id: int) -> None:
    """外部キー制約のため、users に該当行が無ければ作成する。"""
    conn.execute(
        queries.ENSURE_USER,
        {"id": user_id, "created_at": datetime.now().isoformat()},
    )


def save_user_preferences(pref: UserPreference):
    """ユーザーの興味分野を保存する"""
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, pref.user_id)
            # 安全のため、一度削除して最新のみを残す（またはUPSERTを使う）
            conn.execute(queries.DELETE_PREFERENCES, {"user_id": pref.user_id})
            conn.execute(queries.INSERT_PREFERENCE, pref.to_dict())
            conn.commit()
            logger.info(f"User Preference saved: user={pref.user_id}, category={pref.category}")
        except Exception as e:
            logger.error(f"User Preference save failed: {e}")
            raise


def update_user_preferences_list(user_id: int, categories: list[str]):
    """ユーザーの興味分野を一括で置き換える"""
    with db.get_connection() as conn:
        try:
            _ensure_user(conn, user_id)
            conn.execute(queries.DELETE_PREFERENCES, {"user_id": user_id})
            for category in categories:
                pref = UserPreference(user_id=user_id, category=category)
                conn.execute(queries.INSERT_PREFERENCE, pref.to_dict())
            conn.commit()
            logger.info(f"User Preferences updated: user={user_id}, categories={categories}")
        except Exception as e:
            logger.error(f"User Preferences update failed: {e}")
            raise


def get_user_preferences(user_id: int):
    """ユーザーの興味分野を取得する"""
    with db.get_connection() as conn:
        cursor = conn.execute(queries.GET_PREFERENCES, {"user_id": user_id})
        return [row["category"] for row in cursor.fetchall()]


def save_article_feedback(feedback: ArticleFeedback):
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
