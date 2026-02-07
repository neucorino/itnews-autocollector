import os
from google import genai
from dotenv import load_dotenv

# 1. 環境変数の読み込み
load_dotenv()

# 2. クライアントの初期化
# 有料枠（Pay-as-you-go）でも書き方は同じやで！
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 3. 2026年最新モデルでのテスト
# リストにあった 'gemini-2.0-flash' を指定
model_id = 'gemini-2.0-flash'

print(f"--- {model_id} でテスト開始 ---")

try:
    response = client.models.generate_content(
        model=model_id,
        contents="「最強PC」へようこそ！と元気よく挨拶して。また、APIの有料枠が有効になったことをお祝いして！"
    )
    
    print("\nGeminiからの返信:")
    print("-" * 30)
    print(response.text)
    print("-" * 30)
    print("\n✅ 動作確認完了！これでニュース要約もバッチリや。")

except Exception as e:
    print(f"\n❌ エラーが発生したわ：\n{e}")