"""
Train Random Forest model for property price prediction.
Run: python ml/train_model.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

BASE = Path(__file__).resolve().parent
MODEL_OUT = BASE / "property_price_model.pkl"

CITY_MAP = {
    "mumbai": 5, "delhi": 4, "bangalore": 4, "hyderabad": 3,
    "chennai": 3, "pune": 3, "kolkata": 2, "ahmedabad": 2,
}
TYPE_MAP = {"apartment": 1, "villa": 2, "house": 2, "plot": 0, "commercial": 3}


def generate_training_data(n=800):
    """Synthetic dataset when DB is empty."""
    rng = np.random.default_rng(42)
    cities = list(CITY_MAP.keys())
    types = list(TYPE_MAP.keys())
    rows = []

    base_rates = {
        "mumbai": 20000, "delhi": 14000, "bangalore": 10000,
        "hyderabad": 8000, "chennai": 7500, "pune": 8500,
        "kolkata": 7000, "ahmedabad": 6500,
    }

    for _ in range(n):
        city = rng.choice(cities)
        ptype = rng.choice(types)
        area = rng.integers(500, 4000)
        beds = rng.integers(1, 5) if ptype != "plot" else 0
        baths = max(1, beds)
        year = rng.integers(1995, 2024)
        age = 2025 - year
        noise = rng.normal(1, 0.08)
        mult = {"apartment": 1.0, "villa": 1.35, "house": 1.2, "plot": 0.55, "commercial": 1.15}[ptype]
        price = area * base_rates[city] * mult * (1 + beds * 0.05) * (1 - age * 0.005) * noise
        price = max(price, 300000)

        rows.append({
            "area_sqft": area,
            "bedrooms": beds,
            "bathrooms": baths,
            "city_enc": CITY_MAP[city],
            "type_enc": TYPE_MAP[ptype],
            "age": age,
            "price": price,
        })
    return pd.DataFrame(rows)


def load_from_mysql():
    try:
        import mysql.connector
        from dotenv import load_dotenv
        import os
        load_dotenv()
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "property_broker"),
        )
        df = pd.read_sql(
            "SELECT area_sqft, bedrooms, bathrooms, city, property_type, year_built, price FROM properties",
            conn,
        )
        conn.close()
        if len(df) < 20:
            return None
        df["city_enc"] = df["city"].str.lower().map(CITY_MAP).fillna(2)
        df["type_enc"] = df["property_type"].str.lower().map(TYPE_MAP).fillna(1)
        df["age"] = 2025 - df["year_built"].fillna(2015)
        return df[["area_sqft", "bedrooms", "bathrooms", "city_enc", "type_enc", "age", "price"]]
    except Exception:
        return None


def main():
    df = load_from_mysql()
    if df is None:
        print("Using synthetic training data...")
        df = generate_training_data()
    else:
        print(f"Loaded {len(df)} rows from MySQL.")

    X = df[["area_sqft", "bedrooms", "bathrooms", "city_enc", "type_enc", "age"]]
    y = df["price"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=12,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"Test MAE: ₹{mae:,.0f}  |  R²: {r2:.3f}")

    joblib.dump(model, MODEL_OUT)
    print(f"Model saved to {MODEL_OUT}")


if __name__ == "__main__":
    main()
