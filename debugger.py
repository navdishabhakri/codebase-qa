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
g = Github(auth=auth) # github client

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
    local_dir: str

def parse_error(state:State): # nodes in LangGraph take state as input not individual fields
    error_msg = state['error_msg']
    chat_completion = client.chat.completions.create( model="openai/gpt-oss-120b",
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
    error_types = ' '.join([str(e.get('error_type', '')) for e in errors if e.get('error_type')])
    file_names = ' '.join([str(e.get('file_name', '')) for e in errors if e.get('file_name')])
    
    query = f"{state['error_msg']}{error_types}{file_names}".strip()
    chunks = rerank(query, repo_url=state['repo_url'])
    return {"relevant_chunks": chunks}

def generate_fix(state:State):
    fixes={}
    relevant_chunks = state['relevant_chunks'] 
    errors = state['errors']
    
    # Safely filter out None file names
    extracted_files = [e.get('file_name') for e in errors if e.get('file_name')]
    files_to_fix = state.get("failed_files") or list(set(extracted_files))
    
    # If the LLM couldn't find a file name at all, fallback to a default or skip
    if not files_to_fix:
        # Fallback: Just try to fix the first relevant chunk's file if available
        if relevant_chunks:
            files_to_fix = [relevant_chunks[0]['file_path']]
        else:
            return {"generated_fix": fixes} # Nothing to fix
    
    for file in files_to_fix:
        with SessionLocal() as session:
            file_errors = [e for e in errors if e['file_name'] ==file]
            chunks= session.query(Chunk).filter(Chunk.file_path==file).all()
            text = "\n".join([c.chunk_text for c in chunks])
            text= text[:8000]
        
        chat_completion = client.chat.completions.create( model="openai/gpt-oss-120b",
        messages=[{
            "role": "user",  
            "content": f"You are a code fixing assistant. Fix these specific errors in {file}: {file_errors}. Here is the full file context from the codebase: {text}. Return the ENTIRE corrected file content with ALL errors fixed. Complete file only. No explanation, no markdown, no backticks."
        }])
        answer = chat_completion.choices[0].message.content
        fixes[file]= answer # to never lose track of the fixes per file
    return {"generated_fix":fixes}

def validate_fix(state: State):
    fixes = state['generated_fix']
    validation_results = {}
    local_dir = state.get('local_dir', '/tmp')
    
    for file in fixes:
        # Strip redundant directory prefixes if the LLM hallucinates them
        target_file = file
        if target_file.startswith(local_dir):
            target_file = target_file.replace(local_dir, "", 1)
        if target_file.startswith("/"):
            target_file = target_file.lstrip("/")
            
        full_path = os.path.join(local_dir, target_file)
        
        with open(full_path, "r", encoding="utf-8") as f:
            original = f.read()
            
        with open(full_path, "w", encoding="utf-8") as f:
            clean_code = fixes[file].replace("```python", "").replace("```", "").strip()
            f.write(clean_code)
             
        try:
            # Enforce a 10-second timeout on all executions
            if file.endswith(".py"):
                result = subprocess.run(["python", "-m", "py_compile", full_path], capture_output=True, text=True, timeout=10)
            elif file.endswith(".js") or file.endswith(".jsx"):
                result = subprocess.run(["node", full_path], capture_output=True, text=True, timeout=10)
            elif file.endswith(".go"):
                result = subprocess.run(["go", "run", full_path], capture_output=True, text=True, timeout=10)
            elif file.endswith(".ts"):
                result = subprocess.run(["ts-node", full_path], capture_output=True, text=True, timeout=10)
            elif file.endswith(".java"):
                result = subprocess.run(["java", full_path], capture_output=True, text=True, timeout=10)
            elif file.endswith(".rs"):
                result = subprocess.run(["cargo", "run"], capture_output=True, text=True, timeout=10)
            else:
                # Default fallback for unknown extensions to prevent crash
                result = subprocess.CompletedProcess(args=[], returncode=0, stdout='', stderr='')
            
            if result.returncode != 0:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(original)
                validation_results[file] = False
                
                return {
                    "is_valid": False,
                    "validation_results": validation_results,
                    "retry_count": state['retry_count'] + 1,
                    "failed_files": [f for f, is_valid in validation_results.items() if not is_valid]
                }
                
        except subprocess.TimeoutExpired:
            # Revert the file if the LLM code causes an infinite loop
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(original)
            validation_results[file] = False
            
            return {
                "is_valid": False,
                "validation_results": validation_results,
                "retry_count": state['retry_count'] + 1,
                "failed_files": [f for f, is_valid in validation_results.items() if not is_valid]
            }
    
        validation_results[file] = True
        
    return {
        "is_valid": True, 
        "validation_results": validation_results
    }
    
    
def create_pr(state: State):
    fixes = state.get('generated_fix', {})
    validation_results = state.get('validation_results', {})
    
    # GUARD: Only proceed if there is actually code to push
    valid_fixes = [file for file in fixes if validation_results.get(file)]
    if not valid_fixes:
        return {"pr_url": "Failed: No valid fixes were generated by the LLM, so no PR was opened."}

    repo_name = state['repo_url'].split("github.com/")[1]
    repo = g.get_repo(repo_name)
    main_branch = repo.get_branch("main")
    branch_name = f"fix/auto-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    errors = state.get('errors', [])
    error_summary = ', '.join([e.get('error_type', 'bug') for e in errors]) or "bug fix"
    
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=main_branch.commit.sha
    )
    
    for file in fixes:
        if validation_results.get(file):
            github_path = file
            local_dir = state.get('local_dir')
            if local_dir and github_path.startswith(local_dir):
                github_path = os.path.relpath(github_path, local_dir)
                
            contents = repo.get_contents(github_path, ref=branch_name)
            repo.update_file(
                path=github_path,
                message=f"Fix: {error_summary}",
                content=fixes[file],
                sha=contents.sha,
                branch=branch_name
            )
            
    pr = repo.create_pull(
        base="main",
        head=branch_name,
        title=f"Fix: {error_summary}",
        body=f"Automated fix generated by Codebase QA agent for: {error_summary}"
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
