import feedparser
import requests
import csv  # CSVを扱うための道具
from datetime import datetime
import os
from my_utils import send_gmail

# 取得するソース
NEWS_SOURCES = {
    "Zenn (最新)": "https://zenn.dev/feed",
    "はてなブックマーク (IT)": "https://b.hatena.ne.jp/hotentry/it.rss"
}

def collect_itnews():
    # 今日の日付を取得
    today = datetime.now().strftime("%Y-%m-%d")
    filename = "it_news.csv"
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    news_list = []

    print("📰 ニュースを収集してCSVにまとめるよ...")

    for source_name, url in NEWS_SOURCES.items():
        try:
            print(f"📡 {source_name} をチェック中...")
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:10]: # 各サイト上位10件
                news_list.append([
                    today,
                    source_name,
                    entry.title,
                    entry.link
                ])
        except Exception as e:
            print(f"❌ {source_name} の取得失敗: {e}")

    # CSVファイルに書き込み
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        # ヘッダー（見出し）を書く
        writer.writerow(["取得日", "サイト名", "記事タイトル", "URL"])
        # 中身を書く
        writer.writerows(news_list)

    print(f"\n✅ 完成！ {filename} に保存したよ。")

    # ニュースをメールで送るよ
    news_body = "本日のITニュースをお届けします！\n\n"
    
    for source_name, url in NEWS_SOURCES.items():
        # （中略：ニュースを収集する処理）
        response = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        news_body += f"■ {source_name}\n"
        
        for entry in feed.entries[:5]:
            title = entry.title
            link = entry.link
            # 本文用に一行ずつ足していく
            news_body += f"・{title}\n  {link}\n"
        news_body += "\n" # サイトごとの区切り
    
    # 最後に、my_utilsから呼び出した関数にこの本文を渡す！
    send_gmail(subject = "今日のITニュース", body = news_body)
    return news_body
print("メール送ったよ")

if __name__ == "__main__":
    collect_itnews()