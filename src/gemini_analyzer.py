from google import genai
from google.genai import types
import config
from logger import setup_logger

# どのモジュールから出たログか識別する
logger = logging.getLogger(__name__)

def analyze_article_with_gemini(title: str, summary: str) -> dict:
    logger.info("Gemini分析開始")
    
    """記事のタイトルと要約をGemini APIに送信して分析結果を辞書で返す"""
    prompt = f"""
    以下の記事をITエンジニアの視点で分析してください。
    【タイトル】: {title}
    【内容】: {summary}
    出力形式は以下のJSON形式にしてください
    {{
        "summary": "3行で要約した文章、必ず日本語で記述すること",
        "importance": 1から10の数値,
        "reason": "重要度の理由、必ず日本語で記述すること",
        "category": "技術カテゴリ"
    }}"""
    
    system_instruction = """
    あなたは、30年の経験を持つシニアソフトウェアエンジニア兼技術評論家です。
    「実用的な生成AI（LLM）の活用」と「主要ツールの新機能」に最も高い関心を持っています。
    提供されるタイトルから、以下の基準で厳格にスコアリングしてください。

    【最優先：通知対象（7〜9点）】
    ・主要AI（Gemini, ChatGPT, Claude, Grok）の「新機能」「APIアップデート」「公式の活用ガイド」。
    ・既存の生成AIを使った「実戦的な開発手法」「プロンプトエンジニアリングの新機軸」。
    ・大手テック企業（Google, OpenAI, Anthropic, Microsoft, NVIDIA）による実用的なAI発表。

    【興味あり：保留（5〜6点）】
    ・インフラ/ハードウェア（GPU/VM）のベンチマークや性能比較。
    ・特定の開発者向けツール、新しいライブラリ、GitHubリポジトリの紹介。
    ・CPUでの推論最適化など、すぐには使わないが技術的に筋の良い試み。

    【低優先：除外（1〜4点）】
    ・8-9点相当の内容だが、まだ「論文（arXiv）」段階の未実装技術（一律 4点程度に下げる）。
    ・IT・ソフトウェアに直接関係ない科学、美術、一般ニュース（一律 1点）。
    ・OSやデバイスの「噂（Possible, Rumor）」レベルの記事。

    【出力形式】
    必ず以下のJSON形式のみで回答してください。
    {
    "summary": "タイトルから推測される内容を1行で記述（日本語）",
    "importance": 数値(1-10),
    "reason": "なぜその点数か。ユーザーの関心（実用AI>理論/論文）に基づき記述（日本語）",
    "category": "技術カテゴリ"
    }
    """

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", 
                temperature=config.TEMPERATURE)
        )
        raw_text = response.text # Gemini APIからの生のテキストレスポンス
        
    except Exception as e:
        logger.error(f"Gemini APIへのリクエストに失敗しました: {e}")
        return None
