from typing import Any

import httpx
import structlog

from app.tools.errors import ToolExecutionError, ToolTimeoutError
from app.tools.executor import BaseToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult
from app.tools.utcp.schemas import UTCPAuthConfig, UTCPAuthType, UTCPToolSpec
from app.tools.utcp.security import SSRFGuard

logger = structlog.get_logger(__name__)


class UTCPToolExecutor(BaseToolExecutor):
    """Executes a native HTTP tool described by a UTCP tool specification."""

    def __init__(
        self,
        definition: ToolDefinition,
        spec: UTCPToolSpec,
        base_url: str,
        auth_config: UTCPAuthConfig | None = None,
        allow_local_dev: bool = True,
    ):
        super().__init__(definition)
        self.spec = spec
        self.base_url = base_url.rstrip("/")
        self.auth_config = auth_config or UTCPAuthConfig()
        self.allow_local_dev = allow_local_dev

        # Compute full endpoint URL
        if spec.endpoint.startswith("http://") or spec.endpoint.startswith("https://"):
            self.target_url = spec.endpoint
        else:
            rel = spec.endpoint.lstrip("/")
            self.target_url = f"{self.base_url}/{rel}"

    def _prepare_headers(self, context: ToolContext) -> dict[str, str]:
        headers = dict(self.spec.headers)
        headers["User-Agent"] = "AURA-UTCP-Agent/1.0"
        headers["X-AURA-Org-Id"] = str(context.organization_id)
        if context.agent_run_id:
            headers["X-AURA-Run-Id"] = str(context.agent_run_id)
        if context.execution_id:
            headers["X-AURA-Execution-Id"] = context.execution_id

        # Inject configured authentication
        if self.auth_config.auth_type == UTCPAuthType.BEARER and self.auth_config.token:
            headers["Authorization"] = f"Bearer {self.auth_config.token}"
        elif self.auth_config.auth_type == UTCPAuthType.API_KEY and self.auth_config.token:
            header_name = self.auth_config.header_name or "X-API-Key"
            headers[header_name] = self.auth_config.token
        elif self.auth_config.auth_type == UTCPAuthType.HEADER and self.auth_config.token:
            header_name = self.auth_config.header_name or "Authorization"
            headers[header_name] = self.auth_config.token

        return headers

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        # 1. Dry run simulation (processed prior to external network DNS resolution)
        if context.dry_run:
            if self.definition.risk_level in [RiskLevel.WRITE, RiskLevel.EXTERNAL_SIDE_EFFECT]:
                return ToolResult(
                    status="succeeded",
                    result={
                        "_dry_run": True,
                        "simulated_target": self.target_url,
                        "method": self.spec.method,
                        "message": f"Simulated UTCP execution for {self.definition.name}",
                    },
                )
            if self.definition.risk_level != RiskLevel.READ:
                return ToolResult(status="succeeded", result={"_dry_run": True})

        # 2. SSRF Safety Verification
        SSRFGuard.validate_url(self.target_url, allow_local_dev=self.allow_local_dev)

        # 3. Clean arguments of internal metadata
        clean_args = {k: v for k, v in arguments.items() if not k.startswith("_")}
        headers = self._prepare_headers(context)
        method = self.spec.method.upper()

        auth = None
        if self.auth_config.auth_type == UTCPAuthType.BASIC and self.auth_config.username:
            auth = (self.auth_config.username, self.auth_config.password or "")

        timeout = httpx.Timeout(self.definition.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(
                timeout=timeout, auth=auth, follow_redirects=True
            ) as client:
                if method == "GET":
                    response = await client.get(self.target_url, params=clean_args, headers=headers)
                elif method == "POST":
                    response = await client.post(self.target_url, json=clean_args, headers=headers)
                elif method == "PUT":
                    response = await client.put(self.target_url, json=clean_args, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(
                        self.target_url, params=clean_args, headers=headers
                    )
                else:
                    raise ToolExecutionError(f"Unsupported HTTP method: {method}")

            # Check HTTP Status
            if response.status_code >= 400:
                err_text = response.text[:500]
                return ToolResult(
                    status="failed",
                    error_type="http_error",
                    message=f"UTCP endpoint returned HTTP {response.status_code}: {err_text}",
                    retryable=(response.status_code in (429, 502, 503, 504)),
                )

            # Parse JSON or fallback to text
            try:
                data = response.json()
            except Exception:
                data = {"content": response.text}

            return ToolResult(
                status="succeeded", result=data if isinstance(data, dict) else {"items": data}
            )

        except httpx.TimeoutException as e:
            raise ToolTimeoutError(
                f"UTCP tool {self.definition.name} timed out after {self.definition.timeout_seconds}s"
            ) from e
        except Exception as e:
            logger.error(
                "utcp.execution_error", tool=self.definition.name, url=self.target_url, error=str(e)
            )
            raise ToolExecutionError(
                f"UTCP execution failed for {self.definition.name}: {e}"
            ) from e
