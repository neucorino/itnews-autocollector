from dataclasses import dataclass,asdict,field
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


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
    # デフォルト値として現在の時刻を入れる設定
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)

@dataclass
class Ranking:
    article_id: int
    analyses_id: int
    batch_id: int
    rank: int
    rank_score: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


    def to_dict(self):
        return asdict(self)


#APIで画面に表示させる専用のモデル
class RankedArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    source: str
    ai_summary: Optional[str] = None
    importance: Optional[int] = None
    category: Optional[str] = None
    rank: Optional[int] = None
    rank_score: Optional[float] = None
    published_at: Optional[str] = None

# /news で返すリスト全体の設計図（件数なども含めると親切です）
class NewsListResponse(BaseModel):
    total_count: int
    rankedresponses: List[RankedArticleResponse]