#!/usr/bin/env python3
"""
Benchmark: deterministic fast path vs LLM action-selection.

AURA's DecisionNode tries regex/keyword extraction before calling an LLM to
choose the next action (app/agents/execution/decision.py). When a request
contains the structured arguments the tool needs, planning skips the model
entirely; when it doesn't, the request falls through to LLM-based action
selection.

This measures the difference end to end, through the public API, on whatever
deployment you point it at -- no mocks, no internal imports. It reports median
and p95 latency plus token usage per group.

Usage:
    python benchmark_fastpath.py                       # against localhost
    python benchmark_fastpath.py --base-url https://aura-backend-z1qs.onrender.com/api/v1
    python benchmark_fastpath.py --runs 10             # more samples per group

Credentials default to the seeded demo user and can be overridden with
--email / --password or AURA_BENCH_EMAIL / AURA_BENCH_PASSWORD.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

import httpx

# Phrasings that match the structured pattern DecisionNode extracts directly:
#   "for <company> for <N> units of <model> at <tier> tier"
FAST_PATH_REQUESTS = [
    "Generate an invoice for Northwind Trading for 12 units of UC-2000-VE-4T at end_customer tier",
    "Generate an invoice for Baker Logistics for 5 units of UC-2000-VE-4T at reseller tier",
    "Generate an invoice for Halden Systems for 30 units of UC-2000-VE-4T at distributor tier",
]

# Same intent, but without the structured arguments -- forces the planner to
# fall through to LLM-based action selection.
LLM_PATH_REQUESTS = [
    "Could you put together an invoice for that logistics customer we spoke to, standard pricing",
    "I need billing paperwork drawn up for a mid-size reseller order, nothing unusual",
    "Draft an invoice for the new account, they're buying a modest quantity at their usual rate",
]

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "AWAITING_APPROVAL"}


def login(client: httpx.Client, base_url: str, email: str, password: str) -> str:
    r = client.post(
        f"{base_url}/auth/token",
        json={"email": email, "password": password},
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_conversation(client: httpx.Client, base_url: str, headers: dict) -> str:
    r = client.post(
        f"{base_url}/conversations",
        json={"title": "fast-path benchmark"},
        headers=headers,
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()["id"]


def run_once(
    client: httpx.Client, base_url: str, headers: dict, conversation_id: str, request_text: str
) -> dict | None:
    """Submit one agent run, poll to completion, return its recorded metrics."""
    started = time.perf_counter()
    r = client.post(
        f"{base_url}/runs",
        json={"conversation_id": conversation_id, "request": request_text},
        headers=headers,
        timeout=60.0,
    )
    r.raise_for_status()
    run_id = r.json()["run_id"]

    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(1.5)
        detail = client.get(f"{base_url}/runs/{run_id}", headers=headers, timeout=60.0)
        detail.raise_for_status()
        body = detail.json()
        status = str(body.get("status", "")).upper()
        if status in TERMINAL_STATUSES:
            tokens = body.get("token_usage") or {}
            return {
                "wall_ms": (time.perf_counter() - started) * 1000,
                "reported_ms": body.get("latency_ms"),
                "tokens_in": tokens.get("input", 0),
                "tokens_out": tokens.get("output", 0),
                "tool_calls": body.get("tool_call_count", 0),
                "status": status,
            }

    print(f"  ! timed out waiting for run {run_id}", file=sys.stderr)
    return None


def summarize(label: str, samples: list[dict]) -> dict | None:
    ok = [s for s in samples if s]
    if not ok:
        print(f"\n{label}: no successful runs")
        return None

    wall = sorted(s["wall_ms"] for s in ok)
    tokens_total = [s["tokens_in"] + s["tokens_out"] for s in ok]

    def pct(values: list[float], p: float) -> float:
        if len(values) == 1:
            return values[0]
        k = (len(values) - 1) * p
        lo, hi = int(k), min(int(k) + 1, len(values) - 1)
        return values[lo] + (values[hi] - values[lo]) * (k - lo)

    stats = {
        "n": len(ok),
        "median_ms": statistics.median(wall),
        "p95_ms": pct(wall, 0.95),
        "mean_tokens": statistics.mean(tokens_total) if tokens_total else 0,
    }
    print(f"\n{label}")
    print(f"  runs            : {stats['n']}")
    print(f"  median latency  : {stats['median_ms']:.0f} ms")
    print(f"  p95 latency     : {stats['p95_ms']:.0f} ms")
    print(f"  mean tokens     : {stats['mean_tokens']:.0f}")
    print(f"  statuses        : {', '.join(sorted({s['status'] for s in ok}))}")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/api/v1")
    ap.add_argument("--email", default=os.environ.get("AURA_BENCH_EMAIL", "demo@aura-sre.com"))
    ap.add_argument("--password", default=os.environ.get("AURA_BENCH_PASSWORD", "demo1234"))
    ap.add_argument("--runs", type=int, default=3, help="samples per group")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")

    with httpx.Client(follow_redirects=True) as client:
        print(f"Authenticating against {base_url} ...")
        token = login(client, base_url, args.email, args.password)
        headers = {"Authorization": f"Bearer {token}"}
        conversation_id = create_conversation(client, base_url, headers)

        # Warm the instance so a cold start isn't charged to the first sample.
        client.get(f"{base_url}/health", timeout=120.0)

        results: dict[str, list[dict]] = {"fast": [], "llm": []}
        for group, pool in (("fast", FAST_PATH_REQUESTS), ("llm", LLM_PATH_REQUESTS)):
            label = "deterministic fast path" if group == "fast" else "LLM action selection"
            print(f"\nRunning {args.runs} samples -- {label}")
            for i in range(args.runs):
                text = pool[i % len(pool)]
                print(f"  [{i + 1}/{args.runs}] {text[:60]}...")
                results[group].append(run_once(client, base_url, headers, conversation_id, text))

    print("\n" + "=" * 60)
    fast = summarize("Deterministic fast path", results["fast"])
    llm = summarize("LLM action selection", results["llm"])

    if fast and llm and fast["median_ms"] and llm["median_ms"]:
        speedup = llm["median_ms"] / fast["median_ms"]
        saved = llm["mean_tokens"] - fast["mean_tokens"]
        print("\n" + "=" * 60)
        print(f"Fast path is {speedup:.1f}x faster at the median")
        print(f"and uses {saved:.0f} fewer tokens per run on average.")
        print(
            "\nNote: both groups run the same tool; the difference is whether the\n"
            "planner had to call a model to work out the arguments."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
