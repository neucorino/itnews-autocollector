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
from my_utils import send_gmail

# ──────────────────────────────────────────
# 0. 定数と設定
# ──────────────────────────────────────────

# 環境変数の読み込み
load_dotenv()

# ロギングの設定
LOG_FILE = "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# RSSフィードのURL
URL = "https://news.ycombinator.com/rss"

# 過去に処理した記事IDを保存するjsonファイルのパス
json_file_path = "processed_ids.json"

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model_id = "gemini-2.0-flash"
TEMPERATURE = 0.1

# CSV設定
CSV_FILENAME = "/home/yzen-64/projects/it-news-system/it_news_database.csv"
CSV_KEEP_DAYS = 30

IMPORTANCE_THRESHOLD = 7 

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

# ──────────────────────────────────────────
# 4. jsonファイルへの保存関数
# ──────────────────────────────────────────
def save_processed_ids(processed_ids: list, json_file_path: str):
    """処理した記事IDのリストをjsonファイルに保存する"""
    try:
        with open(json_file_path, 'w', encoding="utf-8") as f:
            json.dump(processed_ids, f,ensure_ascii=False, indent=2) # リストをファイルに保存
        logger.info(f"処理した記事IDを {json_file_path} に保存しました。")
    except Exception as e:
        logger.error(f"{json_file_path} への保存に失敗しました: {e}")

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
    
    system_instruction = """
    あなたは、30年の経験を持つシニアソフトウェアエンジニア兼技術評論家です。
    提供されるITニュース記事を、以下の基準で厳格に評価してください。
    採点基準（importance）: 10点満点。
    1〜3: 一般的な製品発表、宣伝記事、既知の情報のまとめ。
    4〜6: 特定のライブラリのアップデート、実用的なTips。
    7〜8: 業界標準を変え得る新技術、重大な脆弱性報告、言語のメジャーアップデート。
    9〜10: 歴史的なブレイクスルー、全エンジニアが知るべきパラダイムシフト。
    出力形式: 必ず純粋なJSON形式のみで回答してください。余計な挨拶や解説は一切不要です。
    """

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", 
                temperature=TEMPERATURE)
        )
        raw_text = response.text # Gemini APIからの生のテキストレスポンス
        clean_text = re.search(r'\{.*\}', raw_text, re.DOTALL).group(0) # 最初のJSONオブジェクトを抽出
        clean_text = json.loads(clean_text) # JSON文字列を辞書に変換
        return clean_text
    except Exception as e:
        logger.error(f"Gemini APIへのリクエストに失敗しました: {e}")
        return None

#──────────────────────────────────────────
#6. CSVファイルへの保存と重複管理
#──────────────────────────────────────────
def save_article_to_csv(title: str, link: str, analysis: dict, CSV_FILENAME: str, CSV_KEEP_DAYS: int) -> None:
    """記事データを CSV に追記し、古いデータを削除する"""
    try:
        new_row = {
            "取得日": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "サイト名": "Hacker News",
            "記事タイトル": title,
            "URL": link,
            "要約": analysis.get("summary", ""),
            "reason": analysis.get("reason", ""),
        }

        #ファイルが存在するかチェック
        if os.path.exists(CSV_FILENAME):
            df = pd.read_csv(CSV_FILENAME) #データ読み込み
            #型変換と30日以内のデータ削除
            df["取得日"] = pd.to_datetime(df["取得日"], errors="coerce")
            df = df.dropna(subset=["取得日"])
            limit_date = datetime.now() - timedelta(days=CSV_KEEP_DAYS)
            df = df[df["取得日"] > limit_date]
        else:
            df = pd.DataFrame()

        #新しい記事の追加
        new_df = pd.DataFrame([new_row])
        df = pd.concat([df, new_df], ignore_index=True)
        #重複削除
        df = df.drop_duplicates(subset=["URL"], keep="first")
        #上書き保存
        df.to_csv(CSV_FILENAME, index=False, encoding="utf-8-sig")

        print(f"📊 CSV更新完了: 現在 {len(clean_df)} 件の記事を保存中")
        logger.info(f"CSV 保存完了: 現在 {len(df)} 件")
    except Exception as e:
        logger.error(f"CSV への保存に失敗しました: {e}")

# -──────────────────────────────────────────
# 7.メール本文の作成
# -──────────────────────────────────────────
def build_email_body(articles: list[dict]) -> str:
    """重要記事リストからメール本文を組み立てて返す"""
    lines = [
        f"本日の重要ITニュース（重要度 {IMPORTANCE_THRESHOLD} 以上）",
        f"対象記事数: {len(articles)} 件",
        "=" * 60,
    ]
    for i, a in enumerate(articles, 1):
        lines += [
            f"\n【{i}】{a['title']}",
            f"  URL      : {a['link']}",
            f"  重要度   : {a['importance']} / 10",
            f"  要約     :\n{a['summary']}",
            "-" * 60,
        ]
    return "\n".join(lines)

# -──────────────────────────────────────────
# 8.重要記事のメール送信
# -──────────────────────────────────────────
def send_important_articles(articles: list[dict]) -> None:
    """重要度の高い記事をまとめてメールで送信する"""
    if not articles:
        logger.info("重要記事なし。メールは送信しません。")
        return

    subject = f"【ITニュース】重要記事 {len(articles)} 件 ({datetime.now().strftime('%Y-%m-%d')})"
    body = build_email_body(articles)

    try:
        send_gmail(subject=subject, body=body)
        logger.info(f"メール送信完了: {len(articles)} 件の重要記事")
    except Exception as e:
        logger.error(f"メール送信に失敗しました: {e}")

#──────────────────────────────────────────
# . 記事のループ処理
#──────────────────────────────────────────
def process_entries(entries: list, processed_ids: list)->tuple[list, list]:
    important_articles = []

    for entry in entries:
        #記事の情報を取得
        title = entry.get('title', '無題')
        link = entry.get('link', '#')
        summary = entry.get('summary', entry.get('description', '本文なし'))
        guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用

        #重複チェック（guid が過去データにないか）
        if guid in processed_ids:
            continue # すでに処理済みの記事はスキップ
        try:
            analysis = analyze_article_with_gemini(title, summary)
            if analysis is None:
                continue # APIエラーなどで分析できなかった記事はスキップ

                importance_score = analysis.get("importance", 0)
                save_article_to_csv(title, link, analysis, CSV_FILENAME, CSV_KEEP_DAYS)
                processed_ids.append(guid)

                if importance_score >= IMPORTANCE_THRESHOLD:
                    print(f"🔥 重要記事発見！スコア: {importance_score}")
                    # jsonファイル保存準備
                    important_articles.append= ({
                        "title":      title,
                        "link":       link,
                        "importance": importance,
                        "reason":     analysis.get("reason", ""),
                        "summary":    analysis.get("summary", ""),
                    })
        except Exception as e:
            logger.error(f"記事解析エラー: {title}, エラー: {e}")
        
    return processed_ids, important_articles

# -──────────────────────────────────────────
# 9.メイン処理
# -──────────────────────────────────────────
def main():
    entries = fetch_feed(URL)
    processed_ids = load_processed_ids(json_file_path)
    updated_ids, important_articles = process_entries(entries, processed_ids)
    save_processed_ids(updated_ids, json_file_path)
    send_important_articles(important_articles)

logger = setup_logger()

if __name__ == "__main__":
    main()