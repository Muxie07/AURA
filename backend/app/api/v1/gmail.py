"""
AURA API v1 - Gmail & Google Workspace Integration Gateway.
Provides Google OAuth 2.0 authorization, state CSRF verification, token management,
Gmail REST API sending, delivery diagnostics, and email approval notification endpoints.
"""

import os
import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, DatabaseDep
from app.config.settings import get_settings
from app.database.models import (
    AgentRun,
    AgentRunStatus,
    ApprovalRequest,
    ApprovalStatus,
    Conversation,
)
from app.services.email_service import EmailNotificationService
from app.services.gmail_service import AuthorizationExpiredError, GmailService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations/gmail", tags=["Gmail Integration"])


# =============================================================================
# Request Schemas
# =============================================================================
class GmailConfigureRequest(BaseModel):
    sender_email: str
    app_password: str
    recipient_email: str | None = None


class GmailTestEmailRequest(BaseModel):
    recipient_email: str


class GmailOAuthExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str | None = None


class GmailOAuthCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str | None = None


class GmailApprovalDispatchRequest(BaseModel):
    recipient_email: str | None = None
    tool_name: str = "quotation.create_draft"
    action_summary: str = "Sign-off 25% Commercial Discount on Cloud Infotech Order"
    company_name: str = "Cloud Infotech Partner"
    model_number: str = "UC-2000-VE-8T (8 Port GSM/VoLTE Gateway)"
    quantity: int = 2
    discount_percent: float = 25.0
    total_amount: str = "₹1,11,732 (excl. 18% GST)"
    reason: str = "Commercial discount of 25.0% exceeds authorized 20% limit."


