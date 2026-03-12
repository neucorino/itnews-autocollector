import sqlite3
from datetime import datetime

DB_PATH = "project_database.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_table():
    conn = get_connection()
    cursor = conn.cursor()

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

def insert_article(title, url, source, published_at):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO articles
    (title, url, source, published_at, fetched_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        title,
        url,
        source,
        published_at,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

create_table()

insert_article(
    "テスト記事",
    "https://example.com",
    "Example News",
    "2026-03-11"
)