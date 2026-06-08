import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from golden_dataset import data
from chunker import chunk_repo
from search import rerank
from groq import Groq
from dotenv import load_dotenv
import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper

embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_KEY"))
from ragas.llms import LangchainLLMWrapper
from langchain_groq import ChatGroq

groq_llm = LangchainLLMWrapper(ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_KEY")
))

def get_context_and_answers(chunks):
    for d in data:
        chunks = rerank(d["question"], chunks)
        d["contexts"] = [c["text"] for c in chunks]
        
        response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"Context: {d['contexts']}\nQuestion: {d['question']}"}]
        )
        answer = response.choices[0].message.content
        d["answer"] = answer
        time.sleep(7)
    
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
    llm=groq_llm,
    embeddings=embeddings
)

print(results)
    