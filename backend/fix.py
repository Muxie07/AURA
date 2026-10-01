import re


def fix_runs():
    path = "app/api/v1/runs.py"
    with open(path) as f:
        content = f.read()

    # CreateRunRequest doesn't have conversation_id, maybe we can accept it or just leave it out, wait, if AgentRun requires conversation_id we should take it from req
    if "conversation_id: uuid.UUID" not in content and "class CreateRunRequest" in content:
        content = content.replace("class CreateRunRequest(BaseModel):", "class CreateRunRequest(BaseModel):\n    conversation_id: uuid.UUID")

    # Replace uuid.uuid4() with req.conversation_id
    content = re.sub(r'conversation_id=uuid\.uuid4\(\)\s*#\s*Mock conversation ID', 'conversation_id=req.conversation_id', content)

    with open(path, "w") as f:
        f.write(content)

def fix_agent():
    path = "app/api/v1/agent.py"
    with open(path) as f:
        content = f.read()

    # Add CurrentUserDep
    if "from app.api.deps import" in content and "CurrentUserDep" not in content:
        content = content.replace("from app.api.deps import DatabaseDep", "from app.api.deps import DatabaseDep, CurrentUserDep")

    # Replace _PLACEHOLDER_ORG_ID and _PLACEHOLDER_USER_ID
    # Find def create_agent_run(..., db: DatabaseDep, ...)
    content = re.sub(r'(def create_agent_run\([^)]+db:\s*DatabaseDep,\n?\s*)(llm:\s*LLMService = Depends\(get_llm\),\n?\s*rag:\s*RAGService = Depends\(get_rag\)\n?\s*\))', r'\1current_user: CurrentUserDep,\n    \2', content)

    # In create_agent_run:
    # replace _PLACEHOLDER_ORG_ID = uuid.UUID(...) with _PLACEHOLDER_ORG_ID = current_user.organization_id
    # replace _PLACEHOLDER_USER_ID = uuid.UUID(...) with _PLACEHOLDER_USER_ID = current_user.id
    content = re.sub(r'_PLACEHOLDER_ORG_ID\s*=\s*uuid\.UUID\("[^"]+"\)', 'org_id = current_user.organization_id', content)
    content = re.sub(r'_PLACEHOLDER_USER_ID\s*=\s*uuid\.UUID\("[^"]+"\)', 'user_id = current_user.id', content)

    content = content.replace("Conversation.organization_id == _PLACEHOLDER_ORG_ID", "Conversation.organization_id == org_id")
    content = content.replace("user_id=_PLACEHOLDER_USER_ID", "user_id=user_id")

    # Fix other endpoints to check organization isolation
    # For now, let's just make sure they take CurrentUserDep, but the prompt says: "verify tenant isolation across agent runs, tools, MCP, RAG, observability, evaluations, approvals".
    # This means we should add isolation checks everywhere.

    with open(path, "w") as f:
        f.write(content)

if __name__ == "__main__":
    fix_runs()
    fix_agent()
    print("Fixed runs and agent")
