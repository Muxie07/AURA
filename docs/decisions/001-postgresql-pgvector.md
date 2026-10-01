# ADR-001: PostgreSQL + pgvector Instead of a Dedicated Vector Database

**Status:** Accepted  
**Date:** 2026-09-13  
**Deciders:** AURA Engineering

## Context

AURA requires a vector database for storing document embeddings and performing
semantic similarity search (Phase 5 — RAG). The options are:

1. **Dedicated vector database** (Pinecone, Weaviate, Qdrant, Chroma)
2. **PostgreSQL + pgvector extension**

## Decision

Use **PostgreSQL + pgvector**.

## Rationale

| Factor | Dedicated Vector DB | PostgreSQL + pgvector |
|--------|--------------------|-----------------------|
| Infrastructure complexity | High (another service) | Low (same DB) |
| Transactional consistency | Not supported | Full ACID |
| Operational cost | High (managed service) | Low (existing DB) |
| Metadata filtering | Limited | Full SQL |
| JOIN with business data | Not possible | Native SQL JOIN |
| Migration path | Hard | Standard SQL migration |
| Team expertise required | Vector DB specific | Standard PostgreSQL |

For an AI startup at v0.1, the engineering cost of running and maintaining a
separate vector database service outweighs the marginal performance benefit.
pgvector's IVFFlat and HNSW indexes provide sufficient performance for the
expected document corpus size (< 10M vectors).

## Consequences

- All data lives in one database — simplifies backups, transactions, and queries
- Embeddings can be JOIN-ed directly with business data (customer, conversation, etc.)
- If scale demands a dedicated vector database later, the migration path is clear:
  replace the `VectorStore` adapter without changing the rest of the system
- Performance cap: pgvector is not suitable for billions of vectors without sharding

## Future Option

The `VectorStore` abstraction (Phase 5) will be designed so that replacing
pgvector with Pinecone or Qdrant requires only changing the adapter implementation.
