from database import engine, SessionLocal, Chunk
from sqlalchemy import insert
from dotenv import load_dotenv
import os
from embeddings import embed_chunks
from chunker import chunk_repo 

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # connects to a SQLite file
 
def store_chunks(chunks,embeddings):
    with SessionLocal() as session:
        for chunk,embedding in zip(chunks,embeddings):
            db_chunk = Chunk(
                file_path=chunk["file_path"],
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                type=chunk["type"],
                parent_class=chunk["parent_class"],
                chunk_text=chunk["text"],
                embedding_vector=embedding
            )
            session.add(db_chunk)
        session.commit()
        
