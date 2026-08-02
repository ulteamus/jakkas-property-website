"""Surat property price prediction (india-property-predictor integration)."""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PREDICTOR_ROOT = BASE_DIR / "ml" / "india_predictor"
MODEL_PATH = PREDICTOR_ROOT / "models" / "price_model.joblib"
LOCALITY_INDEX = PREDICTOR_ROOT / "data" / "locality_price_index.csv"
LOCALITY_RATES = PREDICTOR_ROOT / "data" / "locality_rates_surat_live.csv"
LOCALITY_FALLBACK = PREDICTOR_ROOT / "data" / "locality_rates_surat_fallback.csv"
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


def _read_rates_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_rates() -> list[dict[str, str]]:
    if LOCALITY_RATES.exists():
        return _read_rates_csv(LOCALITY_RATES)
    if LOCALITY_FALLBACK.exists():
        return _read_rates_csv(LOCALITY_FALLBACK)
    return _read_rates_csv(LOCALITY_INDEX)


def _filter_locality_rows(rows: list[dict[str, str]], locality: str) -> list[dict[str, str]]:
    loc_l = locality.strip().lower()
    exact = [row for row in rows if (row.get("locality") or "").strip().lower() == loc_l]
    if exact:
        return exact
    return [
        row for row in rows
        if loc_l in (row.get("locality") or "").strip().lower()
    ]


def resolve_rate(rows: list[dict[str, str]], locality: str, property_type: str) -> float | None:
    canonical = normalize_property_type(property_type)
    spec = _load_property_types()[canonical]
    base_type = spec["rate_from"]
    multiplier = spec["rate_multiplier"]
    subset = _filter_locality_rows(rows, locality)
    if not subset:
        return None

    base_l = base_type.lower()
    match = [row for row in subset if (row.get("property_type") or "").strip().lower() == base_l]
    if not match:
        if base_type == "Office":
            match = [row for row in subset if (row.get("property_type") or "").strip().lower() == "shop"]
        elif base_type == "Shop":
            match = [row for row in subset if (row.get("property_type") or "").strip().lower() == "apartment"]

    if not match:
        return None

    rates = [float(row["price_per_sqft_inr"]) for row in match if row.get("price_per_sqft_inr")]
    if not rates:
        return None
    rate = statistics.median(rates)
    return round(rate * multiplier, 2)


def lookup_locality_rate(city: str, locality: str, property_type: str = "Apartment") -> dict | None:
    canonical = normalize_property_type(property_type)
    rows = _load_rates()
    rate = resolve_rate(rows, locality, canonical)
    if rate is None:
        return None

    matched = _filter_locality_rows(rows, locality)
    row = matched[0] if matched else None

    return {
        "city": city,
        "locality": row["locality"] if row is not None else locality,
        "property_type": canonical,
        "category": get_category(canonical),
        "price_per_sqft_inr": rate,
    }


def _predict_with_ml(city: str, loc: dict, canonical: str, category: str, area_sqft: float, bhk: int, bath: int) -> float | None:
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        import pandas as pd
    except ImportError:
        return None

    model = joblib.load(MODEL_PATH)
    row = pd.DataFrame(
        [
            {
                "city": city or "Surat",
                "locality": loc["locality"],
                "property_type": canonical,
                "category": category,
                "area_sqft": area_sqft,
                "bhk": bhk,
                "bath": bath,
            }
        ]
    )
    return float(model.predict(row)[0])


def predict_price(
    city: str,
    locality: str,
    area_sqft: float,
    bhk: int | None = 2,
    bath: int | None = 2,
    property_type: str = "Apartment",
) -> dict:
    if not locality or not str(locality).strip():
        raise ValueError("Location / area is required for price prediction.")

    canonical = normalize_property_type(property_type)
    category = get_category(canonical)

    if not is_residential(canonical) or canonical == "Plot":
        bhk = 0
        bath = 0
    else:
        bhk = int(bhk) if bhk is not None else 2
        bath = int(bath) if bath is not None else max(1, bhk - 1) if bhk else 2

    area_sqft = float(area_sqft)
    if area_sqft <= 0:
        raise ValueError("Area in sq ft must be greater than zero.")

    loc = lookup_locality_rate(city, locality, canonical)
    if loc is None:
        raise ValueError(f"Could not find rates for location '{locality}'. Try a Surat area like Vesu, Adajan, or Pal.")

    rate_based_inr = round(loc["price_per_sqft_inr"] * area_sqft)
    price_inr = rate_based_inr
    price_lakhs = round(price_inr / 100_000, 2)
    method = "locality_rate"

    ml_lakhs = _predict_with_ml(city, loc, canonical, category, area_sqft, bhk, bath)
    if ml_lakhs is not None:
        ml_inr = round(ml_lakhs * 100_000)
        price_inr = round((ml_inr + rate_based_inr) / 2)
        price_lakhs = round(price_inr / 100_000, 2)
        method = "india_ml_combined"

    low = round(price_inr * 0.92)
    high = round(price_inr * 1.08)

    return {
        "city": city or "Surat",
        "locality": loc["locality"],
        "property_type": canonical,
        "area_sqft": area_sqft,
        "bhk": bhk,
        "predicted_price_inr": price_inr,
        "predicted_price_lakhs": price_lakhs,
        "locality_rate_per_sqft_inr": loc["price_per_sqft_inr"],
        "rate_based_price_inr": rate_based_inr,
        "estimated_value": price_inr,
        "price_range_low": low,
        "price_range_high": high,
        "per_sqft": round(price_inr / max(area_sqft, 1)),
        "method": method,
    }
