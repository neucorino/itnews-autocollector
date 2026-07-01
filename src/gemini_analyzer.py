from typing import Optional, Dict, Any, List
from src.exceptions import GeminiAnalysisError
from google import genai
from google.genai import types
from src.models import Article,ArticleAnalysis
from src import config
import logging
import json
import time

# どのモジュールから出たログか識別する
logger = logging.getLogger(__name__)

#Gemini APIの呼び出しとプロンプトの設定
def analyze_article_with_gemini(
    title: str, 
    summary: str, 
    max_retries: int = config.GEMINI_MAX_RETRIES
    ) -> Optional[Dict[str, Any]]:

    logger.info("Gemini分析開始")

    """記事のタイトルと要約をGemini APIに送信して分析結果を辞書で返す"""
    prompt = config.PROMPT_TEMPLATE.format(title=title, summary=summary)
    
    system_instruction = config.SYSTEM_INSTRUCTION

    for attempt in range(max_retries):
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
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = config.GEMINI_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(f"429エラー。{wait_time}秒後にリトライ ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.exception(f"Gemini APIへのリクエストに失敗しました")
                return None

    logger.error(f"最大リトライ回数到達: {title}")
    raise GeminiAnalysisError(f"Gemini分析失敗（最大リトライ回数到達）: {title}")


# Gemini 分析
def analyze_articles(articles: List[Article], batch_id: int) -> List[ArticleAnalysis]:
    """記事リストをGeminiで分析し、解析結果の辞書リストを返す。
    分析に失敗した記事はスキップする。
    """
    analyses_list = []
    target_articles = articles[:config.MAX_ARTICLES_PER_BATCH]

    for i, article in enumerate(target_articles):
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

        # Gemini APIへのリクエスト間に少し待機する（連続リクエストを避けるため）
        if i < len(target_articles) - 1:
            time.sleep(config.GEMINI_SLEEP_SECONDS)

    return analyses_list