import config

def filter_important_articles(articles):

    important_articles = []

    try:
        logger.info("重要記事のフィルタリング開始")
        for article in articles:
            if article["importance"] >= config.IMPORTANCE_THRESHOLD:
                important_articles.append(article)
    except KeyError as e:
        logger.error(f"キーが見つかりません: {e}")

    return important_articles