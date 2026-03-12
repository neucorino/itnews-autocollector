import feedparser
from models import Article

def fetch_rss(url, source_name):

    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:

        article = Article(
            title=entry.title,
            url=entry.link,
            source=source_name,
            published_at=entry.get("published", "")
        )

        articles.append(article)

    return articles