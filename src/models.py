from dataclasses import dataclass,asdict

# ニュース記事を表すデータクラス
@dataclass
class Batch:
    started_at: str
    ended_at: str
    status: str
    new_articles_count: int

    def to_dict(self):
        return asdict(self)

@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str
    published_at: str

    def to_dict(self):
        return asdict(self)

@dataclass
class ArticleAnalysis:
    article_id: int
    batch_id: int
    ai_summary: str
    importance: int
    reason: str
    category: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Ranking:
    article_id: int
    analyses_id: int
    batch_id: int
    rank: int

    def to_dict(self):
        return asdict(self)
