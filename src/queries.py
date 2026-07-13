"""
it-news-system のデータベースクエリ定義モジュール
"""

# ── テーブル作成クエリ ──────────────────────────────────────────
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
        FOREIGN KEY (batch_id)   REFERENCES batches(id),
        UNIQUE (article_id, batch_id)
    )
"""

CREATE_ARTICLE_ANALYSES_UNIQUE_INDEX = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_article_analyses_article_batch
    ON article_analyses (article_id, batch_id)
"""

CREATE_RANKINGS = """
    CREATE TABLE IF NOT EXISTS rankings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id  INTEGER NOT NULL,
        analyses_id INTEGER NOT NULL,
        batch_id    INTEGER NOT NULL,
        rank        INTEGER,
        rank_score  REAL NOT NULL,
        created_at  TEXT,
        FOREIGN KEY (article_id)  REFERENCES articles(id),
        FOREIGN KEY (analyses_id) REFERENCES article_analyses(id),
        FOREIGN KEY (batch_id)    REFERENCES batches(id)

    )
"""

CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        created_at TEXT
    )
"""

CREATE_USER_PREFERENCES = """
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
"""

CREATE_ARTICLE_FEEDBACKS = """
    CREATE TABLE IF NOT EXISTS article_feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        is_liked BOOLEAN NOT NULL,
        created_at TEXT,
        FOREIGN KEY (article_id) REFERENCES articles(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
"""

# ── INSERT クエリ ──────────────────────────────────────────────
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
    INSERT INTO rankings (article_id, analyses_id, batch_id, rank, rank_score, created_at)
    VALUES (:article_id, :analyses_id, :batch_id, :rank, :rank_score, :created_at)
"""

START_NEW_BATCH = """
    INSERT INTO batches (started_at, status) VALUES (:started_at, :status)
"""

FINISH_BATCH = """
    UPDATE batches 
    SET ended_at = :ended_at, status = :status, new_articles_count = :new_articles_count 
    WHERE id = :id
"""

# ── 通知対象取得クエリ ────────────────────────────────────────────
GET_NOTIFICATION_TARGETS = """
    SELECT
        a.id,
        a.title,
        a.url,
        a.source,
        a.published_at,
        aa.ai_summary,
        aa.importance,
        aa.category,
        r.rank,
        r.rank_score
    FROM rankings r
    INNER JOIN articles a ON r.article_id = a.id
    INNER JOIN article_analyses aa ON r.analyses_id = aa.id
    WHERE r.batch_id = :batch_id
      AND aa.importance >= :min_importance
      AND a.published_at >= datetime('now', '-' || :lookback_days || ' days')
    ORDER BY r.rank ASC
    LIMIT :limit
"""

GET_RANKED_ARTICLES_DYNAMIC = """
    WITH ranked AS (
        SELECT
            a.id AS article_id,
            a.published_at,
            aa.id AS analyses_id,
            aa.importance,
            julianday('now') - julianday(a.published_at) AS age_days
        FROM articles a
        JOIN article_analyses aa
            ON a.id = aa.article_id
        WHERE aa.importance >= :min_importance
        AND a.published_at >= datetime('now', '-' || :lookback_days || ' days')
        AND aa.id IN (
            SELECT MAX(id)
            FROM article_analyses
            GROUP BY article_id
        )
    )

    SELECT
        article_id,
        published_at,
        analyses_id,
        importance,
        age_days,
        ROUND(
            importance *
            CASE
                WHEN age_days < 1 THEN 1.00
                WHEN age_days < 2 THEN 0.95
                WHEN age_days < 3 THEN 0.90
                WHEN age_days < 4 THEN 0.85
                WHEN age_days < 5 THEN 0.60
                WHEN age_days < 6 THEN 0.40
                WHEN age_days < 7 THEN 0.20
                ELSE 0.00
            END ,2
        )AS rank_score
    FROM ranked
    ORDER BY 
        rank_score DESC,
        published_at DESC,
        article_id DESC

    LIMIT :ranking_limit
"""

# ── ユーザーの興味関心を表すクエリ ────────────────────────────────────────────

# クライアント指定の user_id を users に確保する（既存ならスキップ）
ENSURE_USER = """
    INSERT OR IGNORE INTO users (id, created_at)
    VALUES (:id, :created_at)
"""

# ユーザーの興味分野を保存/更新（既存があれば上書きするために一旦削除して挿入する戦略）
DELETE_PREFERENCES = """
    DELETE FROM user_preferences WHERE user_id = :user_id
"""

INSERT_PREFERENCE = """
    INSERT INTO user_preferences (user_id, category, updated_at)
    VALUES (:user_id, :category, :updated_at)
"""

# 記事のいいねを保存
INSERT_FEEDBACK = """
    INSERT INTO article_feedbacks (article_id, user_id, is_liked, created_at)
    VALUES (:article_id, :user_id, :is_liked, :created_at)
"""

# ユーザーの興味分野を取得
GET_PREFERENCES = """
    SELECT category FROM user_preferences WHERE user_id = :user_id
"""