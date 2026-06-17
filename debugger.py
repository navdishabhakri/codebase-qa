import os
import datetime
from dotenv import load_dotenv
load_dotenv() 
from groq import Groq
from typing import TypedDict
import subprocess
from search import rerank
from database import SessionLocal, Chunk
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client
import json
from github import Auth
from github import Github
from github import GithubIntegration
from langgraph.graph import StateGraph, START, END
from IPython.display import Image , display
from langgraph.checkpoint.memory import MemorySaver

access_token = os.getenv("GITHUB_TOKEN")
auth = Auth.Token(access_token)
g = Github(auth=auth)

class State(TypedDict): # state is a dictionary
    errors: list
    error_msg: str
    relevant_chunks: list
    generated_fix: dict
    is_valid: bool
    pr_url: str
    repo_url: str
    retry_count: int
    validation_results: dict
    failed_files: list

def parse_error(state:State): # nodes in LangGraph take state as input not individual fields
    error_msg = state['error_msg']
    chat_completion = client.chat.completions.create( model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user", 
            "content" : f"Extract all errors from this stack trace: {error_msg}. Return ONLY a JSON object with key 'errors' as a list. Each item must have: file_name, line_number, error_type. No explanation."
        }])
    
    answer = chat_completion.choices[0].message.content
    answer = answer.strip().strip("```json").strip("```").strip()
    parsed = json.loads(answer)
    return {"errors" : parsed["errors"]}

def search_codebase(state:State):
    errors = state['errors']
    error_types = ' '.join (e['error_type'] for e in errors)
    file_names = ' '.join (e['file_name'] for e in errors)
    query = f"{state['error_msg']}{error_types}{file_names}"
    chunks = rerank(query,state['repo_url'])
    return {"relevant_chunks": chunks}

def generate_fix(state:State):
    fixes={}
    relevant_chunks = state['relevant_chunks'] 
    errors = state['errors']
    files_to_fix= state.get("failed_files") or list(set(e['file_name'] for e in errors))
    for file in files_to_fix:
        with SessionLocal() as session:
            file_errors = [e for e in errors if e['file_name'] ==file]
            chunks= session.query(Chunk).filter(Chunk.file_path==file).all()
            text = "\n".join([c.chunk_text for c in chunks])
        chat_completion = client.chat.completions.create( model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",  
            "content": f"You are a code fixing assistant. Fix these specific errors in {file}: {file_errors}. Here is the full file context from the codebase: {text}. Return the ENTIRE corrected file content with ALL errors fixed. Complete file only. No explanation, no markdown, no backticks."
        }])
        answer = chat_completion.choices[0].message.content
        fixes[file]= answer # to never lose track of the fixes per file
    return {"generated_fix":fixes}

def validate_fix(state:State):
    fixes= state['generated_fix']
    validation_results={}
    for file in fixes:
        with open(file, "r") as f:
            original = f.read() 
        with open(file,"w") as f:
            f.write(fixes[file])
        if file.endswith(".py"):
            result = subprocess.run(["python", file], capture_output=True, text=True)
        elif file.endswith(".js") or file.endswith(".jsx"):
            result = subprocess.run(["node", file], capture_output=True, text=True)
        elif file.endswith(".go"):
                result = subprocess.run(["go", "run", file], capture_output=True, text=True)
        elif file.endswith(".ts"):
            result = subprocess.run(["ts-node", file], capture_output=True, text=True)
        elif file.endswith(".java"):
            result = subprocess.run(["java", file], capture_output=True, text=True)
        elif file.endswith(".rs"):
            result = subprocess.run(["cargo", "run"], capture_output=True, text=True)
        if result.returncode!=0:
            with open(file, "w") as f:
                f.write(original)
            validation_results[file] = False
            
            return {
            "is_valid": False,
            "validation_results": validation_results,
            "retry_count": state['retry_count'] + 1,
            "failed_files" : [ file for file,boolean in validation_results.items() if not boolean]
        }
    
        validation_results[file] = True
    return {
    "is_valid":True, "validation_results": validation_results}
            
            
def create_pr(state:State):
    repo = g.get_repo(state['repo_url'])
    main_branch = repo.get_branch("main")
    validation_results = state['validation_results']
    branch_name = f"fix/auto-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    fixes= state['generated_fix']
    error_summary = ', '.join([e['error_type'] for e in state['errors']])
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=main_branch.commit.sha
    )
    
    for file in fixes:
        if validation_results[file]:
            contents = repo.get_contents(file, ref=branch_name)
            repo.update_file(
                path=file,
                message=f"Fix {error_summary}",
                content=fixes[file],
                sha=contents.sha,
                branch=branch_name
            )
            
    pr = repo.create_pull(
        base="main",
        head=branch_name,
        title=f"Fix: {error_summary}",
        body=f"Automated fix for: {error_summary}"
    )
   
    return {"pr_url": pr.html_url}


builder = StateGraph(State)    
builder.add_node("parse_error", parse_error)
builder.add_node("search_codebase", search_codebase)
builder.add_node("generate_fix", generate_fix)
builder.add_node("validate_fix", validate_fix)
builder.add_node("create_pr", create_pr)

builder.add_edge(START, "parse_error")
builder.add_edge("parse_error", "search_codebase")
builder.add_edge("search_codebase", "generate_fix")
builder.add_edge("generate_fix", "validate_fix")

def should_retry(state):
    if state['is_valid']:
        return "create_pr"
    elif state["retry_count"]>=3:
        return END
    else: 
        return "generate_fix"
 
builder.add_conditional_edges("validate_fix", should_retry) # after validate go to should retry
builder.add_edge("create_pr", END)

memory = MemorySaver()
graph = builder.compile(checkpointer = memory)
display(Image(graph.get_graph().draw_mermaid_png()))
