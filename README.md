# Agentic AI Debugger

Production-grade RAG system with autonomous AI agents for codebase understanding, automated debugging, and code review — built on hybrid retrieval, LangGraph agent orchestration, and a from-scratch MCP server so Claude Desktop can query your codebase directly.

## Overview

This system lets an AI agent understand a real codebase, diagnose failing tests or reported bugs, generate and validate a fix, and open a pull request automatically — with a separate agent that reviews PRs by pulling diffs, retrieving related context, and posting inline comments. Retrieval quality is evaluated quantitatively with RAGAS rather than assumed.

## Features

### Code Understanding
- **AST-based chunking across 8 languages** (Python, JavaScript, TypeScript, Go, Java, Rust, C++) via Tree-sitter, with a generic fallback covering 20+ additional languages
- **Hybrid search** combining BM25 keyword search, CodeBERT vector embeddings, Reciprocal Rank Fusion (RRF), and Cohere reranking for high-precision context retrieval
- **Query expansion with guardrails** to broaden recall without drifting off-topic, plus configurable temperature control and streaming responses

### Autonomous Debugger
- LangGraph agent (5 nodes, persistent memory, retry logic) that:
  1. Parses the incoming error
  2. Searches the codebase for relevant context
  3. Generates a candidate fix
  4. Validates the fix by actually running the code
  5. Opens a GitHub PR automatically once validated

### Code Review Agent
- Fetches PR diffs, retrieves related codebase context via the same hybrid search pipeline, and posts inline review comments directly on GitHub

### Integrations
- **CI/CD:** GitHub Actions triggers the autonomous debugger automatically on test failure
- **MCP server:** exposes the codebase as a queryable tool so Claude Desktop (or any MCP-compatible client) can search and reason over it directly

## Evaluation

Retrieval and generation quality measured with [RAGAS](https://github.com/explodinggradients/ragas):

| Metric | Score |
|---|---|
| Faithfulness | 0.77 |
| Answer Relevancy | 0.84 |
| Context Recall | 0.88 |

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Database | PostgreSQL + pgvector |
| Embeddings | CodeBERT |
| Agent Orchestration | LangGraph |
| Reranking | Cohere |
| LLM Inference | Groq |
| GitHub Integration | PyGithub |
| Containerization | Docker |
| Deployment | Railway |
| Auth / Storage | Supabase |

## Architecture

```
                ┌─────────────────────┐
                │   Source Codebase    │
                └──────────┬───────────┘
                           │ Tree-sitter AST chunking
                           ▼
                ┌─────────────────────┐
                │   pgvector + BM25    │
                │   (Hybrid Index)     │
                └──────────┬───────────┘
                           │ RRF fusion + Cohere rerank
                           ▼
        ┌──────────────────┴──────────────────┐
        ▼                                      ▼
┌───────────────┐                    ┌───────────────────┐
│ Autonomous     │                    │ Code Review Agent  │
│ Debugger       │                    │                     │
│ (LangGraph,    │                    │ PR diff → context   │
│ 5 nodes)       │                    │ retrieval → inline  │
│                │                    │ comments             │
│ parse → search │                    └───────────────────┘
│ → fix → run    │
│ → open PR      │
└───────────────┘
        ▲
        │ triggered on test failure
┌───────────────┐
│ GitHub Actions │
└───────────────┘

┌─────────────────────┐
│   MCP Server          │──► Claude Desktop queries codebase directly
└─────────────────────┘
```

## Getting Started

### Prerequisites
- Python 3.10+
- Docker
- PostgreSQL with the `pgvector` extension enabled
- API keys: Groq, Cohere, GitHub (personal access token or GitHub App)

### Installation

```bash
git clone https://github.com/navdishabhakri/agentic-ai-debugger.git
cd agentic-ai-debugger
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_debugger
GROQ_API_KEY=your_groq_key
COHERE_API_KEY=your_cohere_key
GITHUB_TOKEN=your_github_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Run with Docker

```bash
docker compose up --build
```

### Run locally

```bash
uvicorn app.main:app --reload
```

### Indexing a codebase

```bash
python scripts/index_repo.py --repo-path /path/to/your/repo
```

## Usage

### Trigger the autonomous debugger

```bash
curl -X POST http://localhost:8000/debug \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo", "error_log": "..."}'
```

### Query the codebase (RAG search)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "where is the rate limiter implemented?"}'
```

### MCP server (Claude Desktop)

Add to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "agentic-ai-debugger": {
      "command": "python",
      "args": ["-m", "app.mcp_server"]
    }
  }
}
```

## CI/CD Integration

Add the provided GitHub Actions workflow (`.github/workflows/auto-debug.yml`) to trigger the autonomous debugger whenever a test suite run fails, opening a PR with a proposed fix automatically.

## Roadmap

- [ ] Expand language-specific AST chunking beyond the current 8 languages
- [ ] Add support for multi-repo context retrieval
- [ ] Human-in-the-loop approval gate before auto-merge



## Author

Navdisha Bhakri — [GitHub](https://github.com/navdishabhakri) · [Portfolio](https://portfolio-navdisha.netlify.app/) · [LinkedIn](https://www.linkedin.com/in/navdisha-bhakri-58745b265/)
