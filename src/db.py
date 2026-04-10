import sqlite3
import models
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)


# テーブル作成の変数を定義
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

# published_at は RSS の RFC 形式のため datetime(published_at) は NULL になりがち。
# ランキングと同様に raw 値と datetime('now', ...) を直接比較する。
# 同一記事に複数の分析行がある場合は、重要度→分析日時→id の順で1件に絞る。
GET_NOTIFICATION_TARGETS = """
    WITH candidates AS (
        SELECT
            a.id,
            a.title,
            a.url,
            a.source,
            aa.ai_summary,
            aa.importance,
            aa.category,
            aa.analyzed_at,
            ROW_NUMBER() OVER (
                PARTITION BY a.id
                ORDER BY aa.importance DESC, aa.analyzed_at DESC, aa.id DESC
            ) AS rn
        FROM articles a
        INNER JOIN article_analyses aa ON aa.article_id = a.id
        WHERE a.published_at >= datetime('now', :since)
          AND aa.importance >= :min_importance
    )
    SELECT id, title, url, source, ai_summary, importance, category
    FROM candidates
    WHERE rn = 1
    ORDER BY importance DESC, analyzed_at DESC, title ASC
    LIMIT :limit
"""



# データベース管理クラス
class DatabaseManager:
    # __init__ 
    def __init__(self,db_path=config.DB_PATH):
        # sqlite3はファイルパスを指定して接続
        self.conn = sqlite3.connect(db_path)
        # sqlite3で辞書形式でデータを取れるようにする設定
        self.conn.row_factory = sqlite3.Row
        logger.info(f"DB接続を開始: {db_path}")
        self.create_tables() # インスタンス化した時にテーブルがなければ作る
    
    
    # テーブルを作成するメソッド（操作）
    def create_tables(self) -> None:
        """テーブルが存在しない場合に作成する。"""
        with self.conn:
            for ddl in (CREATE_BATCHES, CREATE_ARTICLES, CREATE_ARTICLE_ANALYSES, CREATE_RANKINGS):
                self.conn.execute(ddl)
        logger.info("テーブルを作成しました。")
    

    # 記事リストに一括でinsertするメソッド（操作）
    def bulk_insert_articles(self, articles_list):
        """記事リストを一括でinsertする。URLが重複する場合はスキップ。"""
        for article in articles_list:
            cursor = self.conn.execute(INSERT_ARTICLE, article.to_dict())
            self.conn.commit()
            
            if cursor.lastrowid:
                article.id = cursor.lastrowid  # 新規保存された場合
            else:
                # INSERT OR IGNOREでスキップされた場合、URLで既存のidを取得
                row = self.conn.execute(
                    "SELECT id FROM articles WHERE url = ?", (article.url,)
                ).fetchone()
                if row:
                    article.id = row[0] 
        logger.info(f"{len(articles_list)}件の記事を一括処理しました。")
        return articles_list  # idが入った状態で返す


    # 分析結果を一括でinsertするメソッド（操作）
    def bulk_insert_analyses(self, analyses_list):
        records = []
        for a in analyses_list:
            d = a.to_dict()
            if 'analyzed_at' not in d or d['analyzed_at'] is None:
                d['analyzed_at'] = datetime.now().isoformat()
            records.append(d)
    
        logger.info(f"保存しようとしているrecords[0]: {records[0] if records else 'リストが空'}")  # ←追加
        logger.info(f"recordsの件数: {len(records)}")  # ←追加
    
        try:  # ←tryで囲む
            with self.conn:
                self.conn.executemany(INSERT_ANALYSES, records)
            logger.info(f"{len(records)}件保存成功")
        except Exception as e:
            logger.exception(f"INSERT失敗")  # ←これで本当のエラーが見える
    
    
    # ランキングを一括でinsertするメソッド（操作）
    def bulk_insert_rankings(self, rankings_list):
        if not rankings_list:
            logger.warning("保存するランキングデータがありません。")
            return
        records = [a.to_dict() for a in rankings_list]
        with self.conn:
            self.conn.executemany(INSERT_RANKING, records)
        logger.info(f"{len(rankings_list)}件のランキングを一括処理しました。")
    

    # バッチ開始を記録するメソッド（操作）
    def start_new_batch(self):
        logger.info("バッチを開始します...")
        res = self.conn.execute(START_NEW_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'running'))
        self.conn.commit()
        return res.lastrowid


    # バッチ終了を記録するメソッド（操作）
    def finish_batch(self, batch_id, status,count):
        """バッチの結果を更新する"""
        with self.conn:
            self.conn.execute(FINISH_BATCH, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, count, batch_id))
        logger.info(f"バッチID:{batch_id} をステータス:{status} で完了しました。")


    # 通知対象を取得するメソッド（操作）
    def fetch_notification_targets(
        self,
        min_importance=config.IMPORTANCE_THRESHOLD,
        lookback_days=config.NOTIFICATION_LOOKBACK_DAYS,
        limit=config.MAX_NOTIFICATION_COUNT,
        ):
        """過去N日・重要度しきい値以上を満たす記事を、記事ごとに1行（代表の分析）で取得する。"""
        since = f"-{int(lookback_days)} days"
        params = {
            "since": since,
            "min_importance": min_importance,
            "limit": int(limit),
        }
        try:
            with self.conn:
                targets = self.conn.execute(GET_NOTIFICATION_TARGETS, params).fetchall()
            return [dict(t) for t in targets]
        except Exception as e:
            logger.exception(f"通知対象の取得に失敗しました")
            raise