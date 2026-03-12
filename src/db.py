import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "project_database.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

# データベースにテーブルが存在しない場合は作成する
def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    # articlesテーブルを作成（存在しない場合のみ）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT UNIQUE,
        source TEXT,
        published_at TEXT,
        fetched_at TEXT
    )
    """)
    conn.commit()
    conn.close()

#記事をDBに保存する
def insert_article(article):
    conn = get_connection()
    cursor = conn.cursor()

    # URLの重複を避けるため、INSERT OR IGNOREを使用して記事を挿入
    cursor.execute("""
    INSERT OR IGNORE INTO articles 
    (title, url, source, published_at)
    VALUES (?, ?, ?, ?)
    """, (
        article.title,
        article.url,
        article.source,
        article.published_at
    ))

    conn.commit()
    conn.close()