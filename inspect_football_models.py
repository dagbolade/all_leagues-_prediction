"""Inspect existing football models to see structure."""

import joblib
from pathlib import Path

models_path = Path("models/football_models.joblib")

if models_path.exists():
    print(f"Loading {models_path}...")
    data = joblib.load(models_path)

    print(f"\nType: {type(data)}")

    if isinstance(data, dict):
        print(f"\nKeys in saved data:")
        for key in data.keys():
            print(f"  - {key}: {type(data[key])}")
    else:
        print(f"\nDirect object: {type(data)}")
        print(f"Attributes: {dir(data)[:20]}")
else:
    print(f"File not found: {models_path}")
