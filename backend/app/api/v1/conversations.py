"""
AURA API v1 — Conversations Endpoint.

CRUD operations for conversation management.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DatabaseDep, RequestIDDep
from app.core.errors import NotFoundError
from app.database.models import Conversation, ConversationStatus, Message, MessageRole
from app.observability.logging import get_logger
from app.schemas.common import PaginatedResponse
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.message import MessageCreate, MessageResponse

if TYPE_CHECKING:
    from app.api.deps import CurrentUserDep, DatabaseDep, RequestIDDep

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    current_user: CurrentUserDep,
    body: ConversationCreate,
    db: DatabaseDep,
    request_id: RequestIDDep,
) -> ConversationResponse:
    """
    Create a new conversation thread.

    Optionally supply an initial user message which will be stored
    as the first message in the conversation.
    """
    conversation = Conversation(
        organization_id=current_user.organization_id,
        user_id=current_user.user_id,
        title=body.title,
        status=ConversationStatus.ACTIVE,
        metadata_={},
    )
    db.add(conversation)
    await db.flush()  # Get the ID without committing

    message_count = 0
    if body.initial_message:
        message = Message(
            organization_id=current_user.organization_id, conversation_id=conversation.id, role=MessageRole.USER, content=body.initial_message
        )
        db.add(message)
        message_count = 1

    await db.flush()

    logger.info(
        "conversation_created",
        conversation_id=str(conversation.id),
        has_initial_message=bool(body.initial_message),
    )

    return ConversationResponse(
        id=conversation.id,
        organization_id=conversation.organization_id,
        user_id=conversation.user_id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


@router.get(
    "", response_model=PaginatedResponse[ConversationResponse], summary="List conversations"
)
async def list_conversations(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    page: Annotated[int, Query(ge=1, description="Page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
    status_filter: Annotated[
        ConversationStatus | None,
        Query(alias="status", description="Filter by status."),
    ] = None,
) -> PaginatedResponse[ConversationResponse]:
    """
    List conversations with pagination and optional status filtering.
    """
    # Base query scoped to placeholder org (Phase 7 will use real org from JWT)
    base_query = select(Conversation).where(
        Conversation.organization_id == current_user.organization_id
    )

    if status_filter is not None:
        base_query = base_query.where(Conversation.status == status_filter)

    # Count total matching records
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    page_query = base_query.order_by(Conversation.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(page_query)
    # Using scalar subquery for msg_count to avoid N+1 queries
    msg_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .scalar_subquery()
    )
    page_query = page_query.add_columns(msg_count_subq)

    result = await db.execute(page_query)
    rows = result.all()

    items = []
    for conv, msg_count in rows:
        items.append(
            ConversationResponse(
                id=conv.id,
                organization_id=conv.organization_id,
                user_id=conv.user_id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            )
        )

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="Get a conversation")
async def get_conversation(
    current_user: CurrentUserDep, conversation_id: uuid.UUID, db: DatabaseDep
) -> ConversationResponse:
    """Retrieve a single conversation by ID."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation", str(conversation_id))

    msg_count_result = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation.id)
    )
    msg_count = msg_count_result.scalar_one()

    return ConversationResponse(
        id=conversation.id,
        organization_id=conversation.organization_id,
        user_id=conversation.user_id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count,
    )


@router.patch(
    "/{conversation_id}", response_model=ConversationResponse, summary="Update a conversation"
)
async def update_conversation(
    current_user: CurrentUserDep,
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    db: DatabaseDep,
) -> ConversationResponse:
    """Update a conversation's title or status."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation", str(conversation_id))

    if body.title is not None:
        conversation.title = body.title
    if body.status is not None:
        conversation.status = body.status

    await db.flush()
    await db.refresh(conversation)  # Refresh to get server-updated timestamps

    msg_count_result = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation.id)
    )
    msg_count = msg_count_result.scalar_one()

    return ConversationResponse(
        id=conversation.id,
        organization_id=conversation.organization_id,
        user_id=conversation.user_id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count,
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (archive) a conversation",
)
async def delete_conversation(
    current_user: CurrentUserDep, conversation_id: uuid.UUID, db: DatabaseDep
) -> None:
    """
    Archive a conversation (soft delete).

    The conversation is marked as ARCHIVED rather than deleted
    to preserve the audit trail.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation", str(conversation_id))

    conversation.status = ConversationStatus.ARCHIVED
    await db.flush()

    logger.info("conversation_archived", conversation_id=str(conversation_id))


# =============================================================================
# Messages sub-resource
# =============================================================================


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedResponse[MessageResponse],
    summary="List messages in a conversation",
)
async def list_messages(
    current_user: CurrentUserDep,
    conversation_id: uuid.UUID,
    db: DatabaseDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[MessageResponse]:
    """List all messages in a conversation, ordered chronologically."""
    # Verify conversation exists and is accessible
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )
    )
    if conv_result.scalar_one_or_none() is None:
        raise NotFoundError("Conversation", str(conversation_id))

    count_result = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    messages = msg_result.scalars().all()

    items = [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            structured_content=m.structured_content,
            agent_run_id=m.agent_run_id,
            token_count=m.token_count,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in messages
    ]

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a conversation",
)
async def add_message(
    current_user: CurrentUserDep, conversation_id: uuid.UUID, body: MessageCreate, db: DatabaseDep
) -> MessageResponse:
    """Add a message to an existing conversation."""
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )
    )
    if conv_result.scalar_one_or_none() is None:
        raise NotFoundError("Conversation", str(conversation_id))

    message = Message(
        organization_id=current_user.organization_id,
        conversation_id=conversation_id,
        role=body.role,
        content=body.content,
        structured_content=body.structured_content,
    )
    db.add(message)
    await db.flush()

    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        structured_content=message.structured_content,
        agent_run_id=message.agent_run_id,
        token_count=message.token_count,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )
