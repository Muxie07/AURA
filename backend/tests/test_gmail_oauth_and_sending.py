"""
Automated Unit and Integration Tests for AURA Gmail OAuth 2.0, Token Lifecycle,
and Gmail REST API Delivery Services.
"""

import base64
import email
import json
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio

from app.config.settings import Settings, get_settings
from app.security.vault import CredentialVault
from app.services.gmail_service import AuthorizationExpiredError, GmailService


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Configures clean test environment variables."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-client-secret-12345")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/gmail/oauth/callback"
    )
    monkeypatch.setenv("AURA_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    monkeypatch.setenv("AURA_FRONTEND_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key-for-test-suite")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_oauth_authorization_url_generation():
    """Verifies OAuth 2.0 authorization URL construction meets Google specifications."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    auth_info = GmailService.get_authorization_url(org_id, user_id=user_id)
    assert auth_info["configured"] is True
    assert auth_info["redirect_uri"] == "http://localhost:8000/api/v1/integrations/gmail/oauth/callback"

    url = auth_info["auth_url"]
    assert "https://accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=test-google-client-id" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "response_type=code" in url
    assert "scope=" in url
    assert "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send" in url
    assert "state=" in url


@pytest.mark.asyncio
async def test_oauth_state_csrF_and_anti_replay():
    """Verifies state parameter cryptographic validation, tenant binding, and single-use anti-replay."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    state = GmailService.generate_oauth_state(org_id, user_id)
    assert state is not None

    # First consumption succeeds
    data = GmailService.verify_and_consume_oauth_state(state)
    assert data["organization_id"] == str(org_id)
    assert data["user_id"] == str(user_id)

    # Replay of identical state token MUST fail
    with pytest.raises(ValueError, match="replay"):
        GmailService.verify_and_consume_oauth_state(state)


@pytest.mark.asyncio
async def test_oauth_code_exchange():
    """Verifies authorization code exchange, account discovery, and encrypted vault persistence."""
    org_id = uuid.uuid4()
    fake_code = "4/0AeanS0_test_authorization_code"
    redirect_uri = "http://localhost:8000/api/v1/integrations/gmail/oauth/callback"

    def handle_mock_request(request: httpx.Request) -> httpx.Response:
        if request.url == "https://oauth2.googleapis.com/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.test_access_token_mock_value",
                    "refresh_token": "1//test_refresh_token_mock_value",
                    "expires_in": 3600,
                    "scope": "https://www.googleapis.com/auth/gmail.send",
                    "token_type": "Bearer",
                },
            )
        elif request.url == "https://www.googleapis.com/oauth2/v2/userinfo":
            return httpx.Response(
                200,
                json={
                    "id": "123456789",
                    "email": "operations@cloudinfotech.com",
                    "verified_email": True,
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_mock_request)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        res = await GmailService.exchange_code(
            code=fake_code,
            redirect_uri=redirect_uri,
            organization_id=org_id,
            client=client,
        )

    assert res["status"] == "CONNECTED"
    assert res["sender_email"] == "operations@cloudinfotech.com"
    assert res["connected_email"] == "operations@cloudinfotech.com"
    assert res["auth_type"] == "oauth2"
    # Secrets MUST NOT be exposed in response
    assert "access_token" not in res
    assert "refresh_token" not in res
    assert "_decrypted_access_token" not in res


@pytest.mark.asyncio
async def test_token_auto_refresh_on_expiry():
    """Verifies automatic access token refresh when token is expired or near expiry."""
    org_id = uuid.uuid4()

    # Pre-seed an expired token
    expired_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    await GmailService._save_oauth_credentials(
        organization_id=org_id,
        sender_email="operator@aura.internal",
        access_token="old_expired_access_token",
        refresh_token="valid_stored_refresh_token",
        token_expiry=expired_time,
    )

    def handle_refresh(request: httpx.Request) -> httpx.Response:
        if request.url == "https://oauth2.googleapis.com/token":
            body = request.read().decode("utf-8")
            assert "grant_type=refresh_token" in body
            assert "refresh_token=valid_stored_refresh_token" in body
            return httpx.Response(
                200,
                json={
                    "access_token": "new_fresh_access_token_999",
                    "expires_in": 3600,
                    "scope": "https://www.googleapis.com/auth/gmail.send",
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_refresh)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        token, sender = await GmailService.get_valid_access_token(org_id, client=client)

    assert token == "new_fresh_access_token_999"
    assert sender == "operator@aura.internal"


@pytest.mark.asyncio
async def test_token_revocation_handling():
    """Verifies AuthorizationExpiredError is raised when refresh token is revoked in Google account."""
    org_id = uuid.uuid4()

    expired_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    await GmailService._save_oauth_credentials(
        organization_id=org_id,
        sender_email="operator@aura.internal",
        access_token="old_access_token",
        refresh_token="revoked_refresh_token",
        token_expiry=expired_time,
    )

    def handle_revoked(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "Token has been expired or revoked.",
            },
        )

    mock_transport = httpx.MockTransport(handle_revoked)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        with pytest.raises(AuthorizationExpiredError, match="revoked in Google Account"):
            await GmailService.get_valid_access_token(org_id, client=client)


@pytest.mark.asyncio
async def test_gmail_rest_api_send_and_idempotency():
    """Verifies RFC 2822 MIME message construction, base64url encoding, and idempotency deduplication."""
    org_id = uuid.uuid4()

    # Seed active token
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    await GmailService._save_oauth_credentials(
        organization_id=org_id,
        sender_email="approvals@aura.internal",
        access_token="valid_active_bearer_token",
        refresh_token="valid_refresh_token",
        token_expiry=future_time,
    )

    call_count = 0

    def handle_gmail_send(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        if request.url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send":
            call_count += 1
            auth_header = request.headers.get("Authorization")
            assert auth_header == "Bearer valid_active_bearer_token"
            data = json.loads(request.read())
            assert "raw" in data

            # Decode raw base64url message
            raw_padding = data["raw"] + "=" * (-len(data["raw"]) % 4)
            raw_decoded = base64.urlsafe_b64decode(raw_padding).decode("utf-8")
            
            parsed_msg = email.message_from_string(raw_decoded)
            assert parsed_msg["Subject"] == "Urgent Governance Sign-Off"
            assert parsed_msg["To"] == "approver@partner.com"

            payloads = [
                part.get_payload(decode=True).decode("utf-8")
                for part in parsed_msg.walk()
                if part.get_payload(decode=True)
            ]
            assert any("Please authorize quotation draft." in p for p in payloads)

            return httpx.Response(
                200,
                json={
                    "id": "18f92a9b34c01",
                    "threadId": "18f92a9b34c01",
                    "labelIds": ["SENT"],
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_gmail_send)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        idempotency_key = f"idem_test_{uuid.uuid4().hex}"

        # First dispatch
        res1 = await GmailService.send_gmail_api_message(
            organization_id=org_id,
            recipient="approver@partner.com",
            subject="Urgent Governance Sign-Off",
            body_text="Please authorize quotation draft.",
            body_html="<p>Please authorize quotation draft.</p>",
            idempotency_key=idempotency_key,
            client=client,
        )

        assert res1["delivered"] is True
        assert res1["message_id"] == "18f92a9b34c01"
        assert res1["provider"] == "Gmail REST API"
        assert call_count == 1

        # Second dispatch with identical idempotency key MUST NOT call Google API again
        res2 = await GmailService.send_gmail_api_message(
            organization_id=org_id,
            recipient="approver@partner.com",
            subject="Urgent Governance Sign-Off",
            body_text="Please authorize quotation draft.",
            idempotency_key=idempotency_key,
            client=client,
        )

        assert res2["delivered"] is True
        assert res2["message_id"] == "18f92a9b34c01"
        # call_count remains 1 because duplicate send was prevented
        assert call_count == 1


@pytest.mark.asyncio
async def test_disconnect_and_token_revocation():
    """Verifies disconnect calls Google revocation endpoint and purges vault credentials."""
    org_id = uuid.uuid4()

    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    await GmailService._save_oauth_credentials(
        organization_id=org_id,
        sender_email="user@example.com",
        access_token="token_to_revoke",
        refresh_token="refresh_to_revoke",
        token_expiry=future_time,
    )

    revocation_called = False

    def handle_revoke(request: httpx.Request) -> httpx.Response:
        nonlocal revocation_called
        if "oauth2.googleapis.com/revoke" in str(request.url):
            revocation_called = True
            return httpx.Response(200, json={})
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_revoke)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        disc_res = await GmailService.disconnect(organization_id=org_id, client=client)

    assert disc_res["status"] == "DISCONNECTED"
    assert revocation_called is True

    # Status must now report not_connected
    status_info = await GmailService.get_connection_status(org_id)
    assert status_info["status"] == "not_connected"
    assert status_info["connected"] is False
