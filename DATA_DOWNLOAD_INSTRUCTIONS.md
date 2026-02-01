# REAL DATA DOWNLOAD INSTRUCTIONS

## Matching Your Football Data Approach

You downloaded football data from **football-data.co.uk** as Excel files.
Here's how to get equivalent REAL data for other sports:

---

## ✅ FOOTBALL (Already Done by You)
**Source:** https://www.football-data.co.uk/downloadm.php
**What you did:** Downloaded `all-euro-data-2025-2026.xlsx`
**Result:** 3,769 matches, 22 leagues
**Status:** ✓ WORKING

---

## 🏀 BASKETBALL (NBA) - Need to Download

### Option 1: Basketball-Reference.com (RECOMMENDED)
**URL:** https://www.basketball-reference.com/

**Steps:**
1. Go to: https://www.basketball-reference.com/leagues/NBA_2024_games.html
2. Click "Schedule" for each month
3. At bottom of page, click "Share & Export" → "Get table as CSV"
4. Download for seasons: 2022, 2023, 2024
5. Save to: `data/basketball/raw/nba_games_[year].csv`

**What you'll get:**
- Date, Home Team, Away Team, Home Score, Away Score
- Attendance, OT indicator
- Real game results for 1,230 games per season

### Option 2: Kaggle (Alternative)
**URL:** https://www.kaggle.com/datasets/wyattowalsh/basketball
**Steps:**
1. Download the dataset (requires Kaggle account)
2. Extract `games.csv`
3. Place in: `data/basketball/raw/nba_kaggle_games.csv`

---

## 🏈 NFL - Need to Download

### Option 1: Pro-Football-Reference.com (RECOMMENDED)
**URL:** https://www.pro-football-reference.com/

**Steps:**
1. Go to: https://www.pro-football-reference.com/years/2024/games.htm
2. Scroll to "Schedule & Results" table
3. Click "Share & Export" → "Get table as CSV"
4. Download for seasons: 2022, 2023, 2024
5. Save to: `data/nfl/raw/nfl_games_[year].csv`

**What you'll get:**
- Date, Home Team, Away Team, Home Score, Away Score
- Yards gained, Turnovers
- Real game results for ~285 games per season

### Option 2: nflfastR Data (Alternative)
**URL:** https://github.com/nflverse/nflfastR-data
**Steps:**
1. Download play-by-play data (has game summaries)
2. Or use their game-level summaries
3. Place in: `data/nfl/raw/nfl_nflfastr_[year].csv`

---

## 🎾 TENNIS (Already Downloaded - Real Data)
**Source:** Jeff Sackmann's GitHub (Official ATP/WTA data repository)
**Status:** ✓ DONE - 17,072 real matches
**Location:** `data/tennis/raw/tennis_real_data.csv`

---

## QUICK DOWNLOAD LINKS

### NBA (2024 Season)
- 2024: https://www.basketball-reference.com/leagues/NBA_2024_games.html
- 2023: https://www.basketball-reference.com/leagues/NBA_2023_games.html
- 2022: https://www.basketball-reference.com/leagues/NBA_2022_games.html

### NFL (2024 Season)
- 2024: https://www.pro-football-reference.com/years/2024/games.htm
- 2023: https://www.pro-football-reference.com/years/2023/games.htm
- 2022: https://www.pro-football-reference.com/years/2022/games.htm

---

## AFTER DOWNLOADING

Once you have the CSV files, run:

```bash
# Process NBA data
python process_nba_real_data.py

# Process NFL data
python process_nfl_real_data.py

# Train all models with REAL data
python train_all_sports_real.py
```

---

## FILE STRUCTURE (After Download)

```
data/
├── raw/
│   └── all-euro-data-2025-2026.xlsx (✓ You have this)
├── basketball/raw/
│   ├── nba_games_2022.csv (← Download this)
│   ├── nba_games_2023.csv (← Download this)
│   └── nba_games_2024.csv (← Download this)
├── nfl/raw/
│   ├── nfl_games_2022.csv (← Download this)
│   ├── nfl_games_2023.csv (← Download this)
│   └── nfl_games_2024.csv (← Download this)
└── tennis/raw/
    └── tennis_real_data.csv (✓ Already downloaded - 17K matches)
```

---

## WHY DOWNLOAD INSTEAD OF API SCRAPING?

**Your football approach:**
- Download Excel files from trusted source
- One-time download, repeatable
- Complete historical data
- No API rate limits
- No authentication needed

**Same benefits for NBA/NFL:**
- basketball-reference and pro-football-reference are THE trusted sources
- CSV exports are clean and complete
- No scraping, no API limits
- Same quality as your football data

---

*This matches your football data workflow exactly.*
