# AURA E2E Demo Workflow

Here is how a standard production request flows through AURA.

## 1. Request Intention
User: *"Find customer ACME Corp, check their hardware warranty, and draft a quotation for 10 replacement units."*

## 2. Planning & Model Routing
- **ModelRouter**: Detects multi-tool intent and flags `COMPLEX_REASONING`. Routes to `gpt-4o`.
- **Planner**: Generates DAG with `dependencies`.
  - Node A: `retrieve_customer` (independent)
  - Node B: `rag_search` (independent)
  - Node C: `create_quotation` (Depends on A, B)

## 3. Parallel Execution
- `ExecutionNode` fires `asyncio.gather` on Node A and Node B.
- **RAG Engine** uses hybrid search (BM25 + pgvector) to retrieve warranty terms.

## 4. Policy Engine
- Node C triggers `create_quotation`. 
- `PolicyEngine` identifies `create_quotation` as `HIGH` risk.
- Execution halts, committing an `ApprovalRequest` to the DB and yielding a `WAITING` state.

## 5. Human-in-the-Loop & Verification
- Manager clicks **Approve** on the frontend dashboard.
- Workflow resumes.
- `VerificationNode` cross-references chunk citations, calculating `citation_correctness`.

## 6. AI Ops Evaluation
- Trace data routes to `QualityEvaluator` and `SafetyEvaluator`.
- `CostManager` intercepts the token usage and deducts `$0.005` from the organization's daily budget.
- Returns JSON output to the user and logs Ops metrics for the Observability Dashboard.
