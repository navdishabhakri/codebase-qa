import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_cpp as tscpp
import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor
from abc import ABC, abstractmethod
from git import Repo
import os

FALLBACK_EXTENSIONS = [
    ".dart", ".swift", ".kt", ".kts",  # mobile
    ".php", ".rb", ".scala",           # web/backend
    ".cs", ".vb",                      # .NET
    ".r", ".m", ".jl",                 # data science
    ".sh", ".bash", ".zsh",            # shell
    ".lua", ".pl", ".ex", ".exs",      # other
    ".zig", ".nim", ".cr",             # emerging
    ".html", ".css", ".scss",          # frontend
    ".sql",                            # database
    ".yaml", ".yml", ".toml",          # config
    ".json", ".xml",                   # data
]

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
          
def get_js_files(local_dir):
    js_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".js"):
                full_path = os.path.join(dirpath, filename)
                js_files.append(full_path)
    return js_files         

def get_cpp_files(local_dir):
    cpp_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".cpp"):
                full_path = os.path.join(dirpath, filename)
                cpp_files.append(full_path)
    return cpp_files   

def get_ts_files(local_dir):
    ts_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".ts"):
                full_path = os.path.join(dirpath, filename)
                ts_files.append(full_path)
    return ts_files   

def get_java_files(local_dir):
    java_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".java"):
                full_path = os.path.join(dirpath, filename)
                java_files.append(full_path)
    return java_files   

def get_rust_files(local_dir):
    rust_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".rs"):
                full_path = os.path.join(dirpath, filename)
                rust_files.append(full_path)
    return rust_files   

def get_go_files(local_dir):
    go_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if filename.endswith(".go"):
                full_path = os.path.join(dirpath, filename)
                go_files.append(full_path)
    return go_files   

def get_fallback_files(local_dir):
    fallback_files = []
    for dirpath, dirnames, filenames in os.walk(local_dir): # os.walk yields a 3-tuple 
        for filename in filenames:
            if any(filename.endswith(ext) for ext in FALLBACK_EXTENSIONS):
                full_path = os.path.join(dirpath, filename)
                fallback_files.append(full_path)
    return fallback_files   
          
def chunk_repo(local_dir):
    python_files= get_python_files(local_dir)
    javascript_files= get_js_files(local_dir)
    java_files = get_java_files(local_dir)
    ts_files = get_ts_files(local_dir)
    go_files = get_go_files(local_dir)
    rust_files = get_rust_files(local_dir)
    cpp_files = get_cpp_files(local_dir)
    fallback_files = get_fallback_files(local_dir)
    
    python_chunks=[]
    javascript_chunks=[]
    cpp_chunks = []
    ts_chunks = []
    go_chunks = []
    java_chunks =[]
    rust_chunks =[]
    fallback_chunks =[]
    
    for file in python_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = python_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                python_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
        
    for file in javascript_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = javascript_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                javascript_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in java_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = java_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                java_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in cpp_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = cpp_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                cpp_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in go_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = go_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                go_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in rust_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = rust_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                rust_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in ts_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = ts_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                ts_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
    
    for file in fallback_files:
        try:
            with open(file,"r") as f: # because file is a path string, not a file object
                content= f.read()
                file_chunks = fallback_chunker.chunk(content) # class's object is calling the method of class
                for chunk in file_chunks:
                    chunk["file_path"] = file
                fallback_chunks.extend(file_chunks) # because you want one flat list to store embeddings later in pgvector and file_chunks already returns list of dictionary
        except Exception:
            pass
        
    return python_chunks + javascript_chunks + java_chunks + ts_chunks + go_chunks + rust_chunks+fallback_chunks
        
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

class JavaScriptChunker(BaseChunker):
    def chunk(self,source_code):
        # initialize the python language
        JS_LANGUAGE = Language(tsjavascript.language()) # loads python grammar
        parser = Parser(JS_LANGUAGE) # creates a parser that knows this language
        tree= parser.parse(bytes(source_code,"utf8")) # first converts to bytes, then parser reads through the code structure
        
        query = Query(JS_LANGUAGE, """
        (function_declaration) @function 
        (class_declaration) @class 
        """)
        #find every function_declaration node and call it @function"
        # capture function_declaration and class_declaration nodes
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
           

class CppChunker(BaseChunker):
    def chunk(self,source_code):
        # initialize the python language
        CPP_LANGUAGE = Language(tscpp.language()) # loads python grammar
        parser = Parser(CPP_LANGUAGE) # creates a parser that knows this language
        tree= parser.parse(bytes(source_code,"utf8")) # first converts to bytes, then parser reads through the code structure
        
        query = Query(CPP_LANGUAGE, """
        (function_declaration) @function 
        (class_specifier) @class 
        """)
        #find every function_declaration node and call it @function"
        # capture function_declaration and class_declaration nodes
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
           
