from fastapi import FastAPI, UploadFile, File, Query
import requests
import os
from pydantic import BaseModel
from typing import List

app = FastAPI()

# 從環境變數讀取 LangServe 服務的 URL，若未設定則使用預設值
# 支持多種可能的環境變數名稱，確保與Railway兼容
LANGSERVE_URL = os.getenv("LANGSERVE_URL") or os.getenv("LANGSERVE_ENDPOINT") or "http://127.0.0.1:8000"

# 啟用調試日誌
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"LangServe URL配置為: {LANGSERVE_URL}")

class JobResult(BaseModel):
    title: str
    company: str
    link: str

@app.post("/document")
async def process_document_query(query: str, file: UploadFile = File(...)):
    files = {"file": (file.filename, file.file, file.content_type)}
    params = {"query": query}
    response = requests.post(f"{LANGSERVE_URL}/document/", files=files, params=params)
    return response.json()

@app.get("/vectorstore")
async def process_vectorstore_query(query: str):
    params = {"input": {"query": query}}
    response = requests.get(f"{LANGSERVE_URL}/vectorstore/", params=params)
    return response.json()

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
    logger.info(f"收到搜索請求 - 關鍵詞: {keyword}, 頁數: {end_page}")
    
    # 建構API參數
    params = {"keyword": keyword, "end_page": end_page}
    search_url = f"{LANGSERVE_URL}/search_104/"
    
    try:
        # 直接執行搜索請求，不再進行測試請求
        logger.info(f"正在連接: {search_url} 使用參數: {params}")
        response = requests.get(search_url, params=params, timeout=30)
        
        # 檢查回應狀態
        if response.status_code != 200:
            logger.error(f"API返回錯誤狀態碼: {response.status_code}")
            logger.error(f"回應內容: {response.text[:500]}")
            return {
                "error": f"API返回錯誤狀態碼: {response.status_code}",
                "detail": response.text[:500]
            }
            
        # 處理回應
        try:
            result = response.json()
            logger.info(f"成功獲取搜索結果，共 {len(result) if isinstance(result, list) else '未知'} 項")
            return result
        except ValueError as e:
            logger.error(f"無法解析API回應為JSON: {str(e)}")
            return {"error": "無法解析API回應", "detail": str(e)}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"請求過程中發生錯誤: {str(e)}")
        # 根據錯誤類型提供更詳細的錯誤信息
        error_details = str(e)
        suggestion = ""
        
        if "NewConnectionError" in error_details or "Max retries exceeded" in error_details:
            suggestion = f"無法連接到LangServe服務。請確認服務是否運行且可在 {LANGSERVE_URL} 訪問"
        
        return {
            "error": "搜索請求失敗",
            "detail": error_details,
            "suggestion": suggestion
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



