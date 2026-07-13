import logging
from src.db import DatabaseManager
from src.models import UserPreference, ArticleFeedback
from src import queries
from datetime import datetime

logger = logging.getLogger(__name__)
db = DatabaseManager()

def save_user_preferences(pref: UserPreference):
    """ユーザーの興味分野を保存する"""
    with db.get_connection() as conn:
        try:
            # 安全のため、一度削除して最新のみを残す（またはUPSERTを使う）
            conn.execute(queries.DELETE_PREFERENCES, {"user_id": pref.user_id})
            conn.execute(queries.INSERT_PREFERENCE, pref.to_dict())
            conn.commit()
            logger.info(f"User Preference saved: user={pref.user_id}, category={pref.category}")
        except Exception as e:
            logger.error(f"User Preference save failed: {e}")
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
            conn.execute(queries.INSERT_FEEDBACK, feedback.to_dict())
            conn.commit()
            logger.info(f"Article Feedback saved: article={feedback.article_id}, user={feedback.user_id}")
        except Exception as e:
            logger.error(f"Article Feedback save failed: {e}")
            raise