from rss_fetcher import fetch_rss
from db import create_table, insert_article, get_latest_articles
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
        
        for article in articles:
            insert_article(article)

if __name__ == "__main__":
    main()