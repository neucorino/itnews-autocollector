import sqlite3
import models
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

CREATE_BATCHES = """
    CREATE TABLE IF NOT EXISTS batches (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at          TEXT,
        ended_at            TEXT,
        status              TEXT,
        new_articles_count  INTEGER
    )
"""

CREATE_ARTICLES = """
    CREATE TABLE IF NOT EXISTS articles (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        title        TEXT,
        url          TEXT UNIQUE,
        source       TEXT,
        summary      TEXT,
        published_at TEXT
    )
"""

CREATE_ARTICLE_ANALYSES = """
    CREATE TABLE IF NOT EXISTS article_analyses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id  INTEGER NOT NULL,
        batch_id    INTEGER NOT NULL, 
        ai_summary  TEXT,
        importance  INTEGER,
        reason      TEXT,
        category    TEXT,
        analyzed_at TEXT,
        FOREIGN KEY (article_id) REFERENCES articles(id)
        FOREIGN KEY (batch_id)   REFERENCES batches(id)
    )
"""

CREATE_RANKINGS = """
    CREATE TABLE IF NOT EXISTS rankings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id  INTEGER NOT NULL,
        analyses_id INTEGER NOT NULL,
        batch_id    INTEGER NOT NULL,
        rank        INTEGER,
        created_at  TEXT,
        FOREIGN KEY (article_id)  REFERENCES articles(id),
        FOREIGN KEY (analyses_id) REFERENCES article_analyses(id),
        FOREIGN KEY (batch_id)    REFERENCES batches(id)
    )
"""

INSERT_ARTICLE = """
    INSERT OR IGNORE INTO articles (title, url, source, summary, published_at)
    VALUES (:title, :url, :source, :summary, :published_at)
"""

INSERT_ANALYSES = """
    INSERT OR IGNORE INTO article_analyses (
        article_id, batch_id, ai_summary, 
        importance, reason, category, analyzed_at
    )
    VALUES (:article_id, :batch_id, :ai_summary, 
            :importance, :reason, :category, :analyzed_at)
"""

INSERT_RANKING = """
    INSERT INTO rankings (article_id, analyses_id, batch_id, rank, created_at)
    VALUES (:article_id, :analyses_id, :batch_id, :rank, :created_at)
"""

START_NEW_BATCH = """
    INSERT INTO batches (started_at, status) VALUES (:started_at, :status)
"""

FINISH_BATCH = """
    UPDATE batches 
    SET ended_at = :ended_at, status = :status, new_articles_count = :new_articles_count 
    WHERE id = :id
"""

class DatabaseManager:
    # __init__ 
    def __init__(self,db_path=config.DB_PATH):
        # sqlite3はファイルパスを指定して接続
        self.conn = sqlite3.connect(db_path)
        # sqlite3で辞書形式でデータを取れるようにする設定
        self.conn.row_factory = sqlite3.Row
        logger.info(f"DB接続を開始: {db_path}")
        self.create_tables() # インスタンス化した時にテーブルがなければ作る
    
    def create_tables(self) -> None:
        """テーブルが存在しない場合に作成する。"""
        with self.conn:
            for ddl in (CREATE_BATCHES, CREATE_ARTICLES, CREATE_ARTICLE_ANALYSES, CREATE_RANKINGS):
                self.conn.execute(ddl)
    
    # 記事リストに一括でinsertする関数
    def bulk_insert_articles(self,articles_list):
        """記事リストを一括でinsertする。URLが重複する場合はスキップ。"""
        records = [a.to_dict() for a in articles_list]
        with self.conn:
            self.conn.executemany(INSERT_ARTICLE, records)
        logger.info(f"{len(articles_list)}件の記事を一括処理しました。")
    
    def bulk_insert_analyses(self, analyses_list):
        records = [a.to_dict() for a in analyses_list]
        with self.conn:
            self.conn.executemany(INSERT_ANALYSES, records)
        logger.info(f"{len(analyses_list)}件の解析結果を一括処理しました。")
    
    def bulk_insert_rankings(self, rankings_list):
        records = [a.to_dict() for a in rankings_list]
        with self.conn:
            self.conn.executemany(INSERT_RANKING, records)
        logger.info(f"{len(rankings_list)}件のランキングを一括処理しました。")

    # バッチ開始を記録するメソッド（操作）
    def start_new_batch(self):
        logger.info("バッチを開始します...")
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(START_NEW_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'running'))
            # 最後に挿入されたIDを取得
            batch_id = cur.lastrowid
        return batch_id

    # バッチ終了を記録するメソッド（操作）
    def finish_batch(self, batch_id, status,count):
        """バッチの結果を更新する"""
        with self.conn:
            self.conn.execute(FINISH_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, count, batch_id))
        logger.info(f"バッチID:{batch_id} をステータス:{status} で完了しました。")


# 指定した条件で記事を取得する関数
# def fetch_articles(limit=config.LATEST_NEWS_LIMIT, 
#     min_importance=config.IMPORTANCE_THRESHOLD, 
#     days_ago=config.RETENTION_DAYS_WEEKLY
# ):
#     conn = get_connection()
#     # カラム名でデータにアクセスできるように設定
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()
#     # フィルタ条件を動的に組み立てる
#     # importanceがmin_importance以上の記事を取得
#     query = "SELECT * FROM articles WHERE importance >= ?"
#     params = [min_importance]
#     # days_agoが指定された場合は、published_atがdays_ago日以内の記事を取得
#     if days_ago is not None:
#         query += " AND DATE(published_at) >= DATE('now', ?)"
#         params.append(f'-{days_ago} days')
        
#     # 重要度の高い順、公開日時の新しい順で並べ替え、指定した件数だけ取得
#     query += " ORDER BY importance DESC, published_at DESC LIMIT ?"
#     params.append(limit)
    
#     try:
#         # クエリを実行して記事を取得
#         cursor.execute(query, params)
#         return [dict(row) for row in cursor.fetchall()]
#     finally:
#         conn.close()