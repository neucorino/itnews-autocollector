import sqlite3
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    # __init__ 
    def __init__(self,db_path=config.DB_PATH):
        # sqlite3はファイルパスを指定して接続します
        self.conn = sqlite3.connect(db_path)
        # sqlite3で辞書形式でデータを取れるようにする設定
        self.conn.row_factory = sqlite3.Row
        self.create_tables() # インスタンス化した時にテーブルがなければ作る
    
    def create_tables(self):
        """必要なテーブルを作成する（初回のみ）"""
        cur = self.conn.cursor()
        # batchesテーブル作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT,
                new_articles_count INTEGER
            )
        """)

        # articlesテーブルを作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                source TEXT,
                summary TEXT,
                published_at TEXT
            )
        """)

        # article_analysesテーブルを作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                ai_summary TEXT,
                importance INTEGER,
                reason TEXT,
                category TEXT,
                analyzed_at TIMESTAMP
            )
        """)

        # rankingsテーブルを作成
        cusor.execute("""
            CREATE TABLE IF NOT EXISTS rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER REFERENCES articles(id),
                analysis_id INTEGER REFERENCES article_analyses(id),
                rank INTEGER,
                batch_id INTEGER REFERENCES batches(id),
                created_at TIMESTAMP
            )
        """)

        self.conn.commit()

    # バッチ開始を記録するメソッド（操作）
    def start_new_batch(self):
        logger.info("バッチを開始します...")
        cur = self.conn.cursor()
        # sqlite3では %s ではなく ? を使います（重要！）
        sql = "INSERT INTO batches (started_at, status) VALUES (?, ?)"
        cur.execute(sql, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'running'))
        # 最後に挿入されたIDを取得
        batch_id = cur.lastrowid
        
        self.conn.commit()
        return batch_id

    # バッチ終了を記録するメソッド（操作）
    def finish_batch(self, batch_id, status,count):
        """バッチの結果を更新する"""
        cur = self.conn.cursor()
        sql = """
            UPDATE batches 
            SET ended_at = ?, status = ?, new_articles_count = ? 
            WHERE id = ?
        """
        cur.execute(sql, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, count, batch_id))
        self.conn.commit()
        logger.info(f"バッチID:{batch_id} をステータス:{status} で完了しました。")

# データベース接続を取得する関数
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    return conn
    logger.info("DB接続を取得")

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