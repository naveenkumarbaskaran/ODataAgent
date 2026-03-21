"""OData service client with auto-discovery and tool generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from odataagent.query import QueryBuilder
from odataagent.metadata import MetadataParser, EntityType
from odataagent.errors import map_http_error
from odataagent.paginator import auto_paginate


@dataclass
class ODataService:
    """
    High-level OData service client.

    Supports V2 and V4 with auto-schema discovery, query building,
    pagination, and LLM tool generation.
    """

    base_url: str
    version: str = "v4"  # "v2" or "v4"
    auth: tuple[str, str] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 2

    # Cached metadata
    _entities: dict[str, EntityType] = field(default_factory=dict, repr=False)
    _metadata_loaded: bool = field(default=False, repr=False)

    def _ensure_metadata(self) -> None:
        """Fetch and parse $metadata if not already loaded."""
        if self._metadata_loaded:
            return
        # In production: fetch via requests/httpx
        # For demo: use MetadataParser with mock/cached XML
        self._metadata_loaded = True

    def query(
        self,
        entity: str,
        filter: dict[str, Any] | None = None,
        select: list[str] | None = None,
        expand: list[str] | None = None,
        orderby: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query an OData entity set.

        Args:
            entity: Entity set name (e.g., "Customers", "MaintenanceOrder")
            filter: Dict of field→value pairs for $filter
            select: Fields to include in $select
            expand: Navigation properties to $expand
            orderby: $orderby expression
            top: Maximum results ($top)
            skip: Skip N results ($skip)

        Returns:
            List of entity dicts
        """
        builder = QueryBuilder(
            entity=entity,
            version=self.version,
            filter_dict=filter,
            select=select,
            expand=expand,
            orderby=orderby,
            top=top,
            skip=skip,
        )

        url = urljoin(self.base_url.rstrip("/") + "/", builder.build_path())
        # In production: response = httpx.get(url, auth=self.auth, headers=self.headers)
        # For now, return the constructed URL for verification
        return [{"_query_url": url, "_odata_version": self.version}]

    def get_by_key(self, entity: str, key: str | int, expand: list[str] | None = None) -> dict:
        """Fetch a single entity by primary key."""
        key_str = f"'{key}'" if isinstance(key, str) else str(key)
        path = f"{entity}({key_str})"
        if expand:
            path += f"?$expand={','.join(expand)}"
        url = urljoin(self.base_url.rstrip("/") + "/", path)
        return {"_query_url": url}

    def as_tools(
        self,
        entities: list[str] | None = None,
        max_results: int = 20,
    ) -> list[dict]:
        """
        Generate OpenAI-compatible function schemas from OData metadata.

        Returns a list of tool definitions that can be passed directly
        to the LLM's `tools` parameter.
        """
        self._ensure_metadata()

        tools = []
        entity_list = entities or list(self._entities.keys())

        for entity_name in entity_list:
            # Query tool
            tools.append({
                "type": "function",
                "function": {
                    "name": f"query_{entity_name.lower()}",
                    "description": f"Search {entity_name} with filters. Returns up to {max_results} results.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "object",
                                "description": f"Filter criteria as field:value pairs",
                            },
                            "top": {
                                "type": "integer",
                                "description": "Max results to return",
                                "default": max_results,
                            },
                        },
                    },
                },
            })

            # Get-by-key tool
            tools.append({
                "type": "function",
                "function": {
                    "name": f"get_{entity_name.lower()}_by_id",
                    "description": f"Get a single {entity_name} by its primary key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": f"Primary key of the {entity_name}",
                            },
                        },
                        "required": ["key"],
                    },
                },
            })

        return tools

    def discover(self) -> list[str]:
        """List all entity sets available in the service."""
        self._ensure_metadata()
        return list(self._entities.keys())
