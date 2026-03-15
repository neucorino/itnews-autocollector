import config

from datetime import datetime, timedelta

from my_utils import send_gmail
from rss_fetcher import fetch_rss
from db import create_table, insert_article, get_latest_articles
from logger import setup_logger

logger = setup_logger()


# -──────────────────────────────────────────
# 7.メール本文の作成
# -──────────────────────────────────────────
def build_email_body(important_articles: list[dict]) -> str:
    """重要記事リストからメール本文を組み立てて返す"""
    lines = [
        f"本日の重要ITニュース（重要度 {IMPORTANCE_THRESHOLD} 以上）",
        f"対象記事数: {len(important_articles)} 件",
        "=" * 60,
    ]
    for i, a in enumerate(important_articles, 1):
        lines += [
            f"\n【{i}】{a['title']}",
            f"  URL      : {a['link']}",
            f"  重要度   : {a['importance']} / 10",
            f"  要約     :\n{a['summary']}",
            "-" * 60,
        ]
    return "\n".join(lines)

# -──────────────────────────────────────────
# 8.重要記事のメール送信
# -──────────────────────────────────────────
def send_important_articles(important_articles: list[dict]) -> None:
    """重要度の高い記事をまとめてメールで送信する"""
    if not important_articles:
        logger.info("重要記事なし。メールは送信しません。")
        return

    subject = f"【ITニュース】重要記事 {len(important_articles)} 件 ({datetime.now().strftime('%Y-%m-%d')})"
    body = build_email_body(important_articles)

    try:
        send_gmail(subject=subject, body=body)
        logger.info(f"メール送信完了: {len(important_articles)} 件の重要記事")
    except Exception as e:
        logger.error(f"メール送信に失敗しました: {e}")

#──────────────────────────────────────────
# 9. 記事のループ処理
#──────────────────────────────────────────
def process_entries(entries: list, processed_ids: list)->tuple[list, list]:

    for entry in entries:

        black_list = ["PR", "広告", "お詫び"] #重要度が低いと判断するタイトルのキーワード
        if any(keyword in title for keyword in black_list):
            processed_ids.append(guid)
            print(f"スキップ: {title} (理由: ブラックリストマッチ)")
            continue # ブラックリストに含まれる記事はスキップ

        try:
            analysis = analyze_article_with_gemini(title, summary)
            if analysis is None:
                continue # APIエラーなどで分析できなかった記事はスキップ

            # 重要度のスコアを取得（分析結果から importance キーを取得、なければ0）
            importance_score = analysis.get("importance", 0)
            save_article_to_csv(title, link, analysis, CSV_FILENAME, CSV_KEEP_DAYS)
            #print(f"処理完了: {title} (重要度: {importance_score})",reason=analysis.get("reason", "理由なし"))
            print(f"DEBUG: Title: {title} | Analysis Result: {analysis}")

            # if importance_score >= IMPORTANCE_THRESHOLD:
            #     print(f"🔥 重要記事発見！スコア: {importance_score}")
            #     # jsonファイル保存準備
            #     important_articles.append= ({
            #         "title":      title,
            #         "link":       link,
            #         "importance": importance_score,
            #         "reason":     analysis.get("reason", ""),
            #         "summary":    analysis.get("summary", ""),
            #     })
            # processed_ids.append(guid) # 処理済みIDに追加
        except Exception as e:
            logger.error(f"記事解析エラー: {title}, エラー: {e}")

# -──────────────────────────────────────────
# 10.メイン処理
# -──────────────────────────────────────────
def main():
    create_table()

    for rss_url, source in RSS_LIST:

        articles = fetch_rss(rss_url, source)
        
        for article in articles:
            insert_article(article)
logger = setup_logger()

if __name__ == "__main__":
    main()