import os
from pathlib import Path

import joblib
import numpy as np
from flask import current_app

# City encoding for model features
CITY_MAP = {
    "mumbai": 5, "delhi": 4, "bangalore": 4, "hyderabad": 3,
    "chennai": 3, "pune": 3, "kolkata": 2, "ahmedabad": 2,
}
TYPE_MAP = {"apartment": 1, "villa": 2, "house": 2, "plot": 0, "commercial": 3}


def _model_path():
    return Path(current_app.config.get("MODEL_PATH", "ml/property_price_model.pkl"))


def _load_model():
    path = _model_path()
    if path.exists():
        return joblib.load(path)
    return None


def _fallback_price(area_sqft, bedrooms, city, property_type):
    """Heuristic when ML model is not trained yet."""
    base_per_sqft = {
        "mumbai": 18000, "delhi": 12000, "bangalore": 9000,
        "hyderabad": 7000, "chennai": 6500, "pune": 7500,
    }
    city_key = (city or "bangalore").lower()
    rate = base_per_sqft.get(city_key, 8000)
    type_mult = {"apartment": 1.0, "villa": 1.4, "house": 1.2, "plot": 0.6, "commercial": 1.1}
    mult = type_mult.get((property_type or "apartment").lower(), 1.0)
    bedroom_bonus = max(0, (bedrooms or 0) - 2) * 500000
    return round(area_sqft * rate * mult + bedroom_bonus, 2)


def predict_price(area_sqft, bedrooms, bathrooms, city, property_type, year_built=None):
    model = _load_model()
    city_enc = CITY_MAP.get((city or "").lower(), 2)
    type_enc = TYPE_MAP.get((property_type or "apartment").lower(), 1)
    year = year_built or 2015
    age = max(0, 2025 - year)

    if model is None:
        predicted = _fallback_price(area_sqft, bedrooms, city, property_type)
        return {
            "predicted_price": predicted,
            "price_per_sqft": round(predicted / max(area_sqft, 1), 2),
            "method": "heuristic",
            "confidence": "low",
        }

    features = np.array([[area_sqft, bedrooms or 0, bathrooms or 0, city_enc, type_enc, age]])
    predicted = float(model.predict(features)[0])
    predicted = max(predicted, 100000)

    return {
        "predicted_price": round(predicted, 2),
        "price_per_sqft": round(predicted / max(area_sqft, 1), 2),
        "method": "random_forest",
        "confidence": "medium",
    }
