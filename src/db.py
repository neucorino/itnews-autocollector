import sqlite3
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

# データベース接続を取得する関数
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    return conn

# データベースにテーブルが存在しない場合は作成する
def create_table():
    conn = get_connection() #DBに接続
    cursor = conn.cursor() #カーソルを作成

    # articlesテーブルを作成（存在しない場合のみ）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT UNIQUE,
        source TEXT,
        summary TEXT,
        published_at TEXT,
        importance INTEGER,
        reason TEXT,       
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

#記事をDBに保存する
def insert_article(article):
    conn = get_connection() #DBに接続
    cursor = conn.cursor() #カーソルを作成

    # URLの重複を避けるため、INSERT OR IGNOREを使用して記事を挿入
    cursor.execute("""
    INSERT OR IGNORE INTO articles(title, url, source, summary, published_at, importance, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        article.title,
        article.url,
        article.source,
        article.summary,
        article.published_at,
        article.importance,
        article.reason
    ))
    conn.commit()
    conn.close()
    logger.info(f"{cursor.rowcount} 件DB保存")


def get_latest_articles(limit=30):
    """
    最新の記事を指定件数取得し、辞書のリストで返す
    """
    conn = get_connection()
    # カラム名でデータにアクセスできるように設定
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT title, url, source, summary, published_at, importance, reason
            FROM articles 
            ORDER BY published_at DESC 
            LIMIT ?
        """, (limit,))
        
        #結果の取得
        rows = cursor.fetchall()
        # sqlite3.RowオブジェクトをPythonの辞書に変換
        articles = [dict(row) for row in rows]
        return articles
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

    finally:
        conn.close()