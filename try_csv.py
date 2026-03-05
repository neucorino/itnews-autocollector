from datetime import datetime, timedelta
import pandas as pd
import os

#

# CSVファイルにデータを追加
# new_row = {
#             "取得日": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "サイト名": "Hacker News",
#             "記事タイトル": title,
#             "URL": link,
#             "reason": analysis.get("reason", ""),
#             "要約": analysis.get("summary", "")
#             }
# 1. ファイルが存在するかチェック
#file_exists = os.path.exists(CSV_FILENAME)
# 2. DataFrameを作る
#df = pd.DataFrame([new_row])

df = pd.read_csv('/home/yzen-64/projects/it-news-system/it_news_database.csv')

df["取得日"] = pd.to_datetime(df["取得日"], errors='coerce')
df = df.dropna(subset=["取得日"])
print(df["取得日"])