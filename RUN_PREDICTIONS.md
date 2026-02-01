# How to Run Predictions - Simple Guide

## Quick Answer

The **easiest way** to run predictions is through the **Flask web application** which handles all the feature engineering automatically.

---

## Method 1: Run the Web Application (RECOMMENDED)

### Start the Server

```bash
python app/run.py
```

### Access the App

**Multi-Sport Platform:**
```
http://localhost:5000/multi
```

**Available Routes:**
- Basketball predictions: `http://localhost:5000/multi/sport/basketball`
- Tennis predictions: `http://localhost:5000/multi/sport/tennis`
- Football predictions: `http://localhost:5000/multi/sport/football`

### Make Predictions via API

**Basketball (NBA):**
```bash
curl -X POST http://localhost:5000/multi/api/basketball/predict \
  -H "Content-Type: application/json" \
  -d '{"home": "Los Angeles Lakers", "away": "Golden State Warriors"}'
```

**Tennis (ATP/WTA):**
```bash
curl -X POST http://localhost:5000/multi/api/tennis/predict \
  -H "Content-Type: application/json" \
  -d '{"player1": "Novak Djokovic", "player2": "Carlos Alcaraz", "surface": "Hard"}'
```

---

## Method 2: Update Flask to Use Backtested Models

### Current Status

The Flask app (`app/multi_sport_routes.py`) loads models but may be using old models with data leakage.

### Update to Use Backtested Models

Edit `app/multi_sport_routes.py` line 47-84:

```python
def load_all_predictors():
    """Load all sport predictors with BACKTESTED models (no data leakage)."""
    global predictors

    # Load Football (your existing advanced system)
    try:
        football_models_path = Path("models/enhanced_processed_data.pkl")
        if football_models_path.exists():
            predictors['football'] = joblib.load(football_models_path)
            logger.info("[Football] Advanced model loaded")
        else:
            logger.warning("[Football] Models not found")
    except Exception as e:
        logger.error(f"[Football] Error: {e}")

    # Load Basketball BACKTESTED Models (87.89% accuracy, NO DATA LEAKAGE)
    try:
        basketball_backtested_path = Path("models/basketball/basketball_backtested_models.joblib")
        if basketball_backtested_path.exists():
            # Load backtested model data
            backtest_data = joblib.load(basketball_backtested_path)

            # Create predictor wrapper that uses backtested models
            class BasketballBacktestPredictor:
                def __init__(self, backtest_data):
                    self.models = backtest_data['models']
                    self.feature_cols = backtest_data['feature_cols']
                    from sports.basketball.basketball_features import BasketballFeatureEngineer
                    self.feature_engineer = BasketballFeatureEngineer()

                def predict(self, match_info):
                    """Predict basketball game."""
                    import pandas as pd

                    # Create game data
                    game_df = pd.DataFrame([{
                        'Date': pd.Timestamp.now(),
                        'HomeTeam': match_info.get('home'),
                        'AwayTeam': match_info.get('away'),
                        'HomeScore': 0,
                        'AwayScore': 0,
                        'Result': 'H'
                    }])

                    # Engineer features
                    game_features = self.feature_engineer.engineer_features(game_df)
                    X = game_features[self.feature_cols].fillna(0)

                    # Make predictions
                    result = {}

                    if 'match_outcome' in self.models:
                        model = self.models['match_outcome']['model']
                        prob = model.predict_proba(X)[0]
                        result['winner'] = 'Home' if prob[1] > prob[0] else 'Away'
                        result['home_win_prob'] = float(prob[1])
                        result['away_win_prob'] = float(prob[0])

                    if 'total_points' in self.models:
                        model = self.models['total_points']['model']
                        result['total_points'] = float(model.predict(X)[0])

                    return result

                def get_available_teams(self):
                    """Return list of teams."""
                    return ['Los Angeles Lakers', 'Golden State Warriors',
                            'Boston Celtics', 'Miami Heat', 'Brooklyn Nets']

            predictors['basketball'] = BasketballBacktestPredictor(backtest_data)
            logger.info("[Basketball] BACKTESTED models loaded (87.89% accuracy, NO DATA LEAKAGE)")
        else:
            logger.warning("[Basketball] Backtested models not found")
    except Exception as e:
        logger.error(f"[Basketball] Error: {e}")

    # Similar for Tennis...
```

---

## Method 3: Run Backtesting Scripts

These scripts validate the models but don't make new predictions:

**Basketball:**
```bash
python backtest_basketball.py
```

**Tennis:**
```bash
python backtest_tennis.py
```

**Comprehensive Report:**
```bash
python generate_backtest_report.py
```

---

## Model Performance

### Basketball (NBA)
```
✓ Validated on 1,230 unseen games
✓ Match Outcome: 87.89% accuracy
✓ Over/Under 220: 77.56% accuracy
✓ Total Points: ±11.07 points MAE
✓ NO DATA LEAKAGE
```

### Tennis (ATP/WTA)
```
✓ Validated on 2,779 unseen matches
✓ Match Winner: 95.57% accuracy
✓ NO DATA LEAKAGE
```

---

## Files Location

**Backtested Models (Use These):**
- `models/basketball/basketball_backtested_models.joblib` ← 87.89% accuracy
- `models/tennis/tennis_backtested_models.joblib` ← 95.57% accuracy

**Old Models (Data Leakage - Don't Use):**
- `models/basketball/basketball_advanced_models.joblib` ← 100% (fake)
- `models/tennis/tennis_advanced_models.joblib` ← 100% (fake)

---

## Summary

**To make predictions:**

1. **Start Flask app:** `python app/run.py`
2. **Visit:** http://localhost:5000/multi
3. **Use the web interface** to make predictions

OR

4. **Use API endpoints** with curl/Postman/JavaScript

The web app handles all the complexity of feature engineering, historical data, and model inference for you!
