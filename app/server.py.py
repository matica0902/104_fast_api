from fastapi import FastAPI, UploadFile, File, Query
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Chroma
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.llms import OpenAI
from langserve import add_routes
import os
import requests
from bs4 import BeautifulSoup
import time

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def search_document(query: str, file: UploadFile = File(...)):
    """查詢上傳的文件"""
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    loader = TextLoader(file_path)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(texts, embeddings)
    docs = db.similarity_search(query)
    chain = load_qa_with_sources_chain(OpenAI(temperature=0), chain_type="stuff")
    answer = chain.run(input_documents=docs, question=query)

    os.remove(file_path)
    return answer

def search_vectorstore(query: str):
    """查詢向量資料庫"""
    texts = ["LangChain 是一個用於開發由語言模型驅動的應用程序的框架。", "它能讓你建立起語言模型與其他資料來源的連結。"]
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_texts(texts, embeddings)
    docs = db.similarity_search(query)
    chain = load_qa_with_sources_chain(OpenAI(temperature=0), chain_type="stuff")
    answer = chain.run(input_documents=docs, question=query)
    return answer

def get_job_details(job_url):
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

def search_104_jobs(keyword: str, end_page: int):
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
            page_data = {
                "page": current_page,
                "jobs": []
            }

            params = params_template.copy()
            params["page"] = current_page

            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            job_list = data.get("data", {}).get("list", [])
            if not job_list:
                continue

            for index, job in enumerate(job_list, 1):
                if isinstance(job, dict):
                    job_url = job.get("link", {}).get("job", "")

                    job_entry = {
                        "position_index": index,
                        "total_positions": len(job_list),
                        "job_name": job.get("jobName", ""),
                        "company": job.get("custName", ""),
                        "salary": job.get("salaryDesc", ""),
                        "job_url": job_url,
                        "details": {}
                    }

                    if job_url:
                        details = get_job_details(job_url)
                        job_entry["details"] = details

                    page_data["jobs"].append(job_entry)
                    time.sleep(1)

            final_result.append(page_data)
            time.sleep(2)

        return {
            "status": "success",
            "total_pages": len(final_result),
            "data": final_result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": final_result
        }

add_routes(app, search_document, path="/document")
add_routes(app, search_vectorstore, path="/vectorstore")
add_routes(app, search_104_jobs, path="/search_104")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
