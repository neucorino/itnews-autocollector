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
TEMPERATURE = 0.1

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

entries = fetch_feed(URL)

# ──────────────────────────────────────────
# 3.jsonファイルの読み込み
# ──────────────────────────────────────────
def load_processed_ids(json_file_path: str) -> list:
    """jsonファイルから過去に処理した記事IDのリストを読み込む"""
    try:
        with open(json_file_path, 'r', encoding="utf-8") as f:
            processed_ids = json.load(f) # ファイルからリストを復元
            logger.info(f"過去に処理した記事IDの数: {len(processed_ids)}")
            return processed_ids
    except FileNotFoundError:
        logger.warning(f"{json_file_path} が見つかりません。空のリストで初期化します。")
        return [] # ファイルがない場合は空のリストを初期化
    except json.JSONDecodeError:
        logger.error(f"{json_file_path} の内容が不正です。空のリストで初期化します。")
        return []

processed_ids = load_processed_ids(json_file_path)

# ──────────────────────────────────────────
# 4. jsonファイルへの保存関数
# ──────────────────────────────────────────
def save_processed_ids(processed_ids: list, json_file_path: str):
    """処理した記事IDのリストをjsonファイルに保存する"""
    try:
        with open(json_file_path, 'w', encoding="utf-8") as f:
            json.dump(processed_ids, f) # リストをファイルに保存
            logger.info(f"処理した記事IDを {json_file_path} に保存しました。")
    except Exception as e:
        logger.error(f"{json_file_path} への保存に失敗しました: {e}")

save_processed_ids(json_file_path, updated_ids)

# ──────────────────────────────────────────
# 5. Gemini APIへのリクエスト
# ──────────────────────────────────────────
def analyze_article_with_gemini(title: str, summary: str) -> dict:
    """記事のタイトルと要約をGemini APIに送信して分析結果を辞書で返す"""
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
    
    client = genai.Client(api_key=GEMINI_API_KEY)

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

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=TEMPERATURE)
    )
    
    raw_text = response.text
    clean_text = re.search(r'\{.*\}', raw_text, re.DOTALL)
    
    if clean_text:
        clean_text = clean_text.group(0)
        analysis = json.loads(clean_text)#文字列(String)を辞書(dict)に変換！
        importance_score = analysis.get("importance", 0) #importanceの数値を取得（なければ0）
        return analysis
    else:
        logger.warning("GeminiのレスポンスからJSONが見つかりませんでした。")
        return {}

#記事のループ処理
for entry in entries:
    try:
        #記事の情報を取得
        title = entry.get('title', '無題')
        link = entry.get('link', '#')
        summary = entry.get('summary', entry.get('description', '本文なし'))
        guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用

        #重複チェック（guid が過去データにないか）
        if guid not in processed_ids:
            continue # すでに処理済みの記事はスキップ
        try:
            
            analysis = analyze_article_with_gemini(title, summary)
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

            # CSVファイルにデータを追加
            new_row = {
                "取得日": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "サイト名": "Hacker News",
                "記事タイトル": title,
                "URL": link,
                "reason": analysis.get("reason", ""),
                "要約": analysis.get("summary", "")
            }
            # ファイルが存在するかチェック
            file_exists = os.path.exists(CSV_FILENAME)
            # DataFrameを作る
            df = pd.DataFrame([new_row])

            # --- 修正後の流れ ---
            # 既存のデータを読み込む (重複チェックや削除のために一度全出し
            if os.path.exists(CSV_FILENAME):
                df = pd.read_csv(CSV_FILENAME)
                # 型変換と古いデータの削除
                df["取得日"] = pd.to_datetime(df["取得日"], errors='coerce')
                df = df.dropna(subset=["取得日"])
                
                limit_date = datetime.now() - timedelta(days=keep_days)
                clean_df = df[df["取得日"] > limit_date]

                # 今回の新しい記事(new_row)を追加するならここで
                new_df = pd.DataFrame([new_row])
                clean_df = pd.concat([clean_df, new_df], ignore_index=True)

                # 重複削除（URLベース）
                clean_df = clean_df.drop_duplicates(subset=["URL"], keep='first')

                # 上書き保存（mode='a'は使わず、）
                clean_df.to_csv(CSV_FILENAME, index=False, encoding='utf-8-sig')
                
                print(f"📊 CSV更新完了: 現在 {len(clean_df)} 件の記事を保存中")
            
    except Exception as e:
        logger.error(f"記事解析エラー: {title}, エラー: {e}")

 # --- 保存（すべての処理が終わった後に1回だけ） ---
with open("processed_ids.json", "w") as f:
    json.dump(processed_ids, f) # 最新のリストをファイルに上書き保存