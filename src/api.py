import logging
from typing import List
from fastapi import FastAPI, Depends
from src.models import Article
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

# データベース操作を共通化するための関数
def get_db():
    return DatabaseManager()

@app.get("/", tags=["Root"])
def read_root():
    """APIの生存確認用"""
    return {"status": "online", "message": "API is connected to SQLite"}

@app.get("/news", response_model=List[Article], tags=["News"])
def get_news(db: DatabaseManager = Depends(get_db)):
    """DBから最新のニュースを取得して返却"""
    try:
        # DBからデータを取得
        news_list = db.get_news_from_db()
        
        if not news_list:
            logger.warning("ニュースデータが見つかりませんでした")
            return []
            
        return news_list
    except Exception as e:
        logger.error(f"APIエラーが発生しました: {e}")
        return []