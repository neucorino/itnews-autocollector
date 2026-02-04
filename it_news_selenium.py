from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import csv
from datetime import datetime, timedelta
import time
import pandas as pd

# --- 設定 ---
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Ubuntuのパスを指定
service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

# 収集したいURLリスト
urls = [
    {"name": "Zenn", "url": "https://zenn.dev/topics/it"},
    {"name": "はてなブックマークIT", "url": "https://b.hatena.ne.jp/hotentry/it"}
]

news_list = []
filename = "it_news_database.csv"

def save_and_clean_csv(new_data, filename= "it_news_database.csv", keep=30):
        # 新しいデータをDataFrameにする
        new_df = pd.DataFrame(new_data, columns=["取得日", "サイト名", "記事タイトル", "URL"])
        try:
            # 既存のCSVを読み込む
            old_df = pd.read_csv(filename)
            # 合体させる
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        except FileNotFoundError:
            combined_df = new_df

        # 「取得日」を日付型に変換して、古いデータを捨てる
        combined_df["取得日"] = pd.to_datetime(combined_df["取得日"], errors='coerce')
        # 日付に変換できなかった行（見出しとか）をここで削除しておく
        combined_df = combined_df.dropna(subset=["取得日"])
        limit_date = datetime.now() - timedelta(days=keep)
    
        # 保存期間内のデータだけ残す（フィルタリング）
        clean_df = combined_df[combined_df["取得日"] > limit_date]
    
        # 重複を削除（同じタイトルの記事は1つに）
        clean_df = clean_df.drop_duplicates(subset=["記事タイトル"])

        # 上書き保存
        clean_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"📊 データベースを更新したよ。{keep}日分をキープ中！")

try:
    for target in urls:
        print(f"🌐 {target['name']} を読み込み中...")
        driver.get(target['url'])
        time.sleep(3)  # 読み込み待ち

        # サイトごとにタグの構成が違うから、とりあえず共通で取れそうな「タイトル」を探す
        # aタグ（リンク）の中からテキストがあるものを抽出
        elements = driver.find_elements(By.TAG_NAME, "a")
        count = 0
        for el in elements:
            title = el.text.strip()
            link = el.get_attribute("href")
            # 文字数が少なすぎるものやリンクがないものは無視（ゴミ取り）
            if len(title) > 10 and link:
                news_list.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    target['name'],
                    title,
                    link
                ])
                count += 1
            #3トピックを選ぶ
            if count >= 3:
                break
    
    if news_list:
        # 保存と掃除
        save_and_clean_csv(news_list)

        # メールの本文（body）をここで組み立てる！
        mail_body = "【最強PC：ITニュース配信】\n\n"
        for item in news_list:
            # item[1]:サイト名, item[2]:タイトル, item[3]:URL
            mail_body += f"🔹 {item[2]}\n({item[1]})\n🔗 {item[3]}\n\n"
        
        mail_body += "---\nこのメールは最強PCが自動送信したよ！"

        # 共通関数を呼んで送信！
        from my_utils import send_gmail # ここでインポート
        send_gmail(
            subject=f"今日のITニュース ({datetime.now().strftime('%m/%d')})",
            body=mail_body
        )
    
except Exception as e:
    print(f"❌ エラーが発生したよ：{e}")

finally:
    driver.quit()
    print("👋 ブラウザを閉じたよ。")