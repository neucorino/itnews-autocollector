from rss_fetcher import fetch_rss
from db import get_connection, create_table, insert_article, get_latest_articles, get_today_important,get_weekly_important
from gemini_analyzer import analyze_article_with_gemini
from ranking import filter_important_articles
import config
from logger import setup_logger

logger = setup_logger()

RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

def main():

    create_table()

    for rss_url, source in RSS_LIST:

        # RSSから記事を取得
        articles = fetch_rss(rss_url, source)
        # 分析結果を格納するための空リストを用意
        results = []

        # タイトルと要約をGemini APIで分析
        for article in articles:
            result = analyze_article_with_gemini(
            article.title,
            article.summary
            )
            logger.info(f"Gemini分析完了: {article.title}")

        # 分析に失敗した記事はスキップ
        if not result:
            continue
            logger.warning(f"Gemini分析失敗: {article.title}")

        # importanceとreasonをArticleオブジェクトにセットして保存
        article.importance = result.get("importance", 0)
        article.reason = result.get("reason", "")
        # 分析結果をresultsリストに追加
        results.append(article)
        logger.info(f"記事分析結果: {article.title} (重要度: {article.importance})")

        # importanceとreasonをarticleに追加
        for article in results:
            insert_article(article)
            logger.info(f"DB保存: {article.title} (重要度: {article.importance})")

        # 重要度が高い記事をフィルタリング
        today_articles = get_today_important(get_connection())
        if len(today_articles) >= 5:
            result = today_articles
            logger.info(f"通知対象の記事: {[a['title'] for a in result]}")
        elif len(today_articles) < 5:
            weekly_articles = get_weekly_important(get_connection())
            # URLで重複排除
            urls = {a["url"] for a in today_articles}
            extra = [a for a in weekly_articles if a["url"] not in urls]
            result = today_articles + extra
            result = result[:5]
            logger.info(f"通知対象の記事: {[a['title'] for a in result]}")
        else:
            logger.info("重要な記事が見つかりませんでした")


if __name__ == "__main__":
    main()