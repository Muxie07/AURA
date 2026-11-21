"""
AURA Enterprise Gmail & Google Workspace Integration Service.
Provides OAuth 2.0 authorization, encrypted token/credential storage, automatic token refresh,
Gmail REST API delivery, anti-replay CSRF protection, secure cryptographic approval dispatching,
and decoupled dual-channel status tracking (SMTP Gateway & Official Google OAuth 2.0 API).
"""

import base64
import json
import os
import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
import jwt
import structlog

from app.config.settings import get_settings
from app.security.vault import CredentialVault

logger = structlog.get_logger(__name__)

# Fallback config file path (for local dev fallback without active DB)
CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "gmail_credentials.json"
)

# In-memory delivery tracking log
_DELIVERY_LOGS: list[dict[str, Any]] = []
# In-memory single-use anti-replay state nonces
_CONSUMED_NONCES: set[str] = set()
# In-memory idempotency ledger for sent messages
_PROCESSED_IDEMPOTENCY_KEYS: dict[str, dict[str, Any]] = {}
# In-memory fallback credential store when DB is uninitialized (for testing)
_IN_MEMORY_CREDENTIALS: dict[str, dict[str, Any]] = {}
# In-memory capability metadata tracking
_SMTP_METADATA: dict[str, dict[str, Any]] = {}
_OAUTH_METADATA: dict[str, dict[str, Any]] = {}


class AuthorizationExpiredError(Exception):
    """Raised when OAuth access and refresh tokens are expired or revoked."""

    pass


