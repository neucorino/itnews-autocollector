from pathlib import Path
import os
from dotenv import load_dotenv
from src.exceptions import ConfigValidationError

# 環境変数の読み込み
load_dotenv()


#プロジェクトのルート
BASE_DIR = Path(__file__).resolve().parent.parent


#Database
DB_PATH = BASE_DIR / "data" / "news.db"


# RSS
RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://www.theverge.com/rss/index.xml", "The Verge"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica"),
    ("https://github.blog/feed/", "GitHub Blog"),
]

SOURCE_FETCH_LIMIT = 20


# ロギングの設定
LOG_FILE = BASE_DIR / "logs" / "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash-lite"
TEMPERATURE = 1.0
USER_PREFERENCES = """
プログラミング言語 (Python), 
開発ツールの新機能, 
バックエンド技術スタック,
データベース技術スタック,
インフラ技術スタック,
AI/ML技術スタック
"""


#プロンプトのテンプレート
PROMPT_TEMPLATE = """
以下の記事をITエンジニアの視点で分析してください。
今回のユーザーの【特に関心の高いトピック】を踏まえてスコアリングを行う必要があります。

【ユーザーの関心トピック】: {user_preferences}

【記事のID】: {id}
【タイトル】: {title}
【内容】: {summary}

出力は必ずシステム指示（System Instruction）で指定されたJSONの配列（List[dict]）形式のみを返してください。
"""

SYSTEM_INSTRUCTION = """
あなたは、第一線で活躍する好奇心旺盛なシニアソフトウェアエンジニアです。
ユーザーごとにパーソナライズされたITニュースのフィルタリングとスコアリングを担当しています。

提供されるタイトルと内容、そして【ユーザーの関心トピック】を照らし合わせ、以下の基準で【厳格にメリハリをつけて】1〜10点でスコアリング（importance）してください。

【最優先：7〜10点】
・【ユーザーの関心トピック】に直接関連する「新機能」「技術アップデート」「実戦的な活用事例・ガイド」。
・エンジニアの実務や技術選定に強烈なインパクトを与えるような、対象分野の重大な業界ニュース。

【興味あり：5〜6点】
・【ユーザーの関心トピック】に周辺領域として関連するニュース（例：言語が指定された場合の、関連ツールやインフラの話題など）。
・実務にすぐ直結はしないが、技術的に筋の良い新しいアプローチや実験的試み。

【低優先：1〜4点】
・【ユーザーの関心トピック】に全く該当しない、興味の対象外のニュース。
・テック企業に関する単なる政治的・法的な議論、人事の噂話。
・一般的な製品のカジュアルなガジェットレビュー（コンシューマー向け情報）。

出力形式は、必ず以下のJSONスキーマを厳守して返してください：
{
  "id": "記事のID（必ず数字）",
  "ai_summary": "3行で簡潔に要約した文章（必ず日本語）",
  "importance": 1から10の整数値,
  "reason": "今回のユーザーの関心トピックと照らし合わせ、なぜこの重要度スコアにしたのかの具体的な理由（必ず日本語）",
  "category": "技術カテゴリ"
}
"""


#メール設定
FROM_ADDRESS = os.getenv('GMAIL_USER')
MY_PASSWORD = os.getenv('GMAIL_PASS')


# ニュース取得のルール
IMPORTANCE_THRESHOLD = 6    # 通知対象にする重要度のしきい値
MAX_ARTICLES_PER_BATCH = 100  # 1バッチ全体で処理する記事の上限
GEMINI_SLEEP_SECONDS = 5    # リクエスト間のwait時間
GEMINI_MAX_RETRIES = 5        # 429エラー時の最大リトライ回数


# 通知設定
NOTIFICATION_LOOKBACK_DAYS = 7   # 通知対象とする記事の公開日のさかのぼり日数
RANKING_LIMIT = 10            # 上位10件を取得する
NOTIFICATION_LIMIT = 5   # 一度に通知する最大件数

# FastAPI設定
API_TITLE = "IT News Live API"
API_DESCRIPTION = "ITニュースを収集し、Geminiで分析・配信するAPI"
API_VERSION = "1.2.0"

# ランキングの減衰係数（経過日数に応じて重要度を減衰させるためのテーブル）
FRESHNESS_TABLE = {
    0: 1.00,
    1: 0.95,
    2: 0.90,
    3: 0.85,
    4: 0.60,
    5: 0.40,
    6: 0.20,
    7: 0.10,
}


def validate_config() -> None:
    """
    設定値の妥当性を検証。エラーが見つかった場合は ConfigValidationError を raise。
    """
    
    # 必須環境変数チェック
    required_env = ["GEMINI_API_KEY", "GMAIL_USER", "GMAIL_PASS"]
    for env_name in required_env:
        if not os.getenv(env_name):
            raise ConfigValidationError(f"必須環境変数が未設定です: {env_name}")
    
    # 数値設定の範囲チェック
    if not (1 <= IMPORTANCE_THRESHOLD <= 10):
        raise ConfigValidationError(
            f"IMPORTANCE_THRESHOLD は 1-10 の範囲である必要があります (現在値: {IMPORTANCE_THRESHOLD})"
        )
    
    if NOTIFICATION_LIMIT <= 0:
        raise ConfigValidationError(
            f"NOTIFICATION_LIMIT は正数である必要があります (現在値: {NOTIFICATION_LIMIT})"
        )
    
    if NOTIFICATION_LOOKBACK_DAYS <= 0:
        raise ConfigValidationError(
            f"NOTIFICATION_LOOKBACK_DAYS は正数である必要があります (現在値: {NOTIFICATION_LOOKBACK_DAYS})"
        )
    
    if GEMINI_MAX_RETRIES <= 0:
        raise ConfigValidationError(
            f"GEMINI_MAX_RETRIES は正数である必要があります (現在値: {GEMINI_MAX_RETRIES})"
        )
    
    # ディレクトリ存在確認
    if not BASE_DIR.exists():
        raise ConfigValidationError(f"BASE_DIR が存在しません: {BASE_DIR}")
    
    # ログディレクトリ作成
    LOG_FILE.parent.mkdir(exist_ok=True, parents=True)