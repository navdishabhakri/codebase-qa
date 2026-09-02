from transformers import pipeline
from transformers import AutoTokenizer, AutoModel
import torch
from chunker import chunk_repo 

_tokenizer = None
_model = None

def _get_model():
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        _tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        _model = AutoModel.from_pretrained("microsoft/codebert-base")
    return _tokenizer, _model

def embed_chunks(chunks):
    embeddings = []
    tokenizer, model = _get_model()
    for chunk in chunks:
        # 1. Tokenize completely without truncation
        tokens = tokenizer(chunk['text'], return_tensors='pt', truncation=False)
        input_ids = tokens['input_ids'][0]  # Get 1D tensor
        attention_mask = tokens['attention_mask'][0]
        
        max_len = 512
        stride = 256  # 50% overlap prevents cutting context in half
        
        window_embeddings = []
        
        # 2. Slide a window over the tokens
        for i in range(0, len(input_ids), stride):
            window_input_ids = input_ids[i : i + max_len].unsqueeze(0)
            window_attention_mask = attention_mask[i : i + max_len].unsqueeze(0)
            
            with torch.no_grad():
                outputs = model(input_ids=window_input_ids, attention_mask=window_attention_mask)
            
            # Extract the [CLS] token for this specific window
            cls_embedding = outputs.last_hidden_state[:, 0, :]
            window_embeddings.append(cls_embedding.squeeze())
            
            # Stop if the window reached the end of the tokens
            if i + max_len >= len(input_ids):
                break
                
        # 3. Average the windows into a single 768-dimension vector
        if len(window_embeddings) > 1:
            final_embedding = torch.stack(window_embeddings).mean(dim=0).tolist()
        else:
            final_embedding = window_embeddings[0].tolist()
            
        embeddings.append(final_embedding)
        
    return embeddings