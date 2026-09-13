"""Shared validators / sanitizers used across routes and services."""
import re
import uuid

_TAG_RE = re.compile(r"<[^>]*>")
_PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")


def sanitize_text(value: str | None) -> str:
    """Strip HTML tags and excess whitespace from user-generated content
    (e.g. reviews, support messages) to avoid stored XSS."""
    if not value:
        return ""
    stripped = _TAG_RE.sub("", value)
    return stripped.strip()


def is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    return bool(_PHONE_RE.match(phone))


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def new_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex
