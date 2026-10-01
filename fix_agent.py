import io
import re

with io.open("backend/app/api/v1/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Define the background task
background_func = """
async def run_agent_in_background(run_id: uuid.UUID):
    from app.database.base import get_session_factory
    from app.ai.services.llm import LLMService
    from app.knowledge.rag_service import RAGService
    from app.agents.services.agent_service import AgentWorkflowService
    import traceback
    
    SessionFactory = get_session_factory()
    async with SessionFactory() as db:
        llm = LLMService()
        rag = RAGService(db, llm)
        agent_service = AgentWorkflowService(db, llm, rag)
        try:
            await agent_service.execute_run(run_id)
        except BaseException as e:
            traceback.print_exc()
        finally:
            await agent_service.aclose()

"""

# Replace the synchronous execution in create_agent_run
old_exec = """    agent_service = AgentWorkflowService(db, llm, rag)
    try:
        await agent_service.execute_run(run.id)
    except BaseException:
        import traceback
        traceback.print_exc()
    finally:
        await agent_service.aclose()

    await db.refresh(run)"""

new_exec = """    background_tasks.add_task(run_agent_in_background, run.id)"""

content = content.replace(old_exec, new_exec)
if "async def run_agent_in_background" not in content:
    content = content.replace("def get_llm() -> LLMService:", background_func + "def get_llm() -> LLMService:")

with io.open("backend/app/api/v1/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
