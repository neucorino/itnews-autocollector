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
    ("https://news.ycombinator.com/rss", "Hacker News")
]
FETCH_LIMIT = 30


# ロギングの設定
LOG_FILE = BASE_DIR / "logs" / "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash-lite"
TEMPERATURE = 0.2


#プロンプトのテンプレート
PROMPT_TEMPLATE = """
以下の記事をITエンジニアの視点で分析してください。
    【タイトル】: {title}
    【内容】: {summary}
    出力形式は以下のJSON形式にしてください
    {{
        "ai_summary": "3行で要約した文章、必ず日本語で記述すること",
        "importance": 1から10の数値,
        "reason": "重要度の理由、必ず日本語で記述すること",
        "category": "技術カテゴリ"
    }}"""


SYSTEM_INSTRUCTION = """
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
    "ai_summary": "タイトルから推測される内容を1行で記述（日本語）",
    "importance": 数値(1-10),
    "reason": "なぜその点数か。ユーザーの関心（実用AI>理論/論文）に基づき記述（日本語）",
    "category": "技術カテゴリ"
    }
    """ 


#メール設定
FROM_ADDRESS = os.getenv('GMAIL_USER')
MY_PASSWORD = os.getenv('GMAIL_PASS')


# ニュース取得のルール
LATEST_NEWS_LIMIT = 30       # 最新ニュース取得件数
IMPORTANCE_THRESHOLD = 6    # 通知対象にする重要度のしきい値
MAX_ARTICLES_PER_BATCH = 30   # 一度に処理する記事の上限
GEMINI_SLEEP_SECONDS = 5    # リクエスト間のwait時間
GEMINI_MAX_RETRIES = 3        # 429エラー時の最大リトライ回数


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