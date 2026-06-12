from fastapi import FastAPI
from pydantic import BaseModel
from chunker import clone_repo, chunk_repo, PythonChunker
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

load_dotenv() 
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client

app = FastAPI()

local_dir = None

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
    
@app.post("/query")  
def query(request: QueryRequest):
    results = rerank(request.question,repo_url= request.repo_url)
    def generate():
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {
                    "role": "user",
                    "content": f"""Use the following context to answer the question.
                    Context :
                    {[r["text"] for r in results]}
                    {request.repo_url}
                    Question :{request.question} """
                },
            ], stream = True,
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
                if file.endswith(".py"):
                    changed_files.append(file)
                    session.query(Chunk).filter(Chunk.file_path == file).delete() # first delete
                    full_path = os.path.join(local_dir, file)
                    if os.path.exists(full_path):
                        with open(full_path, "r") as f:
                            content = f.read()
                        chunker = PythonChunker()
                        file_chunks = chunker.chunk(content)
                        for chunk in file_chunks:
                            chunk["file_path"] = full_path
                        embeddings = embed_chunks(file_chunks)
                        store_chunks(file_chunks, embeddings)
        session.commit()
        return {"message": f"Re-indexed {len(changed_files)} files"}

                        
                        
                    
                    
                    

            
        