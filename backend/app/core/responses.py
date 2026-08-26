"""Consistent API envelope helpers.

Coding Standard 3.5 requires every endpoint to answer with the same shape:
``{"success": bool, "data": object | None, "error": object | None}``.
"""

from typing import Any


def success_response(data: Any = None) -> dict[str, Any]:
    """Wrap a successful payload in the standard envelope.

    Args:
        data: The payload to return to the client.

    Returns:
        dict: The standard success envelope.
    """
    return {"success": True, "data": data, "error": None}


def error_response(message: str, code: str = "error", details: Any = None) -> dict[str, Any]:
    """Wrap a failure in the standard envelope.

    Args:
        message: A human readable message safe to show to the user.
        code: A stable machine readable error code.
        details: Optional structured detail such as field level validation errors.

    Returns:
        dict: The standard error envelope.
    """
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details},
    }
