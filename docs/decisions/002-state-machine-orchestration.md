# ADR-002: State-Machine Orchestration (LangGraph) Over Autonomous Loops

**Status:** Accepted  
**Date:** 2026-09-13  
**Deciders:** AURA Engineering

## Context

Designing the agent architecture, we must choose between:

1. **Uncontrolled autonomous loop** — LLM decides when to stop, which tools to call, and in what order
2. **Explicit state machine** — Defined states, transitions, and termination conditions

## Decision

Use **LangGraph** as an explicit state machine with typed state, defined transitions,
and hard termination conditions.

## Rationale

### The Problem with Uncontrolled Loops

Uncontrolled LLM agent loops (e.g., vanilla ReAct with no guardrails) exhibit:

- **Runaway behavior**: Agent loops indefinitely if LLM fails to emit a STOP signal
- **Unpredictable cost**: No bounds on token usage or tool calls
- **Debugging difficulty**: No clear trace of state transitions
- **Auditability problems**: Hard to reconstruct what happened and why
- **Human approval**: Cannot pause at a defined checkpoint for approval

### LangGraph State Machine Benefits

```
INITIAL_STATE
    ↓
ANALYZE_INTENT
    ↓
PLAN
    ↓
EXECUTE (tool loop with max_iterations guard)
    ↓
[APPROVAL_REQUIRED] ← pauses here if needed
    ↓
VALIDATE
    ↓
FINALIZE
```

Each transition is:
- **Explicit**: Named, typed, logged
- **Reversible**: Can inspect the full state at any point
- **Bounded**: Hard iteration cap + timeout
- **Observable**: Every transition emits a trace event

## Consequences

- Agent behavior is predictable and auditable
- Maximum response time is bounded by `AURA_AGENT_TIMEOUT_SECONDS`
- Human-in-the-loop approval can pause the state machine at `APPROVAL_REQUIRED`
- The execution trace maps directly to the LangGraph state history
- Debugging is significantly easier than black-box loops

## Alternative Considered

CrewAI's multi-agent framework was considered but rejected because:
- Adds complexity before single-agent behavior is proven
- Less control over individual state transitions
- Harder to implement deterministic approval workflows

Multi-agent coordination will be revisited in a future phase.
