from typing import Any
from groq import Groq
from chunker import clone_repo, chunk_repo, PythonChunker
from embeddings import embed_chunks
from store import store_chunks
from search import rerank
from dotenv import load_dotenv
import tree_sitter_python as tspython
from database import Chunk, SessionLocal
import httpx
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
load_dotenv() 
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client
_chunks_cache={}
import cohere
cohere_key = os.getenv("COHERE")
from search import vector_search
from embeddings import _get_model

mcp = FastMCP("codebase")

import sys
print(f"Python: {sys.executable}", flush=True)
print(f"Path: {sys.path}", flush=True)

print("Loading model...", flush=True)
_get_model()
print("Model ready", flush=True)

@mcp.tool()
def ingest_repo(url: str, local_dir: str) -> str:
    clone_repo(url , local_dir)
    chunks = chunk_repo(local_dir)
    _chunks_cache[local_dir] = chunks
    embeddings = embed_chunks(chunks)
    store_chunks(chunks,embeddings)
    return f"Ingested {len(chunks)} chunks successfully"

@mcp.tool()
def query_codebase(question: str, local_dir: str) -> str:
    vector_results = vector_search(question, top_k=10)
    
    # convert to dicts for reranker
    candidates = [{"text": r.chunk_text, "file_path": r.file_path, "start_line": r.start_line} for r in vector_results]
    
    # rerank
    co = cohere.ClientV2(cohere_key)
    response = co.rerank(
        model="rerank-v3.5",
        query=question,
        documents=[c["text"] for c in candidates],
        top_n=5
    )
    
    reranked = [candidates[r.index] for r in response.results]
    context = [r["text"] for r in reranked]
    
    chat_completion = client.chat.completions.create( model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user", 
            "content": f"Context: {context}\nQuestion: {question}"
        }])
    return chat_completion.choices[0].message.content

if __name__ == "__main__":
    mcp.run(transport="stdio")
    