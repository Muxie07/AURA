# Security Fixes Report

## Findings and Fixes

1. **Mock Identity in Runs API**
   - **File:** `backend/app/api/v1/runs.py`
   - **Line:** ~22
   - **Issue:** Used `uuid4()` for `conversation_id` instead of the one provided in request. Passed mock `organization_id` using incorrect model field.
   - **Fix:** Switched `CreateRunRequest` to require `conversation_id`, verified `Conversation` belongs to `current_user.organization_id`, and properly set `user_id` without setting non-existent `organization_id` on `AgentRun`.

2. **Hardcoded Identity in Agent API**
   - **File:** `backend/app/api/v1/agent.py`
   - **Line:** ~64, ~117, ~133, ~155, ~172, ~207 (all endpoints)
   - **Issue:** Used `_PLACEHOLDER_ORG_ID` and `_PLACEHOLDER_USER_ID` constants instead of authenticated user data. Missing tenant isolation checks in query endpoints.
   - **Fix:** Injected `CurrentUserDep` into all endpoints. Replaced placeholders with `current_user.organization_id` and `current_user.id`. Added `Conversation.organization_id == current_user.organization_id` filters using joins to ensure strict tenant isolation across agent runs, tracing, events, and approvals.

3. **Authentication Bypass & Spoofed Headers in MCP Server**
   - **File:** `backend/app/tools/mcp/routes.py`
   - **Line:** ~23, ~60
   - **Issue:** The ASGI handler `asgi_handler` trusted the `X-Organization-Id` header sent by clients directly without validation.
   - **Fix:** Implemented JWT verification directly in the ASGI handler to securely authenticate the caller. Set `mcp_org_id` and permissions based on verified JWT claims. Explicitly reject mismatched `X-Organization-Id` headers to prevent spoofing.

4. **MCP Direct Execution Policy Bypasses**
   - **File:** `backend/app/tools/mcp/server.py`
   - **Line:** ~48
   - **Issue:** `__aura_context` or `organization_id` could be injected via `arguments`. 
   - **Fix:** Hardened the `call_tool` implementation to drop injection attempts. Validates against `PolicyEngine.evaluate()` before executing the tool, handling `REQUIRE_APPROVAL` and `DENY` decisions correctly.

5. **Security Tests Added**
   - **File:** `backend/tests/tools/mcp/test_security.py`
   - **Added Tests:**
     - `test_mcp_unauthenticated_request_rejected`: Proves unauthenticated request is rejected.
     - `test_mcp_invalid_token_rejected`: Proves invalid token is rejected.
     - `test_mcp_valid_tenant_a_cannot_access_tenant_b`: Proves spoofed organization headers cannot override authenticated organization.
     - `test_mcp_write_permission_denied`: Proves WRITE permission denied without `tools:write`.
     - `test_mcp_direct_execution_cannot_bypass_policy_engine`: Proves direct execution evaluates policy engine correctly.

6. **Agent Orchestration Tests**
   - **File:** `backend/tests/agent/test_orchestration.py`
   - **Line:** ~80
   - **Issue:** Mock nodes in tests lacked the `action_type` field expected by execution flows.
   - **Fix:** Fixed mock structures so orchestration security tests pass with the new policy checks.

The entire scope has been successfully remediated, tested, formatted, and validated.
