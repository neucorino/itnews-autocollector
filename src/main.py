from google import genai
from google.genai import types
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os
import re
from datetime import datetime, timedelta

from my_utils import send_gmail
from rss_fetcher import fetch_rss
from db import create_table, insert_article, get_latest_articles

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
RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model_id = "gemini-2.0-flash"
TEMPERATURE = 0.1

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
        "summary": "3行で要約した文章、必ず日本語で記述すること",
        "importance": 1から10の数値,
        "reason": "重要度の理由、必ず日本語で記述すること",
        "category": "技術カテゴリ"
    }}"""
    
    system_instruction = """
    あなたは、30年の経験を持つシニアソフトウェアエンジニア兼技術評論家です。
    「実用的な生成AI（LLM）の活用」と「主要ツールの新機能」に最も高い関心を持っています。
    提供されるタイトルから、以下の基準で厳格にスコアリングしてください。

    【最優先：通知対象（7〜9点）】
    ・主要AI（Gemini, ChatGPT, Claude, Grok）の「新機能」「APIアップデート」「公式の活用ガイド」。
    ・既存の生成AIを使った「実戦的な開発手法」「プロンプトエンジニアリングの新機軸」。
    ・大手テック企業（Google, OpenAI, Anthropic, Microsoft, NVIDIA）による実用的なAI発表。

    【興味あり：保留（5〜6点）】
    ・インフラ/ハードウェア（GPU/VM）のベンチマークや性能比較。
    ・特定の開発者向けツール、新しいライブラリ、GitHubリポジトリの紹介。
    ・CPUでの推論最適化など、すぐには使わないが技術的に筋の良い試み。

    【低優先：除外（1〜4点）】
    ・8-9点相当の内容だが、まだ「論文（arXiv）」段階の未実装技術（一律 4点程度に下げる）。
    ・IT・ソフトウェアに直接関係ない科学、美術、一般ニュース（一律 1点）。
    ・OSやデバイスの「噂（Possible, Rumor）」レベルの記事。

    【出力形式】
    必ず以下のJSON形式のみで回答してください。
    {
    "summary": "タイトルから推測される内容を1行で記述（日本語）",
    "importance": 数値(1-10),
    "reason": "なぜその点数か。ユーザーの関心（実用AI＞理論/論文）に基づき記述（日本語）",
    "category": "技術カテゴリ"
    }
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

# -──────────────────────────────────────────
# 7.メール本文の作成
# -──────────────────────────────────────────
def build_email_body(important_articles: list[dict]) -> str:
    """重要記事リストからメール本文を組み立てて返す"""
    lines = [
        f"本日の重要ITニュース（重要度 {IMPORTANCE_THRESHOLD} 以上）",
        f"対象記事数: {len(important_articles)} 件",
        "=" * 60,
    ]
    for i, a in enumerate(important_articles, 1):
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
def send_important_articles(important_articles: list[dict]) -> None:
    """重要度の高い記事をまとめてメールで送信する"""
    if not important_articles:
        logger.info("重要記事なし。メールは送信しません。")
        return

    subject = f"【ITニュース】重要記事 {len(important_articles)} 件 ({datetime.now().strftime('%Y-%m-%d')})"
    body = build_email_body(important_articles)

    try:
        send_gmail(subject=subject, body=body)
        logger.info(f"メール送信完了: {len(important_articles)} 件の重要記事")
    except Exception as e:
        logger.error(f"メール送信に失敗しました: {e}")

#──────────────────────────────────────────
# 9. 記事のループ処理
#──────────────────────────────────────────
def process_entries(entries: list, processed_ids: list)->tuple[list, list]:
    #important_articles = []

    for entry in entries:
        #記事の情報を取得
        # title = entry.get('title', '無題')
        # link = entry.get('link', '#')
        # summary = entry.get('summary', entry.get('description', '本文なし'))
        # guid = entry.get('id', entry.link)  # guid がない場合は link を代わりに使用

        #重複チェック（guid が過去データにないか）
        # if guid in processed_ids:
        #     continue # すでに処理済みの記事はスキップ

        black_list = ["PR", "広告", "お詫び"] #重要度が低いと判断するタイトルのキーワード
        if any(keyword in title for keyword in black_list):
            processed_ids.append(guid)
            print(f"スキップ: {title} (理由: ブラックリストマッチ)")
            continue # ブラックリストに含まれる記事はスキップ

        try:
            analysis = analyze_article_with_gemini(title, summary)
            if analysis is None:
                continue # APIエラーなどで分析できなかった記事はスキップ

            # 重要度のスコアを取得（分析結果から importance キーを取得、なければ0）
            importance_score = analysis.get("importance", 0)
            save_article_to_csv(title, link, analysis, CSV_FILENAME, CSV_KEEP_DAYS)
            #print(f"処理完了: {title} (重要度: {importance_score})",reason=analysis.get("reason", "理由なし"))
            print(f"DEBUG: Title: {title} | Analysis Result: {analysis}")

            # if importance_score >= IMPORTANCE_THRESHOLD:
            #     print(f"🔥 重要記事発見！スコア: {importance_score}")
            #     # jsonファイル保存準備
            #     important_articles.append= ({
            #         "title":      title,
            #         "link":       link,
            #         "importance": importance_score,
            #         "reason":     analysis.get("reason", ""),
            #         "summary":    analysis.get("summary", ""),
            #     })
            # processed_ids.append(guid) # 処理済みIDに追加
        except Exception as e:
            logger.error(f"記事解析エラー: {title}, エラー: {e}")

# -──────────────────────────────────────────
# 10.メイン処理
# -──────────────────────────────────────────
def main():
    create_table()

    for rss_url, source in RSS_LIST:

        articles = fetch_rss(rss_url, source)
        
        for article in articles:
            insert_article(article)
logger = setup_logger()

if __name__ == "__main__":
    main()