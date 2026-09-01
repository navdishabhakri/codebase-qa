from embeddings import _get_model
from database import engine, SessionLocal, Chunk
from sqlalchemy import insert, select
from dotenv import load_dotenv
import os
from embeddings import embed_chunks
from chunker import chunk_repo 
from rank_bm25 import BM25Okapi
import numpy as np
import cohere 
import os
import torch
load_dotenv()

cohere_key = os.getenv("COHERE")


def get_chunks_from_db(repo_url=None):
    with SessionLocal() as session:
        if repo_url:
            chunks = session.query(Chunk).filter(Chunk.repo_url == repo_url).all()
        else:
            chunks = session.query(Chunk).all()
        return [{"text": c.chunk_text, "file_path": c.file_path, "start_line": c.start_line} for c in chunks]
    
def embed_question(question):
        tokenizer, model = _get_model()
        inputs = tokenizer(question, return_tensors="pt",truncation=True, max_length=512) # converts text to numbers and return pt meaning pytorch tensors. 
        # 2. Forward pass through the model
        with torch.no_grad(): 
            outputs = model(**inputs) #passes the tokenized input through CodeBERT
        cls_embedding = outputs.last_hidden_state[:, 0, :] #[batch, tokens, 768]. [:, 0, :] means "all batches, first token (CLS), all 768 dimensions".
        return cls_embedding.squeeze().tolist() # squeeze() removes the batch dimension so shape goes from [1, 768] to [768]

def vector_search(question, top_k=5, repo_url = None): #finds semantically similar chunks.
    with SessionLocal() as session:
        question_embed= embed_question(question)
        stmt = (select(Chunk) .order_by(Chunk.embedding_vector.cosine_distance(question_embed)) .limit(top_k)) # less distance more similar
        
        if repo_url:
            stmt = (select(Chunk).where(Chunk.repo_url == repo_url) .order_by(Chunk.embedding_vector.cosine_distance(question_embed)) .limit(top_k)) # less distance more similar
        
        result = session.scalars(stmt).all()
        return result #returns a list of Chunk SQLAlchemy objects

_bm25_cache={}
# you cannot do bm25 in SQL
def bm25_search(question,chunks,top_k=5,repo_url=None): # finds exact keyword matches.
    if not chunks:
        return []
    cache_key = repo_url if repo_url else "default_repo"
    if cache_key not in _bm25_cache or _bm25_cache[cache_key]["chunk_count"] != len(chunks):
        query_corpus = [chunk["text"].split() for chunk in chunks]
        bm25 = BM25Okapi(query_corpus)
        _bm25_cache[cache_key] = {
            "index": bm25,
            "chunk_count": len(chunks)
        }
    # Retrieve the cached index
    bm25 = _bm25_cache[cache_key]["index"]

    tokenized_question = question.split()
    scores = bm25.get_scores(tokenized_question) 
    top_indices = np.argsort(scores)[::-1][:int(top_k)] 
    
    return [chunks[i] for i in top_indices]


    
def reciprocal_rank_fusion(question, top_k=5, k=60, repo_url =None):
    chunks = get_chunks_from_db(repo_url=repo_url)
    bm25_results = bm25_search(question, chunks, top_k,repo_url=repo_url)
    vector_results = vector_search(question, top_k, repo_url=repo_url)
    scores={}
    
    for rank, chunk in enumerate(bm25_results, start = 1): # to make rank start at 1 
        key = chunk["file_path"] + str(chunk["start_line"])
        scores[key] =  scores.get(key, 0) + 1 / (60 + rank)  # gets value of that chunk everytime it appears and add 1/60+rank to it, rank is the position of the chunk
    
    for rank, chunk in enumerate(vector_results, start = 1):
        key = chunk.file_path + str(chunk.start_line)
        scores[key] =  scores.get(key, 0) + 1 / (60 + rank)
         
    # Sort the scores
    sorted_keys = sorted(scores, key=scores.get, reverse=True)[:top_k] # With scores.get it compares the score values.
    
    key_to_chunk={}
    for chunk in bm25_results:
        key = chunk["file_path"] + str(chunk["start_line"])
        key_to_chunk[key] =  chunk # we have two keys so that its unique like auth.py9 and auth.py45 both gets saved
    
    for chunk in vector_results:
        key = chunk.file_path + str(chunk.start_line)
        if key not in key_to_chunk:
            key_to_chunk[key] = {"text": chunk.chunk_text, "file_path": chunk.file_path, "start_line": chunk.start_line}
    
    return [key_to_chunk[k] for k in sorted_keys if k in key_to_chunk]
    
def rerank(question, top_k=5, repo_url = None):
    result = reciprocal_rank_fusion(question, top_k, repo_url = repo_url) # returns array
    if not result:
        return []
    co = cohere.Client(cohere_key)

    response = co.rerank(
        model="rerank-v3.5",
        query=question,
        documents=[chunk["text"] for chunk in result],
        top_n=top_k,
    )

    # Build the final reranked list using the indices returned by Cohere's rerank API.
    # response.results is a list of objects that include the original index of each
    # document in the provided `documents` list. We use that index to pick the
    # corresponding chunk from `result` and preserve the new ranking order.
    reranked = []
    for r in response.results: 
        reranked.append(result[r.index])
    return reranked

