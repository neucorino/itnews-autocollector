from typing import List, Dict, Any
from src.my_utils import send_gmail
from src.service import NewsService
from datetime import datetime
from src import config
from src import constants
from src.exceptions import EmailSendError
import logging

logger = logging.getLogger(__name__)

def build_email_body(articles: List[Dict[str, Any]]) -> str:
    """ランキング形式のメール本文を組み立てる"""

    # 上位5件に制限
    top_articles = articles[:5]

    lines = [
        f"🧠 ITニュースダイジェスト（直近{config.NOTIFICATION_LOOKBACK_DAYS}日）",
        "",
        "---",
        "",
    ]

    for i, a in enumerate(top_articles):
        rank = constants.EMAIL_RANK_EMOJIS[i] if i < len(constants.EMAIL_RANK_EMOJIS) else "📌"

        summary = a["ai_summary"].replace("\n", " ")
        
        published = datetime.strptime(
            a["published_at"],
            "%Y-%m-%d %H:%M:%S"
            )

        # メール本文に追加
        lines += [
            f"{rank}{i+1}位（重要度: {a['importance']}/スコア:{a['rank_score']:.2f}）",
            f"📅 公開日: {published.strftime('%Y-%m-%d %H:%M')}",
            f"{a['title']}",
            f"→ {summary}",
            f"→ {a['url']}",
            constants.EMAIL_SEPARATOR,
            "",
        ]

    # 傾向
    lines += [
        constants.EMAIL_TREND_SECTION_TITLE,
    ] + constants.EMAIL_TREND_ITEMS

    return "\n".join(lines)


def send_daily_email(notify_articles: List[Dict[str, Any]], batch_id: int) -> None:
    """毎日決まった時間に呼び出される関数。重要記事をメールで送信する。"""
    if not notify_articles:
        logger.info("重要記事なし。メールは送信しません。")
        return

    subject = (
        f"【ITニュース】過去{config.NOTIFICATION_LOOKBACK_DAYS}日・TOP{config.NOTIFICATION_LIMIT} "
        f"{len(notify_articles)} 件 ({datetime.now().strftime('%Y-%m-%d')})"
    )
    body = build_email_body(notify_articles)

    try:
        send_gmail(subject=subject, body=body)
        logger.info(f"メール送信完了: {len(notify_articles)} 件の重要記事")
    except EmailSendError as e:
        logger.exception(f"メール送信に失敗しました")
        raise
