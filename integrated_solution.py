"""
整合解決方案 - 直接實現所有功能，不依賴 langserve
"""

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
import requests
from bs4 import BeautifulSoup
import time
import os
import logging
from pydantic import BaseModel
from typing import List, Optional

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 檢查 OpenAI API 密鑰
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("未設置 OPENAI_API_KEY 環境變數，這可能會導致 AI 相關功能失敗")
else:
    logger.info("已設置 OPENAI_API_KEY 環境變數")

app = FastAPI(
    title="104 FastAPI 整合方案",
    description="搜索104工作、處理文檔和向量存儲查詢的集成API",
    version="1.0.0",
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class JobResult(BaseModel):
    title: str
    company: str
    link: str
    description: Optional[str] = None

def get_job_details(job_url):
    """抓取工作詳細信息"""
    if job_url.startswith('//'):
        job_url = 'https:' + job_url

    job_code = job_url.split('job/')[-1].split('?')[0]
    api_url = f'https://www.104.com.tw/job/ajax/content/{job_code}'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": job_url
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        job_data = response.json()
        return {
            "description": job_data.get("data", {}).get("jobDetail", {}).get("jobDescription", "")[:200],
            "requirements": job_data.get("data", {}).get("condition", {}).get("acceptRole", {}).get("description", "")[:200],
            "raw_data": job_data
        }
    except Exception as e:
        return {"error": str(e)}

def search_104_jobs_core(keyword: str, end_page: int):
    """搜索104網站上的工作，實際的爬蟲邏輯"""
    final_result = []
    base_url = "https://www.104.com.tw/jobs/search/list"

    params_template = {
        "ro": 0,
        "kwop": 7,
        "keyword": keyword,
        "order": 1,
        "page": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.104.com.tw/"
    }

    try:
        for current_page in range(1, end_page + 1):
            logger.info(f"正在抓取第 {current_page} 頁")

            params = params_template.copy()
            params["page"] = current_page

            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            jobs_in_page = data.get("data", {}).get("list", [])
            
            for job in jobs_in_page:
                job_name = job.get("jobName", "無標題")
                company_name = job.get("companyName", "未知公司")
                job_link = f"https://www.104.com.tw/job/{job.get('jobNo')}"
                
                job_result = JobResult(
                    title=job_name,
                    company=company_name,
                    link=job_link
                )
                
                # 獲取詳細信息
                details = get_job_details(job_link)
                if details and "error" not in details:
                    job_result.description = details.get("description", "")
                
                final_result.append(job_result)
            
            # 防止請求過於頻繁
            if current_page < end_page:
                time.sleep(1)
                
    except Exception as e:
        logger.error(f"搜索過程中出錯: {e}")
    
    return final_result

def simple_document_search(query: str, file_path: str):
    """簡化版的文檔查詢實現，不使用 LangChain"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 簡單的關鍵字匹配
        found = query.lower() in content.lower()
        
        return {
            "query": query,
            "found": found,
            "answer": f"文檔中{'找到' if found else '未找到'}查詢詞: {query}",
            "context": content[:300] + "..." if len(content) > 300 else content
        }
    except Exception as e:
        logger.error(f"處理文檔時出錯: {e}")
        return {"error": str(e), "message": "處理文檔時發生錯誤"}

def simple_vectorstore_search(query: str):
    """簡化版的向量搜尋實現，不使用 LangChain"""
    # 這裡只是一個占位實現，沒有 OpenAI 依賴
    sample_texts = [
        "LangChain 是一個用於開發由語言模型驅動的應用程序的框架。",
        "它能讓你建立起語言模型與其他資料來源的連結。"
    ]
    
    # 簡單的關鍵字匹配
    matched_texts = [text for text in sample_texts if query.lower() in text.lower()]
    
    return {
        "query": query,
        "answer": f"找到 {len(matched_texts)} 個相關結果",
        "matched_sources": matched_texts
    }

@app.post("/document")
async def process_document_query(query: str, file: UploadFile = File(...)):
    """文件查詢API"""
    logger.info(f"處理文件查詢 - 查詢: {query}")
    try:
        # 將上傳的文件保存
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # 處理查詢
        result = simple_document_search(query, file_path)
        
        # 清理臨時文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return result
    except Exception as e:
        logger.error(f"處理文件查詢時發生錯誤: {str(e)}")
        return {"error": "處理文件查詢失敗", "detail": str(e)}

@app.get("/vectorstore")
async def process_vectorstore_query(query: str):
    """向量存儲查詢API"""
    logger.info(f"處理向量存儲查詢 - 查詢: {query}")
    try:
        result = simple_vectorstore_search(query)
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
        results = search_104_jobs_core(keyword, end_page)
        logger.info(f"成功獲取搜索結果，共 {len(results)} 個職位")
        return {"results": results}
    except Exception as e:
        logger.error(f"處理104搜索請求時發生錯誤: {str(e)}")
        return {
            "error": "搜索請求處理失敗",
            "detail": str(e)
        }

@app.get("/")
async def root():
    """
    根路由，提供健康檢查和API狀態資訊
    """
    return {
        "status": "online",
        "api_version": "1.0.0",
        "endpoints": {
            "/": "API健康檢查",
            "/search_104": "搜索104職缺",
            "/document": "文件查詢",
            "/vectorstore": "向量儲存查詢"
        }
    }

# 維持與原始 langserve 路徑的兼容性
@app.post("/langserve/document")
async def langserve_document_query(query: str, file: UploadFile = File(...)):
    """LangServe 兼容的文檔查詢端點"""
    return await process_document_query(query, file)

@app.get("/langserve/vectorstore")
async def langserve_vectorstore_query(query: str):
    """LangServe 兼容的向量存儲查詢端點"""
    return await process_vectorstore_query(query)

@app.get("/langserve/search_104")
async def langserve_search_104_query(
    keyword: str = Query(..., description="搜尋關鍵詞"), 
    end_page: int = Query(1, description="搜尋頁數", gt=0)
):
    """LangServe 兼容的104搜索端點"""
    return await process_search_104_query(keyword, end_page)