"""
AURA — Agents Package (Phase 3).

The agent orchestration layer will be implemented in Phase 3.
It will use LangGraph to define an explicit state machine workflow.

Planned structure:
    agents/
    ├── state.py          — Typed agent state (AgentState TypedDict)
    ├── graph.py          — LangGraph state machine definition
    ├── nodes/
    │   ├── analyze.py    — Intent analysis node
    │   ├── plan.py       — Planning node
    │   ├── execute.py    — Tool execution node
    │   ├── validate.py   — Result validation node
    │   └── finalize.py   — Response generation node
    └── policies/
        └── approval.py   — Approval policy evaluation
"""
