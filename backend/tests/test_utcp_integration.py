import uuid
import pytest
from app.tools.errors import ToolAuthorizationError, ToolTimeoutError
from app.tools.registry import ToolRegistry
from app.tools.schemas import RiskLevel, ToolContext, ToolSource
from app.tools.utcp.executor import UTCPToolExecutor
from app.tools.utcp.manager import UTCPClientManager
from app.tools.utcp.parser import UTCPManifestParser
from app.tools.utcp.schemas import (
    UTCPAuthConfig,
    UTCPAuthType,
    UTCPManifest,
    UTCPToolSpec,
)
from app.tools.utcp.security import SSRFGuard
from app.security.vault import CredentialVault


def test_ssrf_guard_blocks_private_ips():
    with pytest.raises(ToolAuthorizationError, match="SSRF violation"):
        SSRFGuard.validate_url("http://169.254.169.254/latest/meta-data", allow_local_dev=False)

    with pytest.raises(ToolAuthorizationError, match="SSRF violation"):
        SSRFGuard.validate_url("http://127.0.0.1:8000/api", allow_local_dev=False)

    with pytest.raises(ToolAuthorizationError, match="Invalid URL scheme"):
        SSRFGuard.validate_url("ftp://example.com/file")


def test_ssrf_guard_allows_valid_public_domain():
    # Valid external URL
    url = "https://httpbin.org/get"
    assert SSRFGuard.validate_url(url, allow_local_dev=False) == url


def test_credential_vault_encryption_decryption():
    org_id = uuid.uuid4()
    secret = "sk-live-enterprise-secret-12345"

    encrypted = CredentialVault.encrypt_secret(secret, org_id)
    assert isinstance(encrypted, bytes)
    assert encrypted != secret.encode()

    decrypted = CredentialVault.decrypt_secret(encrypted, org_id)
    assert decrypted == secret

    # Cross-tenant decrypt must fail
    other_org_id = uuid.uuid4()
    with pytest.raises(Exception):
        CredentialVault.decrypt_secret(encrypted, other_org_id)


def test_utcp_manifest_parser():
    sample_manifest = {
        "utcp_version": "1.0.0",
        "name": "payment_gateway",
        "description": "Enterprise Payment Processing Gateway",
        "base_url": "https://api.payments.example.com",
        "auth": {
            "auth_type": "bearer",
            "token": "tok_enterprise_9988"
        },
        "tools": [
            {
                "name": "verify_iban",
                "description": "Verifies bank account IBAN routing code",
                "endpoint": "/v1/iban/verify",
                "method": "POST",
                "risk_level": "READ",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "iban": {"type": "string"}
                    },
                    "required": ["iban"]
                }
            },
            {
                "name": "initiate_settlement",
                "description": "Initiates wire settlement transaction",
                "endpoint": "/v1/settlements/create",
                "method": "POST",
                "risk_level": "EXTERNAL_SIDE_EFFECT",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "currency": {"type": "string"}
                    },
                    "required": ["amount", "currency"]
                }
            }
        ]
    }

    manifest = UTCPManifestParser.parse_manifest_data(sample_manifest)
    assert manifest.name == "payment_gateway"
    assert len(manifest.tools) == 2

    executors = UTCPManifestParser.create_executors(manifest, allow_local_dev=True)
    assert len(executors) == 2

    iban_tool = next(e for e in executors if "verify_iban" in e.definition.name)
    assert iban_tool.definition.source == ToolSource.UTCP
    assert iban_tool.definition.risk_level == RiskLevel.READ
    assert iban_tool.definition.requires_approval is False

    settlement_tool = next(e for e in executors if "initiate_settlement" in e.definition.name)
    assert settlement_tool.definition.risk_level == RiskLevel.EXTERNAL_SIDE_EFFECT
    assert settlement_tool.definition.requires_approval is True


@pytest.mark.asyncio
async def test_utcp_dry_run_simulation():
    spec = UTCPToolSpec(
        name="charge_card",
        description="Charge payment card",
        endpoint="/v1/charge",
        method="POST",
        risk_level=RiskLevel.EXTERNAL_SIDE_EFFECT,
        input_schema={"type": "object", "properties": {"amount": {"type": "number"}}}
    )
    defn = UTCPManifestParser.create_executors(
        UTCPManifest(
            name="billing",
            base_url="https://api.billing.example.com",
            tools=[spec]
        ),
        allow_local_dev=True
    )[0]

    ctx = ToolContext(
        organization_id=uuid.uuid4(),
        execution_id="exec-1234",
        dry_run=True,
    )

    res = await defn.execute({"amount": 100}, ctx)
    assert res.status == "succeeded"
    assert res.result.get("_dry_run") is True


@pytest.mark.asyncio
async def test_utcp_client_manager_registration():
    registry = ToolRegistry()
    manager = UTCPClientManager(registry=registry)
    org_id = uuid.uuid4()

    sample_manifest = {
        "utcp_version": "1.0.0",
        "name": "crm_sync",
        "base_url": "https://api.crm.example.com",
        "tools": [
            {
                "name": "lookup_contact",
                "endpoint": "/contacts/lookup",
                "method": "GET",
                "input_schema": {"type": "object", "properties": {"email": {"type": "string"}}}
            }
        ]
    }

    executors = await manager.register_manifest(org_id, sample_manifest, allow_local_dev=True)
    assert len(executors) == 1
    assert "utcp.crm_sync.lookup_contact" in registry._tools

    tool = registry.get("utcp.crm_sync.lookup_contact")
    assert tool.definition.source == ToolSource.UTCP
