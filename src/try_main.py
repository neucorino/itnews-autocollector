from rss_fetcher import fetch_rss
from db import create_table, insert_article, get_latest_articles
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

        articles = fetch_rss(rss_url, source)
        results = []


        for article in articles:
            #insert_article(article)
            # タイトルと要約をGemini APIで分析
            result = analyze_article_with_gemini(
            article.title,
            article.summary
        )
        if not result:
            continue

        article.importance = result.get("importance", 0)
        article.reason = result.get("reason", "")
        results.append(article)
        # analyzed = analyze_articles(articles)
        # important = filter_important_articles(analyzed)
        for article in results:
            insert_article(article)  

if __name__ == "__main__":
    main()