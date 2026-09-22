"""Structured logging helpers that redact common credential fields."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

SENSITIVE_FRAGMENTS = ("api_key", "authorization", "password", "secret", "token")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if any(fragment in str(key).lower() for fragment in SENSITIVE_FRAGMENTS)
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


def structured_event(event: str, **fields: Any) -> str:
    return json.dumps({"event": event, **redact(fields)}, sort_keys=True, default=str)
