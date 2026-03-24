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

# 記事リストに一括でinsertする関数
def bulk_insert_articles(articles: list):
    if not articles:
        return 0
    conn = get_connection()
    cursor = conn.cursor()

    # executemanyに渡すために、オブジェクトのリストをタプルのリストに変換
    data = [(
        a.title,
        a.url,
        a.source,
        a.summary,
        a.published_at,
        a.importance,
        a.reason
    ) for a in articles]

    try:
        # 一括実行
        cursor.executemany("""
            INSERT OR IGNORE INTO articles (
                title, url, source, summary, published_at, importance, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        saved_count = cursor.rowcount
        conn.commit()
        logger.info(f"{saved_count} 件の新着記事をDBに保存しました")
        return saved_count

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error during bulk insert: {e}")
        raise e # エラーをservice側に伝える
    finally:
        conn.close()


# 指定した条件で記事を取得する関数
def fetch_articles(limit=config.LATEST_NEWS_LIMIT, 
    min_importance=config.IMPORTANCE_THRESHOLD, 
    days_ago=config.RETENTION_DAYS_WEEKLY
):
    conn = get_connection()
    # カラム名でデータにアクセスできるように設定
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # フィルタ条件を動的に組み立てる
    # importanceがmin_importance以上の記事を取得
    query = "SELECT * FROM articles WHERE importance >= ?"
    params = [min_importance]
    # days_agoが指定された場合は、published_atがdays_ago日以内の記事を取得
    if days_ago is not None:
        query += " AND DATE(published_at) >= DATE('now', ?)"
        params.append(f'-{days_ago} days')
        
    # 重要度の高い順、公開日時の新しい順で並べ替え、指定した件数だけ取得
    query += " ORDER BY importance DESC, published_at DESC LIMIT ?"
    params.append(limit)
    
    try:
        # クエリを実行して記事を取得
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()