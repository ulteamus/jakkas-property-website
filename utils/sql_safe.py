"""Allowlist helpers for dynamic SQL fragments (DDL / table names)."""
from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

ALLOWED_TABLES = frozenset(
    {
        "properties",
        "inquiries",
        "owner_submissions",
        "leads",
        "visitor_events",
        "activity_logs",
        "admins",
        "property_images",
        "property_videos",
        "testimonials",
        "review_comments",
        "customer_visits",
        "visitors",
        "property_views",
        "search_analytics",
        "area_demand",
    }
)


def safe_ident(name: str) -> str | None:
    if not name or not _IDENT.match(name):
        return None
    return name


def safe_table(name: str) -> str | None:
    cleaned = safe_ident(name)
    if cleaned and cleaned.lower() in ALLOWED_TABLES:
        return cleaned.lower()
    return None


def safe_column(name: str, allowed: set[str] | frozenset[str] | None = None) -> str | None:
    cleaned = safe_ident(name)
    if not cleaned:
        return None
    if allowed is not None and cleaned.lower() not in {c.lower() for c in allowed}:
        return None
    return cleaned
