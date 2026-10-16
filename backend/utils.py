import re

from flask import jsonify, request
from flask_security import auth_required, roles_required

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Raised for bad client input; converted to a 400 JSON response."""


def error(message, status=400):
    # `error` and `message` carry the same text so any client can read either
    return jsonify({"error": message, "message": message}), status


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


def token_roles(*roles):
    """Require a valid access token AND one of the given roles."""

    def decorator(fn):
        return auth_required("token")(roles_required(*roles)(fn))

    return decorator


def text(value, label, min_len=0, max_len=255, required=False):
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ValidationError(f"{label} is required")
    if value and len(value) < min_len:
        raise ValidationError(f"{label} must be at least {min_len} characters")
    if len(value) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters")
    return value


def number(value, label, cast=float, lo=None, hi=None, required=False):
    """Parse a number. None / '' -> None unless required."""
    if value is None or value == "":
        if required:
            raise ValidationError(f"{label} is required")
        return None
    try:
        value = cast(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a valid number")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ValidationError(f"{label} must be between {lo} and {hi}")
    return value
