import os
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

def get_gemini_summary(title: str) -> str:
    """
    Geminiを使用してニュースタイトルの要約・解説を生成する
    """
    if not GEMINI_API_KEY:
        return "APIキーが設定されていないため要約をスキップします。"
    
    prompt = f"""
    以下のITニュースのタイトルから、その内容を1文（50文字程度）で簡潔に要約し、
    エンジニアにとっての重要度を「高・中・低」で示してください。
    
    タイトル: {title}
    
    出力フォーマット:
    【要約】(要約内容) / 重要度: (高・中・低)
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", # 最新の高速モデルを使用
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"要約エラー: {e}"

def save_and_clean_csv(new_data, filename="it_news_database.csv", keep=30):
    # 列名に「要約」を追加
    columns = ["取得日", "サイト名", "記事タイトル", "URL", "要約"]
    new_df = pd.DataFrame(new_data, columns=columns)
    
    try:
        old_df = pd.read_csv(filename)
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
    except FileNotFoundError:
        combined_df = new_df

    combined_df["取得日"] = pd.to_datetime(combined_df["取得日"], errors='coerce')
    combined_df = combined_df.dropna(subset=["取得日"])
    
    limit_date = datetime.now() - timedelta(days=keep)
    clean_df = combined_df[combined_df["取得日"] > limit_date]
    clean_df = clean_df.drop_duplicates(subset=["記事タイトル"])

    clean_df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"📊 データベース更新完了: {len(clean_df)} 件のデータを保持")

# --- メイン処理 ---
urls = [
    {"name": "Zenn", "url": "https://zenn.dev/topics/it"},
    {"name": "はてブIT", "url": "https://b.hatena.ne.jp/hotentry/it"}
]

news_list = []

try:
    for target in urls:
        print(f"🌐 {target['name']} をスキャン中...")
        driver.get(target['url'])
        
        # 明示的な待機（最大10秒）
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))

        elements = driver.find_elements(By.TAG_NAME, "a")
        count = 0
        
        for el in elements:
            title = el.text.strip()
            link = el.get_attribute("href")
            
            if len(title) > 15 and link and link.startswith("http"):
                print(f"  📝 要約生成中: {title[:20]}...")
                # Geminiによる要約
                summary = get_gemini_summary(title)
                
                news_list.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    target['name'],
                    title,
                    link,
                    summary
                ])
                count += 1
            
            if count >= 3: # 各サイト上位3件
                break
    
    if news_list:
        save_and_clean_csv(news_list)

        # メール本文の構築
        mail_body = f"🚀 【最強PC】ITニュース要約配信 ({datetime.now().strftime('%Y/%m/%d %H:%M')})\n"
        mail_body += "="*40 + "\n\n"
        
        for item in news_list:
            mail_body += f"🔹 {item[2]}\n"
            mail_body += f"   {item[4]}\n" # 要約
            mail_body += f"   🔗 {item[3]}\n\n"
        
        mail_body += "-"*40 + "\nこのメールはWSL2物理サーバーから自動送信されました。"

        from my_utils import send_gmail
        send_gmail(
            subject=f"ITニュース要約 ({datetime.now().strftime('%m/%d')})",
            body=mail_body
        )
    
except Exception as e:
    print(f"❌ システムエラー: {e}")

finally:
    driver.quit()
    print("👋 ブラウザを終了しました。")