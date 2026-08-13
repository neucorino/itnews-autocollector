"""
it-news-system のカスタム例外定義モジュール
"""


class NewsSystemException(Exception):
    """
    news system の基本例外クラス
    すべてのカスタム例外がこれを継承する
    """
    pass


class RSSFetchError(NewsSystemException):
    """
    RSS フェッチ処理に失敗した場合に raise
    """
    pass


class GeminiAnalysisError(NewsSystemException):
    """
    Gemini API での記事分析に失敗した場合に raise
    （最大リトライ回数に達した場合）
    """
    pass


class DatabaseError(NewsSystemException):
    """
    データベース操作に失敗した場合に raise
    """
    pass


class EmailSendError(NewsSystemException):
    """
    メール送信に失敗した場合に raise
    """
    pass


class ConfigValidationError(NewsSystemException):
    """
    設定値の検証に失敗した場合に raise
    """
    pass
