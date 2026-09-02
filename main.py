from fastapi import FastAPI, Request, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import uuid
import requests
from typing import Dict, Any
from dotenv import load_dotenv

from chunker import clone_repo, chunk_repo, PythonChunker, python_chunker, javascript_chunker, ts_chunker, go_chunker, java_chunker, rust_chunker, cpp_chunker, fallback_chunker, ipynb_chunker
from embeddings import embed_chunks
from store import store_chunks
from search import rerank, get_chunks_from_db
from database import Chunk, SessionLocal
from debugger import graph 
from reviewer import graph_review 
from groq import Groq
import tree_sitter_python as tspython

load_dotenv() 
key = os.getenv("GROQ_KEY") 
client = Groq(api_key=key) # create a client
SUPPORTED_EXTENSIONS = [".py", ".js", ".jsx",".ts", ".tsx", ".go", ".java", ".rs", ".cpp", ".ipynb"]

app = FastAPI()

local_dir = None

class Reviewer(BaseModel):
    pr_url: str
    
class Debugger(BaseModel):
    repo_url: str
    error_msg: str
    local_dir: str
    
class Ingest(BaseModel):
    url: str
    local_dir: str

class QueryRequest(BaseModel):
    question: str
    repo_url: str = None
    

def run_review_background(pr_url: str):
    graph_review.invoke(
        {"pr_url": pr_url},
        config={"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    
@app.post('/ingest')
def ingest(request: Ingest):
    global local_dir
    local_dir = request.local_dir
    clone_repo(request.url, request.local_dir)
    chunks = chunk_repo(request.local_dir) 
    embeddings = embed_chunks(chunks)
    store_chunks(chunks, embeddings, repo_url=request.url)
    return {"message": f"Ingested {len(chunks)} chunks successfully"}

@app.post("/debug")
def debug(request: Debugger):
    result = graph.invoke({
        "error_msg": request.error_msg,
        "repo_url": request.repo_url,
        "retry_count": 0,
        "local_dir": request.local_dir
    }, config={"configurable": {"thread_id": str(uuid.uuid4())}}) 
    return {"pr_url": result.get("pr_url"), "validation": result.get("validation_results")}

@app.post('/review')
def review(request: Reviewer):
    result = graph_review.invoke({
        "pr_url" : request.pr_url,
    }, config={"configurable": {"thread_id": str(uuid.uuid4())}})
    return {"posted": result.get("posted")}
    
@app.post("/query")  
def query(request: QueryRequest):
    results = rerank(request.question, repo_url=request.repo_url)
    def generate():
        stream = client.chat.completions.create(
            model="openai/gpt-oss-120b", 
            messages=[
                {
                    "role": "system",
                    "content": "You are a codebase assistant. Only answer using the provided code context. If the context doesn't contain relevant information, say 'I cannot find relevant information in the codebase.' Do not use external knowledge." 
                }, 
                {
                    "role": "user",
                    "content": f"""Context: {[r["text"] for r in results]}\nQuestion: {request.question}"""
                }
            ], stream=True, 
            temperature=0.1 
        ) 
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/webhook")
async def github_webhook(payload: dict = Body(...)):
    
    # Secure API Headers for GitHub to avoid rate limits and access private repos
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    # Catch the simple PR URL sent by your Streamlit app
    if "pr_url" in payload:
        pr_url = payload["pr_url"]
        
        # Parse the GitHub URL: https://github.com/owner/repo/pull/5
        parts = pr_url.rstrip("/").split("/")
        if len(parts) < 4 or parts[-2] != "pull":
            return {"error": "Invalid GitHub PR URL format."}
            
        owner, repo, pr_number = parts[-4], parts[-3], parts[-1]
        
        # 1. Ask GitHub API which files changed in this PR using headers
        gh_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(gh_api_url, headers=headers)
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch PR details. Status: {response.status_code}"}
            
        pr_files = response.json()
        global local_dir
        
        with SessionLocal() as session:
            changed_files = []
            
            # 2. Loop through the changed files
            for file_data in pr_files:
                file_name = file_data.get("filename")
                
                if any(file_name.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    changed_files.append(file_name)
                    full_path = os.path.join(local_dir, file_name) if local_dir else file_name
                    
                    # 3. Wipe the old memory for this specific file
                    session.query(Chunk).filter(Chunk.file_path == full_path).delete()
                    
                    # 4. Fetch the new raw code directly from the PR branch on GitHub
                    raw_url = file_data.get("raw_url")
                    if raw_url:
                        raw_response = requests.get(raw_url, headers=headers)
                        if raw_response.status_code == 200:
                            content = raw_response.text
                            
                            # 5. Chunk, embed, and store
                            chunker = get_chunker_for_file(file_name)
                            file_chunks = chunker.chunk(content)
                            for chunk in file_chunks:
                                chunk["file_path"] = full_path
                            
                            embeddings = embed_chunks(file_chunks)
                            store_chunks(file_chunks, embeddings)
                            
            session.commit()
            return {"message": f"Successfully memorized {len(changed_files)} updated files from PR #{pr_number}."}
            
    return {"status": "Ignored event"}


def expand_query(question): 
    chat_completion = client.chat.completions.create( model="openai/gpt-oss-120b",
        messages=[{
            "role": "user", 
            "content": f"Generate 3 short search queries related to this question about code: '{question}'. Return only the queries separated by newlines, no explanations."
        }])
    expanded = chat_completion.choices[0].message.content.strip().split("\n")
    return [question] + expanded
                        
def search_with_expansion(question, repo_url=None, top_k=5):
    queries = expand_query(question)
    all_results = []
    seen = set()
    for q in queries:
        results = rerank(q, repo_url=repo_url)
        for r in results:
            key = r["file_path"] + str(r["start_line"])
            if key not in seen:
                all_results.append(r)
                seen.add(key)
    return all_results
        
def get_chunker_for_file(file_path):
    if file_path.endswith(".py"):
        return python_chunker
    elif file_path.endswith(".ipynb"):
        return ipynb_chunker
    elif file_path.endswith(".js") or file_path.endswith(".jsx"):
        return javascript_chunker
    elif file_path.endswith(".ts") or file_path.endswith(".tsx"):
        return ts_chunker
    elif file_path.endswith(".go"):
        return go_chunker
    elif file_path.endswith(".java"):
        return java_chunker
    elif file_path.endswith(".rs"):
        return rust_chunker
    elif file_path.endswith(".cpp"):
        return cpp_chunker
    