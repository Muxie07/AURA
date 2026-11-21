import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import structlog

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)

# In-memory thread-safe outbox buffer for recent dispatched emails
_RECENT_EMAILS: list[dict[str, Any]] = []
MAX_OUTBOX_SIZE = 100

# Anti-replay single-use decision token tracking
_CONSUMED_JTIS: set[str] = set()


class EmailNotificationService:
    """
    Enterprise Email Notification Service for AURA.
    Dispatches task approval notifications and completion receipts with cryptographic review action links.
    Recipients inspect the exact frozen snapshot and authorize via secure POST.
    """

    @staticmethod
    def generate_token(approval_id: uuid.UUID | str, decision: str, hours_valid: int = 24) -> str:
        settings = get_settings()
        secret = settings.aura_secret_key.get_secret_value()
        exp = datetime.now(UTC) + timedelta(hours=hours_valid)
        jti = uuid.uuid4().hex
        payload = {
            "sub": str(approval_id),
            "approval_id": str(approval_id),
            "decision": decision.lower(),
            "exp": exp,
            "iss": "aura-platform",
            "iat": datetime.now(UTC),
            "jti": jti,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> dict[str, Any]:
        settings = get_settings()
        secret = settings.aura_secret_key.get_secret_value()
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"], issuer="aura-platform")
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Approval token has expired. Please contact your AURA administrator.")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid approval token: {e}")

    @staticmethod
    def _get_redis():
        try:
            import redis

            settings = get_settings()
            return redis.from_url(settings.redis_url, socket_timeout=1.5)
        except Exception:
            return None

    @classmethod
    def is_token_consumed(cls, jti: str) -> bool:
        if not jti:
            return True
        r = cls._get_redis()
        if r:
            try:
                return bool(r.exists(f"aura:consumed_token:{jti}"))
            except Exception as e:
                logger.warning("redis_token_check_failed", error=str(e))
        return jti in _CONSUMED_JTIS

    @classmethod
    def consume_token(cls, jti: str, ttl_seconds: int = 86400) -> None:
        if not jti:
            return
        _CONSUMED_JTIS.add(jti)
        r = cls._get_redis()
        if r:
            try:
                r.set(f"aura:consumed_token:{jti}", "1", ex=ttl_seconds)
            except Exception as e:
                logger.warning("redis_token_consume_failed", error=str(e))

    # =========================================================================
    # Phase 3: Comprehensive 14-Section Gmail Approval Notification Email
    # =========================================================================

    @staticmethod
    async def _send_via_resend(to: str, subject: str, html: str, text: str) -> str:
        """Send through Resend's HTTPS API and return the provider message id."""
        import httpx

        sender = os.environ.get("RESEND_FROM", "AURA Approvals <onboarding@resend.dev>")
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
                json={"from": sender, "to": [to], "subject": subject, "html": html, "text": text},
            )
        if resp.status_code >= 300:
            raise RuntimeError(f"Resend returned {resp.status_code}: {resp.text[:300]}")
        return str(resp.json().get("id", ""))

    @classmethod
    async def send_approval_request_email(
        cls,
        approval_id: uuid.UUID | str,
        tool_name: str,
        action_summary: str,
        action_details: dict[str, Any],
        reason: str | None = None,
        recipient_email: str | None = None,
        agent_run_id: uuid.UUID | str | None = None,
        organization_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        """
        Builds and dispatches an executive-readable approval notification email containing
        all 14 required business sections and secure review links (GET review, POST decision).
        """
        settings = get_settings()
        api_env = os.environ.get("AURA_API_BASE_URL", "http://localhost:8000")
        api_base = api_env if api_env.endswith("/api/v1") else f"{api_env.rstrip('/')}/api/v1"
        frontend_base = os.environ.get("AURA_FRONTEND_BASE_URL", "http://localhost:3000")

        # 14 Required Executive Details (Phase 3)
        company_name = (
            action_details.get("company_name")
            or action_details.get("customer_name")
            or "Not specified"
        )
        request_id_str = str(approval_id)
        what_aura_wants_to_do = action_details.get("business_objective") or action_summary
        why_necessary = (
            action_details.get("why_necessary")
            or reason
            or f"'{tool_name}' is classified as requiring human approval before it runs."
        )
        evidence = action_details.get("supporting_evidence") or action_details
        evidence_formatted = (
            json.dumps(evidence, indent=2, default=str)
            if isinstance(evidence, dict)
            else str(evidence)
        )[:2000]
        data_affected = action_details.get("data_affected") or "Not specified by the agent."
        target_destination = (
            recipient_email
            or action_details.get("recipient")
            or action_details.get("target_recipient")
            or os.environ.get("GMAIL_RECIPIENT_EMAIL")
            or os.environ.get("AURA_APPROVAL_EMAIL")
        )
        # With no approver address configured nothing can be delivered; say so
        # instead of inventing a recipient.
        configured_recipient = target_destination or None
        target_destination = configured_recipient or "(no approver email configured)"
        if action_details.get("financial_impact"):
            financial_impact = action_details["financial_impact"]
        elif action_details.get("total") is not None:
            financial_impact = f"Total: ${action_details['total']}"
            if action_details.get("discount_percent") is not None:
                financial_impact += f" (discount {action_details['discount_percent']}%)"
        else:
            financial_impact = "Not specified by the agent."
        expected_result = action_details.get("expected_result") or (
            f"The run resumes and executes '{tool_name}': {action_summary}"
        )
        risks_and_uncertainties = (
            action_details.get("risks_and_uncertainties")
            or "Not specified by the agent. Review the action details above before approving."
        )
        if_approved = f"AURA resumes the paused run and executes '{tool_name}' with the arguments shown, then records the outcome in the audit trail."
        if_rejected = "The run is cancelled. The action is not executed, and the rejection is recorded in the audit trail."
        expiration_text = "24 hours from dispatch (Single-use Cryptographic Nonce Token)"

        # Generate cryptographic tokens with single-use nonce
        approve_token = cls.generate_token(approval_id, "approve", hours_valid=24)
        deny_token = cls.generate_token(approval_id, "deny", hours_valid=24)

        # GET review links route to the review and authorization screen
        approve_url = f"{api_base}/approvals/email-action?token={approve_token}&decision=approve"
        deny_url = f"{api_base}/approvals/email-action?token={deny_token}&decision=deny"
        view_in_aura_url = f"{frontend_base}/approvals"

        subject = f"[AURA Action Required] Executive Approval: {tool_name} — {company_name}"
        clean_params = action_details.get("exact_parameters") or {
            k: v for k, v in action_details.items() if not k.startswith("_")
        }
        params_formatted = json.dumps(clean_params, indent=2, default=str)

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #0f172a; line-height: 1.5; }}
    .container {{ max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #cbd5e1; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #0284c7 0%, #0f172a 100%); padding: 32px; color: #ffffff; }}
    .badge {{ display: inline-block; padding: 4px 14px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; background: rgba(255,255,255,0.18); color: #ffffff; margin-bottom: 12px; }}
    .title {{ font-size: 22px; font-weight: 700; margin: 0 0 6px 0; }}
    .content {{ padding: 32px; }}
    .section-title {{ font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 24px 0 8px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
    .section-title:first-of-type {{ margin-top: 0; }}
    .desc-box {{ background: #f8fafc; border-left: 4px solid #0284c7; padding: 14px 18px; border-radius: 8px; font-size: 14px; color: #1e293b; margin-bottom: 16px; }}
    .meta-table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px; }}
    .meta-table td {{ padding: 9px 12px; border-bottom: 1px solid #f1f5f9; }}
    .meta-table td.label {{ font-weight: 600; color: #475569; width: 32%; }}
    .meta-table td.value {{ color: #0f172a; font-weight: 500; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }}
    pre {{ background: #0b1120; color: #38bdf8; padding: 12px; border-radius: 8px; font-size: 11px; overflow-x: auto; margin: 0; }}
    .impact-box {{ background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 12px 16px; color: #065f46; font-size: 13px; margin-bottom: 16px; }}
    .risk-box {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 16px; color: #92400e; font-size: 13px; margin-bottom: 20px; }}
    .actions-panel {{ background: #f8fafc; border-radius: 12px; padding: 24px; text-align: center; border: 1px solid #e2e8f0; margin: 28px 0 16px 0; }}
    .btn {{ display: inline-block; padding: 14px 28px; border-radius: 10px; font-weight: 700; font-size: 14px; text-decoration: none; margin: 0 8px; }}
    .btn-approve {{ background: #16a34a; color: #ffffff !important; box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3); }}
    .btn-deny {{ background: #ef4444; color: #ffffff !important; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }}
    .notice {{ font-size: 11px; color: #64748b; margin-top: 14px; }}
    .footer {{ background: #f8fafc; padding: 20px 32px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; text-align: center; }}
    .footer a {{ color: #0284c7; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="badge">Human-in-the-Loop Governance</span>
      <h1 class="title">Action Approval Required</h1>
      <div style="font-size: 13px; opacity: 0.9;">Target Client: <strong>{company_name}</strong> &bull; Request ID: <span class="mono">{request_id_str}</span></div>
    </div>
    
    <div class="content">
      <!-- 1. Executive Summary & Objective -->
      <div class="section-title">1 &amp; 2. Business Objective &amp; Proposed Action</div>
      <div class="desc-box">
        <strong>What AURA wants to do:</strong><br>
        {what_aura_wants_to_do}
      </div>

      <!-- 3. Why Necessary -->
      <div class="section-title">3. Justification &amp; Policy Requirement</div>
      <p style="font-size: 13px; margin: 0 0 16px 0; color: #334155;">{why_necessary}</p>

      <!-- 4 & 5. Information & Data Affected -->
      <div class="section-title">4 &amp; 5. Supporting Information &amp; Affected Data</div>
      <table class="meta-table">
        <tr>
          <td class="label">Target Client</td>
          <td class="value"><strong>{company_name}</strong></td>
        </tr>
        <tr>
          <td class="label">Recipient Destination</td>
          <td class="value mono">{target_destination}</td>
        </tr>
        <tr>
          <td class="label">Data Affected</td>
          <td class="value">{data_affected}</td>
        </tr>
        <tr>
          <td class="label">Supporting Evidence</td>
          <td class="value"><pre>{evidence_formatted}</pre></td>
        </tr>
      </table>

      <!-- 6 & 7. Financial Impact & Expected Result -->
      <div class="section-title">6 &amp; 7. Financial &amp; Operational Outcome</div>
      <div class="impact-box">
        <strong>Financial Impact:</strong> {financial_impact}<br>
        <strong>Expected Result:</strong> {expected_result}
      </div>

      <!-- 8. Risks and Uncertainties -->
      <div class="section-title">8. Risks &amp; Uncertainties</div>
      <div class="risk-box">
        ⚠️ <strong>Operational Consideration:</strong> {risks_and_uncertainties}
      </div>

      <!-- 9 & 10. Consequence of Approval / Rejection -->
      <div class="section-title">9 &amp; 10. Governance Consequences</div>
      <table class="meta-table">
        <tr>
          <td class="label" style="color: #16a34a;">If Approved</td>
          <td class="value">{if_approved}</td>
        </tr>
        <tr>
          <td class="label" style="color: #ef4444;">If Rejected</td>
          <td class="value">{if_rejected}</td>
        </tr>
        <tr>
          <td class="label">Approval Expiration</td>
          <td class="value mono">{expiration_text}</td>
        </tr>
      </table>

      <!-- Exact Action Parameters -->
      <div class="section-title">Action Parameters Snapshot</div>
      <pre>{params_formatted}</pre>

      <!-- Interactive Decision Buttons -->
      <div class="actions-panel">
        <a href="{approve_url}" class="btn btn-approve">
          ✓ Review &amp; Authorize Action
        </a>
        <a href="{deny_url}" class="btn btn-deny">
          ✕ Reject Action
        </a>
        <div class="notice">
          🔒 Protected by cryptographic single-use nonce &bull; GET link loads verification form; state changes require authenticated POST submission.
        </div>
      </div>
    </div>

    <div class="footer">
      Dispatched by <strong>AURA Enterprise Platform</strong> &bull; <a href="{view_in_aura_url}">Open AURA Governance Inbox</a>
    </div>
  </div>
</body>
</html>"""

        text_body = f"""==================================================================
AURA ENTERPRISE HUMAN-IN-THE-LOOP APPROVAL REQUEST
==================================================================

1. COMPANY NAME: {company_name}
2. AURA REQUEST ID: {request_id_str}
3. WHAT AURA WANTS TO DO: {what_aura_wants_to_do}
4. WHY IT WANTS TO DO IT: {why_necessary}
5. SUPPORTING EVIDENCE:
{evidence_formatted}
6. DATA AFFECTED: {data_affected}
7. EXACT RECIPIENT: {target_destination}
8. FINANCIAL IMPACT: {financial_impact}
9. EXPECTED RESULT: {expected_result}
10. RISKS AND UNCERTAINTIES: {risks_and_uncertainties}
11. WHAT HAPPENS IF APPROVED: {if_approved}
12. WHAT HAPPENS IF REJECTED: {if_rejected}
13. APPROVAL EXPIRATION: {expiration_text}
14. SECURE REVIEW & AUTHORIZE LINK:
{approve_url}

REJECT ACTION LINK:
{deny_url}

OPEN AURA DASHBOARD:
{view_in_aura_url}
==================================================================
"""

        record = {
            "id": str(uuid.uuid4()),
            "approval_id": request_id_str,
            "recipient": target_destination,
            "subject": subject,
            "tool_name": tool_name,
            "company_name": company_name,
            "action_summary": action_summary,
            "approve_url": approve_url,
            "deny_url": deny_url,
            "html": html_body,
            "text": text_body,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "PENDING",
            "delivery_provider": "none",
        }

        # Store in recent outbox buffer
        _RECENT_EMAILS.insert(0, record)
        if len(_RECENT_EMAILS) > MAX_OUTBOX_SIZE:
            _RECENT_EMAILS.pop()

        logger.info(
            "approval_notification_email_dispatched",
            approval_id=request_id_str,
            recipient=target_destination,
            tool=tool_name,
            approve_url=approve_url,
        )

        if not configured_recipient:
            record["status"] = "NOT_SENT"
            record["delivery_error"] = "No approver email configured (set AURA_APPROVAL_EMAIL)."
            return record

        # 0. Resend (HTTPS API). Preferred: free hosts block outbound SMTP ports,
        #    and this needs one API key instead of a Google OAuth consent flow.
        if os.environ.get("RESEND_API_KEY"):
            try:
                message_id = await cls._send_via_resend(
                    configured_recipient, subject, html_body, text_body
                )
                record["status"] = "DELIVERED"
                record["delivery_provider"] = "Resend"
                record["provider_message_id"] = message_id
                return record
            except Exception as resend_err:
                logger.warning("resend_dispatch_failed", error=str(resend_err))
                record["status"] = "FAILED"
                record["delivery_provider"] = "Resend"
                record["delivery_error"] = str(resend_err)
                return record

        # 1. Attempt official Gmail REST API dispatch if organization is configured
        if organization_id:
            try:
                from app.services.gmail_service import GmailService

                await GmailService.send_gmail_api_message(
                    organization_id=organization_id,
                    recipient=target_destination,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                )
                record["gmail_api_delivered"] = True
                record["status"] = "DELIVERED"
                record["delivery_provider"] = (
                    "Gmail REST API (https://www.googleapis.com/auth/gmail.send)"
                )
                return record
            except Exception as gmail_err:
                logger.info(
                    "gmail_api_not_connected_for_notification_fallback_to_smtp",
                    error=str(gmail_err),
                )

        # 2. Fallback to SMTP Dispatch if configured
        from app.services.gmail_service import GmailService

        smtp_creds = await GmailService.get_smtp_credentials(organization_id)
        smtp_host = smtp_creds.get("host") or os.environ.get("SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(smtp_creds.get("port") or os.environ.get("SMTP_PORT", 587))
        smtp_user = (
            smtp_creds.get("sender_email")
            or os.environ.get("GMAIL_USER")
            or os.environ.get("GMAIL_SENDER_EMAIL")
            or os.environ.get("SMTP_USER", "")
        )
        smtp_pass = (
            smtp_creds.get("app_password")
            or os.environ.get("GMAIL_APP_PASSWORD")
            or os.environ.get("SMTP_PASSWORD", "")
        )

        if smtp_user and smtp_pass:
            try:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"AURA Enterprise Platform <{smtp_user}>"
                msg["To"] = target_destination

                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [target_destination], msg.as_string())

                record["smtp_delivered"] = True
                record["status"] = "DELIVERED"
                record["delivery_provider"] = "Gmail SMTP (smtp.gmail.com)"
                logger.info(
                    "email_delivered_via_gmail_smtp", recipient=target_destination, sender=smtp_user
                )
            except Exception as e:
                logger.warning(
                    "gmail_smtp_dispatch_failed", error=str(e), recipient=target_destination
                )
                record["smtp_delivered"] = False
                record["smtp_error"] = str(e)
                record["status"] = "FAILED"
                record["delivery_error"] = str(e)
        else:
            record["smtp_delivered"] = False
            record["status"] = "NOT_SENT"
            record["delivery_error"] = (
                "No email provider configured (set RESEND_API_KEY, or connect Gmail/SMTP)."
            )

        return record

    # =========================================================================
    # Phase 6: Completion & Outcome Notification Email Dispatcher
    # =========================================================================

    @classmethod
    async def send_completion_notification_email(
        cls,
        approval_id: uuid.UUID | str,
        tool_name: str,
        action_summary: str,
        status: str,  # "COMPLETED", "FAILED", "CANCELLED"
        result: Any = None,
        error: str | None = None,
        agent_run_id: uuid.UUID | str | None = None,
        organization_id: uuid.UUID | str | None = None,
        recipient_email: str | None = None,
        execution_time_seconds: float | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Dispatches an executive completion notice after execution completes (Phase 6 requirement).
        Provides the actual execution result, audit trail reference, outcome status, and timestamps.
        """
        frontend_base = os.environ.get("AURA_FRONTEND_BASE_URL", "http://localhost:3000")
        target_recipient = (
            recipient_email
            or os.environ.get("GMAIL_RECIPIENT_EMAIL")
            or os.environ.get("AURA_APPROVAL_EMAIL")
            or "operator@aura.internal"
        )
        is_success = status.upper() == "COMPLETED"
        status_label = (
            "Execution Completed Successfully" if is_success else f"Action {status.title()}"
        )
        status_color = "#16a34a" if is_success else "#ef4444"
        exec_timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        audit_ref = f"AUD-{uuid.uuid4().hex[:12].upper()}"

        client_name = company_name or "Cloud Infotech Partner"
        subject = f"[AURA Action Update] {status_label}: {tool_name} — {client_name}"

        result_formatted = (
            json.dumps(result, indent=2, default=str)
            if result
            else (error or "No payload returned.")
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #0f172a; line-height: 1.5; }}
    .container {{ max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #cbd5e1; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, {status_color} 0%, #0f172a 100%); padding: 32px; color: #ffffff; }}
    .badge {{ display: inline-block; padding: 4px 14px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; background: rgba(255,255,255,0.2); color: #ffffff; margin-bottom: 12px; }}
    .title {{ font-size: 22px; font-weight: 700; margin: 0 0 6px 0; }}
    .content {{ padding: 32px; }}
    .table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
    .table td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
    .table td.label {{ font-weight: 600; color: #475569; width: 32%; }}
    .table td.value {{ color: #0f172a; font-weight: 500; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }}
    pre {{ background: #0b1120; color: #38bdf8; padding: 14px; border-radius: 8px; font-size: 11px; overflow-x: auto; margin: 0; }}
    .footer {{ background: #f8fafc; padding: 20px 32px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; text-align: center; }}
    .footer a {{ color: #0284c7; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="badge">Execution Completion Report</span>
      <h1 class="title">{status_label}</h1>
      <div style="font-size: 13px; opacity: 0.9;">Action: {action_summary}</div>
    </div>
    
    <div class="content">
      <table class="table">
        <tr>
          <td class="label">Action Name</td>
          <td class="value"><strong>{tool_name}</strong></td>
        </tr>
        <tr>
          <td class="label">Target Client / Recipient</td>
          <td class="value">{client_name} ({target_recipient})</td>
        </tr>
        <tr>
          <td class="label">AURA Request ID</td>
          <td class="value mono">{approval_id!s}</td>
        </tr>
        <tr>
          <td class="label">Agent Run ID</td>
          <td class="value mono">{str(agent_run_id) if agent_run_id else "N/A"}</td>
        </tr>
        <tr>
          <td class="label">Audit Trail ID</td>
          <td class="value mono"><strong>{audit_ref}</strong></td>
        </tr>
        <tr>
          <td class="label">Execution Timestamp</td>
          <td class="value">{exec_timestamp}</td>
        </tr>
        <tr>
          <td class="label">Status Outcome</td>
          <td class="value"><span style="color: {status_color}; font-weight: 700;">{status.upper()}</span></td>
        </tr>
      </table>

      <div style="font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 8px;">System Execution Result:</div>
      <pre>{result_formatted}</pre>
    </div>

    <div class="footer">
      Sent by <strong>AURA Enterprise Platform</strong> &bull; <a href="{frontend_base}/approvals">View in Approvals Monitor</a>
    </div>
  </div>
</body>
</html>"""

        text_body = f"""==================================================================
AURA EXECUTION COMPLETION NOTIFICATION
==================================================================
STATUS: {status.upper()}
ACTION NAME: {tool_name}
SUMMARY: {action_summary}
TARGET CLIENT: {client_name}
RECIPIENT: {target_recipient}
REQUEST ID: {approval_id!s}
AGENT RUN ID: {agent_run_id!s}
AUDIT TRAIL REFERENCE: {audit_ref}
TIMESTAMP: {exec_timestamp}

EXECUTION RESULT:
{result_formatted}

VIEW IN AURA: {frontend_base}/approvals
==================================================================
"""

        record = {
            "id": str(uuid.uuid4()),
            "approval_id": str(approval_id),
            "recipient": target_recipient,
            "subject": subject,
            "tool_name": tool_name,
            "status": status.upper(),
            "html": html_body,
            "text": text_body,
            "audit_ref": audit_ref,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "COMPLETION_NOTIFICATION",
            "delivery_provider": "AURA Secure Outbox",
        }

        _RECENT_EMAILS.insert(0, record)
        if len(_RECENT_EMAILS) > MAX_OUTBOX_SIZE:
            _RECENT_EMAILS.pop()

        logger.info(
            "completion_notification_dispatched",
            approval_id=str(approval_id),
            status=status,
            recipient=target_recipient,
            audit_ref=audit_ref,
        )

        # 1. Attempt Gmail REST API dispatch
        if organization_id:
            try:
                from app.services.gmail_service import GmailService

                await GmailService.send_gmail_api_message(
                    organization_id=organization_id,
                    recipient=target_recipient,
                    subject=subject,
                    body_text=text_body,
                    body_html=html_body,
                )
                record["gmail_api_delivered"] = True
                record["delivery_provider"] = (
                    "Gmail REST API (https://www.googleapis.com/auth/gmail.send)"
                )
                return record
            except Exception as gmail_err:
                logger.info(
                    "gmail_api_not_connected_for_completion_fallback_to_smtp", error=str(gmail_err)
                )

        # 2. Attempt SMTP
        from app.services.gmail_service import GmailService

        smtp_creds = await GmailService.get_smtp_credentials(organization_id)
        smtp_host = smtp_creds.get("host") or os.environ.get("SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(smtp_creds.get("port") or os.environ.get("SMTP_PORT", 587))
        smtp_user = (
            smtp_creds.get("sender_email")
            or os.environ.get("GMAIL_USER")
            or os.environ.get("GMAIL_SENDER_EMAIL")
            or os.environ.get("SMTP_USER", "")
        )
        smtp_pass = (
            smtp_creds.get("app_password")
            or os.environ.get("GMAIL_APP_PASSWORD")
            or os.environ.get("SMTP_PASSWORD", "")
        )

        if smtp_user and smtp_pass:
            try:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"AURA Enterprise Platform <{smtp_user}>"
                msg["To"] = target_recipient

                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [target_recipient], msg.as_string())

                record["smtp_delivered"] = True
                record["delivery_provider"] = "Gmail SMTP (smtp.gmail.com)"
            except Exception as e:
                record["smtp_delivered"] = False
                record["smtp_error"] = str(e)

        return record

    @classmethod
    def get_recent_emails(cls) -> list[dict[str, Any]]:
        return list(_RECENT_EMAILS)
