import json
from typing import Any

import structlog
import yaml  # type: ignore

from app.tools.schemas import RiskLevel, ToolDefinition, ToolSource
from app.tools.utcp.executor import UTCPToolExecutor
from app.tools.utcp.schemas import UTCPManifest

logger = structlog.get_logger(__name__)


class UTCPManifestParser:
    """Parses raw JSON, dict, or YAML UTCP manifests into executable ToolDefinition and UTCPToolExecutor instances."""

    @staticmethod
    def parse_manifest_data(raw_data: str | dict[str, Any]) -> UTCPManifest:
        if isinstance(raw_data, str):
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                data = yaml.safe_load(raw_data)
        else:
            data = raw_data

        return UTCPManifest.model_validate(data)

    @classmethod
    def create_executors(
        cls,
        manifest: UTCPManifest,
        allow_local_dev: bool = True,
    ) -> list[UTCPToolExecutor]:
        executors: list[UTCPToolExecutor] = []

        for spec in manifest.tools:
            # Tool name follows namespaced convention: utcp.{manifest_name}.{tool_name}
            namespace = manifest.name.strip().lower().replace(" ", "_")
            tool_name = spec.name.strip().lower().replace(" ", "_")
            qualified_name = f"utcp.{namespace}.{tool_name}" if namespace else f"utcp.{tool_name}"

            # Auto-infer risk level if default
            risk = spec.risk_level
            if risk == RiskLevel.READ:
                method_upper = spec.method.upper()
                if method_upper in ("POST", "PUT", "PATCH", "DELETE"):
                    if any(
                        w in tool_name
                        for w in ("create", "update", "delete", "insert", "send", "submit")
                    ):
                        risk = RiskLevel.WRITE

            # Sanitize description (< 500 chars to avoid LLM context bloat)
            clean_desc = (spec.description or "").strip()
            if len(clean_desc) > 500:
                clean_desc = clean_desc[:497] + "..."

            # Ensure valid JSON Schema for inputs
            schema = (
                dict(spec.input_schema)
                if spec.input_schema
                else {"type": "object", "properties": {}}
            )
            if "type" not in schema:
                schema["type"] = "object"

            definition = ToolDefinition(
                name=qualified_name,
                version=manifest.utcp_version,
                description=clean_desc,
                input_schema=schema,
                output_schema=spec.output_schema,
                risk_level=risk,
                requires_approval=(risk == RiskLevel.EXTERNAL_SIDE_EFFECT),
                idempotent=spec.idempotent,
                timeout_seconds=spec.timeout_seconds,
                organization_scoped=True,
                source=ToolSource.UTCP,
            )

            executor = UTCPToolExecutor(
                definition=definition,
                spec=spec,
                base_url=manifest.base_url,
                auth_config=manifest.auth,
                allow_local_dev=allow_local_dev,
            )
            executors.append(executor)

        logger.info("utcp.manifest_parsed", namespace=manifest.name, tools_count=len(executors))
        return executors
