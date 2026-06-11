from transformers import pipeline
from transformers import AutoTokenizer, AutoModel
import torch
from chunker import chunk_repo 

_tokenizer = None
_model = None

def _get_model():
    global _tokenizer, _model
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        _model = AutoModel.from_pretrained("microsoft/codebert-base")
    return _tokenizer, _model

def embed_chunks(chunks):
    embeddings=[]
    tokenizer,model = _get_model()
    for chunk in chunks: # list of all chunks
        inputs = tokenizer(chunk["text"], return_tensors="pt",truncation=True, max_length=512) # converts text to numbers and return pt meaning pytorch tensors. 
        # 2. Forward pass through the model
        with torch.no_grad(): 
            outputs = model(**inputs) #passes the tokenized input through CodeBERT
        cls_embedding = outputs.last_hidden_state[:, 0, :] #[batch, tokens, 768]. [:, 0, :] means "all batches, first token (CLS), all 768 dimensions".
        embeddings.append(cls_embedding.squeeze().tolist()) # squeeze() removes the batch dimension so shape goes from [1, 768] to [768]
    return embeddings
