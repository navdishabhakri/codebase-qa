from fastapi import FastAPI
from pydantic import BaseModel
from chunker import clone_repo, chunk_repo, PythonChunker, python_chunker, javascript_chunker, ts_chunker, go_chunker, java_chunker, rust_chunker, cpp_chunker, fallback_chunker
from embeddings import embed_chunks
from store import store_chunks
from search import rerank
from groq import Groq
from dotenv import load_dotenv
import os
import tree_sitter_python as tspython
from fastapi import Request
from database import Chunk, SessionLocal
from fastapi.responses import StreamingResponse
from search import get_chunks_from_db
from debugger import graph 
from reviewer import graph_review 
load_dotenv() 
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client
SUPPORTED_EXTENSIONS = [".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs", ".cpp"]

app = FastAPI()

local_dir = None

class Reviewer(BaseModel):
    pr_url: str
    
class Debugger(BaseModel):
    repo_url: str
    error_msg: str
    
class Ingest(BaseModel):
    url: str
    local_dir: str

class QueryRequest(BaseModel):
    question: str
    repo_url:str = None
    
@app.post('/ingest')
def ingest(request:Ingest):
    global local_dir
    local_dir = request.local_dir
    clone_repo(request.url , request.local_dir)
    chunks = chunk_repo(request.local_dir) # since database is empty it should get chunks first and in query it can easily fetch from db
    embeddings = embed_chunks(chunks)
    store_chunks(chunks,embeddings, repo_url = request.url)
    return {"message": f"Ingested {len(chunks)} chunks successfully"}

@app.post("/debug")
def debug(request:Debugger):
    result = graph.invoke({
        "error_msg": request.error_msg,
        "repo_url": request.repo_url,
        "retry_count":0
    },config={"configurable": {"thread_id": "1"}}) # config tells the memory checkpointer which conversation thread this belongs to.
    return {"pr_url": result.get("pr_url"), "validation": result.get("validation_results")}

@app.post('/review')
def review(request: Reviewer):
    result = graph_review.invoke({
        "pr_url" : request.pr_url,
    },config={"configurable": {"thread_id": "1"}})
    return {"posted":result.get("posted")}
    
    
    
@app.post("/query")  
def query(request: QueryRequest):
    results = search_with_expansion(request.question, repo_url = request.repo_url)
    def generate():
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {
                    "role": "system",
                    "content": "You are a codebase assistant. Only answer using the provided code context. If the context doesn't contain relevant information, say 'I cannot find relevant information in the codebase.' Do not use external knowledge." 
                }, #  instructions to the LLM about how to behave
                {
                    "role": "user",
                    "content": f"""Context: {[r["text"] for r in results]}\nQuestion: {request.question}"""
                }
            ], stream = True, 
            temperature = 0.1 
        ) 
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/webhook")
async def github_webhook(request: Request):
    with SessionLocal() as session:
        payload = await request.json()
        changed_files=[]
        for commit in payload["commits"]:
            for file in commit["modified"] + commit["added"]:
                if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    changed_files.append(file) 
                    session.query(Chunk).filter(Chunk.file_path == file).delete() # first delete
                    full_path = os.path.join(local_dir, file)
                    if os.path.exists(full_path):
                        with open(full_path, "r") as f:
                            content = f.read()
                        chunker = get_chunker_for_file(file) 
                        file_chunks = chunker.chunk(content)
                        for chunk in file_chunks:
                            chunk["file_path"] = full_path
                        embeddings = embed_chunks(file_chunks)
                        store_chunks(file_chunks, embeddings)
        session.commit()
        return {"message": f"Re-indexed {len(changed_files)} files"}

def expand_query(question): 
    chat_completion = client.chat.completions.create( model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user", 
            "content": f"Generate 3 short search queries related to this question about code: '{question}'. Return only the queries separated by newlines, no explanations."
        }])
    expanded= chat_completion.choices[0].message.content.strip().split("\n")
    return [question] + expanded
                        
def search_with_expansion(question, repo_url = None, top_k=5):
    queries = expand_query(question)
    all_results=[]
    seen=set()
    for q in queries:
        results= rerank(q, repo_url)
        for r in results:
            key = r["file_path"] + str(r["start_line"])
            if key not in seen:
                all_results.append(r)
                seen.add(key)
    return all_results
        
def get_chunker_for_file(file_path):
    if file_path.endswith(".py"):
        return python_chunker
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
                    
                    

            
        