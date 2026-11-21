"""Resend is a first-class email transport: status card, test email, approval tool."""

import uuid

import httpx
import pytest

from app.services.email_service import EmailNotificationService
from app.services.gmail_service import GmailService
from app.tools.builtin.gmail import gmail_send_approval_def, gmail_send_approval_handler
from app.tools.schemas import RiskLevel, ToolContext

ENV = (
    "RESEND_API_KEY",
    "RESEND_FROM",
    "AURA_APPROVAL_EMAIL",
    "GMAIL_RECIPIENT_EMAIL",
    "GMAIL_USER",
    "GMAIL_SENDER_EMAIL",
    "GMAIL_APP_PASSWORD",
    "SMTP_USER",
    "SMTP_PASSWORD",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)


def _ctx():
    return ToolContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        execution_id=str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_status_reports_resend_active(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("AURA_APPROVAL_EMAIL", "me@example.com")
    st = await GmailService.get_connection_status(None)
    assert st["overall_status"] == "resend_only"
    assert st["can_send_email"] is True
    assert st["active_sending_method"] == "resend"
    assert st["resend"]["recipient_email"] == "me@example.com"


@pytest.mark.asyncio
async def test_status_not_configured_without_any_transport():
    st = await GmailService.get_connection_status(None)
    assert st["overall_status"] == "disconnected"
    assert st["can_send_email"] is False


@pytest.mark.asyncio
async def test_test_email_sent_through_resend(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    sent = {}

    async def fake_post(self, url, headers=None, json=None, **_):
        sent["to"] = json["to"]
        return httpx.Response(200, json={"id": "abc"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    res = await GmailService.send_test_email("me@example.com")
    assert res["delivered"] is True and res["provider"] == "Resend"
    assert sent["to"] == ["me@example.com"]


@pytest.mark.asyncio
async def test_test_email_surfaces_resend_error(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")

    async def fake_post(self, url, headers=None, json=None, **_):
        return httpx.Response(
            403,
            json={"message": "You can only send testing emails to your own email address"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    res = await GmailService.send_test_email("someone-else@example.com")
    assert res["delivered"] is False
    assert "only send testing emails to your own" in res["error"]


@pytest.mark.asyncio
async def test_approval_tool_refuses_to_invent_content(monkeypatch):
    monkeypatch.setenv("AURA_APPROVAL_EMAIL", "me@example.com")
    with pytest.raises(ValueError, match="will not invent"):
        await gmail_send_approval_handler({}, _ctx())


@pytest.mark.asyncio
async def test_approval_tool_ignores_model_chosen_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("AURA_APPROVAL_EMAIL", "me@example.com")
    to = []

    async def fake_post(self, url, headers=None, json=None, **_):
        to.append(json["to"])
        return httpx.Response(200, json={"id": "x"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    out = await EmailNotificationService.send_approval_request_email(
        approval_id=uuid.uuid4(),
        tool_name="quotation.create_draft",
        action_summary="25% discount for Acme",
        action_details={"company_name": "Acme", "discount_percent": 25.0},
        recipient_email=None,
    )
    assert out["status"] == "DELIVERED"
    assert to == [["me@example.com"]]


def test_approval_tool_is_not_itself_gated():
    # It only notifies the configured approver; requiring approval to send the
    # approval email would be circular.
    assert gmail_send_approval_def.risk_level == RiskLevel.WRITE
