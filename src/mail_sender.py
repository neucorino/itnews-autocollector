from my_utils import send_gmail
from service import get_notification_targets
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

def build_email_body(articles):
    """過去N日・重要度しきい値以上から選んだ記事リストからメール本文を組み立てる"""
    lines = [
        f"過去{config.NOTIFICATION_LOOKBACK_DAYS}日間の重要ITニュース（重要度 {config.IMPORTANCE_THRESHOLD} 以上）",
        f"送信件数: {len(articles)} 件（上位最大 {config.MAX_NOTIFICATION_COUNT} 件）",
        "=" * 60,
    ]
    for i, a in enumerate(articles, 1):
        lines += [
            f"\n【{i}】{a['title']}",
            f"  URL      : {a['url']}",
            f"  重要度   : {a['importance']} / 10",
            f"  要約     :\n{a['ai_summary']}",
            "-" * 60,
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
        logger.error(f"メール送信に失敗しました: {e}")
