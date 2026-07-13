import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.models import NewsListResponse, UserPreferencesRequest, FeedbackRequest
from src import config
from src import crud
from src.db import DatabaseManager

# ログの設定
logger = logging.getLogger(__name__)

# FastAPIのインスタンス作成
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)
"""CORSの設定"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"], # GET, POST, PUT, DELETEなどをすべて許可
    allow_headers=["*"] # すべてのHTTPヘッダーを許可
)

# データベース操作を共通化するための関数
def get_db():
    return DatabaseManager()

@app.get("/", tags=["Root"])
def read_root():
    """APIの生存確認用"""
    return {"status": "online", "message": "API is connected to SQLite"}

@app.get("/news",response_model=NewsListResponse, tags=["News"])
def get_news(
    skip: int = 0,
    limit: int = 20,               
    min_importance: int = 0,
    batch_id: int = 1,
    lookback_days: int = 7,
    db: DatabaseManager = Depends(get_db)
):
    """DBから最新のニュースを取得して返却"""
    try:
        # DBからデータを取得
        params = {
            "min_importance": min_importance,
            "limit": limit,
            "batch_id": batch_id,  # バッチIDを追加
            "skip": skip,
            "lookback_days": lookback_days
        }
        news_list = db.get_news_from_db(params)
        
        if not news_list:
            logger.warning("ニュースデータが見つかりませんでした")
            raise HTTPException(status_code=404, detail="ニュースデータが見つかりませんでした")
            
        return {"total_count": len(news_list), "rankedresponses": news_list}
    except Exception as e:
        logger.error(f"ニュースの取得に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="ニュースの取得に失敗しました")


@app.post("/users/preferences", tags=["User Preferences"])
def set_user_preferences(request: UserPreferencesRequest):
    """
    ユーザーがチェックボックスで選んだ興味のあるIT分野を一括保存・更新する
    """
    try:
        # 一括更新用の関数をcrud側に任せる
        crud.update_user_preferences_list(request.user_id, request.categories)
        return {"status": "success", "message": "興味分野を更新しました"}
    except Exception as e:
        logger.error(f"興味分野の保存に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="興味分野の保存に失敗しました")


@app.post("/articles/{article_id}/like", tags=["Feedback"])
def toggle_article_like(article_id: int, request: FeedbackRequest):
    """
    記事に対する「いいね👍」のフィードバックを保存する
    """
    try:
        # dataclassの型に合わせてオブジェクトを生成
        feedback_data = ArticleFeedback(
            article_id=article_id,
            user_id=request.user_id,
            is_liked=request.is_liked
        )
        crud.save_article_feedback(feedback_data)
        return {"status": "success", "message": "フィードバックを記録しました"}
    except Exception as e:
        logger.error(f"フィードバックの保存に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="フィードバックの保存に失敗しました")


@app.get("/health", tags=["System"])
def health_check():
    """
    Docker Engine用のヘルスチェックエンドポイント
    APIサーバーの死活監視に使用
    """
    # 将来的に「DB接続が生きているか」などのセルフテストをここに拡張可能
    return {"status": "healthy"}