import config
from db import insert_article, get_today_important, get_weekly_important
import logging

logger = logging.getLogger(__name__)

# DB保存
def save_articles(articles: list) -> None:
    """記事リストをDBに一括保存する。"""
    for article in articles:
        insert_article(article)
        logger.info(f"DB保存: {article.title} (重要度: {article.importance})")


# 通知対象の取得（DB保存後に呼び出す）
def get_notification_targets(target_count= 5):
    today_articles = get_today_important()

    if len(today_articles) >= target_count:
        targets = today_articles[:target_count]

    elif len(today_articles) > 0:
        weekly_articles = get_weekly_important()

        urls = {a["url"] for a in today_articles}
        extra = [a for a in weekly_articles if a["url"] not in urls]

        targets = (today_articles + extra)[:target_count]

    else:
        weekly_articles = get_weekly_important()

        if weekly_articles:
            targets = weekly_articles[:target_count]
        else:
            targets = []

    logger.info(f"通知対象: {[a['title'] for a in targets]}")
    return targets