from google import genai
from google.genai import types
from models import ArticleAnalysis
import config
import logging
import json

# どのモジュールから出たログか識別する
logger = logging.getLogger(__name__)

#Gemini APIの呼び出しとプロンプトの設定
def analyze_article_with_gemini(title: str, summary: str) -> dict:
    logger.info("Gemini分析開始")

    """記事のタイトルと要約をGemini APIに送信して分析結果を辞書で返す"""
    prompt = config.PROMPT_TEMPLATE.format(title=title, summary=summary)
    
    system_instruction = config.SYSTEM_INSTRUCTION

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
        logger.info("Gemini APIからのレスポンスを受信")
        result = json.loads(raw_text) # JSON形式のテキストを辞書に変換
        return result
        
    except Exception as e:
        logger.exception(f"Gemini APIへのリクエストに失敗しました")
        return None


# Gemini 分析
def analyze_articles(articles: list, batch_id: int) -> list:
    """記事リストをGeminiで分析し、解析結果の辞書リストを返す。
    分析に失敗した記事はスキップする。
    """
    analyses_list = []
    for article in articles:
        # articleオブジェクトからidを取得（ここが article_id になる）
        current_article_id = getattr(article, 'id', None) 
        result = analyze_article_with_gemini(article.title, article.summary)

        if not result:
            logger.warning(f"Gemini分析失敗(スキップ): {article.title}")
            continue

        analyze = ArticleAnalysis(
            article_id=current_article_id,
            batch_id=batch_id,
            ai_summary=result.get("ai_summary", ""),
            importance=result.get("importance", 0),
            reason=result.get("reason", ""),
            category=result.get("category", ""),
        )

        analyses_list.append(analyze)

        logger.info(f"Gemini分析完了: {article.title} (重要度: {result.get('importance', 0)})")

    return analyses_list