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
import re
from urllib.parse import urlparse

# ========================
# ⚙️ 設定値（全て集約）
# ========================
load_dotenv()

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model_id = "gemini-2.0-flash"
TEMPERATURE = 0.2

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

def is_noise_url(url) :
    """
    ニュース収集システム用：記事ではないノイズURLを厳格に判定する。
    
    Args:
        url (str): 判定対象のURL
    
    Returns:
        bool: ノイズ(除外対象)であれば True, 読むべき記事なら False
    """
    
    # ---------------------------------------------------------
    # 1. Zenn (zenn.dev) - 厳格なホワイトリスト判定
    # ---------------------------------------------------------
    if 'zenn.dev' in url:
        # 【許可パターン】
        # 構成: ドメイン / ユーザーID / タイプ(articles等) / スラッグ(1文字以上)
        # 注意: 末尾に "/edit" や "/preview" がつくものは除外対象
        allow_pattern = r'zenn\.dev/[^/]+/(articles|scraps|books)/[^/]+$'
        
        # URLからクエリパラメータ(?以降)やフラグメント(#以降)を除去して判定
        clean_url = url.split('?')[0].split('#')[0].rstrip('/')

        # 許可パターンにマッチしないものは、ユーザーTOP、一覧、Topicsを含め全てノイズ
        if not re.search(allow_pattern, clean_url):
            return True
            
        # 許可パターンにはマッチしたが、編集画面などはノイズ
        if re.search(r'/(edit|preview|dashboard|analytics)', url):
            return True

        # ここまで残ったものだけが「純粋な記事」
        return False

    # ---------------------------------------------------------
    # 2. はてなブックマーク (b.hatena.ne.jp) - ブラックリスト判定
    # ---------------------------------------------------------
    if 'b.hatena.ne.jp' in url:
        # これらは記事そのものではなく、管理画面や一覧、ラッパーページ
        hatena_noise = [
            r'/entry/s/',   # HTTPSサイトのブックマークページ (記事へのリンク集に近い)
            r'/site/',      # 特定ドメインの記事一覧
            r'/search',     # 検索結果
            r'/guide',      # ガイド
            r'/hotentry',   # 人気エントリー一覧
            r'/entrylist',  # 新着エントリー一覧
            r'/ct/',        # カテゴリ一覧
            r'/my',         # マイページ
            r"ad-hatena\.com",
            r"zenn\.dev/topics/",
            r"zenn\.dev/settings",
        ]
        if any(re.search(p, url) for p in hatena_noise):
            return True

    # ---------------------------------------------------------
    # 3. 汎用ブラックリスト (SNS, ログイン, 設定, ファイル)
    # ---------------------------------------------------------
    general_noise = [
        # SNSシェア用リンク
        r'(twitter|x|facebook|line|linkedin)\.com/(share|intent|sharer)',
        
        # システム・管理系
        r'/(login|signin|signup|register|auth|password)',
        r'/(settings|preferences|notifications|account)',
        r'/(search|find|query)\?',
        r'/rss(\.xml)?$',
        r'/feed/?$',
        
        # ユーザープロフィール系 (汎用的なパス)
        # ※誤爆を防ぐため、ドメインを絞るか慎重に適用が必要だが、
        #   Qiitaなどの主要サイト向けにパターンを追加
        r'qiita\.com/[^/]+/(items|following|followers|feed)', # Qiitaのユーザーサブページ
        r'qiita\.com/tags/', # タグ一覧
    ]

    if any(re.search(p, url) for p in general_noise):
        return True

    return False

# --- 動作検証 ---
if __name__ == "__main__":
    test_cases = [
        # --- Zenn (期待値: 記事のみFalse, それ以外True) ---
        ("https://zenn.dev/user/articles/python-tips-123", False),  # 記事詳細 -> OK
        ("https://zenn.dev/user/scraps/scrap-id-999", False),        # スクラップ詳細 -> OK
        ("https://zenn.dev/user/articles", True),                    # 記事一覧(ノイズ) -> OK
        ("https://zenn.dev/user", True),                             # ユーザーTOP -> OK
        ("https://zenn.dev/topics/python", True),                    # トピック一覧 -> OK
        ("https://zenn.dev/p/topic-name", True),                     # トピック詳細 -> OK
        ("https://zenn.dev/user/articles/slug/edit", True),          # 編集画面 -> OK
        
        # --- Hatena (期待値: 記事本体ではないページはTrue) ---
        ("https://b.hatena.ne.jp/entry/s/zenn.dev/articles/...", True), # ブックマークページ -> OK
        ("https://b.hatena.ne.jp/site/zenn.dev", True),              # ドメイン一覧 -> OK
        ("https://b.hatena.ne.jp/hotentry/it", True),                # ホットエントリー -> OK
        
        # --- General ---
        ("https://twitter.com/share?url=...", True),                 # シェアリンク -> OK
    ]

    print(f"{'URL':<60} | {'Is Noise?':<10} | {'Status'}")
    print("-" * 85)
    for url, expected in test_cases:
        result = is_noise_url(url)
        status = "PASS" if result == expected else "FAIL"
        print(f"{url[:57]+'...':<60} | {str(result):<10} | {status}")

