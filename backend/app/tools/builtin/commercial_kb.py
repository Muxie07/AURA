import uuid
from typing import Any

import sqlalchemy as sa
import structlog

from app.database.base import get_session_factory
from app.database.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentVisibility,
    KnowledgeBase,
)

logger = structlog.get_logger(__name__)


async def _get_or_create_commercial_kb(session) -> tuple[uuid.UUID, uuid.UUID]:
    """Finds or creates a KnowledgeBase dedicated to commercial transactions."""
    kb_name = "Distribution Price Lists"
    kb = (
        (await session.execute(sa.select(KnowledgeBase).where(KnowledgeBase.name == kb_name)))
        .scalars()
        .first()
    )

    if kb:
        return kb.id, kb.organization_id

    # Fallback to any existing KB
    kb = (await session.execute(sa.select(KnowledgeBase))).scalars().first()
    if kb:
        return kb.id, kb.organization_id

    # Fallback default UUIDs
    default_org_id = uuid.UUID("a32a6292-2cc0-4523-b779-2e1ba65da0a2")
    new_kb = KnowledgeBase(
        id=uuid.uuid4(),
        organization_id=default_org_id,
        name="Commercial & Financial Records",
        description="Official commercial tax invoices, quotations, and rate records.",
    )
    session.add(new_kb)
    await session.commit()
    await session.refresh(new_kb)
    return new_kb.id, new_kb.organization_id


