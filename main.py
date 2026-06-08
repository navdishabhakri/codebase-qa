from fastapi import FastAPI
from pydantic import BaseModel
from chunker import clone_repo, chunk_repo
from embeddings import embed_chunks
from store import store_chunks
from search import rerank
from groq import Groq
from dotenv import load_dotenv
import os
import tree_sitter_python as tspython

load_dotenv() 
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client

app = FastAPI()


class Ingest(BaseModel):
    url: str
    local_dir: str

class QueryRequest(BaseModel):
    question: str
    local_dir: str
    
@app.post('/ingest')
def ingest(request:Ingest):
    clone_repo(request.url , request.local_dir)
    chunks = chunk_repo(request.local_dir)
    embeddings = embed_chunks(chunks)
    store_chunks(chunks,embeddings)
    return {"message": f"Ingested {len(chunks)} chunks successfully"}
    

@app.post("/query")  
def query(request: QueryRequest):
    chunks = chunk_repo(request.local_dir)
    results = rerank(request.question,chunks)
    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[
            {
                "role": "user",
                "content": f"""Use the following context to answer the question.
                Context :
                {[r["text"] for r in results]}
                Question :{request.question} """
            },
        ],
    )
    return chat_completion.choices[0].message.content

    