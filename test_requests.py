import requests
import feedparser
from google import genai
from google.genai import types
import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

def setup_logger():
    """ロギングを設定して、loggerオブジェクトを返す"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

feed = feedparser.parse("https://news.ycombinator.com/rss")
processed_ids = ["id_1", "id_2", "id_3"]

for entry in feed.entries:
    entry = feed.entries[0]
    title = entry.get('title', '無題')
    link = entry.get('link', '#')
    summary = entry.get('summary', entry.get('description', '本文なし'))
    guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用

    # 2. 重複チェック（guid が過去データにないか）
    if guid not in processed_ids:
        try:

            prompt = f"""
            以下の記事をITエンジニアの視点で分析してください。
            【タイトル】: {title}
            【内容】: {summary}
            出力形式は以下のJSON形式にしてください
            {{
                "summary": "3行で要約した文章",
                "importance": 1から10の数値,
                "reason": "重要度の理由",
                "category": "技術カテゴリ"
            }}"""
            gemini_importance = gemini_model.generate(prompt)
            # 4. 統合
            entry["importance"] = gemini_importance
                
            # 5. フィルタリング（例：重要度7以上なら通知）
            if entry["importance"] >= 7:
                logger.info(f"重要度7以上の記事: {title}")
            # bozo という属性で、feedparser特有の解析エラーもチェックできる
            if feed.bozo:
                raise Exception("RSSの形式が壊れています")
            logging.info(f"{len(feed.entries)} 件の記事を取得しました。")

        except Exception as e:
            logger.error(f"記事解析エラー: {title}, エラー: {e}")