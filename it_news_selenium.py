import os
import json
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
import logging
from logging.handlers import RotatingFileHandler
from my_utils import send_gmail

# ========================
# ⚙️ 設定値（全て集約）
# ========================
load_dotenv()

# APIキー
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Webドライバー設定
CHROMEDRIVER_PATH = '/usr/bin/chromedriver'
DRIVER_TIMEOUT = 10
WINDOW_SIZE = '1920,1080'

# ニュース収集設定
NEWS_SOURCES = [
    {"name": "Zenn", "url": "https://zenn.dev/topics/it"},
    {"name": "はてブIT", "url": "https://b.hatena.ne.jp/hotentry/it"}
]
MAX_ARTICLES_PER_SOURCE = 8
MAX_TOTAL_ARTICLES = 15

# CSV設定
CSV_FILENAME = "/home/yzen-64/projects/it-news-system/it_news_database.csv"
CSV_KEEP_DAYS = 30
CSV_COLUMNS = ["取得日", "サイト名", "記事タイトル", "URL", "要約"]

# ロギング設定
LOG_FILE = "it_news_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# メール設定
EMAIL_HEADER_SEPARATOR = "=" * 40
EMAIL_ITEM_SEPARATOR = "-" * 40
MAIL_SIGNATURE = "このメールはWSL2物理サーバーから自動送信されました。"

# ========================
# 🔧 ロギング初期化
# ========================
def setup_logger():
    """ロギングを設定して、loggerオブジェクトを返す"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logger()

# ========================
# 🌐 Seleniumドライバー初期化
# ========================
def create_chrome_driver():
    """Chromeドライバーを初期化して返す"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={WINDOW_SIZE}')
    
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)


# ========================
# 🤖 Gemini API用関数
# ========================
def process_news_batch(items):
    """
    複数のニュース記事をGemini APIで一括処理
    
    Args:
        items (list): 辞書のリスト。各要素は 'title', 'url' キーを持つ
    
    Returns:
        list: 'optimized_title', 'summary' が追加された辞書のリスト
    """
    if not items or not GEMINI_API_KEY:
        return []

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
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"Gemini APIに {len(items)} 件のリクエストを送信中...")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        logger.info("Gemini APIからのレスポンスを受信しました。")
        
        results = json.loads(response.text)
        for i, res in enumerate(results):
            items[i]['optimized_title'] = res.get('optimized_title', items[i]['title'])
            items[i]['summary'] = res.get('summary', '要約に失敗しました')
        return items

    except Exception as e:
        logger.error(f"Gemini一括処理で例外発生: {e}", exc_info=True)
        print(f"⚠️ Gemini一括処理エラー: {e}")
        for item in items:
            item['optimized_title'] = item['title']
            item['summary'] = "要約を生成できませんでした"
        return items


# ========================
# 💾 CSV操作関数
# ========================
def save_and_clean_csv(new_data, filename=CSV_FILENAME, keep_days=CSV_KEEP_DAYS):
    """
    新しいニュースデータをCSVに追加し、古いデータを削除
    
    Args:
        new_data (list): 追加する辞書のリスト
        filename (str): CSVファイルパス
        keep_days (int): 保持する日数
    """
    if not new_data:
        print("⚠️ 保存するデータがないため、CSV更新をスキップします。")
        return
    
    try:
        # 新しいデータをDataFrameに変換
        new_df = pd.DataFrame(new_data)
        new_df['date'] = pd.to_datetime(new_df['date'], errors='coerce')
        # print("--- [DEBUG] new_data の中身 ---")
        # print(new_df[['date']].head())  # 最初の方の数行だけ表示
        # print(new_df['date'].dtype)     # データの型（objectなら文字列、datetime64なら日付型）
        
        # 列名をマッピング
        column_mapping = {
            "date": "取得日",
            "site": "サイト名",
            "optimized_title": "記事タイトル",
            "url": "URL",
            "summary": "要約"
        }
        new_df = new_df.rename(columns=column_mapping)
        new_df = new_df[CSV_COLUMNS]
        
        # 既存CSVと統合
        if os.path.exists(filename):
            old_df = pd.read_csv(filename)
            # 既存の「取得日」も念のため日付型にしておく
            old_df["取得日"] = pd.to_datetime(old_df["取得日"], errors='coerce')
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        #print(f"DEBUG: 合体直後の件数: {len(combined_df)}") # ←追加
        
        # データ掃除：日付を正規化、古いデータを削除
        combined_df["取得日"] = pd.to_datetime(combined_df["取得日"], errors='coerce')
        combined_df = combined_df.dropna(subset=["取得日"])
        #print(f"DEBUG: 日付変換後の有効件数: {combined_df['取得日'].notna().sum()}") # ←追加
        limit_date = datetime.now() - timedelta(days=keep_days)
        clean_df = combined_df[combined_df["取得日"] > limit_date]
        
        # 重複削除（URLベース）
        clean_df = clean_df.drop_duplicates(subset=["URL"], keep='first')
        #print(f"DEBUG: 30日以内フィルタ後の件数: {len(clean_df)}") # ←追加
        # 保存
        clean_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"📊 CSV更新完了: 現在 {len(clean_df)} 件の記事を保存中")
        logger.info(f"CSV保存完了: {len(clean_df)} 件")
        
    except Exception as e:
        logger.error(f"CSV操作中にエラーが発生しました: {e}", exc_info=True)
        print(f"❌ CSV操作中にエラーが発生しました: {e}")


# ========================
# 📰 ニュース取得関数
# ========================
def fetch_news_items(driver, sources=NEWS_SOURCES, max_per_source=MAX_ARTICLES_PER_SOURCE):
    """
    複数のソースからニュース記事を取得
    
    Args:
        driver: Seleniumドライバー
        sources (list): Webソースのリスト
        max_per_source (int): 各ソースから取得する最大記事数
    
    Returns:
        list: 取得したニュース記事の辞書リスト
    """
    news_items = []
    
    for source in sources:
        print(f"🌐 {source['name']} をスキャン中...")
        logger.info(f"{source['name']} から記事を取得中...")
        
        try:
            driver.get(source['url'])
            wait = WebDriverWait(driver, DRIVER_TIMEOUT)
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
            
            elements = driver.find_elements(By.TAG_NAME, "a")
            count = 0
            
            for element in elements:
                title = element.text.strip()
                url = element.get_attribute("href")
                
                # 無効な記事を除外
                if not title or len(title) < 10:
                    continue
                if not url or not url.startswith("http"):
                    continue
                
                news_items.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "site": source['name'],
                    "title": title,
                    "url": url
                })
                count += 1
                
                if count >= max_per_source:
                    break
                    
        except Exception as e:
            logger.warning(f"{source['name']} の取得中にエラー: {e}")
            print(f"⚠️ {source['name']} の取得中にエラー: {e}")
    
    return news_items


# ========================
# 📧 メール本文構築関数
# ========================
def build_mail_content(news_items):
    """
    ニュース記事からメール本文を構築
    
    Args:
        news_items (list): 要約済みニュース記事の辞書リスト
    
    Returns:
        tuple: (件名, 本文)
    """
    subject = f"ITニュース要約 ({datetime.now().strftime('%m/%d')})"
    body = f"🚀 【最強PC】ITニュース配信 ({datetime.now().strftime('%Y/%m/%d %H:%M')})\n"
    body += EMAIL_HEADER_SEPARATOR + "\n\n"
    
    if not news_items:
        body += "現在主要なニュースはございません。\n"
    else:
        for item in news_items:
            body += f"🔹 {item['optimized_title']}\n"
            body += f"   {item['summary']}\n"
            body += f"   🔗 {item['url']}\n\n"
    
    body += EMAIL_ITEM_SEPARATOR + "\n" + MAIL_SIGNATURE
    
    return subject, body


# ========================
# 🚀 メイン処理
# ========================
def main():
    """メイン処理を実行"""
    driver = create_chrome_driver()
    
    try:
        logger.info("=== ニュース収集処理開始 ===")
        
        # 1. ニュース取得
        news_items = fetch_news_items(driver)
        news_items = news_items[:MAX_TOTAL_ARTICLES]
        logger.info(f"{len(news_items)} 件のニュース記事を取得")
        
        # 2. 要約・リライト
        summarized_news = process_news_batch(news_items)
        logger.info(f"{len(summarized_news)} 件のニュース要約完了")
        
        # 3. メール本文構築
        subject, body = build_mail_content(summarized_news)
        
        # 4. CSV保存
        if summarized_news:
            save_and_clean_csv(summarized_news)
        
        # 5. メール送信
        send_gmail(subject=subject, body=body)
        print("✅ 処理が正常に完了しました。")
        logger.info("メール送信完了")
        
    except Exception as e:
        logger.critical(f"システムが異常終了しました: {e}", exc_info=True)
        print(f"❌ システムエラー: {e}")
        
    finally:
        driver.quit()
        logger.info("=== ニュース収集処理終了 ===")


if __name__ == "__main__":
    main()