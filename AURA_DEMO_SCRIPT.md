# AURA Demo Script: Enterprise AI Operations Platform

This guide outlines a high-impact, step-by-step demonstration of AURA, tailored for startup founders, engineering leaders, and venture capitalists.

## Prerequisites
1. Docker must be running.
2. Run `docker compose up -d`
3. (If fresh) Run `docker exec aura-backend python scripts/seed_demo.py`
4. Open your browser to `http://localhost:3000`

---

## 1. Authentication & Tenant Isolation
**Action:**
- Navigate to `http://localhost:3000`. You will be redirected to the secure login page.
- Log in with the demo credentials:
  - **Email:** `demo@aura-sre.com`
  - **Password:** `demo1234`

**Talking Points:**
- Highlight that AURA is built from the ground up for the enterprise. It features **strict JWT-based authentication** and **multi-tenant isolation**. 
- The data you are about to see is completely isolated to the "AURA Demo Inc" tenant organization.

## 2. The Dashboard (High-Level Overview)
**Action:**
- Once logged in, show the main dashboard.
- Point out the metrics: Total Agent Runs, Pending Approvals, Recent Runs, Action Required.

**Talking Points:**
- This is the command center. You can immediately see the volume of agent activity and whether any high-risk actions are blocked waiting for human approval.
- Point out the active/completed runs populated by the demo data (e.g., "Investigating production API latency", "Customer churn analysis").

## 3. The AI Agent in Action
**Action:**
- Navigate to the **Conversations** tab.
- Click on an existing conversation (e.g., "Investigating production API latency") or start a new one.
- Explain the agent workflow.

**Talking Points:**
- AURA isn't just a chatbot; it's an **autonomous agent** using a directed graph architecture.
- When an alert comes in, AURA performs **Intent Analysis**, creates a **Plan**, retrieves context via **RAG**, executes **Tools**, and verifies the outcome before responding.

## 4. Knowledge Base & RAG
**Action:**
- Navigate to the **Knowledge** tab.
- Show the 6 seeded enterprise knowledge bases (e.g., SRE Runbooks, Company Policies, Security Procedures).

**Talking Points:**
- The agent doesn't guess; it grounds its decisions in your company's actual documentation using **PgVector** embeddings.
- If a database goes down, AURA reads the exact "Database Migration Planning" or "SRE Runbook" document specific to this tenant.

## 5. Tools & MCP (Model Context Protocol)
**Action:**
- Navigate to the **Tools** tab.
- Show the Tools Registry (e.g., `customer.search`, `restart_service`, `kill_process`).

**Talking Points:**
- AURA interacts with your infrastructure through the **Model Context Protocol (MCP)**.
- Notice the **Risk Levels**. Tools like `customer.search` are LOW risk and auto-execute. Tools like `restart_service` are HIGH risk and require human approval.

## 6. Human-in-the-Loop (HITL) Approvals
**Action:**
- Navigate to the **Approvals** tab.
- Point out the pending, approved, and denied requests.
- Show a `PENDING` request (e.g., `kill_process` or `order.create`).

**Talking Points:**
- **Enterprise Safety**: AURA *cannot* mutate critical state without explicit human approval. This is the **Human-in-the-Loop (HITL)** architecture.
- **Idempotency**: Under the hood, if you click approve twice, or the network drops, **Redis and Postgres** ensure the action is only executed once.

## 7. Observability & Audit Trails
**Action:**
- Navigate to the **Observability** tab.
- Show the detailed trace events for the agent runs.

**Talking Points:**
- **Auditability**: Every tool call, prompt, plan, and human approval is logged immutably.
- You can see exactly how long the planner took, what query was sent to the RAG system, and which tools were executed. 
- This provides a complete compliance and post-mortem artifact out of the box.

## 8. Conclusion
**Talking Points:**
- AURA takes the chaos out of enterprise operations. It combines the reasoning of modern AI with the strict security, multi-tenancy, and audibility required by enterprise IT and SRE teams.
