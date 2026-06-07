import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor
from abc import ABC, abstractmethod
from git import Repo
import os

def clone_repo(url, local_dir):
    if not os.path.exists(local_dir): # if this directory doesnt exist, then only add the cloned repo here
        cloned_repo = Repo.clone_from(url, local_dir)

def get_python_files(local_dir):
    python_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                python_files.append(full_path)
    return python_files 
            
def chunk_repo(local_dir):
    files= get_python_files(local_dir)
    chunks=[]
    for file in files:
        with open(file,"r") as f: # because file is a path string, not a file object
            content= f.read()
            file_chunks = chunker.chunk(content) # class's object is calling the method of class
            for chunk in file_chunks:
                chunk["file_path"] = file
            chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
    return chunks
        
class BaseChunker(ABC):
    @abstractmethod
    def chunk(self,source_code):
        pass


class PythonChunker(BaseChunker):
    def chunk(self,source_code):
        # initialize the python language
        PY_LANGUAGE = Language(tspython.language()) # loads python grammar
        parser = Parser(PY_LANGUAGE) # creates a parser that knows this language
        tree= parser.parse(bytes(source_code,"utf8")) # first converts to bytes, then parser reads through the code structure
        
        query = Query(PY_LANGUAGE, """
        (function_definition) @function 
        (class_definition) @class 
    """)
        #find every function_definition node and call it @function"
        # capture function_definition and class_definition nodes
        # class and function are your keys, values are - [node1,node 2] so "function" : [ node4,node5]
       
        chunks=[] 
        captures = QueryCursor(query).captures(tree.root_node)
        for name, nodes in captures.items(): # per capture
            for node in nodes: # per value 
                chunk = {}  
                chunk["text"] = node.text.decode("utf8") # Think of each node as a pointer to a specific part of the code tree with metadata about where it is and what it contains.
                chunk["start_line"] = node.start_point[0]
                chunk["end_line"] = node.end_point[0]
                chunk["type"] = "class" if "class" in name else "function"
                if node.parent and node.parent.parent and node.parent.parent.type == "class_definition":
                    chunk["parent_class"] = node.parent.parent.child_by_field_name("name").text.decode("utf8") # first parent is block , then class definition whose child is name and body. you're taking body and then is converted into string
                else:
                    chunk["parent_class"] = None
                chunks.append(chunk) 
        return chunks # list of dictionaries
                                                                                            
chunker= PythonChunker()
obj1 = PythonChunker()
# print(obj1.chunk("""
# class Account:
#     def __init__(self):
#         self.balance =0 
#     def deposit(self,amount):
#         self.balance+=amount
#     def withdraw(self,amount):
#         if balance>=amount:
#             self.balance-=amount
#         raise ValueError("balance cannot be negative")
# """))

clone_repo("https://github.com/tiangolo/fastapi", "/Users/apple/Desktop/fastapi")
chunks = chunk_repo("/Users/apple/Desktop/fastapi")
# print(len(chunks))


