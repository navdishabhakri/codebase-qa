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
client = Groq(api_key= key ) # create a clie

class State(TypedDict):
    pr_url: str
    files: list
    repo_name: str
    chunks: dict
    difference:dict
    answer : dict
    posted : bool
    
def receive(state:State):
    pr_url = state['pr_url']
    pr_number = int(pr_url.split('/')[-1])
    repo_name = pr_url.split("github.com/")[1].split("/pull")[0]
    files = g.get_repo(repo_name).get_pull(pr_number).get_files()
    return {"files" : files, "repo_name":repo_name} 

def get_diff_and_chunks(state:State):
    chunks={}
    difference={}
    files = state["files"]
    repo_url =  f"https://github.com/{state['repo_name']}"
    for file in files:
        difference[file.filename] = file.patch
        query = f"{file.filename} {file.patch[:500]}"
        chunks[file.filename] = rerank(query, repo_url) # rerank gives you the diff + file 
    return {"chunks":chunks, "difference":difference}

def review(state:State):
    files = state["files"]
    difference = state["difference"]
    chunks=state["chunks"]
    answer = {}
    for file in files:
        chat_completion = client.chat.completions.create( model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",  
            "content": f"You are a senior code reviewer. Review this code change in {file.filename}. Diff: {difference[file.filename]}. Related codebase context: {chunks[file.filename]}. Provide specific, actionable review comments. Point out bugs, missing error handling, pattern violations, and improvements. Be concise and direct."
        }])   
        answer[file.filename]= chat_completion.choices[0].message.content
    return {"answer" : answer} # review for all files

def post_comments(state:State):
    pr_number = int(state['pr_url'].split('/')[-1])
    pr =  g.get_repo(state['repo_name']).get_pull(pr_number)
    reviews = state['answer']
    files = state['files']
    
    for file in files:
        pr.create_issue_comment(
            f"**Review for {file.filename} : **\n\n {reviews[file.filename]}"
        )
    
    return {"posted" : True}
        
   
builder = StateGraph(State)    
builder.add_node("receive", receive)
builder.add_node("get_diff_and_chunks",get_diff_and_chunks)
builder.add_node("review",review)
builder.add_node("post_comments",post_comments)

builder.add_edge(START, "receive")
builder.add_edge("receive", "get_diff_and_chunks")
builder.add_edge("get_diff_and_chunks", "review")
builder.add_edge("review", "post_comments")
builder.add_edge("post_comments", END) 

memory = MemorySaver()
graph_review = builder.compile(checkpointer = memory) 
display(Image(graph_review.get_graph().draw_mermaid_png()))


        
      
    