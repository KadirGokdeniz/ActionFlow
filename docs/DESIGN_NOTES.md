# Design Notes

## Policy Search: Two Independent Backends

The codebase has two separate policy search systems:

### 1. pgvector (policy_service.py + embedding.py)
- Model: text-embedding-3-small
- Used by: /api/v1/policies/search (REST API)
- Data: policies table, content_embedding column
- Consistent: creation + search both use text-embedding-3-small

### 2. Pinecone (rag_service.py)
- Model: text-embedding-ada-002
- Used by: info_agent.py (AI agent policy Q&A)
- Data: Pinecone index "actionflow-policies"
- Consistent: indexing + search both use text-embedding-ada-002

### Known Gap
Adding/updating a policy via REST API updates pgvector but NOT Pinecone.
The AI agent will NOT see policies that were not indexed in Pinecone.

### Recommended Fix (future)
Option A: Use pgvector for AI agent too (remove Pinecone dependency)
Option B: Sync Pinecone when policies are updated in the DB
