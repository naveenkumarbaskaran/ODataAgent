"""OData result pagination handlers."""

from __future__ import annotations

from typing import Any, Callable


def auto_paginate(
    fetch_fn: Callable[[str], dict[str, Any]],
    initial_url: str,
    version: str = "v4",
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """
    Automatically paginate through OData results.

    V4: Follows @odata.nextLink
    V2: Increments $skip by page size

    Args:
        fetch_fn: Function that takes a URL and returns the JSON response
        initial_url: Starting query URL
        version: OData version ("v2" or "v4")
        max_pages: Safety limit on pages fetched

    Returns:
        Combined list of all results
    """
    all_results: list[dict[str, Any]] = []
    url = initial_url
    pages = 0

    while url and pages < max_pages:
        response = fetch_fn(url)
        pages += 1

        if version == "v4":
            # V4: results in "value" array, next page in "@odata.nextLink"
            results = response.get("value", [])
            all_results.extend(results)
            url = response.get("@odata.nextLink")

        elif version == "v2":
            # V2: results in "d.results" array, next in "__next"
            d = response.get("d", {})
            if isinstance(d, dict):
                results = d.get("results", [])
                all_results.extend(results)
                url = d.get("__next")
            else:
                break
        else:
            break

    return all_results


def paginated_query(
    entity: str,
    page_size: int = 100,
    max_results: int = 1000,
) -> list[dict[str, str]]:
    """
    Generate pagination parameters for manual query construction.

    Returns list of query param dicts for each page.
    """
    pages = []
    offset = 0
    while offset < max_results:
        pages.append({
            "$top": str(page_size),
            "$skip": str(offset),
        })
        offset += page_size
    return pages