class GoChunker(BaseChunker):
    def chunk(self, source_code):
        GO_LANGUAGE = Language(tsgo.language())
        parser = Parser(GO_LANGUAGE)
        tree = parser.parse(bytes(source_code, "utf8"))
        query = Query(GO_LANGUAGE, """
        (function_declaration) @function
        (method_declaration) @function
        (type_declaration) @class
        """)
        chunks = []
        captures = QueryCursor(query).captures(tree.root_node)
        for name, nodes in captures.items():
            for node in nodes:
                chunk = {}
                chunk["text"] = node.text.decode("utf8")
                chunk["start_line"] = node.start_point[0]
                chunk["end_line"] = node.end_point[0]
                chunk["type"] = "class" if "class" in name else "function"
                if node.parent and node.parent.parent and node.parent.parent.type == "class_definition":
                    chunk["parent_class"] = node.parent.parent.child_by_field_name("name").text.decode("utf8") # first parent is block , then class definition whose child is name and body. you're taking body and then is converted into string
                else:
                    chunk["parent_class"] = None
                chunks.append(chunk)
        return chunks

class JavaChunker(BaseChunker):
    def chunk(self, source_code):
        JAVA_LANGUAGE = Language(tsjava.language())
        parser = Parser(JAVA_LANGUAGE)
        tree = parser.parse(bytes(source_code, "utf8"))
        query = Query(JAVA_LANGUAGE, """
        (method_declaration) @function
        (class_declaration) @class
        """)
        chunks = []
        captures = QueryCursor(query).captures(tree.root_node)
        for name, nodes in captures.items():
            for node in nodes:
                chunk = {}
                chunk["text"] = node.text.decode("utf8")
                chunk["start_line"] = node.start_point[0]
                chunk["end_line"] = node.end_point[0]
                chunk["type"] = "class" if "class" in name else "function"
                if node.parent and node.parent.parent and node.parent.parent.type == "class_definition":
                    chunk["parent_class"] = node.parent.parent.child_by_field_name("name").text.decode("utf8") # first parent is block , then class definition whose child is name and body. you're taking body and then is converted into string
                else:
                    chunk["parent_class"] = None
                chunks.append(chunk)
        return chunks

class RustChunker(BaseChunker):
    def chunk(self, source_code):
        RUST_LANGUAGE = Language(tsrust.language())
        parser = Parser(RUST_LANGUAGE)
        tree = parser.parse(bytes(source_code, "utf8"))
        query = Query(RUST_LANGUAGE, """
        (function_item) @function
        (impl_item) @class
        """)
        chunks = []
        captures = QueryCursor(query).captures(tree.root_node)
        for name, nodes in captures.items():
            for node in nodes:
                chunk = {}
                chunk["text"] = node.text.decode("utf8")
                chunk["start_line"] = node.start_point[0]
                chunk["end_line"] = node.end_point[0]
                chunk["type"] = "class" if "class" in name else "function"
                if node.parent and node.parent.parent and node.parent.parent.type == "class_definition":
                    chunk["parent_class"] = node.parent.parent.child_by_field_name("name").text.decode("utf8") # first parent is block , then class definition whose child is name and body. you're taking body and then is converted into string
                else:
                    chunk["parent_class"] = None
                chunks.append(chunk)
        return chunks

class TypeScriptChunker(BaseChunker):
    def chunk(self, source_code):
        TS_LANGUAGE = Language(tstypescript.language_typescript())
        parser = Parser(TS_LANGUAGE)
        tree = parser.parse(bytes(source_code, "utf8"))
        query = Query(TS_LANGUAGE, """
        (function_declaration) @function
        (class_declaration) @class
        (interface_declaration) @class
        """)
        chunks = []
        captures = QueryCursor(query).captures(tree.root_node)
        for name, nodes in captures.items():
            for node in nodes:
                chunk = {}
                chunk["text"] = node.text.decode("utf8")
                chunk["start_line"] = node.start_point[0]
                chunk["end_line"] = node.end_point[0]
                chunk["type"] = "class" if "class" in name else "function"
                if node.parent and node.parent.parent and node.parent.parent.type == "class_definition":
                    chunk["parent_class"] = node.parent.parent.child_by_field_name("name").text.decode("utf8") # first parent is block , then class definition whose child is name and body. you're taking body and then is converted into string
                else:
                    chunk["parent_class"] = None
                chunks.append(chunk)
        return chunks

class FallbackChunker(BaseChunker):
    def chunk(self, source_code):
        chunks=[]
        lines = source_code.split("\n")
        for i in range(0,len(lines),50):
            chunk_lines= lines[i:i+50] # first 50 lines
            if any (line.strip() for line in chunk_lines): # is any line filled with content
                chunks.append({"text":"\n".join(chunk_lines),
                    "start_line": i,
                    "end_line": min(i+50, len(lines)),
                    "type": "function",
                    "parent_class": None})
        return chunks
               
                                                                                 
python_chunker= PythonChunker()
javascript_chunker = JavaScriptChunker()
go_chunker = GoChunker()
java_chunker = JavaChunker()
rust_chunker = RustChunker()
ts_chunker = TypeScriptChunker()
cpp_chunker = CppChunker()
fallback_chunker = FallbackChunker()

# chunks = chunk_repo("/Users/apple/Desktop/fastapi")
# print(len(chunks))