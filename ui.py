import streamlit as st
import requests
import json
import os

# Updated to use your Oracle Public IP as the default fallback
API_BASE_URL = os.getenv("BACKEND_URL", "http://147.5.115.124:8000")

st.set_page_config(page_title="AI Agent Studio", layout="wide")
st.title("🤖 AI Codebase Agent Studio")
st.markdown("Interact with all endpoints, or run the fully autonomous loop in Tab 3.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 1. Ingest Repo", 
    "💬 2. Q&A Agent", 
    "🐛 3. Autonomous Loop", 
    "🛠️ 4. Manual Reviewer", 
    "🪝 5. Manual Webhook"
])

with tab1:
    st.text("Clone and vectorize a repository for search.")
    repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/user/repo", key="ingest_repo")
    local_dir = st.text_input("Local Temp Directory Name", value="./temp_repo", key="ingest_dir")
    
    if st.button("Run Ingestion"):
        with st.spinner("Processing..."):
            res = requests.post(f"{API_BASE_URL}/ingest", json={"url": repo_url, "local_dir": local_dir})
            st.json(res.json() if res.status_code == 200 else {"error": "Failed to ingest"})

with tab2:
    st.text("Ask questions about the ingested codebase.")
    query_repo = st.text_input("Target Repository URL", placeholder="https://github.com/user/repo", key="query_repo")
    question = st.text_area("Question", placeholder="How does the calculate_average function work?", key="query_q")
    
    if st.button("Ask Q&A Agent"):
        with st.spinner("Searching..."):
            res = requests.post(f"{API_BASE_URL}/query", json={"question": question, "repo_url": query_repo})
            st.markdown(res.text if res.status_code == 200 else "Error communicating with API.")

with tab3:
    st.text("End-to-End Pipeline: Debug -> Open PR -> Review -> Re-Ingest")
    debug_repo = st.text_input("Target Repository URL", placeholder="https://github.com/user/repo", key="debug_repo")
    debug_dir = st.text_input("Local Temp Directory Name", value="./temp_repo", key="debug_dir")
    error_msg = st.text_area("Paste the exact terminal error", key="debug_err")
    
    if st.button("Trigger Autonomous Loop"):
        with st.status("🚀 Initializing Autonomous AI Loop...", expanded=True) as status:
            
            st.write("🐛 **Phase 1: Debugging & Opening PR...**")
            res_debug = requests.post(f"{API_BASE_URL}/debug", json={"repo_url": debug_repo, "error_msg": error_msg, "local_dir": debug_dir})
            
            if res_debug.status_code == 200:
                debug_data = res_debug.json()
                pr_url = debug_data.get("pr_url")
                
                if pr_url and "Failed" not in str(pr_url):
                    st.success(f"Pull Request created: {pr_url}")
                    
                    st.write("🛠️ **Phase 2: Triggering Reviewer Agent...**")
                    res_review = requests.post(f"{API_BASE_URL}/review", json={"pr_url": pr_url})
                    if res_review.status_code == 200:
                        st.success("Code review posted to GitHub.")
                    else:
                        st.error("Reviewer agent failed.")
                        
                    st.write("🪝 **Phase 3: Firing Webhook for Re-ingestion...**")
                    payload = {"action": "opened", "pull_request": {"html_url": pr_url}}
                    res_webhook = requests.post(f"{API_BASE_URL}/webhook", json=payload)
                    if res_webhook.status_code == 200:
                        st.success("Vector database successfully updated with new code.")
                    else:
                        st.error("Webhook payload failed.")
                        
                    status.update(label="Loop Complete! System Fully Updated.", state="complete", expanded=False)
                else:
                    st.error("Debugger failed to return a valid Pull Request URL.")
                    status.update(label="Pipeline halted at Debugger.", state="error")
            else:
                st.error("Debugger API request failed.")
                status.update(label="Pipeline crashed.", state="error")

with tab4:
    st.text("Manually trigger a code review on a specific PR.")
    pr_url = st.text_input("Pull Request URL", placeholder="https://github.com/user/repo/pull/1", key="review_pr")
    
    if st.button("Run Reviewer"):
        with st.spinner("Reviewing PR..."):
            res = requests.post(f"{API_BASE_URL}/review", json={"pr_url": pr_url})
            st.json(res.json() if res.status_code == 200 else {"error": "Failed to run reviewer"})

with tab5:
    st.text("Manually test webhook payloads.")
    payload = st.text_area("Paste JSON Payload", value='{\n  "action": "opened",\n  "pull_request": {\n    "html_url": "https://github.com/user/repo/pull/1"\n  }\n}', height=200)
    
    if st.button("Simulate Webhook"):
        try:
            parsed_payload = json.loads(payload)
            res = requests.post(f"{API_BASE_URL}/webhook", json=parsed_payload)
            st.json(res.json() if res.status_code == 200 else {"error": "Webhook failed"})
        except json.JSONDecodeError:
            st.error("Invalid JSON format.")