async def async_ingest_invoice_to_kb(invoice: dict[str, Any]) -> None:
    """Ingests generated invoice as an indexed Document and DocumentChunk in PostgreSQL."""
    try:
        sf = get_session_factory()
        async with sf() as session:
            kb_id, org_id = await _get_or_create_commercial_kb(session)

            inv_id = invoice.get("invoice_id", "INV-UNKNOWN")
            comp = invoice.get("billed_to", {})
            comp_name = comp.get("name", "Client")
            comp_email = comp.get("email", "")
            comp_addr = comp.get("address", "")
            created_date = invoice.get("created_date_formatted") or invoice.get(
                "invoice_date", "17.11.2026"
            )
            due_date = invoice.get("due_date_formatted") or invoice.get("due_date", "17.12.2026")

            items_str = ""
            for item in invoice.get("items", []):
                items_str += f"- Model: {item.get('model')} ({item.get('category')}) | Qty: {item.get('quantity')} | Unit Rate: ₹{item.get('unit_price')} | Total: ₹{item.get('total')}\n"

            subtotal = invoice.get("subtotal", 0.0)
            gst_18 = invoice.get("gst_18_percent", 0.0)
            grand_total = invoice.get("grand_total", 0.0)

            markdown_content = f"""# Commercial Tax Invoice Record: {inv_id}
- Client Company / Billed To: {comp_name} ({comp_email}, {comp_addr})
- Invoice Creation Date & Time: {created_date}
- Official Invoice Date: {invoice.get("invoice_date", "17.11.2026")}
- Payment Due Date: {due_date}
- Pricing Tier: {invoice.get("pricing_tier", "End-Customer Price")}
- Ordered Hardware Items:
{items_str}
- Subtotal: ₹{subtotal:,.2f}
- GST (18%): ₹{gst_18:,.2f}
- Grand Total (inc. 18% GST): ₹{grand_total:,.2f}
- Hardware Warranty: 3 Years Comprehensive DINSTAR Hardware Warranty
- Surface Transport: Free of Cost (FOC) across India
- Commercial Status: APPROVED & ISSUED
"""

            filename = f"commercial_invoice_{inv_id}.md"

            # Check if doc exists and delete or update
            existing_doc = (
                (
                    await session.execute(
                        sa.select(Document).where(
                            Document.filename == filename, Document.organization_id == org_id
                        )
                    )
                )
                .scalars()
                .first()
            )

            if existing_doc:
                existing_doc.content_type = "text/markdown"
                existing_doc.file_size = len(markdown_content.encode("utf-8"))
                existing_doc.status = DocumentStatus.READY
                existing_doc.is_latest = True
                existing_doc.metadata_ = {
                    "invoice_id": inv_id,
                    "company": comp_name,
                    "date": invoice.get("invoice_date"),
                    "created_at": invoice.get("created_at"),
                    "created_date_formatted": created_date,
                    "grand_total": grand_total,
                }
                # Update chunk
                chunk = (
                    (
                        await session.execute(
                            sa.select(DocumentChunk).where(
                                DocumentChunk.document_id == existing_doc.id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                if chunk:
                    chunk.content = markdown_content
                    chunk.metadata_ = {
                        "source": filename,
                        "invoice_id": inv_id,
                        "company": comp_name,
                        "date": invoice.get("invoice_date"),
                        "created_date_formatted": created_date,
                    }
                await session.commit()
            else:
                doc_id = uuid.uuid4()
                doc = Document(
                    id=doc_id,
                    knowledge_base_id=kb_id,
                    organization_id=org_id,
                    filename=filename,
                    content_type="text/markdown",
                    file_size=len(markdown_content.encode("utf-8")),
                    status=DocumentStatus.READY,
                    is_latest=True,
                    visibility=DocumentVisibility.PUBLIC,
                    allowed_roles=[],
                    allowed_user_ids=[],
                    metadata_={
                        "invoice_id": inv_id,
                        "company": comp_name,
                        "date": invoice.get("invoice_date"),
                        "created_at": invoice.get("created_at"),
                        "created_date_formatted": created_date,
                        "grand_total": grand_total,
                    },
                )
                session.add(doc)

                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    organization_id=org_id,
                    chunk_index=0,
                    content=markdown_content,
                    token_count=len(markdown_content) // 4,
                    metadata_={
                        "source": filename,
                        "invoice_id": inv_id,
                        "company": comp_name,
                        "date": invoice.get("invoice_date"),
                        "created_date_formatted": created_date,
                    },
                )
                session.add(chunk)
                await session.commit()

            logger.info("invoice_ingested_to_knowledge_base", invoice_id=inv_id, company=comp_name)
    except Exception as e:
        logger.warning("invoice_kb_ingestion_skipped", error=str(e))


async def async_ingest_quotation_to_kb(quotation: dict[str, Any]) -> None:
    """Ingests generated quotation as an indexed Document and DocumentChunk in PostgreSQL."""
    try:
        sf = get_session_factory()
        async with sf() as session:
            kb_id, org_id = await _get_or_create_commercial_kb(session)

            qid = quotation.get("quotation_id", "Q-UNKNOWN")
            comp_name = quotation.get(
                "company_name", quotation.get("customer", {}).get("name", "Client")
            )
            created_date = quotation.get("created_date_formatted") or quotation.get(
                "quotation_date", "17.11.2026"
            )
            valid_until = quotation.get("valid_until_formatted") or quotation.get(
                "valid_until", "01.12.2026"
            )

            items_str = ""
            for item in quotation.get("items", []):
                items_str += f"- Model: {item.get('model')} | Qty: {item.get('quantity')} | Unit Rate: ₹{item.get('unit_price')} | Total: ₹{item.get('total')}\n"

            subtotal = quotation.get("subtotal", 0.0)
            gst_18 = quotation.get("gst_18_percent", 0.0)
            grand_total = quotation.get("grand_total", 0.0)

            markdown_content = f"""# Commercial Quotation Record: {qid}
- Client Company: {comp_name}
- Quotation Creation Date & Time: {created_date}
- Official Quotation Date: {quotation.get("quotation_date", "17.11.2026")}
- Quotation Validity Until: {valid_until}
- Pricing Tier: {quotation.get("pricing_tier", "End-Customer Price")}
- Quoted Products:
{items_str}
- Subtotal: ₹{subtotal:,.2f}
- GST (18%): ₹{gst_18:,.2f}
- Grand Total (inc. 18% GST): ₹{grand_total:,.2f}
- Hardware Warranty: 3 Years Comprehensive DINSTAR Hardware Warranty
- Status: {quotation.get("status", "ACTIVE")}
"""

            filename = f"commercial_quotation_{qid}.md"

            existing_doc = (
                (
                    await session.execute(
                        sa.select(Document).where(
                            Document.filename == filename, Document.organization_id == org_id
                        )
                    )
                )
                .scalars()
                .first()
            )

            if existing_doc:
                existing_doc.file_size = len(markdown_content.encode("utf-8"))
                existing_doc.status = DocumentStatus.READY
                existing_doc.is_latest = True
                chunk = (
                    (
                        await session.execute(
                            sa.select(DocumentChunk).where(
                                DocumentChunk.document_id == existing_doc.id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                if chunk:
                    chunk.content = markdown_content
                await session.commit()
            else:
                doc_id = uuid.uuid4()
                doc = Document(
                    id=doc_id,
                    knowledge_base_id=kb_id,
                    organization_id=org_id,
                    filename=filename,
                    content_type="text/markdown",
                    file_size=len(markdown_content.encode("utf-8")),
                    status=DocumentStatus.READY,
                    is_latest=True,
                    visibility=DocumentVisibility.PUBLIC,
                    allowed_roles=[],
                    allowed_user_ids=[],
                    metadata_={
                        "quotation_id": qid,
                        "company": comp_name,
                        "date": quotation.get("quotation_date"),
                        "created_at": quotation.get("created_at"),
                        "created_date_formatted": created_date,
                    },
                )
                session.add(doc)

                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    organization_id=org_id,
                    chunk_index=0,
                    content=markdown_content,
                    token_count=len(markdown_content) // 4,
                    metadata_={
                        "source": filename,
                        "quotation_id": qid,
                        "company": comp_name,
                        "date": quotation.get("quotation_date"),
                        "created_date_formatted": created_date,
                    },
                )
                session.add(chunk)
                await session.commit()

            logger.info("quotation_ingested_to_knowledge_base", quotation_id=qid, company=comp_name)
    except Exception as e:
        logger.warning("quotation_kb_ingestion_skipped", error=str(e))


def sync_ingest_invoice(invoice: dict[str, Any]) -> None:
    """Synchronous / fire-and-forget bridge for invoice ingestion."""
    try:
        import asyncio

        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            asyncio.create_task(async_ingest_invoice_to_kb(invoice))
        else:
            asyncio.run(async_ingest_invoice_to_kb(invoice))
    except Exception:
        pass


def sync_ingest_quotation(quotation: dict[str, Any]) -> None:
    """Synchronous / fire-and-forget bridge for quotation ingestion."""
    try:
        import asyncio

        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            asyncio.create_task(async_ingest_quotation_to_kb(quotation))
        else:
            asyncio.run(async_ingest_quotation_to_kb(quotation))
    except Exception:
        pass
