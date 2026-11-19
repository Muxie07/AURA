import uuid
from typing import Any

import httpx
import structlog

from app.tools.registry import ToolRegistry
from app.tools.utcp.executor import UTCPToolExecutor
from app.tools.utcp.parser import UTCPManifestParser

logger = structlog.get_logger(__name__)


class UTCPClientManager:
    """Manages active UTCP tool endpoints, remote manifest discovery, and registry synchronisation."""

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry
        # Cache key: (organization_id, endpoint_url) -> list[UTCPToolExecutor]
        self._cache: dict[tuple[str, str], list[UTCPToolExecutor]] = {}

    async def register_manifest(
        self,
        organization_id: uuid.UUID | str,
        manifest_data: str | dict[str, Any],
        registry: ToolRegistry | None = None,
        allow_local_dev: bool = True,
    ) -> list[UTCPToolExecutor]:
        manifest = UTCPManifestParser.parse_manifest_data(manifest_data)
        executors = UTCPManifestParser.create_executors(manifest, allow_local_dev=allow_local_dev)

        target_registry = registry or self.registry
        for executor in executors:
            if target_registry:
                # If tool already registered, replace it or update
                if executor.definition.name in target_registry._tools:
                    target_registry._tools[executor.definition.name] = executor
                else:
                    target_registry.register(executor)

        cache_key = (str(organization_id), manifest.base_url)
        self._cache[cache_key] = executors
        logger.info(
            "utcp.manager.registered",
            org_id=str(organization_id),
            tools=[e.definition.name for e in executors],
        )
        return executors

    async def fetch_and_register_remote(
        self,
        organization_id: uuid.UUID | str,
        manifest_url: str,
        auth_headers: dict[str, str] | None = None,
        registry: ToolRegistry | None = None,
        allow_local_dev: bool = True,
    ) -> list[UTCPToolExecutor]:
        headers = auth_headers or {}
        headers["User-Agent"] = "AURA-UTCP-Client/1.0"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(manifest_url, headers=headers)
            resp.raise_for_status()
            raw_text = resp.text

        return await self.register_manifest(
            organization_id=organization_id,
            manifest_data=raw_text,
            registry=registry,
            allow_local_dev=allow_local_dev,
        )

    def list_cached_tools(self, organization_id: uuid.UUID | str) -> list[UTCPToolExecutor]:
        result = []
        for (org_key, _), executors in self._cache.items():
            if org_key == str(organization_id):
                result.extend(executors)
        return result
