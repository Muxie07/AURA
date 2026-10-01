import uuid
from typing import Any

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Query, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.ai.services.llm import LLMService
from app.api.deps import CurrentUserDep, DatabaseDep
from app.security.rate_limit import rate_limit_dependency
from app.database.models import Document, DocumentStatus, KnowledgeBase
from app.knowledge.ingestion import DocumentIngestionService
from app.knowledge.rag_service import RAGService
from app.knowledge.storage import LocalFileStorage

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Knowledge"])

# Schemas
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None

class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    file_size: int

class SearchQuery(BaseModel):
    query: str

class RAGQuery(BaseModel):
    query: str

class RAGResponseSchema(BaseModel):
    answer: str
    sources: list[dict[str, Any]]

# Dependencies
def get_storage() -> Any:
    return LocalFileStorage()

def get_llm() -> LLMService:
    return LLMService()

# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------

@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    current_user: CurrentUserDep, kb: KnowledgeBaseCreate,

    db: DatabaseDep
) -> Any:
    new_kb = KnowledgeBase(
        organization_id=current_user.organization_id,
        name=kb.name,
        description=kb.description
    )
    db.add(new_kb)
    await db.commit()
    await db.refresh(new_kb)
    return new_kb

@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    current_user: CurrentUserDep, db: DatabaseDep, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
) -> Any:
    result = await db.execute(
        sa.select(KnowledgeBase).where(KnowledgeBase.organization_id == current_user.organization_id).offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all()

# ---------------------------------------------------------------------------
# Document Ingestion
# ---------------------------------------------------------------------------

@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse, dependencies=[Depends(rate_limit_dependency)])
async def upload_document(
    current_user: CurrentUserDep, kb_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: DatabaseDep,
    file: UploadFile = File(...),
    storage: LocalFileStorage = Depends(get_storage),
    llm_service: LLMService = Depends(get_llm)
) -> Any:
    # Verify KB belongs to org
    result = await db.execute(
        sa.select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.organization_id == current_user.organization_id
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")

    # Read file content safely (Phase 3 limit: maybe 20MB)
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 20MB.")

    # Create document record
    doc = Document(
        knowledge_base_id=kb.id,
        organization_id=current_user.organization_id,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        status=DocumentStatus.UPLOADED
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger background ingestion
    ingestion_service = DocumentIngestionService(db, storage, llm_service)
    background_tasks.add_task(
        ingestion_service.ingest_document,
        document_id=doc.id,
        file_content=content,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream"
    )

    return doc

@router.get("/documents/{doc_id}/status", response_model=DocumentResponse)
async def get_document_status(
    current_user: CurrentUserDep, doc_id: uuid.UUID,

    db: DatabaseDep
) -> Any:
    result = await db.execute(
        sa.select(Document).where(
            Document.id == doc_id,
            Document.organization_id == current_user.organization_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc

# ---------------------------------------------------------------------------
# Query / Search
# ---------------------------------------------------------------------------

@router.post("/knowledge-bases/{kb_id}/query", response_model=RAGResponseSchema, dependencies=[Depends(rate_limit_dependency)])
async def query_knowledge_base(
    current_user: CurrentUserDep, kb_id: uuid.UUID,
    query: RAGQuery,

    db: DatabaseDep,
    llm_service: LLMService = Depends(get_llm)
) -> Any:
    rag_service = RAGService(db, llm_service)

    try:
        response = await rag_service.query(
            organization_id=current_user.organization_id,
            knowledge_base_id=kb_id,
            question=query.query
        )

        return {
            "answer": response.answer,
            "sources": [
                {
                    "chunk_id": s.chunk_id,
                    "document_id": s.document_id,
                    "source": s.source,
                    "score": s.score
                } for s in response.sources
            ]
        }
    except Exception as e:
        logger.error("rag_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process query.") from e
