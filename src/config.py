from pathlib import Path
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

#プロジェクトのルート
BASE_DIR = Path(__file__).resolve().parent.parent

#Database
DB_PATH = BASE_DIR / "data" / "project_database.db"

# RSS
RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News")
]
FETCH_LIMIT = 30

# ロギングの設定
LOG_FILE = "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.0-flash"
TEMPERATURE = 0.1

#重要度の閾値
IMPORTANCE_THRESHOLD = 7 

#メール設定
FROM_ADDRESS = os.getenv('GMAIL_USER')
MY_PASSWORD = os.getenv('GMAIL_PASS')
