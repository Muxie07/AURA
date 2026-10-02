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
        result = await self.db.execute(sa.select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            logger.error("document_not_found", document_id=str(document_id))
            return

        try:
            import hashlib
            file_hash = hashlib.sha256(file_content).hexdigest()
            document.metadata_["checksum"] = file_hash

            # Dedupe: check if document with same checksum exists in this KB
            dup_stmt = sa.select(Document).where(
                Document.knowledge_base_id == document.knowledge_base_id,
                Document.id != document.id,
                Document.status == DocumentStatus.READY,
            )
            dup_res = await self.db.execute(dup_stmt)
            for dup_doc in dup_res.scalars():
                if dup_doc.metadata_.get("checksum") == file_hash:
                    document.status = DocumentStatus.FAILED
                    document.metadata_["error"] = "Duplicate checksum"
                    await self.db.commit()
                    logger.info("document_ingestion_skipped_duplicate", document_id=str(document_id))
                    return

            # Versioning: mark older docs with same filename as not latest
            ver_stmt = sa.update(Document).where(
                Document.knowledge_base_id == document.knowledge_base_id,
                Document.filename == document.filename,
                Document.id != document.id
            ).values(is_latest=False)
            await self.db.execute(ver_stmt)

            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            # 1. Save file & magic byte validate
            # Pure python magic byte check for PDF and Office files
            header = file_content[:4]
            if header.startswith(b'%PDF'):
                mime_group = "pdf"
            elif header.startswith(b'PK\x03\x04'):
                mime_group = "office/docx"
            elif header.startswith(b'\xd0\xcf\x11\xe0'):
                mime_group = "office/legacy"
            elif all(b < 128 for b in header):
                mime_group = "text"
            else:
                raise ValueError(f"Invalid or unsupported file type, header: {header}")

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
                "knowledge_base_id": str(document.knowledge_base_id),
            }
            if "pages" in parsed_metadata:
                base_meta["pages"] = parsed_metadata["pages"]

            chunks_data = self.chunker.chunk(text, base_meta)

            if not chunks_data:
                raise ValueError("Document is empty or contains no extractable text.")

            # 4. Embed (batching for large documents)
            batch_size = 100
            for i in range(0, len(chunks_data), batch_size):
                batch = chunks_data[i : i + batch_size]
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
                        token_count=len(chunk["content"]) // 4,  # Rough approximation
                    )
                    self.db.add(doc_chunk)

                await self.db.commit()

            document.status = DocumentStatus.READY
            await self.db.commit()
            logger.info(
                "document_ingestion_complete", document_id=str(document.id), chunks=len(chunks_data)
            )

        except Exception as e:
            logger.error("document_ingestion_failed", document_id=str(document_id), error=str(e))
            document.status = DocumentStatus.FAILED
            document.metadata_["error"] = str(e)
            await self.db.commit()

    async def migrate_embeddings(self, new_model: str, batch_size: int = 100) -> None:
        stmt = sa.select(DocumentChunk)
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.content for c in batch]
            embeddings = await self.llm.provider.embed(texts, model=new_model)
            for j, chunk in enumerate(batch):
                chunk.embedding = embeddings[j]
            await self.db.commit()
