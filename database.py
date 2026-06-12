from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from pgvector.sqlalchemy import Vector
from sqlalchemy import Text, Column, Integer, String
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # connects to a SQLite file
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine) # session so that app talks with db 
Base = declarative_base()  # base class that models inherit from

class Chunk(Base):
    __tablename__ = 'code_chunks'
    id = Column(Integer, primary_key = True, unique = True, nullable = False)
    file_path = Column(String(150),  nullable = False)
    start_line = Column(Integer,  nullable = False)
    end_line = Column(Integer,  nullable = False)
    type = Column(String(50),  nullable = False)
    repo_url = Column(String(500), nullable=True)
    parent_class = Column(String(50))
    chunk_text = Column(Text,  nullable = False)
    embedding_vector = Column(Vector(768))

Base.metadata.create_all(bind=engine)  # this creates table when app starts
