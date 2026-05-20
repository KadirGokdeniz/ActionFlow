# Design Notes

## Policy Search: Two Independent Backends

The codebase has two separate policy search systems:

### 1. pgvector (policy_service.py + embedding.py)
- Model: text-embedding-3-small
- Used by: /api/v1/policies/search (REST API)
- Data: policies table, content_embedding column

### 2. Pinecone (rag_service.py)
- Model: text-embedding-ada-002
- Used by: info_agent.py (AI agent policy Q&A)
- Data: Pinecone index "actionflow-policies"

### Sync Strategy (implemented)
policy_service.py syncs to Pinecone automatically on:
- POST /policies        -> rag_service.sync_policy()
- PUT  /policies/{id}  -> rag_service.sync_policy()
- DELETE /policies/{id} -> rag_service.delete_policy()

Both backends stay in sync. The AI agent sees all policies
that are managed via the REST API.
