from my_utils import send_gmail
from service import get_notification_targets
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

def build_email_body(articles):
    """ランキング形式のメール本文を組み立てる"""

    # 上位5件に制限
    top_articles = articles[:5]

    rank_emojis = ["🥇", "🥈", "🥉", "📌", "📌"]

    lines = [
        "🧠 ITニュースダイジェスト（直近7日）",
        "",
        "---",
        "",
    ]

    for i, a in enumerate(top_articles):
        rank = rank_emojis[i]

        summary = a["ai_summary"].replace("\n", " ")

        # メール本文に追加
        lines += [
            f"{rank}{i+1}位（重要度: {a['importance']}）",
            f"{a['title']}",
            f"→ {summary}",
            f"→ {a['url']}",
            "----------------------------------",
            "",
        ]

    # 傾向（仮：あとでGeminiで生成してもOK）
    lines += [
        "📌 今日の傾向",
        "・AI関連ニュースが多め",
        "・大手テック企業の動きが活発",
    ]

    return "\n".join(lines)


def send_daily_email():
    """毎日決まった時間に呼び出される関数。重要記事をメールで送信する。"""
    important_articles = get_notification_targets()

    if not important_articles:
        logger.info("重要記事なし。メールは送信しません。")
        return

    subject = (
        f"【ITニュース】過去{config.NOTIFICATION_LOOKBACK_DAYS}日・TOP{config.MAX_NOTIFICATION_COUNT} "
        f"{len(important_articles)} 件 ({datetime.now().strftime('%Y-%m-%d')})"
    )
    body = build_email_body(important_articles)

    try:
        send_gmail(subject=subject, body=body)
        logger.info(f"メール送信完了: {len(important_articles)} 件の重要記事")
    except Exception as e:
        logger.exception(f"メール送信に失敗しました")
