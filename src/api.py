import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from src.models import NewsListResponse
from src.config import API_TITLE, API_DESCRIPTION, API_VERSION
from src.db import DatabaseManager

# ログの設定
logger = logging.getLogger(__name__)

# FastAPIのインスタンス作成
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
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
    category: str | None = None,             
    min_importance: int = 0,
    batch_id: int = 1,
    db: DatabaseManager = Depends(get_db)
):
    """DBから最新のニュースを取得して返却"""
    try:
        # DBからデータを取得
        params = {
            "min_importance": min_importance,
            "limit": limit,
            "category": category,  # カテゴリフィルタを追加
            "batch_id": batch_id,  # バッチIDを追加
            "skip": skip
        }
        news_list = db.get_news_from_db(params)
        
        if not news_list:
            logger.warning("ニュースデータが見つかりませんでした")
            raise HTTPException(status_code=404, detail="ニュースデータが見つかりませんでした")
            
        return {"total_count": len(news_list), "rankedresponses": news_list}
    except Exception as e:
        logger.error(f"ニュースの取得に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="ニュースの取得に失敗しました")