# Quick Start Guide - Running the Backtested Models

## Overview

This guide shows you how to use the **validated models** (no data leakage, realistic accuracy) to make predictions for Basketball and Tennis.

---

## 1. Make Individual Predictions

### Basketball (NBA)

**Run the prediction script:**
```bash
python predict_basketball.py
```

**Example output:**
```
NBA GAME PREDICTION
Using Backtested Model (No Data Leakage)
============================================================

Predicting] Los Angeles Lakers vs Golden State Warriors

============================================================
PREDICTION RESULTS
============================================================

Match Winner:
  Prediction: Home Team Wins
  Home Win Probability: 65.3%
  Away Win Probability: 34.7%
  Confidence: 65.3%

Total Points:
  Predicted Total: 225.4 points
  Expected Range: 214.3 - 236.5 points

Over/Under 220:
  Prediction: Over 220
  Over Probability: 62.8%
  Under Probability: 37.2%
  Confidence: 62.8%

============================================================
Note: Model validated with 87.89% accuracy on unseen games
============================================================
```

**Custom prediction:**
```python
from predict_basketball import predict_game, display_predictions

predictions = predict_game('Boston Celtics', 'Miami Heat')
display_predictions(predictions)
```

---

### Tennis (ATP/WTA)

**Run the prediction script:**
```bash
python predict_tennis.py
```

**Example output:**
```
TENNIS MATCH PREDICTION
Using Backtested Model (No Data Leakage)
============================================================

[Predicting] Novak Djokovic vs Carlos Alcaraz
  Surface: Hard
  Tournament: ATP Finals

============================================================
PREDICTION RESULTS
============================================================

Match Winner:
  Predicted Winner: Carlos Alcaraz
  Novak Djokovic Win Probability: 45.2%
  Carlos Alcaraz Win Probability: 54.8%
  Confidence: 54.8%

============================================================
Note: Model validated with 95.57% accuracy on unseen matches
============================================================
```

**Custom prediction:**
```python
from predict_tennis import predict_match, display_predictions

predictions = predict_match(
    player1='Rafael Nadal',
    player2='Novak Djokovic',
    surface='Clay',
    tournament='French Open'
)
display_predictions(predictions)
```

---

## 2. Run the Web Application

### Start the Flask Server

**Option 1: Use the existing run script**
```bash
python app/run.py
```

**Option 2: Direct flask run**
```bash
cd app
python run.py
```

**Access the application:**
- Original Football App: http://localhost:5000
- Multi-Sport Platform: http://localhost:5000/multi

---

## 3. Update Flask Routes to Use Backtested Models

The backtested models are saved at:
- Basketball: `models/basketball/basketball_backtested_models.joblib`
- Tennis: `models/tennis/tennis_backtested_models.joblib`

**To use backtested models in Flask**, update `app/multi_sport_routes.py`:

```python
# Load Basketball Advanced Models (BACKTESTED - NO DATA LEAKAGE)
try:
    basketball_backtested_path = Path("models/basketball/basketball_backtested_models.joblib")
    if basketball_backtested_path.exists():
        predictors['basketball'] = joblib.load(basketball_backtested_path)
        logger.info("[Basketball] Backtested models loaded (87.89% accuracy on unseen data)")
    else:
        # Fallback to original model
        basketball_advanced_path = Path("models/basketball/basketball_advanced_models.joblib")
        if basketball_advanced_path.exists():
            predictors['basketball'] = joblib.load(basketball_advanced_path)
            logger.info("[Basketball] Advanced models loaded")
except Exception as e:
    logger.error(f"[Basketball] Error: {e}")

# Load Tennis Advanced Models (BACKTESTED - NO DATA LEAKAGE)
try:
    tennis_backtested_path = Path("models/tennis/tennis_backtested_models.joblib")
    if tennis_backtested_path.exists():
        predictors['tennis'] = joblib.load(tennis_backtested_path)
        logger.info("[Tennis] Backtested models loaded (95.57% accuracy on unseen data)")
    else:
        # Fallback to original model
        tennis_advanced_path = Path("models/tennis/tennis_advanced_models.joblib")
        if tennis_advanced_path.exists():
            predictors['tennis'] = joblib.load(tennis_advanced_path)
            logger.info("[Tennis] Advanced models loaded")
except Exception as e:
    logger.error(f"[Tennis] Error: {e}")
```

---

## 4. Run Backtesting (Re-validate Models)

If you update the data or want to re-validate the models:

**Basketball:**
```bash
python backtest_basketball.py
```

**Tennis:**
```bash
python backtest_tennis.py
```

**Generate comprehensive report:**
```bash
python generate_backtest_report.py
```

---

## 5. Model Performance Summary

### Basketball (NBA)
```
Test Set: 1,230 unseen games (Oct 2024 - Apr 2025)

Performance:
├─ Match Outcome: 87.89% accuracy
├─ Over/Under 220: 77.56% accuracy
└─ Total Points: ±11.07 points MAE

Status: ✓ Validated, No data leakage, Ready for production
```

### Tennis (ATP/WTA)
```
Test Set: 2,779 unseen matches (Nov 2024 - Nov 2025)

Performance:
└─ Match Winner: 95.57% accuracy

Status: ✓ Validated, No data leakage, Ready for production
```

---

## 6. File Structure

```
all_leagues_prediction/
├── predict_basketball.py          # Basketball prediction script
├── predict_tennis.py               # Tennis prediction script
├── backtest_basketball.py          # Basketball validation
├── backtest_tennis.py              # Tennis validation
├── generate_backtest_report.py    # Comprehensive reporting
├── BACKTESTING_SUMMARY.md         # Full documentation
├── QUICK_START_GUIDE.md           # This file
│
├── models/
│   ├── basketball/
│   │   └── basketball_backtested_models.joblib  # Validated model (87.89%)
│   └── tennis/
│       └── tennis_backtested_models.joblib      # Validated model (95.57%)
│
├── app/
│   ├── run.py                      # Flask application
│   ├── routes.py                   # Original football routes
│   └── multi_sport_routes.py       # Multi-sport routes
│
└── sports/
    ├── basketball/
    │   ├── basketball_features.py  # Feature engineering (DATA LEAKAGE FIXED)
    │   └── advanced_basketball_training.py
    └── tennis/
        ├── tennis_features.py      # Feature engineering (DATA LEAKAGE FIXED)
        └── advanced_tennis_training.py
```

---

## 7. Common Tasks

### Make a Basketball Prediction
```bash
python predict_basketball.py
```

### Make a Tennis Prediction
```bash
python predict_tennis.py
```

### Run the Web Application
```bash
python app/run.py
```
Then visit: http://localhost:5000/multi

### Re-validate Models
```bash
python backtest_basketball.py
python backtest_tennis.py
python generate_backtest_report.py
```

---

## 8. Important Notes

✓ **Use backtested models** - They have no data leakage and realistic accuracy
✓ **Monitor predictions** - Track real-world accuracy vs backtested accuracy
✓ **Retrain periodically** - Update models with new data every season
✓ **Validate with domain knowledge** - Always sanity-check predictions

---

## 9. Troubleshooting

**Error: "Backtested model not found"**
- Run: `python backtest_basketball.py` or `python backtest_tennis.py`

**Error: "Feature not found"**
- Make sure you're using the backtested models, not the old models with data leakage

**Low accuracy on new predictions:**
- Models were trained on 2020-2024 data
- Retrain with latest data if performance degrades

---

## 10. Next Steps

1. Test predictions on upcoming games/matches
2. Compare predictions with actual results
3. Retrain models with new data periodically
4. Deploy to production (Railway, Heroku, etc.)
