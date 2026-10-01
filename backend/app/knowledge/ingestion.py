import uuid

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.services.llm import LLMService
from app.database.models import Document, DocumentChunk, DocumentStatus
from app.knowledge.chunking import DocumentChunker
from app.knowledge.parsers import get_parser
from app.knowledge.storage import FileStorage

logger = structlog.get_logger(__name__)

class DocumentIngestionService:
    """Orchestrates document ingestion, parsing, chunking, and embedding."""

    def __init__(
        self,
        db_session: AsyncSession,
        storage: FileStorage,
        llm_service: LLMService,
    ):
        self.db = db_session
        self.storage = storage
        self.llm = llm_service
        # Default settings, can be overridden by config
        self.chunker = DocumentChunker()
        from app.config.settings import get_settings
        self.embedding_model = get_settings().embedding_model

    async def ingest_document(
        self,
        document_id: uuid.UUID,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> None:
        """
        Main pipeline:
        1. Save to storage
        2. Parse text & metadata
        3. Chunk text
        4. Generate embeddings
        5. Save chunks to DB
        """
        # Fetch document
        result = await self.db.execute(
            sa.select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            logger.error("document_not_found", document_id=str(document_id))
            return

        try:
            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            # 1. Save file
            storage_path = await self.storage.save_file(file_content, filename)
            document.metadata_["storage_path"] = storage_path

            # 2. Parse
            parser = get_parser(content_type, filename)
            text, parsed_metadata = parser.parse(file_content)

            if not text.strip():
                raise ValueError("Document is empty or contains no extractable text.")

            # Update doc metadata
            document.metadata_.update(parsed_metadata)

            # 3. Chunk
            base_meta = {
                "source": filename,
                "document_id": str(document.id),
                "knowledge_base_id": str(document.knowledge_base_id)
            }
            if "pages" in parsed_metadata:
                base_meta["pages"] = parsed_metadata["pages"]

            chunks_data = self.chunker.chunk(text, base_meta)

            if not chunks_data:
                raise ValueError("Document is empty or contains no extractable text.")

            # 4. Embed (batching for large documents)
            batch_size = 100
            for i in range(0, len(chunks_data), batch_size):
                batch = chunks_data[i:i+batch_size]
                texts = [c["content"] for c in batch]

                # Use embed API from LLMService
                # Assuming provider factory works correctly
                embeddings = await self.llm.provider.embed(texts, model=self.embedding_model)

                # 5. Save chunks
                for j, chunk in enumerate(batch):
                    doc_chunk = DocumentChunk(
                        document_id=document.id,
                        organization_id=document.organization_id,
                        chunk_index=chunk["metadata"]["chunk_index"],
                        content=chunk["content"],
                        metadata_=chunk["metadata"],
                        embedding=embeddings[j],
                        token_count=len(chunk["content"]) // 4 # Rough approximation
                    )
                    self.db.add(doc_chunk)

                await self.db.commit()

            document.status = DocumentStatus.READY
            await self.db.commit()
            logger.info("document_ingestion_complete", document_id=str(document.id), chunks=len(chunks_data))

        except Exception as e:
            logger.error("document_ingestion_failed", document_id=str(document_id), error=str(e))
            document.status = DocumentStatus.FAILED
            document.metadata_["error"] = str(e)
            await self.db.commit()
