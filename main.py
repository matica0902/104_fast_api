from fastapi import FastAPI, UploadFile, File, Query
import requests
from pydantic import BaseModel
from typing import List

app = FastAPI()

LANGSERVE_URL = "http://127.0.0.1:8000"

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
async def process_search_104_query(keyword: str = Query(...), end_page: int = Query(...)):
    params = {"keyword": keyword, "end_page": end_page}
    response = requests.get(f"{LANGSERVE_URL}/search_104/", params=params)
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
