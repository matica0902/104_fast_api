from fastapi import FastAPI, UploadFile, File, Query
import requests
import os
from pydantic import BaseModel
from typing import List
from urllib.parse import urljoin
from langserve import add_routes

# 導入 LangServe 服務函數
from app.server import search_document, search_vectorstore, search_104_jobs

app = FastAPI()

# 直接在主應用中添加 LangServe 路由
add_routes(app, search_document, path="/langserve/document")
add_routes(app, search_vectorstore, path="/langserve/vectorstore")
add_routes(app, search_104_jobs, path="/langserve/search_104")

# 啟用調試日誌
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 本地 LangServe URL(已整合到主應用)
INTERNAL_PORT = int(os.getenv('PORT', 8080))
LANGSERVE_URL = f"http://localhost:{INTERNAL_PORT}/langserve"
logger.info(f"LangServe URL配置為本地整合模式: {LANGSERVE_URL}")

class JobResult(BaseModel):
    title: str
    company: str
    link: str

@app.post("/document")
async def process_document_query(query: str, file: UploadFile = File(...)):
    """文件查詢API - 直接調用內部函數而不是通過HTTP請求"""
    logger.info(f"處理文件查詢 - 查詢: {query}")
    try:
        # 直接調用導入的函數
        result = search_document(query=query, file=file)
        return result
    except Exception as e:
        logger.error(f"處理文件查詢時發生錯誤: {str(e)}")
        return {"error": "處理文件查詢失敗", "detail": str(e)}

@app.get("/vectorstore")
async def process_vectorstore_query(query: str):
    """向量存儲查詢API - 直接調用內部函數而不是通過HTTP請求"""
    logger.info(f"處理向量存儲查詢 - 查詢: {query}")
    try:
        # 直接調用導入的函數
        result = search_vectorstore(query=query)
        return result
    except Exception as e:
        logger.error(f"處理向量存儲查詢時發生錯誤: {str(e)}")
        return {"error": "處理向量存儲查詢失敗", "detail": str(e)}

@app.get("/search_104")
async def process_search_104_query(
    keyword: str = Query(..., description="搜尋關鍵詞"), 
    end_page: int = Query(1, description="搜尋頁數", gt=0)
):
    """
    搜索104網站上的工作
    
    - **keyword**: 搜索關鍵字 (例如: Python, 數據分析)
    - **end_page**: 搜索的結束頁數 (默認: 1)
    """
    logger.info(f"處理104搜索請求 - 關鍵詞: {keyword}, 頁數: {end_page}")
    
    try:
        # 直接調用導入的函數，不通過HTTP請求
        result = search_104_jobs(keyword=keyword, end_page=end_page)
        logger.info(f"成功獲取搜索結果")
        return result
    except Exception as e:
        logger.error(f"處理104搜索請求時發生錯誤: {str(e)}")
        return {
            "error": "搜索請求處理失敗",
            "detail": str(e)
        }

@app.get("/", tags=["健康檢查"])
async def root():
    """
    根路由，提供健康檢查和API狀態資訊
    """
    return {
        "status": "online",
        "api_version": "1.0.0",
        "langserve_url": LANGSERVE_URL,
        "endpoints": {
            "/": "API健康檢查",
            "/search_104": "搜索104職缺",
            "/document": "文件查詢",
            "/vectorstore": "向量儲存查詢"
        }
    }

if __name__ == "__main__":
    import uvicorn
    # 使用主要的PORT環境變數，這是Railway會設置的
    port = int(os.getenv('PORT', 8080))
    logger.info(f"啟動FastAPI應用於端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)



