# AURA Knowledge Intelligence & RAG Architecture

This document describes the design and implementation of Phase 3: Enterprise RAG (Retrieval-Augmented Generation) & Knowledge Intelligence.

## 1. Architecture Overview
AURA implements an enterprise-grade ingestion and retrieval system.

**Key Components**:
- **Ingestion Pipeline**: Asynchronously extracts text, chunks it, embeds it, and stores it in PostgreSQL.
- **Storage Layer**: An abstract FileStorage handles raw file storage. 
- **Retrieval Engine**: Isolated, tenant-aware semantic search via pgvector.
- **RAG Service**: Orchestrates retrieval, reranking, context building, and generation.

## 2. Ingestion Pipeline
1. **Upload & Validation**: Files are checked for size and type limits.
2. **Storage**: The file is stored in LocalFileStorage (production will use S3).
3. **Parsing**: DocumentParser reads PDF, DOCX, TXT, or MD, extracting raw text and metadata.
4. **Chunking**: DocumentChunker splits the document, maintaining overlapping context (default 512 chars with 64 overlap). 
5. **Embedding**: LLMService (using 	ext-embedding-3-small or mock) converts chunks into 1536-dimensional vectors.
6. **Vector Storage**: The vectors, content, and metadata are persisted into PostgreSQL using the DocumentChunk model.

## 3. Database & pgvector Decision
We rely on **PostgreSQL with pgvector**.
- **Why?** It prevents the need to maintain a separate vector database (like Pinecone or Qdrant), reducing operational complexity while maintaining high performance. 
- **Isolation**: Tenant isolation is strictly enforced via organization_id at the database query level (WHERE organization_id = :org_id).

## 4. Chunking Strategy
The chunking strategy uses Recursive Character Splitting.
- It is deterministic and preserves document order.
- Each chunk stores metadata, which retains tracking information such as the source document, page number, and chunk index. This enables exact source attribution for the LLM.

## 5. Embedding Abstraction
The LLMProvider abstraction from Phase 2 was expanded. 
- The application uses embed() without hardcoding OpenAI. 
- Tests run locally against a MockLLMProvider which returns deterministic embeddings, saving cost and running instantly.

## 6. Retrieval Strategy (Tenant Isolated)
The retrieval layer implements semantic similarity search via pgvector's <=> (cosine distance) operator.
- **Tenant Isolation**: A query belonging to Organization A will *never* retrieve documents from Organization B because the SQL query strictly filters by organization_id.

## 7. Hybrid Retrieval (Future)
We have introduced a conceptual abstraction for hybrid search. While the current implementation prioritizes vector semantic search, the Retriever class is structured so that keyword/BM25 can be blended and re-weighted.

## 8. Reranking
A Reranker interface is introduced.
- **Current (Phase 3)**: A MockReranker sorts by vector similarity score. 
- **Future**: A cross-encoder model (like Cohere Rerank) can be plugged in without modifying the RAGService.

## 9. Context Building & Source Attribution
The ContextBuilder:
- Deduplicates chunks based on chunk_id.
- Truncates context securely to fit within the LLM's context window.
- Formats context clearly with citations (e.g., Source: filename.pdf, Page 4).
- Ensures the final LLM response can directly point back to specific document sources.

## 10. Security Boundaries
- Uploaded content is treated as untrusted data.
- Prompt injection protection boundaries are prepped (but fully addressed in Phase 5).
- Tenant isolation is database-enforced, NOT prompt-enforced.

## 11. Background Processing
Document ingestion can be slow. Therefore, the API endpoint utilizes FastAPI's BackgroundTasks to offload parsing/embedding, immediately returning the Document ID and PROCESSING status to the user.

## 12. Future Evaluation Strategy
The abstractions support future testing for Recall@K, Precision@K, and MRR. The metrics telemetry logs queries, top-k configurations, and retrieved candidates, which sets the foundation for continuous evaluation.
