"""Property Price Prediction - XGBoost / RandomForest with heuristic fallback."""
from pathlib import Path

SURAT_RATES = {
    "flat": 6500, "shop": 12000, "office": 7500, "bungalow": 9000, "plot": 3500,
}
AREA_MULT = {
    "vesu": 1.35, "piplod": 1.3, "adajan": 1.15, "pal": 1.1, "dumas": 1.4,
    "varachha": 0.95, "katargam": 0.9, "althan": 1.05, "city light": 1.25,
}
TYPE_ALIASES = {
    "apartment": "flat",
    "villa": "bungalow",
    "commercial": "shop",
    "residential": "flat",
}


def _area_mult(area):
    if not area:
        return 1.0
    key = area.lower().strip()
    for k, v in AREA_MULT.items():
        if k in key:
            return v
    return 1.0


def _load_model():
    try:
        import joblib
        from config import PRICE_MODEL_PATH
        if PRICE_MODEL_PATH.exists():
            return joblib.load(PRICE_MODEL_PATH)
    except Exception:
        pass
    return None


def _coerce_sq_ft(value):
    raw = str(value or "").strip().replace(",", "")
    if not raw:
        raise ValueError("Area in sq ft is required.")
    try:
        parsed = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Area in sq ft must be a valid number.") from exc
    if parsed <= 0:
        raise ValueError("Area in sq ft must be greater than zero.")
    return parsed


def _coerce_bhk(value):
    raw = str(value or "").strip()
    if not raw:
        return 0
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("BHK must be a valid whole number.") from exc
    if parsed < 0:
        raise ValueError("BHK cannot be negative.")
    return parsed


def _normalize_property_type(value):
    key = (value or "flat").strip().lower()
    normalized = TYPE_ALIASES.get(key, key)
    return normalized if normalized in SURAT_RATES else "flat"


def predict(area_name, bhk, sq_ft, property_type):
    area_name = (area_name or "").strip() or "Surat"
    sq_ft = _coerce_sq_ft(sq_ft)
    bhk = _coerce_bhk(bhk)
    property_type = _normalize_property_type(property_type)
    base_rate = SURAT_RATES.get(property_type, 6000) * _area_mult(area_name)
    heuristic = sq_ft * base_rate * (1 + max(0, bhk - 2) * 0.04)

    model = _load_model()
    if model:
        try:
            import numpy as np
            type_map = {"flat": 0, "shop": 1, "office": 2, "bungalow": 3, "plot": 4}
            feat = np.array([[sq_ft, bhk, type_map.get(property_type, 0), _area_mult(area_name) * 100]])
            pred = float(model.predict(feat)[0])
            estimate = 0.6 * pred + 0.4 * heuristic
        except Exception:
            estimate = heuristic
    else:
        estimate = heuristic

    low = estimate * 0.92
    high = estimate * 1.08
    return {
        "estimated_value": round(estimate, 0),
        "price_range_low": round(low, 0),
        "price_range_high": round(high, 0),
        "per_sqft": round(estimate / max(sq_ft, 1), 0),
        "method": "ml" if model else "heuristic",
    }
