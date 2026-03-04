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
from datetime import datetime, timedelta
import pandas as pd

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

# CSV設定
CSV_FILENAME = "/home/yzen-64/projects/it-news-system/it_news_database.csv"
CSV_KEEP_DAYS = 30

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

            # --- システム指示を定義 ---
            system_instruction = f"""
            あなたは、30年の経験を持つシニアソフトウェアエンジニア兼技術評論家です。
            提供されるITニュース記事を、以下の基準で厳格に評価してください。
            採点基準（importance）: 10点満点。
            1〜3: 一般的な製品発表、宣伝記事、既知の情報のまとめ。
            4〜6: 特定のライブラリのアップデート、実用的なTips。
            7〜8: 業界標準を変え得る新技術、重大な脆弱性報告、言語のメジャーアップデート。
            9〜10: 歴史的なブレイクスルー、全エンジニアが知るべきパラダイムシフト。
            出力形式: 必ず純粋なJSON形式のみで回答してください。余計な挨拶や解説は一切不要です。
            JSON構成: {{"importance": "1から10の数値", "summary": "3行で要約した文章", "reason": "理由"}}"
            """

            # APIからのレスポンスを受信
            response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=TEMPERATURE)
            )
            #logger.info("Gemini APIからのレスポンスを受信しました。")


            
            raw_text = response.text # ここに「JSONっぽい文字列」が入る
            # もし Gemini が ```json ... ``` という装飾をつけてきたら除去する
            clean_text = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if clean_text:
                clean_text = clean_text.group(0) # マッチした部分を取り出す
                analysis = json.loads(clean_text)#文字列(String)を辞書(dict)に変換！
                importance_score = analysis.get("importance", 0) #importanceの数値を取得（なければ0）
                #print(f"解析成功！スコア: {analysis['importance']}") #importanceの数値を表示
            else:
                logger.warning("GeminiのレスポンスからJSONが見つかりませんでした。")

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

            # CSVファイルにデータを追加
            new_row = {
                "取得日": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "サイト名": "Hacker News",
                "記事タイトル": title,
                "URL": link,
                "reason": analysis.get("reason", ""),
                "要約": analysis.get("summary", "")
            }
            # 1. ファイルが存在するかチェック
            file_exists = os.path.exists(CSV_FILENAME)
            # 2. DataFrameを作る
            df = pd.DataFrame([new_row])
            # 3. 追記モード('a' = append)で保存
            # header=not file_exists は「ファイルがない時だけ見出しを付ける」という魔法の呪文です
            df.to_csv(CSV_FILENAME, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
            
    except Exception as e:
        logger.error(f"記事解析エラー: {title}, エラー: {e}")

 # --- 保存（すべての処理が終わった後に1回だけ） ---
with open("processed_ids.json", "w") as f:
    json.dump(processed_ids, f) # 最新のリストをファイルに上書き保存