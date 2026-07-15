import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from src.models import (
    ArticleFeedback,
    ArticleLikeRequest,
    NewsListResponse,
    UserPreferencesRequest,
)
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
    limit: int = 10,               
    min_importance: int = 7,
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
            "lookback_days": lookback_days
        }
        news_list = crud.get_news_from_db(db, params)
        
        if not news_list:
            logger.warning("ニュースデータが見つかりませんでした")
            raise HTTPException(status_code=404, detail="ニュースデータが見つかりませんでした")
            
        return {"total_count": len(news_list), "rankedresponses": news_list}
    except Exception as e:
        logger.error(f"ニュースの取得に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="ニュースの取得に失敗しました")


@app.get("/v1/categories", response_model=List[str], tags=["Preferences"])
def get_available_categories():
    """
    フロントエンドのチェックボックス用に、選択可能なIT分野のマスターリストを返す。
    システムが認識している有効なカテゴリの一覧です。
    """
    # 将来的にDBやconfigから動的に引きたい場合は拡張可能
    available_categories = [
        "AI・LLM", 
        "Cloud・Infrastructure", 
        "CyberSecurity", 
        "Webフロントエンド", 
        "バックエンド・DevOps",
        "モバイルアプリ開発"
    ]
    return available_categories


# ==========================================
# 2. POST /v1/users/preferences
# ==========================================
@app.post("/v1/users/preferences", tags=["Preferences"])
def update_user_preferences(
    payload: UserPreferencesRequest, 
    db: DatabaseManager = Depends(get_db) # 綺麗なDI（依存性の注入）
):
    """
    ユーザーが画面のチェックボックスで選んだ興味分野を一括で保存する。
    裏側で「古い設定を一括削除 ➔ 新しい設定をループ挿入」する挙動をします。
    """
    try:
        crud.update_user_preferences_list(
            db=db, 
            user_id=payload.user_id, 
            categories=payload.categories
        )
        return {"status": "success", "message": f"User {payload.user_id}'s preferences updated successfully."}
    except Exception as e:
        logger.error(f"API Error in update_user_preferences: {e}")
        raise HTTPException(status_code=500, detail="興味分野の保存に失敗しました。")


# ==========================================
# 3. POST /v1/articles/{article_id}/like
# ==========================================
@app.post("/v1/articles/{article_id}/like", tags=["Feedback"])
def like_article(
    article_id: int, 
    payload: ArticleLikeRequest, 
    db: DatabaseManager = Depends(get_db)
):
    """
    タイムライン画面で記事の「いいね👍」ボタンが押されたときの処理を受け付ける。
    記事IDはパスから、ユーザーIDと状態はボディから安全に受け取ります。
    """
    try:
        # dataclassのArticleFeedbackオブジェクトを組み立ててCRUDに丸投げ！
        feedback_data = ArticleFeedback(
            user_id=payload.user_id,
            article_id=article_id,
            is_liked=payload.is_liked
        )
        crud.add_article_feedback(db=db, feedback=feedback_data)
        
        status_msg = "liked" if payload.is_liked else "unliked"
        return {"status": "success", "message": f"Article {article_id} has been {status_msg} by user {payload.user_id}."}
    except Exception as e:
        logger.error(f"API Error in like_article: {e}")
        raise HTTPException(status_code=500, detail="フィードバックの保存に失敗しました。")

@app.get("/health", tags=["System"])
def health_check():
    """
    Docker Engine用のヘルスチェックエンドポイント
    APIサーバーの死活監視に使用
    """
    # 将来的に「DB接続が生きているか」などのセルフテストをここに拡張可能
    return {"status": "healthy"}