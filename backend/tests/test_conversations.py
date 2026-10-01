"""
AURA Tests — Conversations API.

Tests CRUD operations on the conversations endpoints including:
- Creating conversations
- Listing with pagination
- Getting by ID
- Updating
- Soft delete (archive)
- Message sub-resource
- Error handling (not found, validation)
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_conversation_minimal(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """POST /api/v1/conversations should create a conversation with no title."""
    response = await client.post("/api/v1/conversations", json={})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "active"
    assert data["title"] is None
    assert data["message_count"] == 0


@pytest.mark.asyncio
async def test_create_conversation_with_title(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """POST /api/v1/conversations with a title stores it correctly."""
    response = await client.post(
        "/api/v1/conversations",
        json={"title": "Quotation for Customer ABC"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Quotation for Customer ABC"


@pytest.mark.asyncio
async def test_create_conversation_with_initial_message(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """POST with initial_message should create conversation with 1 message."""
    response = await client.post(
        "/api/v1/conversations",
        json={
            "title": "Hello",
            "initial_message": "We need 500 units of Product X.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["message_count"] == 1


@pytest.mark.asyncio
async def test_list_conversations_empty(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """GET /api/v1/conversations should return empty list when no conversations exist."""
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_conversations_pagination(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """Creating 3 conversations and listing with page_size=2 should paginate."""
    for i in range(3):
        await client.post("/api/v1/conversations", json={"title": f"Conv {i}"})

    response = await client.get("/api/v1/conversations?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["pages"] == 2


@pytest.mark.asyncio
async def test_get_conversation_found(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """GET /api/v1/conversations/{id} should return the conversation."""
    create_resp = await client.post(
        "/api/v1/conversations",
        json={"title": "Test"},
    )
    conv_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["title"] == "Test"


@pytest.mark.asyncio
async def test_get_conversation_not_found(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """GET with a non-existent ID should return 404 with structured error."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/conversations/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"
    assert "request_id" in data


@pytest.mark.asyncio
async def test_update_conversation_title(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """PATCH should update the conversation title."""
    create_resp = await client.post("/api/v1/conversations", json={"title": "Old Title"})
    conv_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "New Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_archive_conversation(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """DELETE should soft-archive the conversation, not hard delete."""
    create_resp = await client.post("/api/v1/conversations", json={})
    conv_id = create_resp.json()["id"]

    # Archive
    response = await client.delete(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 204

    # Should still exist but as archived
    get_resp = await client.get(f"/api/v1/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_filter_conversations_by_status(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """GET with status filter should only return matching conversations."""
    # Create active conversation
    await client.post("/api/v1/conversations", json={"title": "Active"})

    # Create and archive another
    arch_resp = await client.post("/api/v1/conversations", json={"title": "To Archive"})
    arch_id = arch_resp.json()["id"]
    await client.delete(f"/api/v1/conversations/{arch_id}")

    # Filter for active only
    response = await client.get("/api/v1/conversations?status=active")
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "active" for item in data["items"])


@pytest.mark.asyncio
async def test_add_message_to_conversation(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """POST /conversations/{id}/messages should add a message."""
    create_resp = await client.post("/api/v1/conversations", json={})
    conv_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Hello AURA!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"
    assert data["content"] == "Hello AURA!"
    assert data["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_list_messages_in_conversation(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """GET /conversations/{id}/messages should return paginated messages."""
    create_resp = await client.post("/api/v1/conversations", json={})
    conv_id = create_resp.json()["id"]

    # Add two messages
    await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "First message"},
    )
    await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "assistant", "content": "Response message"},
    )

    response = await client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["role"] == "user"
    assert data["items"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_message_for_nonexistent_conversation(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """Adding a message to a non-existent conversation should return 404."""
    fake_id = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/conversations/{fake_id}/messages",
        json={"role": "user", "content": "Hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_validation_error_returns_structured_response(
    client: AsyncClient,
    organization,
    user,
) -> None:
    """Invalid request body should return 422 with field-level error details."""
    # Send a message with empty content (violates min_length=1)
    create_resp = await client.post("/api/v1/conversations", json={})
    conv_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": ""},  # Empty content
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "validation_error"
    assert "fields" in data["error"]["details"]