# ========================
# 🤖 Gemini API用関数
# ========================
def process_news_batch(items):
    """
    複数のニュース記事をGemini APIで一括処理
    
    Args:
        items (list): 辞書のリスト。各要素は 'ID', 'title', 'url' キーを持つ
    
    Returns:
        list: 'optimized_title', 'summary' ,'analysis', 'score' が追加された辞書のリスト
    """
    if not items or not GEMINI_API_KEY:
        return []
    
    # interests.txtからユーザーの興味関心を読み込む
    interests_path = '/home/yzen-64/projects/it-news-system/interests.txt'
    if os.path.exists(interests_path):
        with open(interests_path, 'r', encoding='utf-8') as f:
            user_interests = f.read()
    else:
        user_interests = "IT全般、最新技術動向" # ファイルがない場合のデフォルト

    titles_input = "\n".join([f"ID:{i+1} | Title: {item['title']} | URL: {item.get('url', 'N/A')}" for i, item in enumerate(items)])
    
    # Gemini APIへのプロンプトを構築
    prompt = f"""
    【Role】
    あなたは「情報の質」に妥協を許さない、超合理主義なシニアエンジニア向けの技術顧問です。
    提供されたニュース記事を、ユーザーの【関心事】に基づき、以下の【評価指標】でステップバイステップに分析し、その結果をJSON形式で出力してください。
    あなたの時間は極めて貴重であり、読むに値しない「ゴミ記事」を推薦した部下には即座に解雇を言い渡します。

    【ユーザーの関心事】
    {user_interests}

    【評価指標（各10点満点で内部評価）】
    1. 関心事合致度: ユーザーの関心事と技術スタックにどれだけ直結するか
    2. 技術的密度: コード、アーキテクチャ、具体的なTipsが含まれているか
    3. 再現性・即効性: すぐに試せるか、または具体的なアクションに繋がるか
    4. 将来性・普及性: 一過性の流行ではなく、今後の標準技術になるか
    5. 信頼性・ノイズ排除: 宣伝や釣り記事ではなく、信頼できる情報源か

    【Step-by-Step Analysis (Chain of Thought)】
    以下の手順で記事を冷徹に査定してください。
    1. **形式チェック**: 
    - これは「記事本体」か？ それとも「一覧画面」「プロフィール」「ログインページ」か？
    - 記事でない場合は、その時点で Score: 1 とし分析を終了せよ。

    2. **ターゲット層の特定**:
    - 対象読者は「プロフェッショナル」か「初心者」か？
    - 「やってみた」「基礎解説」「入門」という単語が含まれる場合、シニア向けではないと判断せよ。

    3. **情報の密度 (Information Density)**:
    - 記事の中に「具体的なコード」「ベンチマークデータ」「アーキテクチャ図」「未公開のTips」が含まれているか？
    - 表面的なニュースの要約（コピペ）に過ぎない場合は厳しく減点せよ。

    4. **最終審判**:
    - 以上の分析を踏まえ、シニアエンジニアが「今日、この5分を割いて読む価値があるか」を自問自答し、スコアを出せ。

    【拒絶命令】
    - 宣伝目的のプレスリリースは無視せよ。
    - 「AIで稼ぐ方法」のような低俗なトピックは即座に Score: 1 とせよ。
    - 具体的実装のない「未来予想図」は不要だ。

    【処理・出力手順】
    各記事について、以下のJSONフォーマットで出力してください。
    - summary: 記事の要約（3行以内）
    - analysis: 各指標のスコア根拠（思考プロセス）
    - score: 最終的な総合重要度（1-5の5段階評価）
    - optimized_title: エンジニア向けにリライトされたタイトル

    出力は必ず以下のJSON配列形式のみとし、他のテキストは含めないでください：
    [
    {{
        "id": 1,
        "optimized_title": "...",
        "summary": "...",
        "analysis": "...",
        "score": 5
    }}
    ]

    【対象記事リスト】
    {titles_input}
    """

    try:
        # Geminiクライアントを初期化してAPIリクエストを送信
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"Gemini APIに {len(items)} 件のリクエストを送信中...")

        # APIからのレスポンスを受信
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=TEMPERATURE)
        )

        logger.info("Gemini APIからのレスポンスを受信しました。")
        
        #JSONとしてパース
        results = json.loads(response.text)
        # 結果を元のアイテムにマージ
        for i, item in enumerate(items):
            # IDで紐付け（Geminiの出力順が正しい前提だが、念のためIDチェック）
            analysis_data = results[i] if i < len(results) else {}
            item['optimized_title'] = analysis_data.get('optimized_title', item['title'])
            item['summary'] = analysis_data.get('summary', '分析失敗')
            item['analysis'] = analysis_data.get('analysis', '')
            item['score'] = analysis_data.get('score', 0)
            
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
        # 【ここでノイズ除去】日付変換などの重い処理の前に、行数を減らしておく
        # is_noise_urlがTrueを返すものを除去
        new_df = new_df[~new_df['url'].apply(is_noise_url)].copy()
        new_df['date'] = pd.to_datetime(new_df['date'], errors='coerce')
        
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
        limit_date = datetime.now() - timedelta(days=keep_days)
        clean_df = combined_df[combined_df["取得日"] > limit_date]
        
        # 重複削除（URLベース）
        clean_df = clean_df.drop_duplicates(subset=["URL"], keep='first')

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