class GmailService:
    """
    Dedicated Enterprise Gmail Service for AURA.
    Manages OAuth 2.0 tokens, automatic token refresh, Gmail REST API sending,
    CredentialVault encryption, sender verification, and approval request notifications.
    Decouples SMTP transport from Google OAuth REST API authorization.
    """

    GMAIL_API_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REQUIRED_SCOPE = "https://www.googleapis.com/auth/gmail.send"
    _SMTP_METADATA: dict[str, dict[str, Any]] = _SMTP_METADATA
    _OAUTH_METADATA: dict[str, dict[str, Any]] = _OAUTH_METADATA

    # =========================================================================
    # Redis / Distributed Cache Helper
    # =========================================================================
    @classmethod
    def _get_redis(cls):
        try:
            import redis

            settings = get_settings()
            return redis.from_url(settings.redis_url, socket_timeout=1.5)
        except Exception:
            return None

    # =========================================================================
    # OAuth 2.0 State & CSRF Protection
    # =========================================================================
    @classmethod
    def generate_oauth_state(
        cls,
        organization_id: uuid.UUID | str,
        user_id: uuid.UUID | str | None = None,
        ttl_minutes: int = 15,
    ) -> str:
        settings = get_settings()
        secret = settings.aura_secret_key.get_secret_value()
        nonce = uuid.uuid4().hex
        exp = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        payload = {
            "sub": str(organization_id),
            "org_id": str(organization_id),
            "user_id": str(user_id) if user_id else "",
            "nonce": nonce,
            "exp": exp,
            "iat": datetime.now(UTC),
            "iss": "aura-gmail-oauth",
        }

        r = cls._get_redis()
        if r:
            try:
                r.set(f"aura:gmail_oauth_nonce:{nonce}", "valid", ex=ttl_minutes * 60)
            except Exception as e:
                logger.warning("redis_nonce_storage_failed", error=str(e))
        else:
            _CONSUMED_NONCES.discard(nonce)

        return jwt.encode(payload, secret, algorithm="HS256")

    @classmethod
    def verify_and_consume_oauth_state(cls, state_token: str) -> dict[str, Any]:
        if not state_token:
            raise ValueError("OAuth state token is missing or empty.")

        settings = get_settings()
        secret = settings.aura_secret_key.get_secret_value()

        try:
            payload = jwt.decode(
                state_token, secret, algorithms=["HS256"], issuer="aura-gmail-oauth"
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("OAuth state token has expired. Please initiate connection again.")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid OAuth state token: {e}")

        nonce = payload.get("nonce")
        if not nonce:
            raise ValueError("Invalid OAuth state token: missing cryptographic nonce.")

        r = cls._get_redis()
        if r:
            try:
                key = f"aura:gmail_oauth_nonce:{nonce}"
                exists = r.get(key)
                if not exists:
                    raise ValueError(
                        "OAuth state token has already been consumed or is invalid (replay detected)."
                    )
                r.delete(key)
            except ValueError:
                raise
            except Exception as e:
                logger.warning("redis_nonce_check_failed", error=str(e))
                if nonce in _CONSUMED_NONCES:
                    raise ValueError("OAuth state token replay detected.")
                _CONSUMED_NONCES.add(nonce)
        else:
            if nonce in _CONSUMED_NONCES:
                raise ValueError("OAuth state token replay detected.")
            _CONSUMED_NONCES.add(nonce)

        return {
            "organization_id": payload.get("org_id") or payload.get("sub"),
            "user_id": payload.get("user_id"),
        }

    # =========================================================================
    # OAuth Authorization URL Generator
    # =========================================================================
    @classmethod
    def get_authorization_url(
        cls,
        organization_id: uuid.UUID | str,
        user_id: uuid.UUID | str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else os.environ.get("GOOGLE_CLIENT_SECRET")
        )

        if not (client_id and client_secret):
            get_settings.cache_clear()
            settings = get_settings()
            client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = (
                settings.google_client_secret.get_secret_value()
                if settings.google_client_secret
                else os.environ.get("GOOGLE_CLIENT_SECRET")
            )

        effective_redirect_uri = (
            redirect_uri
            or settings.google_redirect_uri
            or os.environ.get(
                "GOOGLE_REDIRECT_URI",
                "http://localhost:8000/api/v1/integrations/gmail/oauth/callback",
            )
        )

        if not (client_id and client_secret):
            return {
                "configured": False,
                "auth_url": None,
                "redirect_uri": effective_redirect_uri,
                "message": (
                    "Google OAuth credentials not configured on server. "
                    "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
                ),
            }

        state = cls.generate_oauth_state(organization_id, user_id)
        scopes = f"{cls.REQUIRED_SCOPE} https://www.googleapis.com/auth/userinfo.email"

        from urllib.parse import urlencode

        params = {
            "client_id": client_id,
            "redirect_uri": effective_redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        return {
            "configured": True,
            "auth_url": auth_url,
            "redirect_uri": effective_redirect_uri,
        }

    # =========================================================================
    # Authorization Code Exchange & Token Storage
    # =========================================================================
    @classmethod
    async def exchange_code(
        cls,
        code: str,
        redirect_uri: str,
        organization_id: uuid.UUID | str,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else os.environ.get("GOOGLE_CLIENT_SECRET")
        )

        if not (client_id and client_secret):
            get_settings.cache_clear()
            settings = get_settings()
            client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = (
                settings.google_client_secret.get_secret_value()
                if settings.google_client_secret
                else os.environ.get("GOOGLE_CLIENT_SECRET")
            )

        if not (client_id and client_secret):
            raise ValueError("Google OAuth credentials not configured on server.")

        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            owns_client = True

        try:
            token_resp = await client.post(
                cls.GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if token_resp.status_code != 200:
                err_text = token_resp.text
                logger.error(
                    "oauth_token_exchange_failed", status=token_resp.status_code, response=err_text
                )
                try:
                    err_json = token_resp.json()
                    err_desc = (
                        err_json.get("error_description") or err_json.get("error") or err_text
                    )
                except Exception:
                    err_desc = err_text
                raise ValueError(f"Google OAuth token exchange failed: {err_desc}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = int(token_data.get("expires_in", 3600))

            if not access_token:
                raise ValueError("Google did not return an access token.")

            # Identify connected account email
            user_email = None
            try:
                userinfo_resp = await client.get(
                    cls.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if userinfo_resp.status_code == 200:
                    user_email = userinfo_resp.json().get("email")
            except Exception as e:
                logger.warning("failed_to_fetch_google_userinfo", error=str(e))

            if not user_email:
                user_email = (
                    settings.gmail_sender_email
                    or os.environ.get("GMAIL_SENDER_EMAIL")
                    or "connected-gmail@google.com"
                )

            # If refresh_token was not returned (user already consented), preserve existing refresh token
            if not refresh_token:
                oauth_status = await cls.get_oauth_status(organization_id)
                refresh_token = oauth_status.get("_decrypted_refresh_token")

            expiry_dt = datetime.now(UTC) + timedelta(seconds=expires_in)

            saved_meta = await cls._save_oauth_credentials(
                organization_id=organization_id,
                sender_email=user_email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=expiry_dt.isoformat(),
            )

            cls._record_delivery_log(
                event="OAUTH_CONNECTED",
                recipient=user_email,
                status="CONNECTED",
                details=f"Authorized Gmail account {user_email} with scope {cls.REQUIRED_SCOPE}.",
            )

            org_str = str(organization_id)
            cls._OAUTH_METADATA[org_str] = {
                "last_api_operation_at": datetime.now(UTC).isoformat(),
                "last_error": None,
            }

            return {
                "status": "CONNECTED",
                "sender_email": user_email,
                "connected_email": user_email,
                "auth_type": "oauth2",
                "token_expiry": expiry_dt.isoformat(),
                "last_verified_at": saved_meta.get("last_verified_at"),
            }
        finally:
            if owns_client:
                await client.aclose()

    # =========================================================================
    # Credential Persistence & Encryption
    # =========================================================================
    @classmethod
    async def _save_oauth_credentials(
        cls,
        organization_id: uuid.UUID | str,
        sender_email: str,
        access_token: str,
        refresh_token: str | None,
        token_expiry: str,
    ) -> dict[str, Any]:
        org_str = str(organization_id)
        now_iso = datetime.now(UTC).isoformat()
        payload_data = {
            "auth_type": "oauth2",
            "sender_email": sender_email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": token_expiry,
            "scope": cls.REQUIRED_SCOPE,
            "connected_at": now_iso,
            "last_verified_at": now_iso,
        }

        enc_payload = CredentialVault.encrypt_secret(json.dumps(payload_data), org_str).hex()

        # Store in-memory under multiple keys for resilient multi-lookup
        _IN_MEMORY_CREDENTIALS[f"{org_str}:oauth2"] = payload_data
        _IN_MEMORY_CREDENTIALS[org_str] = payload_data

        # Store in local config file
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "auth_type": "oauth2",
                        "sender_email": sender_email,
                        "organization_id": org_str,
                        "token_expiry": token_expiry,
                        "last_verified_at": now_iso,
                        "encrypted_payload": enc_payload,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning("failed_to_write_local_gmail_config", error=str(e))

        # Persist to database IntegrationCredential table
        try:
            import sqlalchemy as sa

            from app.database.base import get_session_factory
            from app.database.models import IntegrationCredential

            org_uuid = uuid.UUID(org_str)
            session_factory = get_session_factory()
            async with session_factory() as db:
                stmt = sa.select(IntegrationCredential).where(
                    IntegrationCredential.organization_id == org_uuid,
                    IntegrationCredential.name.in_(["gmail_oauth", "gmail"]),
                    IntegrationCredential.credential_type == "oauth2",
                )
                existing = (await db.scalars(stmt)).first()
                if existing:
                    existing.name = "gmail_oauth"
                    existing.credential_type = "oauth2"
                    existing.encrypted_payload = enc_payload
                else:
                    new_cred = IntegrationCredential(
                        organization_id=org_uuid,
                        name="gmail_oauth",
                        credential_type="oauth2",
                        encrypted_payload=enc_payload,
                    )
                    db.add(new_cred)
                await db.commit()
        except Exception as db_err:
            logger.debug("persisting_credential_db_note", detail=str(db_err))

        return {"last_verified_at": now_iso}

    # =========================================================================
    # Token Refresh Lifecycle
    # =========================================================================
    @classmethod
    async def get_valid_access_token(
        cls,
        organization_id: uuid.UUID | str,
        client: httpx.AsyncClient | None = None,
    ) -> tuple[str, str]:
        oauth_status = await cls.get_oauth_status(organization_id)
        if not oauth_status.get("connected"):
            raise ValueError(
                f"Gmail is not connected via OAuth 2.0 for organization {organization_id}. Connect Gmail first."
            )

        access_token = oauth_status.get("_decrypted_access_token")
        refresh_token = oauth_status.get("_decrypted_refresh_token")
        sender_email = oauth_status.get("authorized_account") or "me"
        token_expiry_str = oauth_status.get("token_expiry")

        needs_refresh = False
        if not access_token:
            needs_refresh = True
        elif token_expiry_str:
            try:
                expiry_dt = datetime.fromisoformat(token_expiry_str.replace("Z", "+00:00"))
                if datetime.now(UTC) + timedelta(seconds=300) >= expiry_dt:
                    needs_refresh = True
            except Exception:
                needs_refresh = True

        if not needs_refresh and access_token:
            return access_token, sender_email

        if not refresh_token:
            raise AuthorizationExpiredError(
                "Access token has expired and no refresh token is stored. Please re-authorize Gmail."
            )

        settings = get_settings()
        client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else os.environ.get("GOOGLE_CLIENT_SECRET")
        )

        if not (client_id and client_secret):
            raise ValueError("Google OAuth credentials missing on server.")

        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            owns_client = True

        try:
            refresh_resp = await client.post(
                cls.GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if refresh_resp.status_code != 200:
                err_text = refresh_resp.text
                logger.error(
                    "token_refresh_failed", status=refresh_resp.status_code, error=err_text
                )
                if "invalid_grant" in err_text:
                    raise AuthorizationExpiredError(
                        "Gmail authorization has expired or was revoked in Google Account settings. Please reconnect Gmail."
                    )
                raise ValueError(f"Failed to refresh Google access token: {err_text}")

            refresh_data = refresh_resp.json()
            new_access_token = refresh_data.get("access_token")
            new_refresh_token = refresh_data.get("refresh_token") or refresh_token
            expires_in = int(refresh_data.get("expires_in", 3600))
            new_expiry = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()

            await cls._save_oauth_credentials(
                organization_id=organization_id,
                sender_email=sender_email,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_expiry=new_expiry,
            )

            logger.info("gmail_access_token_refreshed_successfully", sender=sender_email)
            return new_access_token, sender_email
        finally:
            if owns_client:
                await client.aclose()

    # =========================================================================
    # Backend Gmail REST API Sending Service
    # =========================================================================
    @classmethod
    async def send_gmail_api_message(
        cls,
        organization_id: uuid.UUID | str,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        idempotency_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        if idempotency_key and idempotency_key in _PROCESSED_IDEMPOTENCY_KEYS:
            logger.info(
                "gmail_message_idempotent_duplicate_prevented", idempotency_key=idempotency_key
            )
            return _PROCESSED_IDEMPOTENCY_KEYS[idempotency_key]

        access_token, sender_email = await cls.get_valid_access_token(
            organization_id, client=client
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AURA Enterprise Platform <{sender_email}>"
        msg["To"] = recipient

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        raw_bytes = msg.as_bytes()
        encoded_message = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=20.0)
            owns_client = True

        try:
            api_resp = await client.post(
                cls.GMAIL_API_SEND_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": encoded_message},
            )

            if api_resp.status_code not in (200, 201):
                err_text = api_resp.text
                logger.error(
                    "gmail_api_send_failed", status=api_resp.status_code, response=err_text
                )
                if api_resp.status_code == 401:
                    raise AuthorizationExpiredError(
                        "Google API returned 401 Unauthorized. Access token revoked or invalid."
                    )
                raise ValueError(
                    f"Gmail REST API send rejected (HTTP {api_resp.status_code}): {err_text}"
                )

            result_data = api_resp.json()
            message_id = result_data.get("id", f"msg_{uuid.uuid4().hex[:12]}")
            thread_id = result_data.get("threadId", "")

            cls._record_delivery_log(
                event="EMAIL_SENT_GMAIL_API",
                recipient=recipient,
                status="DELIVERED",
                details=f"Dispatched message ID {message_id} to {recipient} via official Gmail REST API.",
            )

            delivery_result = {
                "delivered": True,
                "status": "DELIVERED",
                "message_id": message_id,
                "thread_id": thread_id,
                "recipient": recipient,
                "sender_email": sender_email,
                "delivery_provider": f"Gmail REST API ({cls.REQUIRED_SCOPE})",
                "provider": "Gmail REST API",
                "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            }

            if idempotency_key:
                _PROCESSED_IDEMPOTENCY_KEYS[idempotency_key] = delivery_result

            org_str = str(organization_id)
            cls._OAUTH_METADATA[org_str] = {
                "last_api_operation_at": datetime.now(UTC).isoformat(),
                "last_error": None,
            }

            return delivery_result
        finally:
            if owns_client:
                await client.aclose()

    # =========================================================================
    # Capability 1: SMTP Status & Inspection (Independent)
    # =========================================================================
    @classmethod
    async def get_smtp_status(
        cls, organization_id: uuid.UUID | str | None = None
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"
        settings = get_settings()

        smtp_host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        recipient = (
            os.environ.get("GMAIL_RECIPIENT_EMAIL")
            or os.environ.get("AURA_APPROVAL_EMAIL")
            or "mufeed.career@gmail.com"
        )

        sender = None
        has_password = False
        source = "none"

        # 1. Check in-memory store
        smtp_mem_key = f"{org_str}:smtp"
        if smtp_mem_key in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[smtp_mem_key]
            sender = mem.get("sender_email")
            has_password = bool(mem.get("app_password") or mem.get("encrypted_password"))
            source = "memory"
        elif (
            org_str in _IN_MEMORY_CREDENTIALS
            and _IN_MEMORY_CREDENTIALS[org_str].get("auth_type") == "smtp"
        ):
            mem = _IN_MEMORY_CREDENTIALS[org_str]
            sender = mem.get("sender_email")
            has_password = bool(mem.get("app_password") or mem.get("encrypted_password"))
            source = "memory"

        # 2. Check Database IntegrationCredential
        if not sender and organization_id and str(organization_id) != "org-default":
            try:
                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                org_uuid = uuid.UUID(str(organization_id))
                session_factory = get_session_factory()
                async with session_factory() as db:
                    stmt = (
                        sa.select(IntegrationCredential)
                        .where(
                            IntegrationCredential.organization_id == org_uuid,
                            IntegrationCredential.name.in_(["gmail_smtp", "gmail"]),
                            IntegrationCredential.credential_type == "smtp",
                        )
                        .order_by(IntegrationCredential.created_at.desc())
                    )
                    cred = (await db.scalars(stmt)).first()
                    if cred and cred.encrypted_payload:
                        decrypted_str = CredentialVault.decrypt_secret(
                            cred.encrypted_payload, str(org_uuid)
                        )
                        payload = json.loads(decrypted_str)
                        sender = payload.get("sender_email")
                        has_password = bool(payload.get("app_password"))
                        recipient = payload.get("recipient_email") or recipient
                        source = "vault"
                        _IN_MEMORY_CREDENTIALS[smtp_mem_key] = payload
            except Exception as e:
                logger.debug("failed_to_query_smtp_credential_db", error=str(e))

        # 3. Check local config file fallback
        if not sender and os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
                    file_cfg = json.load(f)
                    if file_cfg.get("auth_type") == "smtp" or file_cfg.get("encrypted_password"):
                        sender = file_cfg.get("sender_email")
                        has_password = bool(
                            file_cfg.get("encrypted_password") or file_cfg.get("app_password")
                        )
                        recipient = file_cfg.get("recipient_email") or recipient
                        source = "file"
            except Exception:
                pass

        # 4. Check server environment variables fallback
        if not (sender and has_password):
            env_sender = (
                os.environ.get("GMAIL_SENDER_EMAIL")
                or os.environ.get("GMAIL_USER")
                or settings.gmail_sender_email
            )
            if env_sender:
                env_sender = env_sender.strip().strip("'\"")
            env_pass = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASSWORD")
            if env_pass:
                env_pass = env_pass.strip().strip("'\"")

            if env_sender and env_pass:
                sender = env_sender
                has_password = True
                source = "env"

        configured = bool(sender and has_password)
        meta = cls._SMTP_METADATA.get(org_str, {})

        last_delivery = meta.get("last_delivery_at")
        if not last_delivery:
            for l in reversed(_DELIVERY_LOGS):
                if l.get("status") in ["DELIVERED", "SUCCESS"] and "SMTP" in str(
                    l.get("details", "")
                ):
                    last_delivery = l.get("timestamp")
                    break

        return {
            "status": "configured" if configured else "not_configured",
            "configured": configured,
            "host": smtp_host,
            "port": smtp_port,
            "security": "STARTTLS",
            "sender_email": sender,
            "recipient_email": recipient,
            "source": source,
            "last_tested_at": meta.get("last_tested_at"),
            "last_delivery_at": last_delivery,
            "last_error": meta.get("last_error"),
        }

    # =========================================================================
    # Capability 2: Google OAuth Status & Inspection (Independent)
    # =========================================================================
    @classmethod
    async def get_oauth_status(
        cls, organization_id: uuid.UUID | str | None = None
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"
        settings = get_settings()

        client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else os.environ.get("GOOGLE_CLIENT_SECRET")
        )
        if not (client_id and client_secret):
            get_settings.cache_clear()
            settings = get_settings()
            client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = (
                settings.google_client_secret.get_secret_value()
                if settings.google_client_secret
                else os.environ.get("GOOGLE_CLIENT_SECRET")
            )

        oauth_configured = bool(client_id and client_secret)
        effective_redirect_uri = settings.google_redirect_uri or os.environ.get(
            "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/gmail/oauth/callback"
        )
        client_id_preview = None
        if client_id:
            c_str = str(client_id).strip().strip("'\"")
            client_id_preview = f"{c_str[:12]}...{c_str[-16:]}" if len(c_str) > 28 else c_str

        user_email = None
        access_token = None
        refresh_token = None
        token_expiry_str = None
        source = "none"

        # 1. In-memory
        oauth_mem_key = f"{org_str}:oauth2"
        if oauth_mem_key in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[oauth_mem_key]
            user_email = mem.get("sender_email")
            access_token = mem.get("access_token")
            refresh_token = mem.get("refresh_token")
            token_expiry_str = mem.get("token_expiry")
            source = "memory"
        elif (
            org_str in _IN_MEMORY_CREDENTIALS
            and _IN_MEMORY_CREDENTIALS[org_str].get("auth_type") == "oauth2"
        ):
            mem = _IN_MEMORY_CREDENTIALS[org_str]
            user_email = mem.get("sender_email")
            access_token = mem.get("access_token")
            refresh_token = mem.get("refresh_token")
            token_expiry_str = mem.get("token_expiry")
            source = "memory"

        # 2. Database
        if (
            not (access_token or refresh_token)
            and organization_id
            and str(organization_id) != "org-default"
        ):
            try:
                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                org_uuid = uuid.UUID(str(organization_id))
                session_factory = get_session_factory()
                async with session_factory() as db:
                    stmt = (
                        sa.select(IntegrationCredential)
                        .where(
                            IntegrationCredential.organization_id == org_uuid,
                            IntegrationCredential.name.in_(["gmail_oauth", "gmail"]),
                            IntegrationCredential.credential_type == "oauth2",
                        )
                        .order_by(IntegrationCredential.created_at.desc())
                    )
                    cred = (await db.scalars(stmt)).first()
                    if cred and cred.encrypted_payload:
                        decrypted_str = CredentialVault.decrypt_secret(
                            cred.encrypted_payload, str(org_uuid)
                        )
                        payload = json.loads(decrypted_str)
                        user_email = payload.get("sender_email")
                        access_token = payload.get("access_token")
                        refresh_token = payload.get("refresh_token")
                        token_expiry_str = payload.get("token_expiry")
                        source = "vault"
                        _IN_MEMORY_CREDENTIALS[oauth_mem_key] = payload
            except Exception as e:
                logger.debug("failed_to_query_oauth_credential_db", error=str(e))

        # 3. File
        if not (access_token or refresh_token) and os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
                    file_cfg = json.load(f)
                    if file_cfg.get("auth_type") == "oauth2":
                        user_email = file_cfg.get("sender_email")
                        token_expiry_str = file_cfg.get("token_expiry")
                        enc_p = file_cfg.get("encrypted_payload")
                        if enc_p and organization_id:
                            try:
                                dec_str = CredentialVault.decrypt_secret(
                                    enc_p, str(organization_id)
                                )
                                payload = json.loads(dec_str)
                                access_token = payload.get("access_token")
                                refresh_token = payload.get("refresh_token")
                                source = "file_vault"
                            except Exception:
                                pass
            except Exception:
                pass

        is_token_expired = False
        if token_expiry_str:
            try:
                expiry_dt = datetime.fromisoformat(token_expiry_str.replace("Z", "+00:00"))
                is_token_expired = datetime.now(UTC) >= expiry_dt
            except Exception:
                pass

        if not (access_token or refresh_token):
            oauth_status = "not_connected"
            connected = False
        elif is_token_expired and not refresh_token:
            oauth_status = "authorization_expired"
            connected = False
        elif not refresh_token and not access_token:
            oauth_status = "authorization_required"
            connected = False
        else:
            oauth_status = "connected"
            connected = True

        meta = cls._OAUTH_METADATA.get(org_str, {})
        last_api_op = meta.get("last_api_operation_at")
        if not last_api_op:
            for l in reversed(_DELIVERY_LOGS):
                if l.get("status") in ["DELIVERED", "SUCCESS"] and "REST API" in str(
                    l.get("details", "")
                ):
                    last_api_op = l.get("timestamp")
                    break

        return {
            "status": oauth_status,
            "connected": connected,
            "configured": oauth_configured,
            "client_id_configured": bool(client_id),
            "client_secret_configured": bool(client_secret),
            "client_id_preview": client_id_preview,
            "redirect_uri": effective_redirect_uri,
            "authorized_account": user_email if connected else None,
            "scope": cls.REQUIRED_SCOPE,
            "token_expiry": token_expiry_str,
            "is_token_expired": is_token_expired,
            "last_api_operation_at": last_api_op,
            "last_error": meta.get("last_error"),
            "source": source,
            "_decrypted_access_token": access_token,
            "_decrypted_refresh_token": refresh_token,
        }

    # =========================================================================
    # Capability 3: Combined Connection Status (Truthful Multi-Channel)
    # =========================================================================
    @classmethod
    async def get_connection_status(
        cls, organization_id: uuid.UUID | str | None = None
    ) -> dict[str, Any]:
        smtp_status = await cls.get_smtp_status(organization_id)
        oauth_status = await cls.get_oauth_status(organization_id)

        resend_key = bool(os.environ.get("RESEND_API_KEY"))
        approver = os.environ.get("AURA_APPROVAL_EMAIL") or os.environ.get("GMAIL_RECIPIENT_EMAIL")
        resend_status = {
            "configured": resend_key,
            "from": os.environ.get("RESEND_FROM", "AURA Approvals <onboarding@resend.dev>"),
            "recipient_email": approver,
        }

        if resend_key and not (smtp_status["configured"] or oauth_status["connected"]):
            overall_status = "resend_only"
            overall_label = "Email Active (Resend)"
            overall_desc = "Approval emails are delivered over Resend's HTTPS API" + (
                f" to {approver}."
                if approver
                else ". Set AURA_APPROVAL_EMAIL to choose the approver."
            )
        elif smtp_status["configured"] and oauth_status["connected"]:
            overall_status = "fully_connected"
            overall_label = "Email Active (SMTP + Google OAuth)"
            overall_desc = (
                "Fully operational: Official Gmail REST API connected with verified SMTP fallback."
            )
        elif oauth_status["connected"]:
            overall_status = "oauth_only"
            overall_label = "Google OAuth Active"
            overall_desc = f"Connected via Google OAuth 2.0 (Gmail REST API) as {oauth_status['authorized_account']}."
        elif smtp_status["configured"]:
            overall_status = "smtp_only"
            overall_label = "Email Active (SMTP Transport)"
            overall_desc = "Email sending operational via SMTP transport (smtp.gmail.com). Google OAuth available to connect."
        else:
            overall_status = "disconnected"
            overall_label = "Not Connected"
            overall_desc = "No email delivery method configured. Connect with Google OAuth 2.0 or set up an App Password (SMTP)."

        can_send_email = bool(smtp_status["configured"] or oauth_status["connected"] or resend_key)
        can_use_gmail_api = bool(oauth_status["connected"])
        active_method = (
            "resend"
            if resend_key
            else (
                "gmail_api"
                if oauth_status["connected"]
                else ("smtp" if smtp_status["configured"] else "none")
            )
        )

        return {
            "overall_status": overall_status,
            "overall_label": overall_label,
            "overall_description": overall_desc,
            "can_send_email": can_send_email,
            "can_use_gmail_api": can_use_gmail_api,
            "active_sending_method": active_method,
            "smtp": smtp_status,
            "oauth": oauth_status,
            "resend": resend_status,
            # Backwards-compatibility fields for legacy callers
            "integration": "gmail",
            "smtp_host": smtp_status.get("host", "smtp.gmail.com"),
            "smtp_port": smtp_status.get("port", 587),
            "status": "connected" if can_send_email else "not_connected",
            "connected": can_send_email,
            "auth_type": "oauth2"
            if oauth_status["connected"]
            else ("smtp" if smtp_status["configured"] else "none"),
            "sender_email": oauth_status.get("authorized_account")
            or smtp_status.get("sender_email"),
            "connected_email": oauth_status.get("authorized_account")
            or smtp_status.get("sender_email"),
            "recipient_email": smtp_status.get("recipient_email")
            or os.environ.get("GMAIL_RECIPIENT_EMAIL"),
            "scope": cls.REQUIRED_SCOPE,
            "permission_granted": f"Gmail send permission only ({cls.REQUIRED_SCOPE})",
            "oauth_configured": oauth_status["configured"],
            "last_verified_at": oauth_status.get("last_api_operation_at")
            or smtp_status.get("last_tested_at"),
            "token_expiry": oauth_status.get("token_expiry"),
        }

    # =========================================================================
    # Helper: Raw SMTP Credentials Retrieval
    # =========================================================================
    @classmethod
    async def get_smtp_credentials(
        cls, organization_id: uuid.UUID | str | None = None
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"
        settings = get_settings()

        smtp_mem_key = f"{org_str}:smtp"
        if smtp_mem_key in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[smtp_mem_key]
            if mem.get("sender_email") and mem.get("app_password"):
                return {
                    "sender_email": mem["sender_email"],
                    "app_password": mem["app_password"],
                    "host": mem.get("smtp_host", "smtp.gmail.com"),
                    "port": mem.get("smtp_port", 587),
                    "recipient_email": mem.get("recipient_email"),
                }

        if organization_id and str(organization_id) != "org-default":
            try:
                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                org_uuid = uuid.UUID(str(organization_id))
                session_factory = get_session_factory()
                async with session_factory() as db:
                    stmt = (
                        sa.select(IntegrationCredential)
                        .where(
                            IntegrationCredential.organization_id == org_uuid,
                            IntegrationCredential.name.in_(["gmail_smtp", "gmail"]),
                            IntegrationCredential.credential_type == "smtp",
                        )
                        .order_by(IntegrationCredential.created_at.desc())
                    )
                    cred = (await db.scalars(stmt)).first()
                    if cred and cred.encrypted_payload:
                        decrypted_str = CredentialVault.decrypt_secret(
                            cred.encrypted_payload, str(org_uuid)
                        )
                        payload = json.loads(decrypted_str)
                        if payload.get("sender_email") and payload.get("app_password"):
                            _IN_MEMORY_CREDENTIALS[smtp_mem_key] = payload
                            return {
                                "sender_email": payload["sender_email"],
                                "app_password": payload["app_password"],
                                "host": payload.get("smtp_host", "smtp.gmail.com"),
                                "port": payload.get("smtp_port", 587),
                                "recipient_email": payload.get("recipient_email"),
                            }
            except Exception as e:
                logger.debug("failed_to_query_smtp_db_creds", error=str(e))

        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
                    file_cfg = json.load(f)
                    if (
                        file_cfg.get("auth_type") == "smtp" or file_cfg.get("app_password")
                    ) and file_cfg.get("sender_email"):
                        app_pass = file_cfg.get("app_password")
                        enc_p = file_cfg.get("encrypted_payload")
                        if not app_pass and enc_p and organization_id:
                            try:
                                dec_str = CredentialVault.decrypt_secret(
                                    enc_p, str(organization_id)
                                )
                                app_pass = json.loads(dec_str).get("app_password")
                            except Exception:
                                pass
                        if app_pass:
                            return {
                                "sender_email": file_cfg["sender_email"],
                                "app_password": app_pass,
                                "host": file_cfg.get("smtp_host", "smtp.gmail.com"),
                                "port": file_cfg.get("smtp_port", 587),
                                "recipient_email": file_cfg.get("recipient_email"),
                            }
            except Exception:
                pass

        env_sender = (
            os.environ.get("GMAIL_SENDER_EMAIL")
            or os.environ.get("GMAIL_USER")
            or settings.gmail_sender_email
        )
        if env_sender:
            env_sender = env_sender.strip().strip("'\"")
        env_pass = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASSWORD")
        if env_pass:
            env_pass = env_pass.strip().strip("'\"")

        if env_sender and env_pass:
            return {
                "sender_email": env_sender,
                "app_password": env_pass,
                "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.environ.get("SMTP_PORT", 587)),
                "recipient_email": os.environ.get("GMAIL_RECIPIENT_EMAIL"),
            }

        return {}

    # =========================================================================
    # SMTP Connection Verification & Test Endpoint
    # =========================================================================
    @classmethod
    async def test_smtp_connection(
        cls,
        organization_id: uuid.UUID | str | None = None,
        test_recipient: str | None = None,
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"
        creds = await cls.get_smtp_credentials(organization_id)
        sender = creds.get("sender_email")
        password = creds.get("app_password")
        host = creds.get("host", "smtp.gmail.com")
        port = int(creds.get("port", 587))

        if not (sender and password):
            err_msg = "SMTP credentials not configured. Please provide a Gmail sender address and 16-character App Password."
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": datetime.now(UTC).isoformat(),
                "last_error": err_msg,
            }
            return {"success": False, "error": err_msg}

        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(sender, password)

                if test_recipient:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = "[AURA] SMTP Connection Test"
                    msg["From"] = f"AURA Platform <{sender}>"
                    msg["To"] = test_recipient
                    msg.attach(
                        MIMEText(
                            f"AURA SMTP connection verified at {datetime.now(UTC).isoformat()}.",
                            "plain",
                        )
                    )
                    server.sendmail(sender, [test_recipient], msg.as_string())

            now_iso = datetime.now(UTC).isoformat()
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": now_iso,
                "last_delivery_at": now_iso
                if test_recipient
                else cls._SMTP_METADATA.get(org_str, {}).get("last_delivery_at"),
                "last_error": None,
            }
            cls._record_delivery_log(
                event="SMTP_TEST",
                recipient=test_recipient or sender,
                status="SUCCESS",
                details=f"SMTP authentication verified with {host}:{port} for {sender}.",
            )
            return {
                "success": True,
                "message": f"SMTP connection verified successfully for {sender}.",
                "host": host,
                "port": port,
                "sender": sender,
                "tested_at": now_iso,
            }
        except smtplib.SMTPAuthenticationError as auth_err:
            err_msg = f"Gmail SMTP authentication failed: Ensure 2-Step Verification is active and use a 16-character App Password. ({auth_err})"
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": datetime.now(UTC).isoformat(),
                "last_error": err_msg,
            }
            return {"success": False, "error": err_msg}
        except Exception as e:
            err_msg = f"SMTP connection error ({host}:{port}): {e}"
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": datetime.now(UTC).isoformat(),
                "last_error": err_msg,
            }
            return {"success": False, "error": err_msg}

    # =========================================================================
    # Diagnostic Test Email Dispatcher (Multi-Channel Capable)
    # =========================================================================
    @classmethod
    async def send_test_email(
        cls,
        recipient: str,
        organization_id: uuid.UUID | str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"

        if os.environ.get("RESEND_API_KEY"):
            from app.services.email_service import EmailNotificationService

            now_txt = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            try:
                message_id = await EmailNotificationService._send_via_resend(
                    recipient,
                    "[AURA Test] Email delivery verification",
                    f"<p>This is a test email from AURA, sent over Resend at {now_txt}.</p>"
                    "<p>If you can read this, approval emails can reach you.</p>",
                    f"This is a test email from AURA, sent over Resend at {now_txt}.",
                )
                return {
                    "delivered": True,
                    "status": "DELIVERED",
                    "provider": "Resend",
                    "message_id": message_id,
                    "recipient": recipient,
                }
            except Exception as e:  # surface Resend's real answer, never a generic one
                return {
                    "delivered": False,
                    "status": "FAILED",
                    "provider": "Resend",
                    "recipient": recipient,
                    "error": f"Resend rejected the email: {e}",
                }

        oauth_status = await cls.get_oauth_status(organization_id)
        smtp_status = await cls.get_smtp_status(organization_id)

        if not oauth_status["connected"] and not smtp_status["configured"]:
            return {
                "delivered": False,
                "status": "FAILED",
                "recipient": recipient,
                "error": "No email delivery method is configured. Authorize with Google OAuth 2.0 or set up an App Password (SMTP).",
            }

        subject = "[AURA Test] Gmail Delivery Verification"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Try Gmail REST API if OAuth is connected
        if oauth_status["connected"]:
            body_text = (
                f"This is an automated test email from your AURA Platform.\n"
                f"Delivery Transport: Gmail REST API (Google OAuth 2.0)\n"
                f"Scope: {cls.REQUIRED_SCOPE}\n"
                f"Timestamp: {now_str}\n"
                f"Status: Operational.\n"
            )
            body_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; padding: 24px; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <h2 style="color: #2563eb; margin-top: 0;">AURA Gmail Delivery Test</h2>
    <p>Your Gmail integration is active and operating normally.</p>
    <div style="background: #f1f5f9; padding: 14px 18px; border-radius: 8px; font-family: ui-monospace, Menlo, Monaco, Consolas, monospace; font-size: 12px; line-height: 1.6;">
      <strong>Status:</strong> DELIVERED<br>
      <strong>Transport:</strong> Gmail REST API (Google OAuth 2.0)<br>
      <strong>Sender:</strong> {oauth_status.get("authorized_account") or "Authorized Account"}<br>
      <strong>Recipient:</strong> {recipient}<br>
      <strong>Scope:</strong> {cls.REQUIRED_SCOPE}<br>
      <strong>Timestamp:</strong> {now_str}
    </div>
  </div>
</body>
</html>"""
            try:
                res = await cls.send_gmail_api_message(
                    organization_id=org_str,
                    recipient=recipient,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    idempotency_key=f"test_email_{uuid.uuid4().hex[:8]}",
                    client=client,
                )
                cls._OAUTH_METADATA[org_str] = {
                    "last_api_operation_at": datetime.now(UTC).isoformat(),
                    "last_error": None,
                }
                res["delivery_provider"] = (
                    "Gmail REST API (https://www.googleapis.com/auth/gmail.send)"
                )
                return res
            except Exception as e:
                logger.warning("gmail_api_test_email_failed_trying_smtp", error=str(e))
                cls._OAUTH_METADATA[org_str] = {
                    "last_api_operation_at": datetime.now(UTC).isoformat(),
                    "last_error": str(e),
                }

        # 2. SMTP Transport
        smtp_creds = await cls.get_smtp_credentials(organization_id)
        sender = smtp_creds.get("sender_email")
        password = smtp_creds.get("app_password")
        host = smtp_creds.get("host", "smtp.gmail.com")
        port = int(smtp_creds.get("port", 587))

        if not (sender and password):
            return {
                "delivered": False,
                "status": "FAILED",
                "recipient": recipient,
                "error": "SMTP credentials not configured on server.",
            }

        body_text = (
            f"This is an automated test email from your AURA Platform.\n"
            f"Delivery Transport: Gmail SMTP ({host}:{port})\n"
            f"Timestamp: {now_str}\n"
            f"Status: Operational.\n"
        )
        body_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; padding: 24px; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <h2 style="color: #2563eb; margin-top: 0;">AURA Gmail Delivery Test</h2>
    <p>Your Gmail integration is active and operating normally.</p>
    <div style="background: #f1f5f9; padding: 14px 18px; border-radius: 8px; font-family: ui-monospace, Menlo, Monaco, Consolas, monospace; font-size: 12px; line-height: 1.6;">
      <strong>Status:</strong> DELIVERED<br>
      <strong>Transport:</strong> Gmail SMTP ({host}:{port})<br>
      <strong>Sender:</strong> {sender}<br>
      <strong>Recipient:</strong> {recipient}<br>
      <strong>Timestamp:</strong> {now_str}
    </div>
  </div>
</body>
</html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AURA Enterprise Platform <{sender}>"
        msg["To"] = recipient
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())

            now_iso = datetime.now(UTC).isoformat()
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": now_iso,
                "last_delivery_at": now_iso,
                "last_error": None,
            }
            cls._record_delivery_log(
                event="SMTP_TEST_EMAIL",
                recipient=recipient,
                status="DELIVERED",
                details=f"Test email delivered to {recipient} via Gmail SMTP.",
            )
            return {
                "delivered": True,
                "status": "DELIVERED",
                "recipient": recipient,
                "delivery_provider": f"Gmail SMTP ({host}:{port})",
                "sender_email": sender,
                "timestamp": now_iso,
            }
        except Exception as e:
            cls._SMTP_METADATA[org_str] = {
                "last_tested_at": datetime.now(UTC).isoformat(),
                "last_error": str(e),
            }
            return {
                "delivered": False,
                "status": "FAILED",
                "recipient": recipient,
                "error": f"SMTP delivery failed: {e}",
            }

    # =========================================================================
    # Legacy Compatibility Get Config
    # =========================================================================
    @classmethod
    def get_config(cls, organization_id: uuid.UUID | str | None = None) -> dict[str, Any]:
        settings = get_settings()
        client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else os.environ.get("GOOGLE_CLIENT_SECRET")
        )
        if not (client_id and client_secret):
            get_settings.cache_clear()
            settings = get_settings()
            client_id = settings.google_client_id or os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = (
                settings.google_client_secret.get_secret_value()
                if settings.google_client_secret
                else os.environ.get("GOOGLE_CLIENT_SECRET")
            )

        org_str = str(organization_id) if organization_id else "org-default"
        cfg = {
            "auth_type": "none",
            "connected": False,
            "sender_email": None,
            "connected_email": None,
            "recipient_email": os.environ.get("GMAIL_RECIPIENT_EMAIL")
            or os.environ.get("AURA_APPROVAL_EMAIL"),
            "smtp_host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
            "oauth_configured": bool(client_id and client_secret),
            "token_expiry": None,
            "last_verified_at": None,
            "last_test_email_at": None,
            "scope": cls.REQUIRED_SCOPE,
            "permission_granted": f"Gmail send permission only ({cls.REQUIRED_SCOPE})",
            "organization_id": org_str,
        }

        if org_str in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[org_str]
            cfg["sender_email"] = mem.get("sender_email")
            cfg["connected_email"] = mem.get("sender_email")
            cfg["auth_type"] = mem.get("auth_type", "oauth2")
            cfg["connected"] = True
            cfg["token_expiry"] = mem.get("token_expiry")
            cfg["last_verified_at"] = mem.get("last_verified_at")
            return cfg

        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
                    file_cfg = json.load(f)
                    sender = file_cfg.get("sender_email")
                    if sender:
                        cfg["sender_email"] = sender
                        cfg["connected_email"] = sender
                        cfg["auth_type"] = file_cfg.get("auth_type", "oauth2")
                        cfg["connected"] = True
                        cfg["token_expiry"] = file_cfg.get("token_expiry")
                        cfg["last_verified_at"] = file_cfg.get("last_verified_at")
            except Exception:
                pass

        env_sender = (
            os.environ.get("GMAIL_SENDER_EMAIL")
            or os.environ.get("GMAIL_USER")
            or settings.gmail_sender_email
        )
        env_pass = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASSWORD")
        if env_sender:
            env_sender = env_sender.strip().strip("'\"")
        if env_pass:
            env_pass = env_pass.strip().strip("'\"")

        if not cfg["connected"] and env_sender and env_pass:
            cfg["sender_email"] = env_sender
            cfg["connected_email"] = env_sender
            cfg["connected"] = True
            cfg["auth_type"] = "smtp"

        return cfg

    @classmethod
    async def get_tenant_config(
        cls, organization_id: uuid.UUID | str | None = None
    ) -> dict[str, Any]:
        cfg = cls.get_config(organization_id)
        org_str = str(organization_id) if organization_id else "org-default"

        oauth_mem_key = f"{org_str}:oauth2"
        if oauth_mem_key in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[oauth_mem_key]
            cfg["sender_email"] = mem.get("sender_email")
            cfg["connected_email"] = mem.get("sender_email")
            cfg["auth_type"] = "oauth2"
            cfg["connected"] = True
            cfg["token_expiry"] = mem.get("token_expiry")
            cfg["last_verified_at"] = mem.get("last_verified_at")
            cfg["_decrypted_access_token"] = mem.get("access_token")
            cfg["_decrypted_refresh_token"] = mem.get("refresh_token")
            return cfg

        smtp_mem_key = f"{org_str}:smtp"
        if smtp_mem_key in _IN_MEMORY_CREDENTIALS:
            mem = _IN_MEMORY_CREDENTIALS[smtp_mem_key]
            cfg["sender_email"] = mem.get("sender_email")
            cfg["connected_email"] = mem.get("sender_email")
            cfg["auth_type"] = "smtp"
            cfg["connected"] = True
            cfg["_decrypted_password"] = mem.get("app_password")
            return cfg

        if not organization_id or str(organization_id) == "org-default":
            return cfg

        try:
            import sqlalchemy as sa

            from app.database.base import get_session_factory
            from app.database.models import IntegrationCredential

            org_uuid = uuid.UUID(str(organization_id))
            session_factory = get_session_factory()
            async with session_factory() as db:
                stmt = (
                    sa.select(IntegrationCredential)
                    .where(
                        IntegrationCredential.organization_id == org_uuid,
                        IntegrationCredential.name.in_(["gmail_oauth", "gmail_smtp", "gmail"]),
                    )
                    .order_by(IntegrationCredential.created_at.desc())
                )
                creds = (await db.scalars(stmt)).all()
                for cred in creds:
                    if cred.encrypted_payload:
                        decrypted_str = CredentialVault.decrypt_secret(
                            cred.encrypted_payload, str(org_uuid)
                        )
                        payload = json.loads(decrypted_str)
                        if cred.credential_type == "oauth2" and not cfg.get(
                            "_decrypted_access_token"
                        ):
                            cfg["sender_email"] = payload.get("sender_email")
                            cfg["connected_email"] = payload.get("sender_email")
                            cfg["auth_type"] = "oauth2"
                            cfg["connected"] = True
                            cfg["token_expiry"] = payload.get("token_expiry")
                            cfg["last_verified_at"] = payload.get("last_verified_at")
                            cfg["_decrypted_access_token"] = payload.get("access_token")
                            cfg["_decrypted_refresh_token"] = payload.get("refresh_token")
                            _IN_MEMORY_CREDENTIALS[oauth_mem_key] = payload
                        elif cred.credential_type == "smtp" and not cfg.get("_decrypted_password"):
                            cfg["_decrypted_password"] = payload.get("app_password")
                            _IN_MEMORY_CREDENTIALS[smtp_mem_key] = payload
        except Exception as e:
            logger.debug("failed_to_load_tenant_gmail_credential_db", error=str(e))

        return cfg

    # =========================================================================
    # Disconnect & Revoke (Channel-Aware)
    # =========================================================================
    @classmethod
    async def disconnect(
        cls,
        organization_id: uuid.UUID | str | None = None,
        method: str = "all",
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        org_str = str(organization_id) if organization_id else "org-default"

        if method in ["oauth", "all"]:
            oauth_mem_key = f"{org_str}:oauth2"
            mem = _IN_MEMORY_CREDENTIALS.get(oauth_mem_key, {})
            token_to_revoke = mem.get("refresh_token") or mem.get("access_token")

            if token_to_revoke:
                owns_client = False
                if client is None:
                    client = httpx.AsyncClient(timeout=10.0)
                    owns_client = True
                try:
                    await client.post(cls.GOOGLE_REVOKE_URL, params={"token": token_to_revoke})
                except Exception as e:
                    logger.warning("failed_to_revoke_google_token", error=str(e))
                finally:
                    if owns_client:
                        await client.aclose()

            _IN_MEMORY_CREDENTIALS.pop(oauth_mem_key, None)
            if (
                org_str in _IN_MEMORY_CREDENTIALS
                and _IN_MEMORY_CREDENTIALS[org_str].get("auth_type") == "oauth2"
            ):
                _IN_MEMORY_CREDENTIALS.pop(org_str, None)
            cls._OAUTH_METADATA.pop(org_str, None)

            try:
                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                if organization_id and org_str != "org-default":
                    org_uuid = uuid.UUID(org_str)
                    session_factory = get_session_factory()
                    async with session_factory() as db:
                        await db.execute(
                            sa.delete(IntegrationCredential).where(
                                IntegrationCredential.organization_id == org_uuid,
                                IntegrationCredential.name.in_(["gmail_oauth", "gmail"]),
                                IntegrationCredential.credential_type == "oauth2",
                            )
                        )
                        await db.commit()
            except Exception as e:
                logger.debug("failed_to_delete_oauth_db_credential", error=str(e))

        if method in ["smtp", "all"]:
            smtp_mem_key = f"{org_str}:smtp"
            _IN_MEMORY_CREDENTIALS.pop(smtp_mem_key, None)
            if (
                org_str in _IN_MEMORY_CREDENTIALS
                and _IN_MEMORY_CREDENTIALS[org_str].get("auth_type") == "smtp"
            ):
                _IN_MEMORY_CREDENTIALS.pop(org_str, None)
            cls._SMTP_METADATA.pop(org_str, None)

            try:
                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                if organization_id and org_str != "org-default":
                    org_uuid = uuid.UUID(org_str)
                    session_factory = get_session_factory()
                    async with session_factory() as db:
                        await db.execute(
                            sa.delete(IntegrationCredential).where(
                                IntegrationCredential.organization_id == org_uuid,
                                IntegrationCredential.name.in_(["gmail_smtp", "gmail"]),
                                IntegrationCredential.credential_type == "smtp",
                            )
                        )
                        await db.commit()
            except Exception as e:
                logger.debug("failed_to_delete_smtp_db_credential", error=str(e))

        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
                    file_data = json.load(f)
                file_org = file_data.get("organization_id")
                if not organization_id or (file_org and str(file_org) == org_str):
                    os.remove(CONFIG_FILE_PATH)
            except Exception:
                pass

        cls._record_delivery_log(
            event=f"GMAIL_DISCONNECTED_{method.upper()}",
            recipient="",
            status="DISCONNECTED",
            details=f"Disconnected {method} integration channel.",
        )

        return {
            "status": "DISCONNECTED",
            "method": method,
            "message": f"Successfully disconnected {method} integration.",
        }

    # =========================================================================
    # Approval Request Notification Dispatcher
    # =========================================================================
    @classmethod
    async def dispatch_approval_request(
        cls,
        approval_id: uuid.UUID,
        tool_name: str,
        action_summary: str,
        action_details: dict[str, Any],
        reason: str | None = None,
        recipient_email: str | None = None,
        agent_run_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        from app.services.email_service import EmailNotificationService

        smtp_status = await cls.get_smtp_status(organization_id)
        oauth_status = await cls.get_oauth_status(organization_id)
        target = (
            recipient_email
            or smtp_status.get("recipient_email")
            or os.environ.get("GMAIL_RECIPIENT_EMAIL")
            or os.environ.get("AURA_APPROVAL_EMAIL")
        )

        if not target:
            raise ValueError("No recipient email specified for human approval notification.")

        result = await EmailNotificationService.send_approval_request_email(
            approval_id=approval_id,
            tool_name=tool_name,
            action_summary=action_summary,
            action_details=action_details,
            reason=reason,
            recipient_email=target,
            agent_run_id=agent_run_id,
            organization_id=organization_id,
        )

        cls._record_delivery_log(
            event="APPROVAL_REQUEST_SENT",
            recipient=target,
            status="SENT"
            if (result.get("smtp_delivered") or result.get("gmail_api_delivered"))
            else "STAGED",
            details=f"Approval request for '{action_summary}' dispatched. Delivery: {result.get('delivery_provider', 'Staged')}.",
        )

        return result

    # =========================================================================
    # Delivery Logs
    # =========================================================================
    @classmethod
    def _record_delivery_log(cls, event: str, recipient: str, status: str, details: str):
        entry = {
            "id": f"log_{uuid.uuid4().hex[:8]}",
            "event": event,
            "recipient": recipient,
            "status": status,
            "details": details,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        _DELIVERY_LOGS.insert(0, entry)
        if len(_DELIVERY_LOGS) > 40:
            _DELIVERY_LOGS.pop()

    @classmethod
    def get_delivery_logs(cls) -> list[dict[str, Any]]:
        return list(_DELIVERY_LOGS)

    # =========================================================================
    # SMTP Configuration Persistence
    # =========================================================================
    @classmethod
    def save_smtp_config(
        cls,
        sender_email: str,
        app_password: str,
        recipient_email: str,
        organization_id: uuid.UUID | str = "org-default",
    ) -> dict[str, Any]:
        clean_sender = sender_email.strip()
        clean_pass = app_password.replace(" ", "").strip()
        clean_recipient = recipient_email.strip()
        org_str = str(organization_id)
        now_iso = datetime.now(UTC).isoformat()

        payload_data = {
            "auth_type": "smtp",
            "sender_email": clean_sender,
            "app_password": clean_pass,
            "recipient_email": clean_recipient,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "last_verified_at": now_iso,
        }
        enc_payload = CredentialVault.encrypt_secret(json.dumps(payload_data), org_str).hex()

        # 1. Update in-memory
        _IN_MEMORY_CREDENTIALS[f"{org_str}:smtp"] = payload_data
        _IN_MEMORY_CREDENTIALS[org_str] = payload_data
        cls._SMTP_METADATA[org_str] = {
            "last_tested_at": now_iso,
            "last_error": None,
        }

        # 2. Update config file
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "auth_type": "smtp",
                        "sender_email": clean_sender,
                        "organization_id": org_str,
                        "recipient_email": clean_recipient,
                        "smtp_host": "smtp.gmail.com",
                        "smtp_port": 587,
                        "last_verified_at": now_iso,
                        "encrypted_payload": enc_payload,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning("failed_to_write_smtp_config_file", error=str(e))

        # 3. Update database
        if organization_id and org_str != "org-default":
            try:
                import asyncio

                import sqlalchemy as sa

                from app.database.base import get_session_factory
                from app.database.models import IntegrationCredential

                async def _save_db():
                    try:
                        org_uuid = uuid.UUID(org_str)
                        session_factory = get_session_factory()
                        async with session_factory() as db:
                            stmt = sa.select(IntegrationCredential).where(
                                IntegrationCredential.organization_id == org_uuid,
                                IntegrationCredential.name.in_(["gmail_smtp", "gmail"]),
                                IntegrationCredential.credential_type == "smtp",
                            )
                            existing = (await db.scalars(stmt)).first()
                            if existing:
                                existing.name = "gmail_smtp"
                                existing.credential_type = "smtp"
                                existing.encrypted_payload = enc_payload
                            else:
                                new_cred = IntegrationCredential(
                                    organization_id=org_uuid,
                                    name="gmail_smtp",
                                    credential_type="smtp",
                                    encrypted_payload=enc_payload,
                                )
                                db.add(new_cred)
                            await db.commit()
                    except Exception as err:
                        logger.debug("failed_to_persist_smtp_db_task", error=str(err))

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_save_db())
                except RuntimeError:
                    asyncio.run(_save_db())
            except Exception as e:
                logger.debug("failed_to_persist_smtp_db", error=str(e))

        cls._record_delivery_log(
            event="GMAIL_CONFIGURED",
            recipient=clean_recipient,
            status="SUCCESS",
            details=f"SMTP authenticated and stored encrypted in CredentialVault for {clean_sender}.",
        )

        return {
            "status": "CONFIGURED",
            "sender_email": clean_sender,
            "recipient_email": clean_recipient,
            "auth_type": "smtp",
        }
