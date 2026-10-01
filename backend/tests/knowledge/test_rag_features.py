import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.services.llm import LLMService
from app.database.models import Document, DocumentStatus, KnowledgeBase
from app.knowledge.ingestion import DocumentIngestionService
from app.knowledge.rag_service import RAGService
from app.knowledge.storage import FileStorage


@pytest_asyncio.fixture
async def knowledge_base(db_session: AsyncSession, organization) -> KnowledgeBase:
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        organization_id=organization.id,
        name="Test KB",
        description="Test KB description"
    )
    db_session.add(kb)
    await db_session.flush()
    return kb

@pytest_asyncio.fixture
async def document(db_session: AsyncSession, organization, knowledge_base) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        organization_id=organization.id,
        knowledge_base_id=knowledge_base.id,
        filename="test_doc.txt",
        content_type="text/plain",
        status=DocumentStatus.UPLOADED,
        file_size=0,
        checksum="testchecksum",
        metadata_={}
    )
    db_session.add(doc)
    await db_session.flush()
    return doc

class DummyProvider:
    async def embed(self, texts, model=None):
        return [[0.1]*1536 for _ in texts]
    async def generate_simple(self, prompt, system_prompt):
        return prompt + " expanded"
    async def generate(self, request):
        from unittest.mock import Mock
        m = Mock()
        m.text = "Mocked answer"
        return m

class MockLLMService(LLMService):
    def __init__(self):
        self.provider = DummyProvider()
    async def generate_simple(self, prompt, system_prompt):
        if "synonyms and closely related keywords" in prompt:
            return "expanded keywords"
        return "mock"
    async def generate(self, request):
        from unittest.mock import Mock
        m = Mock()
        m.text = f"Mocked answer based on context: {request.messages[0].content}"
        return m

@pytest.mark.asyncio
async def test_empty_document_handling(db_session, document):
    db_session.commit = db_session.flush
    llm = MockLLMService()
    class MockStorage(FileStorage):
        async def save_file(self, content, filename):
            return f"/mock/{filename}"
        async def load_file(self, path):
            return b""
        async def delete_file(self, path):
            pass
    storage = MockStorage()
    ingestion = DocumentIngestionService(db_session, storage, llm)

    # Try empty content
    await ingestion.ingest_document(document.id, b"   \n  ", "empty.txt", "text/plain")

    # await db_session.refresh(document)
    assert document.status == DocumentStatus.FAILED
    assert "empty or contains no extractable text" in document.metadata_.get("error", "")

@pytest.mark.asyncio
async def test_full_rag_pipeline(db_session, organization, knowledge_base, document):
    db_session.commit = db_session.flush
    llm = MockLLMService()

    # Storage mock
    class MockStorage(FileStorage):
        def __init__(self):
            pass
        async def save_file(self, content, filename):
            return f"/mock/{filename}"
        async def load_file(self, path):
            return b"content"
        async def delete_file(self, path):
            pass

    storage = MockStorage()
    ingestion = DocumentIngestionService(db_session, storage, llm)

    # 1. Ingest
    content = b"This is a test document containing important business facts about AURA enterprise. AURA was founded in 2026."
    await ingestion.ingest_document(document.id, content, "test.txt", "text/plain")

    # await db_session.refresh(document)
    assert document.status == DocumentStatus.READY

    # 2. Retrieval, Query Expansion, and Context building via RAGService
    rag = RAGService(db_session, llm)
    
    # Mock retriever since SQLite doesn't support pgvector/tsvector
    from app.knowledge.retrieval import RetrievalResult
    async def mock_search(*args, **kwargs):
        return [
            RetrievalResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(document.id),
                content="AURA was founded in 2026.",
                metadata={"source": "test.txt", "chunk_index": 0},
                score=0.9,
                source="test.txt",
                version=1
            )
        ]
    rag.retriever.search = mock_search
    
    response = await rag.query(organization.id, knowledge_base.id, "When was AURA founded?")

    assert response.sources is not None
    assert len(response.sources) > 0

    # Verify citations in sources
    source = response.sources[0]
    assert source.metadata["source"] == "test.txt"

    # 3. Verify context actually reaches agent
    # The MockLLMService puts the system prompt into the text response
    assert "=== RETRIEVED CONTEXT ===" in response.answer
    assert "AURA was founded" in response.answer
