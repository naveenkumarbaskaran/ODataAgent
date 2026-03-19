"""OData query builder — constructs $filter, $select, $expand, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote


@dataclass
class QueryBuilder:
    """
    Builds OData query URLs from structured parameters.

    Handles differences between V2 and V4 syntax:
    - V2: $format=json, string values in single quotes
    - V4: Native JSON, function syntax for contains/startswith
    """

    entity: str
    version: str = "v4"
    filter_dict: dict[str, Any] | None = None
    select: list[str] | None = None
    expand: list[str] | None = None
    orderby: str | None = None
    top: int | None = None
    skip: int | None = None

    def build_path(self) -> str:
        """Build the relative URL path with query parameters."""
        parts = [self.entity]
        params = []

        if self.filter_dict:
            params.append(f"$filter={self._build_filter()}")

        if self.select:
            params.append(f"$select={','.join(self.select)}")

        if self.expand:
            params.append(f"$expand={','.join(self.expand)}")

        if self.orderby:
            params.append(f"$orderby={self.orderby}")

        if self.top is not None:
            params.append(f"$top={self.top}")

        if self.skip is not None:
            params.append(f"$skip={self.skip}")

        if self.version == "v2":
            params.append("$format=json")

        path = self.entity
        if params:
            path += "?" + "&".join(params)

        return path

    def _build_filter(self) -> str:
        """Convert filter dict to OData $filter expression."""
        if not self.filter_dict:
            return ""

        clauses = []
        for key, value in self.filter_dict.items():
            if isinstance(value, str):
                clauses.append(f"{key} eq '{value}'")
            elif isinstance(value, bool):
                clauses.append(f"{key} eq {str(value).lower()}")
            elif isinstance(value, (int, float)):
                clauses.append(f"{key} eq {value}")
            elif isinstance(value, list):
                # OR clause for multiple values
                or_parts = []
                for v in value:
                    if isinstance(v, str):
                        or_parts.append(f"{key} eq '{v}'")
                    else:
                        or_parts.append(f"{key} eq {v}")
                clauses.append(f"({' or '.join(or_parts)})")
            elif isinstance(value, dict):
                # Operators: {"gt": 5, "lt": 10}
                for op, val in value.items():
                    if isinstance(val, str):
                        clauses.append(f"{key} {op} '{val}'")
                    else:
                        clauses.append(f"{key} {op} {val}")

        return " and ".join(clauses)


def build_filter_string(filters: dict[str, Any], version: str = "v4") -> str:
    """Standalone filter builder."""
    builder = QueryBuilder(entity="", version=version, filter_dict=filters)
    return builder._build_filter()
