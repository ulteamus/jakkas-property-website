"""Defensive type coercion — never raise ValueError on bad client input."""
from __future__ import annotations

from typing import Any, Optional, Union


def safe_int(value: Any, default: int = 0, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    try:
        if value is None or value == "":
            result = default
        else:
            result = int(float(str(value).strip().replace(",", "")))
    except (TypeError, ValueError, OverflowError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def safe_float(
    value: Any,
    default: float = 0.0,
    *,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> float:
    try:
        if value is None or value == "":
            result = float(default)
        else:
            result = float(str(value).strip().replace(",", ""))
        if result != result:  # NaN
            result = float(default)
        if result in (float("inf"), float("-inf")):
            result = float(default)
    except (TypeError, ValueError, OverflowError):
        result = float(default)
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def safe_str(value: Any, default: str = "", *, max_len: int = 2000) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len > 0 and len(text) > max_len:
        return text[:max_len]
    return text


def clamp_ids(raw_ids: Any, *, limit: int = 200) -> list[int]:
    out: list[int] = []
    if raw_ids is None:
        return out
    if isinstance(raw_ids, (list, tuple, set)):
        items = list(raw_ids)
    else:
        items = [raw_ids]
    for item in items:
        n = safe_int(item, default=-1, minimum=1)
        if n > 0:
            out.append(n)
        if len(out) >= limit:
            break
    return out
