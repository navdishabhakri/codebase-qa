from debugger import g
from typing import TypedDict
from search import rerank
from groq import Groq
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from IPython.display import Image , display
from langgraph.checkpoint.memory import MemorySaver

load_dotenv() 
key= os.getenv("GROQ_KEY") 
client = Groq(api_key= key ) # create a client

class State(TypedDict):
    pr_url: str
    repo_name: str
    diff_data: list
    chunks: dict
    answer : dict
    posted : bool
    
def get_diff_and_chunks(state:State):
    repo_name = state['pr_url'].split("github.com/")[1].split("/pull")[0]
    pr_number = int(state['pr_url'].split("/")[-1])
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    diff_data = []
    files = pr.get_files()
    for file in files:
        diff_data.append({
            "filename": file.filename,
            "patch": file.patch
        })
        
    chunks = {}
    for item in diff_data:
        # Pass repo_url as a keyword argument to rerank
        query = f"Provide context for this file modification: {item['filename']} {item['patch']}"
        chunks[item['filename']] = rerank(query, repo_url=f"https://github.com/{repo_name}")
        
    # Return the clean dictionary of string data, not the PyGithub object
    return {"diff_data": diff_data, "chunks": chunks, "repo_name": repo_name}

def review(state:State):
    diff_data = state.get("diff_data") or state.get("diff", [])
    chunks=state.get("chunks", {})
    answer = {}
    for item in diff_data:
        filename = item.get('filename')
        patch = item.get('patch')
        relevant_chunks = chunks.get(filename, [])
        
        # Safely parse text from chunks
        context_text = "\n".join([c.get('text', '') if isinstance(c, dict) else str(c) for c in relevant_chunks]) if relevant_chunks else ""
        
        chat_completion = client.chat.completions.create( 
            model="openai/gpt-oss-120b",
            messages=[{
                "role": "user",  
                "content": f"You are a senior code reviewer. Review this code change in {filename}. Diff: {patch}. Related codebase context: {context_text}. Provide specific, actionable review comments. Point out bugs, missing error handling, pattern violations, and improvements. Be concise and direct."
            }]
        )    
        answer[filename] = chat_completion.choices[0].message.content
        
    return {"answer": answer}

def post_comments(state: State):
    pr_url = state['pr_url']
    pr_number = int(pr_url.split('/')[-1])
    
    # Define repo_name locally so the next line doesn't crash
    repo_name = pr_url.split("github.com/")[1].split("/pull")[0]
    pr = g.get_repo(repo_name).get_pull(pr_number)
    
    reviews = state.get('answer', {})
    diff_data = state.get("diff_data") or state.get("diff", [])
    
    consolidated_review = "### 🤖 Automated Code Review\n\n"
    
    for item in diff_data:
        filename = item.get('filename')
        if filename in reviews:
            consolidated_review += f"#### **`{filename}`**\n{reviews[filename]}\n\n---\n\n"
            
    # Post exactly ONE comment containing all the feedback
    pr.create_issue_comment(consolidated_review)
    
    return {"posted": True}

   
builder = StateGraph(State)    

builder.add_node("get_diff_and_chunks",get_diff_and_chunks)
builder.add_node("review",review)
builder.add_node("post_comments",post_comments)

builder.add_edge(START, "get_diff_and_chunks")
builder.add_edge("get_diff_and_chunks", "review")
builder.add_edge("review", "post_comments")
builder.add_edge("post_comments", END) 

memory = MemorySaver()
graph_review = builder.compile(checkpointer = memory) 
display(Image(graph_review.get_graph().draw_mermaid_png()))


        
      
    