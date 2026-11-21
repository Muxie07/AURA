"""Approval notification email: transport selection, honest status, no invented content."""

import uuid

import httpx
import pytest

from app.services.email_service import EmailNotificationService

DETAILS = {"company_name": "Northwind Trading", "total": "4,200.00", "discount_percent": 10}
FABRICATED = ["Cloud Infotech", "cloudinfotech", "18,750", "QT-2026-0042", "UC-2000-VE-8T"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in (
        "RESEND_API_KEY",
        "RESEND_FROM",
        "GMAIL_RECIPIENT_EMAIL",
        "AURA_APPROVAL_EMAIL",
        "GMAIL_USER",
        "GMAIL_SENDER_EMAIL",
        "GMAIL_APP_PASSWORD",
        "SMTP_USER",
        "SMTP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AURA_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("AURA_FRONTEND_BASE_URL", "https://app.example.test")


async def _send(**kw):
    return await EmailNotificationService.send_approval_request_email(
        approval_id=uuid.uuid4(),
        tool_name="quotation.send",
        action_summary="Send quotation to Northwind Trading",
        action_details=kw.pop("details", DETAILS),
        **kw,
    )


@pytest.mark.asyncio
async def test_resend_delivers_with_working_links(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    sent = {}

    async def fake_post(self, url, headers=None, json=None, **_):
        sent.update(url=url, headers=headers, body=json)
        return httpx.Response(200, json={"id": "msg_123"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    rec = await _send(recipient_email="mufeed.career@gmail.com")

    assert rec["status"] == "DELIVERED" and rec["delivery_provider"] == "Resend"
    assert rec["provider_message_id"] == "msg_123"
    assert sent["url"] == "https://api.resend.com/emails"
    assert sent["headers"]["Authorization"] == "Bearer re_test"
    assert sent["body"]["to"] == ["mufeed.career@gmail.com"]
    # Approve / decline buttons must point at the public API, not localhost.
    assert "https://api.example.test/api/v1/approvals/email-action?token=" in sent["body"]["html"]
    assert "decision=approve" in rec["approve_url"] and "decision=deny" in rec["deny_url"]


@pytest.mark.asyncio
async def test_resend_failure_is_reported_not_hidden(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")

    async def fake_post(self, url, **_):
        return httpx.Response(403, text="domain not verified", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    rec = await _send(recipient_email="someone@example.com")
    assert rec["status"] == "FAILED" and "403" in rec["delivery_error"]


@pytest.mark.asyncio
async def test_no_recipient_is_not_sent_and_not_invented(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    rec = await _send()
    assert rec["status"] == "NOT_SENT"
    assert "AURA_APPROVAL_EMAIL" in rec["delivery_error"]


@pytest.mark.asyncio
async def test_default_recipient_comes_from_env(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("AURA_APPROVAL_EMAIL", "approver@example.com")
    seen = {}

    async def fake_post(self, url, json=None, **_):
        seen.update(json)
        return httpx.Response(200, json={"id": "m"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    rec = await _send()
    assert rec["status"] == "DELIVERED" and seen["to"] == ["approver@example.com"]


@pytest.mark.asyncio
async def test_no_provider_configured_is_not_sent():
    rec = await _send(recipient_email="someone@example.com")
    assert rec["status"] == "NOT_SENT"


@pytest.mark.asyncio
async def test_email_never_invents_business_details(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        lambda self, url, **_: _ok(url),
    )
    rec = await _send(recipient_email="a@example.com", details={})
    body = rec["html"] + rec["text"]
    for fake in FABRICATED:
        assert fake not in body, f"fabricated content leaked into email: {fake}"
    assert "Not specified" in body


async def _ok(url):
    return httpx.Response(200, json={"id": "m"}, request=httpx.Request("POST", url))


def test_token_roundtrip_and_decision_binding():
    aid = uuid.uuid4()
    tok = EmailNotificationService.generate_token(aid, "approve")
    claims = EmailNotificationService.verify_token(tok)
    assert claims["approval_id"] == str(aid) and claims["decision"] == "approve"


@pytest.mark.asyncio
@pytest.mark.parametrize("customer", ["Acme Technologies", "procurement@customer.example"])
async def test_approval_goes_to_approver_not_customer(monkeypatch, customer):
    """Regression: the customer named in the action must never be the delivery address."""
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("AURA_APPROVAL_EMAIL", "mufeed.career@gmail.com")
    sent = {}

    async def fake_post(self, url, headers=None, json=None, **_):
        sent.update(body=json)
        return httpx.Response(200, json={"id": "m1"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    details = {**DETAILS, "target_recipient": customer, "recipient": customer}

    rec = await _send(details=details, recipient_email=None)

    assert rec["status"] == "DELIVERED"
    assert sent["body"]["to"] == ["mufeed.career@gmail.com"]
    assert customer in rec["html"]  # still shown as the action's recipient
