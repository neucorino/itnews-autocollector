import requests
import feedparser
from google import genai
from google.genai import types
import logging
from logging.handlers import RotatingFileHandler
import json
from dotenv import load_dotenv
import os

load_dotenv()

LOG_FILE = "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

URL = "https://news.ycombinator.com/rss"

json_file_path = "processed_ids.json"

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model_id = "gemini-2.0-flash"
TEMPERATURE = 0.2

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

# ──────────────────────────────────────────
# 2. RSS フィードの取得
# ──────────────────────────────────────────
def fetch_feed(url: str) -> list:
    """RSS フィードを取得してエントリ一覧を返す"""
    #RSSの取得と解析
    feed = feedparser.parse(url)
    if feed.bozo:
        raise Exception("RSSの形式が壊れています")
    logger.info(f"{len(feed.entries)} 件の記事を取得しました。")
    return feed.entries

try:
    # 1. 読み込み
    with open("processed_ids.json", 'r',encoding="utf-8") as f:
        processed_ids = json.load(f) # ファイルからリストを復元
except FileNotFoundError:
    processed_ids = [] # ファイルがない場合は空のリストを初期化
except json.JSONDecodeError:
    logger.error("processed_ids.json の内容が不正です。空のリストで初期化します。")
    processed_ids = []
print(f"過去に処理した記事IDの数: {len(processed_ids)}")

for entry in fetch_feed(URL):
    # title = entry.get('title', '無題')
    # link = entry.get('link', '#')
    # summary = entry.get('summary', entry.get('description', '本文なし'))
    guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用
    print(f"ID:{guid}")

    #2. 重複チェック（guid が過去データにないか）
    if guid not in processed_ids:
        # 新着記事の処理（Geminiに投げるなど）
        print(f"新着記事を発見: {entry.title}")
        
        # 記憶リストに追加
        processed_ids.append(guid)
    # --- 3. 保存（すべての処理が終わった後に1回だけ） ---
with open("processed_ids.json", "w") as f:
    json.dump(processed_ids, f) # 最新のリストをファイルに上書き保存
        #try:

            # prompt = f"""
            # 以下の記事をITエンジニアの視点で分析してください。
            # 【タイトル】: {title}
            # 【内容】: {summary}
            # 出力形式は以下のJSON形式にしてください
            # {{
            #     "summary": "3行で要約した文章",
            #     "importance": 1から10の数値,
            #     "reason": "重要度の理由",
            #     "category": "技術カテゴリ"
            # }}"""

            # # Geminiクライアントを初期化してAPIリクエストを送信
            # client = genai.Client(api_key=GEMINI_API_KEY)
            # # APIからのレスポンスを受信
            # response = client.models.generate_content(
            # model=model_id,
            # contents=prompt,
            # config=types.GenerateContentConfig(response_mime_type="application/json", temperature=TEMPERATURE)
            # )
            
            # logger.info("Gemini APIからのレスポンスを受信しました。")

            # gemini_importance = json.loads(response.text)["importance"]
            # 4. 統合
            # entry["importance"] = gemini_importance
                
            # 5. フィルタリング（例：重要度7以上なら通知）
            # if entry["importance"] >= 7:
            #     logger.info(f"重要度7以上の記事: {title}")
            
        # except Exception as e:
        #     logger.error(f"記事解析エラー: {title}, エラー: {e}")