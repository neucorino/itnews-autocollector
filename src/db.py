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
        FOREIGN KEY (article_id) REFERENCES articles(id),
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

GET_NOTIFICATION_TARGETS = """
    SELECT 
        a.title,
        a.url,
        a.source,
        aa.ai_summary,
        aa.importance,
        aa.category,
        r.rank
    FROM rankings r
    JOIN articles a ON r.article_id = a.id
    JOIN article_analyses aa ON r.article_id = aa.article_id
    WHERE aa.importance >= :min_importance
    ORDER BY r.rank ASC
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
        # records = [a.to_dict() for a in analyses_list]
        records = []
        for a in analyses_list:
            d = a.to_dict()
            # もし辞書の中に analyzed_at がなければ、ここで現在の時刻を追加する
            if 'analyzed_at' not in d or d['analyzed_at'] is None:
                d['analyzed_at'] = datetime.now().isoformat()
                records.append(d)
        with self.conn:
            self.conn.executemany(INSERT_ANALYSES, records)
        logger.info(f"{len(analyses_list)}件の解析結果を一括処理しました。")
    
    def bulk_insert_rankings(self, rankings_list):
        if not rankings_list:
            logger.warning("保存するランキングデータがありません。")
            return
        records = [a.to_dict() for a in rankings_list]
        with self.conn:
            self.conn.executemany(INSERT_RANKING, records)
        logger.info(f"{len(rankings_list)}件のランキングを一括処理しました。")
    
    def start_new_batch(self):
        logger.info("バッチを開始します...")
        # 1. カーソルを作成
        cursor = self.conn.cursor()
        try:
            # 2. 実行
            cursor.execute(START_NEW_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'running'))
            # 3. IDを取得
            batch_id = cursor.lastrowid
            # 4. コミット（sqlite3では接続オブジェクトで行う）
            self.conn.commit()
            return batch_id
        finally:
            # 5. 必ずクローズする
            cursor.close()

    # バッチ終了を記録するメソッド（操作）
    def finish_batch(self, batch_id, status,count):
        """バッチの結果を更新する"""
        with self.conn:
            self.conn.execute(FINISH_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, count, batch_id))
        logger.info(f"バッチID:{batch_id} をステータス:{status} で完了しました。")

    def fetch_notification_targets(self, min_importance=config.IMPORTANCE_THRESHOLD):
        """通知対象をDBから取得する"""
        try:
            with self.conn:
                targets = self.conn.execute(GET_NOTIFICATION_TARGETS, (min_importance,)).fetchall()
            return [dict(t) for t in targets]
        except Exception as e:
            logger.error(f"通知対象の取得に失敗しました: {e}")
            raise