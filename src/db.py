import sqlite3
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

# データベース接続を取得する関数
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    return conn
    logger.info("DB接続を取得")

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
    logger.info("DBテーブルの作成を確認")
    conn.commit()
    conn.close()

# 記事をデータベースに挿入する関数
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
    logger.info(f"{cursor.rowcount} 件DB保存")
    conn.commit()
    conn.close()

# 最新の記事を指定件数取得し、辞書のリストで返す
def get_latest_articles(limit=30):
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
        logger.info(f"{len(articles)} 件DBから取得")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
        logger.error(f"Database error: {e}")

    finally:
        conn.close()

# 記事の重要度判定の条件
def get_today_important(min_score=config.IMPORTANCE_THRESHOLD):
    conn = get_connection() 
    cursor = conn.cursor()

    # 重要度がmin_score以上の記事を取得
    logger.info("今日の重要記事の取得開始")
    cursor.execute("""
        SELECT * FROM articles
        WHERE importance >= ?
        AND DATE(published_at) = DATE('now')
        ORDER BY importance DESC
    """, (min_score,))

    return cursor.fetchall()

def get_weekly_important(min_score=config.IMPORTANCE_THRESHOLD):
    conn = get_connection() 
    cursor = conn.cursor()

    # 重要度がmin_score以上の記事を取得
    logger.info("過去7日間の重要記事の取得開始")
    cursor.execute("""
        SELECT * FROM articles
        WHERE importance >= ?
        AND DATE(published_at) >= DATE('now', '-7 days')
        ORDER BY importance DESC
    """, (min_score,))

    return cursor.fetchall()