import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google import genai
from google.genai import types

# .envの読み込み
load_dotenv()

# --- Gemini 設定 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- Selenium 設定 ---
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

def process_news_batch(items):
    """
    最大15件のニュースを一括で要約・リライトする
    """
    if not items or not GEMINI_API_KEY:
        return []

    # プロンプトの構築
    titles_input = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(items)])
    
    prompt = f"""
    以下のITニュース記事のリストを処理してください。
    
    【処理ルール】
    1. 各記事のタイトルを、内容を損なわず50文字以内で魅力的にリライトしてください。
    2. 各記事の内容を1文（50文字程度）で要約し、重要度（高・中・低）を判定してください。
    3. 出力は必ず以下のJSON形式の配列で返してください。
    
    JSON形式例:
    [
      {{"id": 1, "optimized_title": "リライト後のタイトル", "summary": "【要約】内容 / 重要度: 高"}},
      ...
    ]

    【対象リスト】
    {titles_input}
    """

    try:
        # JSONモードでレスポンスを取得
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # JSONをパースして元のデータと結合
        results = json.loads(response.text)
        for i, res in enumerate(results):
            items[i]['optimized_title'] = res.get('optimized_title', items[i]['title'])
            items[i]['summary'] = res.get('summary', '要約に失敗しました')
        
        return items
    except Exception as e:
        print(f"⚠️ Gemini一括処理エラー: {e}")
        # エラー時は元のタイトルを使用し、要約をエラーメッセージにする
        for item in items:
            item['optimized_title'] = item['title']
            item['summary'] = "要約を生成できませんでした"
        return items

def save_and_clean_csv(new_data, filename="it_news_database.csv", keep=30):
    if not new_data: return
    
    columns = ["取得日", "サイト名", "記事タイトル", "URL", "要約"]
    # DataFrame作成用に整形
    rows = [[d['date'], d['site'], d['optimized_title'], d['url'], d['summary']] for d in new_data]
    new_df = pd.DataFrame(rows, columns=columns)
    
    try:
        old_df = pd.read_csv(filename)
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
    except FileNotFoundError:
        combined_df = new_df

    combined_df["取得日"] = pd.to_datetime(combined_df["取得日"], errors='coerce')
    combined_df = combined_df.dropna(subset=["取得日"])
    limit_date = datetime.now() - timedelta(days=keep)
    clean_df = combined_df[combined_df["取得日"] > limit_date].drop_duplicates(subset=["記事タイトル"])
    clean_df.to_csv(filename, index=False, encoding="utf-8-sig")

# --- メイン処理 ---
urls = [
    {"name": "Zenn", "url": "https://zenn.dev/topics/it"},
    {"name": "はてブIT", "url": "https://b.hatena.ne.jp/hotentry/it"}
]

raw_news_items = []

try:
    for target in urls:
        print(f"🌐 {target['name']} をスキャン中...")
        driver.get(target['url'])
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))

        elements = driver.find_elements(By.TAG_NAME, "a")
        count = 0
        for el in elements:
            title = el.text.strip()
            link = el.get_attribute("href")
            
            # 無効な記事の除外（条件3）
            if not title or title == "不明" or len(title) < 10:
                continue
            if not link or not link.startswith("http"):
                continue

            raw_news_items.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "site": target['name'],
                "title": title,
                "url": link
            })
            count += 1
            if count >= 8: # 各サイトから多めに取って後で絞る（合計15件程度にするため）
                break

    # 最大15件に絞り込み
    raw_news_items = raw_news_items[:15]

    # 一括要約・リライト処理（条件1, 2）
    processed_news = process_news_batch(raw_news_items)

    # メール本文の構築
    mail_subject = f"ITニュース要約 ({datetime.now().strftime('%m/%d')})"
    mail_body = f"🚀 【最強PC】ITニュース配信 ({datetime.now().strftime('%Y/%m/%d %H:%M')})\n"
    mail_body += "="*40 + "\n\n"

    if not processed_news:
        # 空リストへの対応（条件4）
        mail_body += "現在主要なニュースはございません。\n"
    else:
        for item in processed_news:
            mail_body += f"🔹 {item['optimized_title']}\n"
            mail_body += f"   {item['summary']}\n"
            mail_body += f"   🔗 {item['url']}\n\n"
        
        save_and_clean_csv(processed_news)

    mail_body += "-"*40 + "\nこのメールはWSL2物理サーバーから自動送信されました。"

    from my_utils import send_gmail
    send_gmail(subject=mail_subject, body=mail_body)
    print("✅ 処理が正常に完了しました。")

except Exception as e:
    print(f"❌ システムエラー: {e}")

finally:
    driver.quit()