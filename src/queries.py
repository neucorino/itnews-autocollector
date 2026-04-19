"""
it-news-system のデータベースクエリ定義モジュール
"""

# テーブル作成クエリ
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

# INSERT クエリ
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

# 通知対象取得クエリ
GET_NOTIFICATION_TARGETS = """
    SELECT
        a.id,
        a.title,
        a.url,
        a.source,
        aa.ai_summary,
        aa.importance,
        aa.category,
        r.rank
    FROM rankings r
    INNER JOIN articles a ON r.article_id = a.id
    INNER JOIN article_analyses aa ON r.analyses_id = aa.id
    WHERE r.batch_id = :batch_id
    ORDER BY r.rank ASC
    LIMIT :limit
"""

# ランキング取得クエリ
GET_RANKED_ARTICLES = """
    SELECT 
        a.id AS article_id, 
        aa.id AS analyses_id,
        aa.importance
    FROM articles a
    INNER JOIN article_analyses aa ON a.id = aa.article_id
    WHERE aa.id IN (
        SELECT MAX(id)
        FROM article_analyses 
        GROUP BY article_id
    )
    ORDER BY aa.importance DESC, a.published_at DESC
    LIMIT 10
"""
