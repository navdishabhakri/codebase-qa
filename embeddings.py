from transformers import pipeline
from transformers import AutoTokenizer, AutoModel
import torch
tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")
from chunker import chunk_repo 

def embed_chunks(chunks):
    embeddings=[]
    for chunk in chunks: # list of all chunks
        inputs = tokenizer(chunk["text"], return_tensors="pt",truncation=True, max_length=512) # converts text to numbers and return pt meaning pytorch tensors. 
        # 2. Forward pass through the model
        with torch.no_grad(): 
            outputs = model(**inputs) #passes the tokenized input through CodeBERT
        cls_embedding = outputs.last_hidden_state[:, 0, :] #[batch, tokens, 768]. [:, 0, :] means "all batches, first token (CLS), all 768 dimensions".
        embeddings.append(cls_embedding.squeeze().tolist()) # squeeze() removes the batch dimension so shape goes from [1, 768] to [768]
    return embeddings

# The CLS token (first token) is a special token that CodeBERT adds at the beginning of every input. It's designed to capture the overall meaning of the entire input sequence.

chunks=chunk_repo("/Users/apple/Desktop/fastapi")
# print(embed_chunks(chunks[:3]))