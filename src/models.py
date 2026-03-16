from dataclasses import dataclass

# ニュース記事を表すデータクラス
@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str
    published_at: str
