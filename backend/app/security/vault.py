import base64
import hashlib
import os
import uuid

from cryptography.fernet import Fernet

from app.config.settings import get_settings


def _derive_tenant_fernet_key(organization_id: uuid.UUID | str) -> bytes:
    """
    Derives a cryptographically strong, tenant-isolated Fernet key using SHA-256 HKDF-like construction.
    Key material is sourced from AURA_ENCRYPTION_KEY or AURA_SECRET_KEY, salted with the organization ID.
    """
    settings = get_settings()
    enc_key = os.environ.get("AURA_ENCRYPTION_KEY")
    if enc_key and enc_key.strip():
        master_secret = enc_key.strip().encode("utf-8")
    else:
        master_secret = settings.aura_secret_key.get_secret_value().encode("utf-8")

    if not master_secret:
        raise ValueError(
            "Encryption key not configured: set AURA_ENCRYPTION_KEY or AURA_SECRET_KEY."
        )

    salt = str(organization_id).encode("utf-8")
    derived = hashlib.sha256(master_secret + b":" + salt).digest()
    return base64.urlsafe_b64encode(derived)


class CredentialVault:
    """Provides authenticated tenant-scoped symmetric encryption for external tool secrets."""

    @staticmethod
    def encrypt_secret(plaintext: str, organization_id: uuid.UUID | str) -> bytes:
        key = _derive_tenant_fernet_key(organization_id)
        f = Fernet(key)
        return f.encrypt(plaintext.encode("utf-8"))

    @staticmethod
    def decrypt_secret(ciphertext: bytes, organization_id: uuid.UUID | str) -> str:
        key = _derive_tenant_fernet_key(organization_id)
        f = Fernet(key)
        return f.decrypt(ciphertext).decode("utf-8")
