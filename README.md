# codebase-qa
Production-grade RAG system + autonomous AI agents for codebase understanding and automated debugging
* AST chunking across 8 languages (Python, JS, TS, Go, Java, Rust, C++, + fallback for 20+ more) using Tree-sitter
* Hybrid search — BM25 + CodeBERT vector search + RRF fusion + Cohere reranking
* Query expansion with guardrails, temperature control, streaming responses
* Autonomous debugger — LangGraph agent (5 nodes, memory, retry) that parses errors, searches codebase, generates fixes, validates by running code, and opens GitHub PRs automatically
* Code review agent — fetches PR diffs, searches related codebase context, posts inline GitHub comments
* CI/CD integration — GitHub Actions triggers auto-debugging on test failure
* MCP server — Claude Desktop can query your codebase directly
* RAGAS evaluation: faithfulness 0.67 · answer relevancy 0.84 · context recall 0.68
* Stack: FastAPI · PostgreSQL + pgvector · CodeBERT · LangGraph · Cohere · Groq · PyGithub · Docker · Railway · Supabase
