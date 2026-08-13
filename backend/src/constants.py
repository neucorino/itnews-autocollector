"""
it-news-system のアプリケーション定数定義モジュール
"""

# メール関連の定数
EMAIL_RANK_EMOJIS = ["🥇", "🥈", "🥉", "📌", "📌"]
EMAIL_DIGEST_TITLE = "🧠 ITニュースダイジェスト（直近{lookback}日）"
EMAIL_TREND_SECTION_TITLE = "📌 今日の傾向"
EMAIL_TREND_ITEMS = [
    "・AI関連ニュースが多め",
    "・大手テック企業の動きが活発",
]
EMAIL_SEPARATOR = "----------------------------------"

# ランキング関連の定数
TOP_RANKED_ARTICLES_LIMIT = 10
