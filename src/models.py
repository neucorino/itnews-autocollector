from dataclasses import dataclass

@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: str