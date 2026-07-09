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
    id: int,
    title: str, 
    summary: str, 
    max_retries: int = config.GEMINI_MAX_RETRIES,
    user_preferences: str = config.USER_PREFERENCES
    ) -> Optional[Dict[str, Any]]:

    logger.info("Gemini分析開始")

    """記事のタイトルと要約をGemini APIに送信して分析結果を辞書で返す"""
    prompt = config.PROMPT_TEMPLATE.format(
        id=id,
        title=title, 
        summary=summary, 
        user_preferences=user_preferences
    )
    
    system_instruction = config.SYSTEM_INSTRUCTION

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=config.MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json", 
                    temperature=config.TEMPERATURE,
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(
                            mode="NONE"
                        )
                    )
                )
            )
            raw_text = response.text # Gemini APIからの生のテキストレスポンス
            logger.info("Gemini APIからのレスポンスを受信")
            result_list = json.loads(raw_text) # JSON形式のテキストを辞書に変換
            if isinstance(result_list, list) and len(result_list) > 0:
                return result_list[0]
            else:
                logger.error("Geminiからの出力がリスト形式ではありませんでした。")
                return None

        except Exception as e:
            error_str = str(e)
            # 💡 429（レート制限）に加えて、503（サーバー一時混雑）もリトライ対象にする
            is_temporary_error = (
                "429" in error_str 
                or "RESOURCE_EXHAUSTED" in error_str 
                or "503" in error_str 
                or "UNAVAILABLE" in error_str
            )

            if is_temporary_error:
                wait_time = config.GEMINI_SLEEP_SECONDS * (2 ** attempt)
                logger.warning(
                    f"一時的なAPIエラーを確認。"
                    f"{wait_time}秒後に自動リトライします。({attempt+1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                # 🛑 認証エラーやプログラムのバグなど、リトライしても無駄なものは即座に諦める
                logger.exception(f"回復不能なエラーのため、Gemini APIへのリクエストを中断します: {title}")
                return None

    # すべてのリトライ回数を使い切ってもダメだった場合
    logger.error(f"最大リトライ回数({max_retries}回)に達したため、この記事をスキップします: {title}")
    return None  # 💡 上位層(forループ)を止めないよう、例外を投げずにNoneを返して安全にスキップ


# Gemini 分析
def analyze_articles(articles: List[Article], batch_id: int) -> List[ArticleAnalysis]:
    """記事リストをGeminiで分析し、解析結果の辞書リストを返す。
    分析に失敗した記事はスキップする。
    """
    analyses_list = []
    # 複数RSSソースで同一URLが重複する場合に備え、article_id で一意化する
    seen_ids: set[int] = set()
    unique_articles = []
    for article in articles:
        if article.id is not None and article.id not in seen_ids:
            seen_ids.add(article.id)
            unique_articles.append(article)
    target_articles = unique_articles[:config.MAX_ARTICLES_PER_BATCH]

    for i, article in enumerate(target_articles):
        try:
            result = analyze_article_with_gemini(article.id, article.title, article.summary)

            if result:
                analyze = ArticleAnalysis(
                article_id=article.id,
                batch_id=batch_id,
                ai_summary=result.get("ai_summary", ""),
                importance=result.get("importance", 0),
                reason=result.get("reason", ""),
                category=result.get("category", ""),
            )
                analyses_list.append(analyze)
                logger.info(f"Gemini分析完了: {article.title} (重要度: {result.get('importance', 0)})")
            else:
                # 最大リトライに達して None が返ってきた場合
                logger.warning(f"分析失敗のため、ダミーレコードを生成します: {article.title}")
                # 失敗データ（重要度0）を作成して同じリストに混ぜる！
                analyses_list.append(ArticleAnalysis(
                    article_id=article.id,
                    batch_id=batch_id,
                    ai_summary="[分析失敗] APIエラーのため要約を生成できませんでした。",
                    importance=0,  # 0点にしておくことでランキングや通知の条件(>=6)から自動で外れる
                    category="Error"
                ))
                logger.info(f"ダミーレコードを生成します: {article.title}")

        except Exception as e:
            # 429/503以外の致命的なエラーで即座に諦める場合も同様にダミーを混ぜる
            logger.error(f"回復不能なエラーによるスキップ: {e}")
            analyses_list.append(ArticleAnalysis(
                article_id=article.id,
                batch_id=batch_id,
                ai_summary=f"[回復不能なエラー] {str(e)}",
                importance=0,
                category="Error"
            ))
            logger.info(f"ダミーレコードを生成します: {article.title}")

        # Gemini APIへのリクエスト間に少し待機する（連続リクエストを避けるため）
        if i < len(target_articles) - 1:
            time.sleep(config.GEMINI_SLEEP_SECONDS)

    return analyses_list