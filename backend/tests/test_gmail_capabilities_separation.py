"""
Regression and capabilities separation test suite for AURA Gmail Integration.

Verifies:
1. SMTP status is reported independently from Google OAuth status.
2. Google OAuth callback updates OAuth connection status without mutating SMTP.
3. send_test_email dynamically uses the active transport (API or SMTP) and truthfully reports which was used.
4. Missing or disconnected OAuth does NOT mark SMTP as broken or erase SMTP credentials.
"""

import base64
import email
import json
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config.settings import get_settings
from app.services.gmail_service import GmailService


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure clean test environment."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "869968176287-test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "GOCSPX-test-client-secret-abc")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/gmail/oauth/callback")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test.operator@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-app-pass-word")
    monkeypatch.setenv("GMAIL_RECIPIENT_EMAIL", "mufeed.career@gmail.com")
    monkeypatch.setenv("AURA_SECRET_KEY", "test-secret-key-32-chars-minimum-safe")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-key")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_smtp_reported_independently_from_oauth():
    """Unit test 1: Verifies that SMTP status is reported independently from OAuth status."""
    org_id = uuid.uuid4()

    # Seed SMTP credentials only (synchronous)
    GmailService.save_smtp_config(
        organization_id=org_id,
        sender_email="test.operator@gmail.com",
        app_password="test-app-pass-word",
        recipient_email="mufeed.career@gmail.com",
    )

    status = await GmailService.get_connection_status(org_id)

    # Truthful status check
    assert status["overall_status"] == "smtp_only"
    assert status["can_send_email"] is True
    assert status["can_use_gmail_api"] is False
    assert status["active_sending_method"] == "smtp"

    # SMTP details block
    assert status["smtp"]["configured"] is True
    assert status["smtp"]["host"] == "smtp.gmail.com"
    assert status["smtp"]["port"] == 587
    assert status["smtp"]["sender_email"] == "test.operator@gmail.com"

    # OAuth details block must truthfully report disconnected
    assert status["oauth"]["connected"] is False
    assert status["oauth"]["client_id_configured"] is True
    assert "869968176287" in (status["oauth"]["client_id_preview"] or "")


@pytest.mark.asyncio
async def test_oauth_callback_properly_updates_connection_status():
    """Unit test 2: Verifies that OAuth callback properly updates connection status."""
    org_id = uuid.uuid4()

    def handle_mock_oauth(request: httpx.Request) -> httpx.Response:
        if "oauth2.googleapis.com/token" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.test_token_regression",
                    "refresh_token": "1//test_refresh_regression",
                    "expires_in": 3600,
                    "scope": "https://www.googleapis.com/auth/gmail.send",
                    "token_type": "Bearer",
                },
            )
        elif "googleapis.com/oauth2/v2/userinfo" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "email": "authorized.user@aura.internal",
                    "verified_email": True,
                },
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_mock_oauth)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        exchange_res = await GmailService.exchange_code(
            code="test_auth_code_regression",
            redirect_uri="http://localhost:8000/api/v1/integrations/gmail/oauth/callback",
            organization_id=org_id,
            client=client,
        )

    assert exchange_res["status"] == "CONNECTED"
    assert exchange_res["sender_email"] == "authorized.user@aura.internal"

    status = await GmailService.get_connection_status(org_id)
    assert status["oauth"]["connected"] is True
    assert status["oauth"]["authorized_account"] == "authorized.user@aura.internal"
    assert status["can_use_gmail_api"] is True


@pytest.mark.asyncio
async def test_send_test_email_uses_active_transport_and_reports_transport():
    """Unit test 3: Verifies send_test_email uses active transport and truthfully reports provider."""
    org_id = uuid.uuid4()

    # Sub-case A: With SMTP configured and no OAuth, must use Gmail SMTP
    GmailService.save_smtp_config(
        organization_id=org_id,
        sender_email="test.operator@gmail.com",
        app_password="test-app-pass-word",
        recipient_email="mufeed.career@gmail.com",
    )

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        res_smtp = await GmailService.send_test_email(
            recipient="mufeed.career@gmail.com",
            organization_id=org_id,
        )

        assert res_smtp["delivered"] is True
        assert "SMTP" in res_smtp.get("delivery_provider", "")
        assert res_smtp["recipient"] == "mufeed.career@gmail.com"

    # Sub-case B: With OAuth active, must prioritize Gmail REST API
    await GmailService._save_oauth_credentials(
        organization_id=org_id,
        sender_email="oauth.sender@aura.internal",
        access_token="valid_active_access_token",
        refresh_token="valid_refresh_token",
        token_expiry="2099-01-01T00:00:00Z",
    )

    def handle_mock_send(request: httpx.Request) -> httpx.Response:
        if "messages/send" in str(request.url):
            return httpx.Response(
                200,
                json={"id": "msg_oauth_test_123", "threadId": "th_123", "labelIds": ["SENT"]},
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handle_mock_send)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        res_api = await GmailService.send_test_email(
            recipient="mufeed.career@gmail.com",
            organization_id=org_id,
            client=client,
        )

    assert res_api["delivered"] is True
    assert "REST API" in res_api.get("delivery_provider", "")
    assert res_api["message_id"] == "msg_oauth_test_123"


@pytest.mark.asyncio
async def test_missing_oauth_does_not_mark_smtp_as_broken():
    """Unit test 4: Validation test ensuring missing OAuth does NOT mark SMTP as broken."""
    org_id = uuid.uuid4()

    # Configure SMTP
    GmailService.save_smtp_config(
        organization_id=org_id,
        sender_email="test.operator@gmail.com",
        app_password="test-app-pass-word",
        recipient_email="mufeed.career@gmail.com",
    )

    # Disconnect OAuth explicitly
    await GmailService.disconnect(organization_id=org_id, method="oauth")

    # SMTP must still be fully intact and report operational
    smtp_status = await GmailService.get_smtp_status(org_id)
    assert smtp_status["configured"] is True
    assert smtp_status["status"] == "configured"
    assert smtp_status["sender_email"] == "test.operator@gmail.com"

    # Overall status must remain smtp_only, and can_send_email must remain True
    overall = await GmailService.get_connection_status(org_id)
    assert overall["overall_status"] == "smtp_only"
    assert overall["can_send_email"] is True
    assert overall["smtp"]["configured"] is True
    assert overall["oauth"]["connected"] is False
