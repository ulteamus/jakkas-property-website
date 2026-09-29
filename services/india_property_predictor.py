"""Surat locality and property-type helpers."""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PREDICTOR_ROOT = BASE_DIR / "ml" / "india_predictor"
PROPERTY_TYPES_PATH = PREDICTOR_ROOT / "config" / "property_types.json"
LOCALITIES_PATH = PREDICTOR_ROOT / "config" / "surat_localities.json"

_TYPES: dict | None = None
_ALIAS_MAP: dict[str, str] | None = None

SELL_TYPE_MAP = {
    "apartment": "Apartment",
    "villa": "Villa",
    "bungalow": "Bungalow",
    "plot": "Plot",
    "commercial": "Shop",
    "residential": "Apartment",
    "flat": "Flat",
    "shop": "Shop",
    "office": "Office",
}


def list_surat_localities() -> list[str]:
    if not LOCALITIES_PATH.exists():
        return []
    rows = json.loads(LOCALITIES_PATH.read_text(encoding="utf-8"))
    return [row["locality"] for row in rows if row.get("locality")]


def _load_property_types() -> dict:
    global _TYPES, _ALIAS_MAP
    if _TYPES is None:
        _TYPES = json.loads(PROPERTY_TYPES_PATH.read_text(encoding="utf-8"))
        _ALIAS_MAP = {}
        for name, spec in _TYPES.items():
            _ALIAS_MAP[name.lower()] = name
            for alias in spec.get("aliases", []):
                _ALIAS_MAP[alias.lower()] = name
    return _TYPES


def normalize_property_type(value: str) -> str:
    key = (value or "Apartment").strip().lower()
    if key in SELL_TYPE_MAP:
        return SELL_TYPE_MAP[key]
    types = _load_property_types()
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]
    title = value.strip().title()
    if title in types:
        return title
    return "Apartment"


def get_category(property_type: str) -> str:
    canonical = normalize_property_type(property_type)
    return _load_property_types()[canonical]["category"]


def is_residential(property_type: str) -> bool:
    return get_category(property_type) == "residential"
