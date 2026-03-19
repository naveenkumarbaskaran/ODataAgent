"""HTTP error mapping for OData responses."""

from __future__ import annotations


# HTTP status → agent-friendly message
ERROR_MAP: dict[int, str] = {
    400: "Invalid query parameters. Check filter syntax.",
    401: "Authentication required. Verify credentials.",
    403: "Access denied. Insufficient authorization for this entity.",
    404: "Entity or resource not found.",
    405: "Operation not supported on this entity.",
    408: "Request timed out. Try reducing result set with $top.",
    429: "Rate limited. Too many requests — wait and retry.",
    500: "Server error. The backend service is experiencing issues.",
    502: "Bad gateway. The OData service may be restarting.",
    503: "Service unavailable. Try again in a few minutes.",
}


def map_http_error(status_code: int, raw_body: str = "") -> str:
    """
    Map an HTTP error to a safe, agent-friendly message.

    Never exposes raw server error details (stack traces, internal paths, etc.)
    """
    safe_msg = ERROR_MAP.get(status_code, f"Unexpected error (HTTP {status_code}).")

    # Extract OData error message if present (without internal details)
    if raw_body:
        import json
        try:
            body = json.loads(raw_body)
            # V4 format
            if "error" in body and "message" in body["error"]:
                odata_msg = body["error"]["message"]
                if isinstance(odata_msg, str) and len(odata_msg) < 200:
                    safe_msg += f" Detail: {odata_msg}"
            # V2 format
            elif "error" in body and "message" in body["error"]:
                inner = body["error"]["message"]
                if isinstance(inner, dict) and "value" in inner:
                    val = inner["value"]
                    if len(val) < 200:
                        safe_msg += f" Detail: {val}"
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # Don't expose parse errors

    return safe_msg


class ODataError(Exception):
    """Raised for OData API errors."""

    def __init__(self, status_code: int, message: str, raw_body: str = ""):
        self.status_code = status_code
        self.message = message
        self.raw_body = raw_body
        self.safe_message = map_http_error(status_code, raw_body)
        super().__init__(self.safe_message)
