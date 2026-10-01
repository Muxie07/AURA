import os

# Fix knowledge.py
kb_path = r'backend/app/api/v1/knowledge.py'
with open(kb_path, 'r') as f:
    kb_code = f.read()

# Add rate limit import if missing
if 'from app.security.rate_limit import rate_limit_dependency' not in kb_code:
    kb_code = kb_code.replace(
        'from app.api.deps import CurrentUserDep, DatabaseDep',
        'from app.api.deps import CurrentUserDep, DatabaseDep\nfrom app.security.rate_limit import rate_limit_dependency'
    )

# Add pagination to list_knowledge_bases
if 'async def list_knowledge_bases(' in kb_code and 'page: int = Query' not in kb_code:
    kb_code = kb_code.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, Query')
    kb_code = kb_code.replace(
        'async def list_knowledge_bases(\n\n    current_user: CurrentUserDep, db: DatabaseDep\n) -> Any:',
        'async def list_knowledge_bases(\n    current_user: CurrentUserDep, db: DatabaseDep, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)\n) -> Any:'
    )
    old_list_kb_query = '''    result = await db.execute(
        sa.select(KnowledgeBase).where(KnowledgeBase.organization_id == current_user.organization_id)
    )'''
    new_list_kb_query = '''    result = await db.execute(
        sa.select(KnowledgeBase).where(KnowledgeBase.organization_id == current_user.organization_id).offset((page - 1) * page_size).limit(page_size)
    )'''
    kb_code = kb_code.replace(old_list_kb_query, new_list_kb_query)

# Add rate limits to upload_document
if '@router.post(\"/knowledge-bases/{kb_id}/documents\", response_model=DocumentResponse)' in kb_code:
    kb_code = kb_code.replace(
        '@router.post(\"/knowledge-bases/{kb_id}/documents\", response_model=DocumentResponse)',
        '@router.post(\"/knowledge-bases/{kb_id}/documents\", response_model=DocumentResponse, dependencies=[Depends(rate_limit_dependency)])'
    )

# Add rate limits to query_knowledge_base
if '@router.post(\"/knowledge-bases/{kb_id}/query\", response_model=RAGResponseSchema)' in kb_code:
    kb_code = kb_code.replace(
        '@router.post(\"/knowledge-bases/{kb_id}/query\", response_model=RAGResponseSchema)',
        '@router.post(\"/knowledge-bases/{kb_id}/query\", response_model=RAGResponseSchema, dependencies=[Depends(rate_limit_dependency)])'
    )

with open(kb_path, 'w') as f:
    f.write(kb_code)

print('Done patching knowledge.py.')
