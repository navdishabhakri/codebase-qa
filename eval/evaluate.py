import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from golden_dataset import data
from chunker import chunk_repo
from search import rerank
from dotenv import load_dotenv
import os
import ollama
load_dotenv()
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from langchain_community.chat_models import ChatOllama

ollama_llm = LangchainLLMWrapper(ChatOllama(model="llama3.2", timeout=300))

embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)

def get_context_and_answers(chunks):
    for d in data:
        chunks = rerank(d["question"], chunks)
        d["contexts"] = [c["text"] for c in chunks]

        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": f"Context: {d['contexts']}\nQuestion: {d['question']}"}]
        )
        d["answer"] = response["message"]["content"]
    
chunks = chunk_repo("/Users/apple/Desktop/fastapi")
get_context_and_answers(chunks)
eval_dataset = Dataset.from_list(data)  

results = evaluate(
    eval_dataset,
    metrics=[
        faithfulness, 
        answer_relevancy,
        context_recall,
    ], 
    llm=ollama_llm, 
    embeddings=embeddings,
    raise_exceptions=False,
    batch_size=1,
)

print(results)
    