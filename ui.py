import streamlit as st
import requests
import json
import os

API_BASE_URL = os.getenv("BACKEND_URL", "http://147.5.115.124:8000")

st.set_page_config(page_title="AI Code Assistant", layout="wide")
st.markdown("""
    <style>
    /* Hide the default Streamlit top menu and footer for a clean, app-like feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Make the main title look premium */
    h1 {
        color: #1E3A8A;
        font-weight: 800;
        letter-spacing: -1px;
    }
    
    /* Style all buttons with a sleek, modern gradient and hover effect */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    /* Clean up the tab navigation bar */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F3F4F6;
        border-radius: 6px;
        padding: 8px 16px;
        border: 1px solid #E5E7EB;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 AI Code Assistant")
st.markdown("Your automated partner for reading, reviewing, and fixing code. Select a tab below to get started.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 1. Connect Project", 
    "💬 2. Chat with Code", 
    "🛠️ 3. Auto-Fix Bugs", 
    "👀 4. Code Review", 
    "⚙️ 5. Developer Tools"
])

with tab1:
    st.write("**Connect Your Project**")
    st.text("Give the AI access to read and understand your codebase.")
    repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/user/repo", key="ingest_repo")
    local_dir = st.text_input("Project Name (Internal)", value="./temp_repo", key="ingest_dir")
    
    if st.button("Analyze Project"):
        with st.spinner("Reading project files..."):
            res = requests.post(f"{API_BASE_URL}/ingest", json={"url": repo_url, "local_dir": local_dir})
            st.json(res.json() if res.status_code == 200 else {"error": "Failed to connect to the project."})

with tab2:
    st.write("**Ask Questions**")
    st.text("Ask the AI anything about how this project works.")
    query_repo = st.text_input("Target Repository URL", placeholder="https://github.com/user/repo", key="query_repo")
    question = st.text_area("What do you want to know?", placeholder="How does the login function work?", key="query_q")
    
    if st.button("Ask AI"):
        with st.spinner("Thinking..."):
            res = requests.post(f"{API_BASE_URL}/query", json={"question": question, "repo_url": query_repo})
            st.markdown(res.text if res.status_code == 200 else "Error communicating with AI.")

with tab3:
    st.write("**Autonomous Bug Fixer**")
    st.text("Paste a repository link and an error message. The AI will find the bug, write the code to fix it, and propose a solution automatically.")
    debug_repo = st.text_input("Target Repository URL", placeholder="https://github.com/user/repo", key="debug_repo")
    debug_dir = st.text_input("Project Name (Internal)", value="./temp_repo", key="debug_dir")
    error_msg = st.text_area("Paste the exact error message", key="debug_err")
    
    if st.button("Fix My Code"):
        with st.status("🚀 Launching AI Fixer...", expanded=True) as status:
            
            st.write("🐛 **Phase 1: Finding the bug & writing a fix...**")
            res_debug = requests.post(f"{API_BASE_URL}/debug", json={"repo_url": debug_repo, "error_msg": error_msg, "local_dir": debug_dir})
            
            if res_debug.status_code == 200:
                debug_data = res_debug.json()
                pr_url = debug_data.get("pr_url")
                
                if pr_url and "Failed" not in str(pr_url):
                    st.success(f"Fix proposed! View it on GitHub: {pr_url}")
                    
                    st.write("👀 **Phase 2: Having a second AI review the fix...**")
                    res_review = requests.post(f"{API_BASE_URL}/review", json={"pr_url": pr_url})
                    if res_review.status_code == 200:
                        st.success("Code review completed.")
                    else:
                        st.error("AI Reviewer ran into an issue.")
                        
                    st.write("🔄 **Phase 3: Updating system memory...**")
                    # FIXED: Sending the correct simple payload to your new smart webhook
                    payload = {"pr_url": pr_url}
                    res_webhook = requests.post(f"{API_BASE_URL}/webhook", json=payload)
                    if res_webhook.status_code == 200:
                        st.success("System successfully learned the new code.")
                    else:
                        st.error("System memory update failed.")
                        
                    status.update(label="All done! Your code has been fixed.", state="complete", expanded=False)
                else:
                    st.error("The AI couldn't create a fix for this error.")
                    status.update(label="Process halted.", state="error")
            else:
                st.error("Failed to connect to the bug fixer.")
                status.update(label="Process crashed.", state="error")

with tab4:
    st.write("**Manual Code Review**")
    st.text("Ask the AI to review a specific proposed change (Pull Request) on GitHub.")
    pr_url = st.text_input("Pull Request URL", placeholder="https://github.com/user/repo/pull/1", key="review_pr")
    
    if st.button("Review Code"):
        with st.spinner("Reading the proposed changes..."):
            res = requests.post(f"{API_BASE_URL}/review", json={"pr_url": pr_url})
            st.json(res.json() if res.status_code == 200 else {"error": "Failed to run reviewer"})

with tab5:
    # FIXED: Properly indented everything inside Tab 5
    st.header("⚙️ 5. Developer Tools")
    st.write("Manage the AI's internal memory state.")

    st.subheader("🔄 Smart PR Sync")
    st.write("Paste a Pull Request link to automatically fetch and memorize the modified files.")

    # Clean, simple user input
    pr_link = st.text_input("Pull Request URL", placeholder="https://github.com/owner/repo/pull/5", key="webhook_pr")

    if st.button("Sync PR Changes to Memory", use_container_width=True):
        if not pr_link:
            st.warning("Please provide a valid GitHub Pull Request link.")
        else:
            with st.spinner("Fetching files from GitHub and updating vector database..."):
                # The only payload Streamlit sends is the URL itself
                payload = {"pr_url": pr_link}
                res = requests.post(f"{API_BASE_URL}/webhook", json=payload)
                
                if res.status_code == 200:
                    server_msg = res.json().get("message", "Vector database updated successfully!")
                    st.success(f"Sync complete! {server_msg}")
                else:
                    st.error(f"Failed to sync. Server responded with: {res.status_code}")