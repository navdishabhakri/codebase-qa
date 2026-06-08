from transformers import pipeline
from transformers import AutoTokenizer, AutoModel
import torch
tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")
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
load_dotenv()

cohere_key = os.getenv("COHERE")

def embed_question(question):

        inputs = tokenizer(question, return_tensors="pt",truncation=True, max_length=512) # converts text to numbers and return pt meaning pytorch tensors. 
        # 2. Forward pass through the model
        with torch.no_grad(): 
            outputs = model(**inputs) #passes the tokenized input through CodeBERT
        cls_embedding = outputs.last_hidden_state[:, 0, :] #[batch, tokens, 768]. [:, 0, :] means "all batches, first token (CLS), all 768 dimensions".
        return cls_embedding.squeeze().tolist() # squeeze() removes the batch dimension so shape goes from [1, 768] to [768]

def vector_search(question, top_k=5):
    with SessionLocal() as session:
        question_embed= embed_question(question)
        stmt = (select(Chunk) .order_by(Chunk.embedding_vector.cosine_distance(question_embed)) .limit(top_k))
        result = session.scalars(stmt).all()
        return result #returns a list of Chunk SQLAlchemy objects

# you cannot do bm25 in SQL
def bm25_search(question,chunks,top_k=5):
    
    query = [chunk["text"].split() for chunk in chunks] #BM25 needs tokenized text — lists of words, not strings
    bm25 = BM25Okapi(query) #it calculates document frequencies, average document length, IDF for every word. 

    tokenized_question = question.split()
    scores = bm25.get_scores(tokenized_question) #computes a score for every chunk against your question. Returns an array of 5282 numbers.
    top_indices = np.argsort(scores)[::-1][:top_k] # the 5 highest scoring indices
    return [chunks[i] for i in top_indices] #  a list of chunk dicts

    
def reciprocal_rank_fusion(question,chunks, top_k=5, k=60):
    bm25_results = bm25_search(question, chunks, top_k)
    vector_results = vector_search(question, top_k)
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
        key_to_chunk[key] = chunk
    
    for chunk in vector_results:
        key = chunk.file_path + str(chunk.start_line)
        if key not in key_to_chunk:
            key_to_chunk[key] = {"text": chunk.chunk_text, "file_path": chunk.file_path, "start_line": chunk.start_line}
    
    return [key_to_chunk[k] for k in sorted_keys if k in key_to_chunk]
    
def rerank(question, chunks, top_k=5):
    result = reciprocal_rank_fusion(question,chunks, top_k)
    co = cohere.Client(cohere_key)

    response = co.rerank(
        model="rerank-v3.5",
        query=question,
        documents=[chunk["text"] for chunk in result],
        top_n=top_k,
    )

    reranked = []
    for r in response.results:
        reranked.append(result[r.index])
    return reranked



results= rerank("how does authentication work?",chunk_repo("/Users/apple/Desktop/fastapi"))
for r in results:
    print(r["file_path"], r["start_line"])