# =============================================================================
# Status Endpoint
# =============================================================================
@router.get("/status")
async def get_gmail_status(
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Check real-time Gmail connection, active auth type, permissions, and timestamps
    for the current user's organization.
    """
    return await GmailService.get_connection_status(current_user.organization_id)


# =============================================================================
# OAuth 2.0 Authorization Flow
# =============================================================================
@router.post("/oauth/credentials")
async def save_oauth_credentials(
    req: GmailOAuthCredentialsRequest,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Save Google OAuth Client ID and Secret into the server environment and update .env.
    """
    clean_id = req.client_id.strip()
    clean_secret = req.client_secret.strip()
    clean_redirect = (
        req.redirect_uri.strip()
        if req.redirect_uri
        else "http://localhost:8000/api/v1/integrations/gmail/oauth/callback"
    )

    if not clean_id or not clean_secret:
        raise HTTPException(status_code=400, detail="Client ID and Client Secret cannot be empty.")

    os.environ["GOOGLE_CLIENT_ID"] = clean_id
    os.environ["GOOGLE_CLIENT_SECRET"] = clean_secret
    os.environ["GOOGLE_REDIRECT_URI"] = clean_redirect
    get_settings.cache_clear()

    try:
        env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
        content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        updates = {
            "GOOGLE_CLIENT_ID": clean_id,
            "GOOGLE_CLIENT_SECRET": clean_secret,
            "GOOGLE_REDIRECT_URI": clean_redirect,
        }
        lines = content.splitlines()
        new_lines = []
        found_keys = set()
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                k = line.split("=", 1)[0].strip()
                if k in updates:
                    new_lines.append(f"{k}={updates[k]}")
                    found_keys.add(k)
                    continue
            new_lines.append(line)
        for k, v in updates.items():
            if k not in found_keys:
                new_lines.append(f"{k}={v}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        logger.warning("env_file_update_warning", error=str(e))

    return {
        "status": "SUCCESS",
        "message": "Google OAuth credentials saved successfully.",
        "client_id": clean_id[:12] + "..." + clean_id[-8:] if len(clean_id) > 20 else clean_id,
        "redirect_uri": clean_redirect,
    }


@router.get("/oauth/url")
async def get_oauth_url(
    current_user: CurrentUserDep,
    redirect_uri: str | None = Query(None, description="Optional custom redirect URI"),
) -> dict[str, Any]:
    """
    Generates the Google OAuth 2.0 authorization URL with a tenant-bound,
    anti-replay CSRF state token.
    Scope is strictly restricted to https://www.googleapis.com/auth/gmail.send.
    """
    return GmailService.get_authorization_url(
        organization_id=current_user.organization_id,
        user_id=getattr(current_user, "user_id", None),
        redirect_uri=redirect_uri,
    )


@router.get("/oauth/callback")
async def handle_oauth_get_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> RedirectResponse:
    """
    Server-side OAuth 2.0 redirect endpoint called by Google upon user authorization.
    Verifies state token CSRF nonce, exchanges authorization code for tokens,
    encrypts and persists tokens, and redirects the user back to the AURA frontend.
    """
    settings = get_settings()
    frontend_base = settings.aura_frontend_base_url.rstrip("/")

    # Handle user cancellation or Google authorization error
    if error:
        err_msg = error_description or error
        logger.warning("google_oauth_callback_error", error=error, description=error_description)
        redirect_url = f"{frontend_base}/settings?tab=integrations&status=cancelled&error={quote_plus(err_msg)}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if not code or not state:
        logger.warning(
            "google_oauth_callback_missing_params", has_code=bool(code), has_state=bool(state)
        )
        redirect_url = f"{frontend_base}/settings?tab=integrations&status=error&error=Missing+authorization+code+or+state"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    try:
        # Validate state token and extract bound organization
        state_data = GmailService.verify_and_consume_oauth_state(state)
        org_id = state_data["organization_id"]

        # Determine the redirect URI matching Google's registration
        registered_redirect_uri = settings.google_redirect_uri

        # Exchange authorization code for tokens
        await GmailService.exchange_code(
            code=code,
            redirect_uri=registered_redirect_uri,
            organization_id=org_id,
        )

        logger.info("google_oauth_connected_via_callback", org_id=str(org_id))
        redirect_url = f"{frontend_base}/settings?tab=integrations&status=connected"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    except Exception as e:
        logger.error("google_oauth_callback_processing_failed", error=str(e))
        redirect_url = (
            f"{frontend_base}/settings?tab=integrations&status=error&error={quote_plus(str(e))}"
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post("/oauth/callback")
async def handle_oauth_post_callback(
    req: GmailOAuthExchangeRequest,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Programmatic / SPA OAuth 2.0 authorization code exchange endpoint.
    Exchanges code for access & refresh tokens and stores in encrypted CredentialVault.
    """
    try:
        if req.state:
            state_data = GmailService.verify_and_consume_oauth_state(req.state)
            org_id = state_data["organization_id"]
        else:
            org_id = current_user.organization_id

        result = await GmailService.exchange_code(
            code=req.code,
            redirect_uri=req.redirect_uri,
            organization_id=org_id,
        )
        return {
            "status": "SUCCESS",
            "message": f"Successfully authorized Gmail account: {result['sender_email']}",
            "details": result,
        }
    except Exception as e:
        logger.error("oauth_exchange_post_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Test Email Dispatcher
# =============================================================================
@router.post("/test-email")
async def send_test_email(
    req: GmailTestEmailRequest,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Dispatches an actual diagnostic verification email through the Gmail REST API
    (or SMTP fallback). Verifies delivery acceptance from Google API.
    """
    try:
        res = await GmailService.send_test_email(
            recipient=str(req.recipient_email),
            organization_id=current_user.organization_id,
        )
        if not res.get("delivered") and res.get("error"):
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except AuthorizationExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Disconnect Endpoint
# =============================================================================
@router.post("/oauth/disconnect")
async def disconnect_oauth(current_user: CurrentUserDep) -> dict[str, Any]:
    """Revokes Google OAuth tokens without affecting SMTP configuration."""
    return await GmailService.disconnect(
        organization_id=current_user.organization_id, method="oauth"
    )


@router.post("/smtp/disconnect")
async def disconnect_smtp(current_user: CurrentUserDep) -> dict[str, Any]:
    """Clears SMTP credentials without affecting Google OAuth configuration."""
    return await GmailService.disconnect(
        organization_id=current_user.organization_id, method="smtp"
    )


@router.post("/smtp/test")
async def test_smtp_connection(
    current_user: CurrentUserDep,
    req: GmailTestEmailRequest | None = None,
) -> dict[str, Any]:
    """Tests the SMTP transport connection to smtp.gmail.com:587 with stored or env credentials."""
    recipient = str(req.recipient_email) if req and req.recipient_email else None
    res = await GmailService.test_smtp_connection(
        organization_id=current_user.organization_id,
        test_recipient=recipient,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "SMTP test failed."))
    return res


@router.post("/disconnect")
async def disconnect_gmail(
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Revokes active Google OAuth tokens and clears credentials from CredentialVault.
    """
    return await GmailService.disconnect(organization_id=current_user.organization_id)


# =============================================================================
# Diagnostics & Logs
# =============================================================================
@router.get("/diagnostics")
async def get_diagnostics(
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Returns real-time delivery logs, connection health, and diagnostics.
    """
    status_info = await GmailService.get_connection_status(current_user.organization_id)
    logs = GmailService.get_delivery_logs()
    return {
        **status_info,
        "delivery_logs": logs,
        "recent_deliveries": logs,
    }


# =============================================================================
# Manual SMTP Configuration (Fallback)
# =============================================================================
@router.post("/configure")
async def configure_gmail_smtp(
    req: GmailConfigureRequest,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """
    Verify SMTP credentials with Google, encrypt password, and persist configuration.
    """
    clean_pass = req.app_password.replace(" ", "").strip()
    clean_sender = str(req.sender_email).strip()
    clean_recipient = str(req.recipient_email).strip() if req.recipient_email else clean_sender

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=8) as server:
            server.starttls()
            server.login(clean_sender, clean_pass)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=400,
            detail="Gmail Authentication Failed. Ensure 2-Step Verification is active and you are using a 16-character Google App Password.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to reach smtp.gmail.com:587: {e}",
        )

    saved = GmailService.save_smtp_config(
        sender_email=clean_sender,
        app_password=clean_pass,
        recipient_email=clean_recipient,
        organization_id=current_user.organization_id,
    )

    return {
        "status": "SUCCESS",
        "message": f"Gmail successfully connected and authenticated as {clean_sender}.",
        "details": saved,
    }


# =============================================================================
# Approval Notification Dispatcher
# =============================================================================
@router.post("/send-approval")
async def dispatch_approval_email(
    req: GmailApprovalDispatchRequest,
    current_user: CurrentUserDep,
    db: DatabaseDep,
) -> dict[str, Any]:
    """
    Creates a persistent human approval request and dispatches a notification email
    with cryptographically signed decision URLs that link back to AURA.
    """
    cfg = await GmailService.get_tenant_config(current_user.organization_id)
    target_recipient = (
        str(req.recipient_email)
        if req.recipient_email
        else (cfg.get("recipient_email") or current_user.email)
    )

    if not target_recipient:
        raise HTTPException(
            status_code=400,
            detail="No recipient email address specified. Configure your recipient email in Gmail settings.",
        )

    # 1. Create or load Conversation
    import sqlalchemy as sa

    conv = await db.scalar(
        sa.select(Conversation)
        .where(Conversation.organization_id == current_user.organization_id)
        .limit(1)
    )
    if not conv:
        conv = Conversation(
            organization_id=current_user.organization_id,
            user_id=getattr(current_user, "user_id", None),
            title="Commercial Quotation Sign-Off Thread",
        )
        db.add(conv)
        await db.flush()

    # 2. Create AgentRun
    run = AgentRun(
        organization_id=current_user.organization_id,
        conversation_id=conv.id,
        user_id=getattr(current_user, "user_id", None),
        user_request=f"Commercial quotation draft for {req.company_name} ({req.discount_percent}% discount)",
        status=AgentRunStatus.PENDING,
    )
    db.add(run)
    await db.flush()

    # 3. Create frozen payload snapshot
    details_payload = {
        "company_name": req.company_name,
        "model_number": req.model_number,
        "quantity": req.quantity,
        "discount_percent": req.discount_percent,
        "total_authorized": req.total_amount,
        "_reason": req.reason,
    }

    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=current_user.organization_id,
        tool_name=req.tool_name,
        action_summary=req.action_summary,
        action_details=details_payload,
        args_hash="gmail_" + uuid.uuid4().hex[:12],
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)

    # 4. Dispatch Email with signed HMAC tokens
    email_result = await GmailService.dispatch_approval_request(
        approval_id=approval.id,
        tool_name=req.tool_name,
        action_summary=req.action_summary,
        action_details=details_payload,
        reason=req.reason,
        recipient_email=target_recipient,
        agent_run_id=run.id,
        organization_id=current_user.organization_id,
    )

    return {
        "status": "DISPATCHED",
        "approval_id": str(approval.id),
        "recipient": target_recipient,
        "subject": email_result.get("subject"),
        "approve_url": email_result.get("approve_url"),
        "deny_url": email_result.get("deny_url"),
        "smtp_delivered": email_result.get("smtp_delivered", False),
        "delivery_provider": email_result.get("delivery_provider", "Gmail REST API"),
        "notice": (
            f"Approval notification dispatched to {target_recipient}. "
            "When the approver opens the link, AURA displays the frozen action snapshot for authorization."
        ),
    }


@router.get("/dispatches")
async def list_recent_dispatches() -> dict[str, Any]:
    """Returns recent dispatched approval notifications."""
    return {"dispatches": EmailNotificationService.get_recent_emails()}
