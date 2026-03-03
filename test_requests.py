import requests
import feedparser
from google import genai
from google.genai import types
import logging
from logging.handlers import RotatingFileHandler
import json
from dotenv import load_dotenv
import os
import re

# ──────────────────────────────────────────
# 0. 定数と設定
# ──────────────────────────────────────────
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

# ──────────────────────────────────────────
# 1. ロギングの設定
# ──────────────────────────────────────────
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

#jsonファイルから過去に処理した記事IDのリストを読み込む
try:
    # 読み込み
    with open("processed_ids.json", 'r',encoding="utf-8") as f:
        processed_ids = json.load(f) # ファイルからリストを復元
except FileNotFoundError:
    processed_ids = [] # ファイルがない場合は空のリストを初期化
except json.JSONDecodeError:
    logger.error("processed_ids.json の内容が不正です。空のリストで初期化します。")
    processed_ids = []
print(f"過去に処理した記事IDの数: {len(processed_ids)}")

#記事のループ処理
for entry in fetch_feed(URL):
    try:
        #記事の情報を取得
        title = entry.get('title', '無題')
        link = entry.get('link', '#')
        summary = entry.get('summary', entry.get('description', '本文なし'))
        guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用

        #重複チェック（guid が過去データにないか）
        if guid not in processed_ids:
            #continue # すでに処理済みの記事はスキップ
            # 新着記事の処理（Geminiに投げるなど）
            print(f"新着記事を発見: {entry.title}",f"ID:{guid}")

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

            # Geminiクライアントを初期化してAPIリクエストを送信
            client = genai.Client(api_key=GEMINI_API_KEY)

            # APIからのレスポンスを受信
            response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=TEMPERATURE)
            )
            logger.info("Gemini APIからのレスポンスを受信しました。")

            raw_text = response.text # ここに「JSONっぽい文字列」が入る
            # もし Gemini が ```json ... ``` という装飾をつけてきたら除去する
            # 正規表現を使って { } の外側の余計な文字を削るのがコツです
            clean_text = re.search(r'\{.*\}', raw_text, re.DOTALL).group()
            # 文字列(String)を辞書(dict)に変換！
            analysis= json.loads(clean_text)
            # これで数値として取り出せる
            importance_score = analysis.get("importance", 0)

            if importance_score >= 7:
                print(f"🔥 重要記事発見！スコア: {importance_score}")
            
            article_data = {
            "guid": guid,
            "title": title,
            "importance": analysis.get("importance"),
            "summary": analysis.get("summary"),
            "reason": analysis.get("reason"),
            "category": analysis.get("category"),
            }
            # 記憶リストに追加
            processed_ids.append(guid)

    except Exception as e:
        logger.error(f"記事解析エラー: {title}, エラー: {e}")

 # --- 保存（すべての処理が終わった後に1回だけ） ---
with open("processed_ids.json", "w") as f:
    json.dump(processed_ids, f) # 最新のリストをファイルに上書き保存