"""Train ML models - uses numpy + sklearn only."""
from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor

OUT = Path(__file__).resolve().parent / "models"
OUT.mkdir(parents=True, exist_ok=True)


def train_lead_scorer(n=500):
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(n):
        pv = rng.integers(0, 15)
        time_s = rng.integers(0, 600)
        saved = rng.integers(0, 5)
        wa = rng.integers(0, 5)
        call = rng.integers(0, 4)
        has_prop = rng.integers(0, 2)
        score = min(100, pv * 8 + time_s // 30 + saved * 10 + wa * 12 + call * 10 + has_prop * 10)
        X.append([pv, time_s, saved, wa, call, has_prop])
        y.append(score)
    X, y = np.array(X), np.array(y)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, OUT / "lead_scorer.pkl")
    print(f"Lead scorer saved. R2: {model.score(X, y):.3f}")


if __name__ == "__main__":
    train_lead_scorer()
