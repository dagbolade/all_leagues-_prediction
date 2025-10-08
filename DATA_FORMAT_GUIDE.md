# Data Format and Structure Guide

This document outlines the expected format and structure for input data files used by the football prediction system. Understanding these requirements is essential for contributors who want to add new data sources or modify existing data processing workflows.

## Overview

The system processes football match data from multiple leagues across different seasons. The data is organized in a hierarchical structure that supports both individual league analysis and cross-league predictions using advanced Bayesian modeling techniques.

## File Organization

### Directory Structure

```
data/
├── raw/                           # Original data files
│   ├── all-euro-data-2023-2024.xlsx
│   ├── all-euro-data-2024-2025.xlsx
│   └── new_leagues_data.xlsx      # Additional leagues
└── processed/                     # Processed data files
    ├── enhanced_bayesian_data.pkl
    ├── enhanced_features.csv
    └── complete_features.csv
```

### Naming Convention

**Season Files:** `all-euro-data-{YYYY-YYYY}.xlsx`
- Example: `all-euro-data-2023-2024.xlsx`
- Must follow the exact pattern for automatic discovery
- Years represent the season span (e.g., 2023-2024 for the 2023/24 season)

## Excel File Structure

### Multi-Sheet Architecture

Each season file contains multiple worksheets, where each worksheet represents a different football league:

| Sheet Name | League Description | Example Teams |
|------------|-------------------|---------------|
| E0 | English Premier League | Arsenal, Chelsea, Liverpool |
| E1 | English Championship | Leeds, Leicester, Southampton |
| D1 | German Bundesliga | Bayern Munich, Dortmund |
| D2 | German 2. Bundesliga | Hamburg, Stuttgart |
| SP1 | Spanish La Liga | Real Madrid, Barcelona |
| I1 | Italian Serie A | Juventus, AC Milan |
| F1 | French Ligue 1 | PSG, Marseille |
| N1 | Dutch Eredivisie | Ajax, PSV |
| B1 | Belgian Pro League | Club Brugge, Anderlecht |

### Required Columns

Each league worksheet must contain the following columns with exact naming:

#### Core Match Data
| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| `Date` | datetime | Match date | 2024-01-15 |
| `HomeTeam` | string | Home team name | Arsenal |
| `AwayTeam` | string | Away team name | Chelsea |
| `FTHG` | integer | Full-time home goals | 2 |
| `FTAG` | integer | Full-time away goals | 1 |
| `FTR` | string | Full-time result | H |

#### Result Codes
- `FTR` values: `H` (Home win), `A` (Away win), `D` (Draw)

#### Optional Betting Data
| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| `B365H` | float | Bet365 home win odds | 2.10 |
| `B365D` | float | Bet365 draw odds | 3.40 |
| `B365A` | float | Bet365 away win odds | 3.50 |
| `B365>2.5` | float | Over 2.5 goals odds | 1.85 |
| `B365<2.5` | float | Under 2.5 goals odds | 1.95 |

## Data Quality Requirements

### Essential Validation Rules

1. **Date Format**: All dates must be parseable by pandas
   - Preferred: `YYYY-MM-DD`
   - Acceptable: `DD/MM/YYYY`, `MM/DD/YYYY`

2. **Team Names**: Must be consistent within each league
   - Case-sensitive matching
   - No special characters or extra spaces
   - Examples: "Manchester United" not "Man United" or "manchester united"

3. **Goal Counts**: Non-negative integers only
   - `FTHG` and `FTAG` must be >= 0
   - Missing values should be avoided

4. **Result Consistency**: `FTR` must match actual goals
   - `H`: `FTHG` > `FTAG`
   - `A`: `FTHG` < `FTAG` 
   - `D`: `FTHG` == `FTAG`

### Data Completeness

- **Minimum Records**: At least 30 matches per league per season
- **Season Span**: Complete seasons preferred (full fixture list)
- **Missing Data**: No more than 5% missing values in core columns

## Integration with Global Data

### Adding New Leagues

The system supports integration of additional leagues through `global_data_integration.py`. New leagues should follow this structure:

#### Supported League Codes
```
ARG1  - Argentina Primera División
AUT1  - Austrian Bundesliga
BRA1  - Brazilian Serie A
CHN1  - Chinese Super League
DNK1  - Danish Superliga
FIN1  - Finnish Veikkausliiga
IRL1  - Irish Premier Division
JPN1  - Japanese J1 League
MEX1  - Mexican Liga MX
NOR1  - Norwegian Eliteserien
POL1  - Polish Ekstraklasa
ROU1  - Romanian Liga 1
RUS1  - Russian Premier League
SWE1  - Swedish Allsvenskan
SWZ1  - Swiss Super League
USA1  - Major League Soccer
```

### Global Data File Format

When adding new leagues, create a file named `new_leagues_data.xlsx` with:
- Each league as a separate worksheet
- League code as worksheet name (e.g., "ARG1", "BRA1")
- Standard column structure as defined above

## Processing Pipeline

### Data Flow

1. **Loading**: `load_data.py` reads multi-sheet Excel files
2. **Merging**: Combines multiple seasons and leagues
3. **Cleaning**: Removes betting columns and validates data
4. **Feature Engineering**: Adds Bayesian rolling features
5. **Model Training**: Trains prediction models
6. **Output**: Saves processed data and trained models

### Key Processing Steps

#### Phase 1: Data Loading
```python
# Automatic file discovery
files = sorted(data_dir.glob("all-euro-data-*.xlsx"))
season_paths = {_season_from_fname(f): f for f in files}

# Load and merge data
data_by_season, sheets = load_season_data_any(season_paths)
merged_df = load_and_merge_multi(data_by_season)
```

#### Phase 2: Data Cleaning
```python
# Remove betting columns
cleaned_df = clean_betting_columns(merged_df)

# Validate essential columns
needed_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
cleaned_df = cleaned_df.dropna(subset=needed_cols)
```

#### Phase 3: Feature Engineering
- Bayesian Elo ratings
- Rolling form statistics
- Head-to-head records
- Expected goals calculations

## Common Issues and Solutions

### Issue: Team Name Inconsistencies
**Problem**: Same team appears with different names
**Solution**: Implement team name standardization before processing

```python
team_mapping = {
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Spurs": "Tottenham"
}
```

### Issue: Missing Date Information
**Problem**: Unparseable date formats
**Solution**: Use pandas flexible date parsing

```python
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
```

### Issue: Invalid Goal Counts
**Problem**: Negative goals or non-integer values
**Solution**: Data validation and cleaning

```python
df['FTHG'] = pd.to_numeric(df['FTHG'], errors='coerce').fillna(0).astype(int)
df['FTAG'] = pd.to_numeric(df['FTAG'], errors='coerce').fillna(0).astype(int)
```

## Testing Data Quality

### Validation Script

Run the following to validate your data:

```python
from footy.data_cleaning import explore_dataset

# Load your data
df = pd.read_excel('your_data.xlsx', sheet_name='E0')

# Validate structure
exploration = explore_dataset(df)
print(f"Unique teams: {len(exploration['unique_home_teams'])}")
print(f"Missing values: {exploration['missing_values'].sum()}")
```

### Expected Output
- No missing values in core columns
- Consistent team names across home/away
- Valid date ranges
- Logical goal distributions

## Best Practices

1. **Consistency**: Use standardized team names and formats
2. **Completeness**: Include full seasons when possible
3. **Validation**: Test data quality before processing
4. **Documentation**: Document any custom league codes or formats
5. **Version Control**: Keep track of data updates and changes

## Troubleshooting

### Common Error Messages

**"No season files found in data/raw"**
- Ensure files follow naming convention: `all-euro-data-YYYY-YYYY.xlsx`
- Check file permissions and location

**"Invalid team names detected"**
- Verify team name consistency
- Check for special characters or extra spaces

**"Date parsing failed"**
- Ensure dates are in recognizable format
- Check for invalid date values

**"Missing required columns"**
- Verify all core columns are present
- Check column names match exactly (case-sensitive)

## Practical Examples

### Example 1: Creating a New League Sheet

For adding a new league (e.g., Portuguese Primeira Liga):

```python
import pandas as pd

# Sample data structure for P1 (Portuguese Primeira Liga)
sample_data = {
    'Date': ['2024-01-15', '2024-01-15', '2024-01-16'],
    'HomeTeam': ['Benfica', 'Porto', 'Sporting CP'],
    'AwayTeam': ['Braga', 'Guimarães', 'Vitória'],
    'FTHG': [2, 1, 3],
    'FTAG': [1, 0, 1],
    'FTR': ['H', 'H', 'H'],
    'B365H': [1.85, 2.10, 1.65],
    'B365D': [3.40, 3.20, 4.20],
    'B365A': [4.50, 3.80, 5.50]
}

df = pd.DataFrame(sample_data)

# Save to Excel with P1 as sheet name
with pd.ExcelWriter('all-euro-data-2024-2025.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='P1', index=False)
```

### Example 2: Data Validation Script

```python
def validate_league_data(file_path, sheet_name):
    """Validate a single league's data format"""
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Check required columns
        required_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Validate data types
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date'].isnull().any():
            return False, "Invalid date format detected"
        
        # Validate goals are non-negative integers
        if (df['FTHG'] < 0).any() or (df['FTAG'] < 0).any():
            return False, "Negative goal counts found"
        
        # Validate result consistency
        inconsistent_results = []
        for idx, row in df.iterrows():
            if row['FTR'] == 'H' and row['FTHG'] <= row['FTAG']:
                inconsistent_results.append(f"Row {idx}: Home win but goals don't match")
            elif row['FTR'] == 'A' and row['FTHG'] >= row['FTAG']:
                inconsistent_results.append(f"Row {idx}: Away win but goals don't match")
            elif row['FTR'] == 'D' and row['FTHG'] != row['FTAG']:
                inconsistent_results.append(f"Row {idx}: Draw but goals don't match")
        
        if inconsistent_results:
            return False, f"Result inconsistencies: {inconsistent_results[:3]}"
        
        return True, f"Validation passed for {len(df)} matches"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# Usage
is_valid, message = validate_league_data('all-euro-data-2024-2025.xlsx', 'E0')
print(f"Validation result: {is_valid}, Message: {message}")
```

### Example 3: Team Name Standardization

```python
def standardize_team_names(df, team_mapping):
    """Standardize team names using a mapping dictionary"""
    
    # Common team name variations
    team_mapping = {
        'Man United': 'Manchester United',
        'Man City': 'Manchester City',
        'Man Utd': 'Manchester United',
        'Tottenham': 'Tottenham Hotspur',
        'Spurs': 'Tottenham Hotspur',
        'Brighton': 'Brighton & Hove Albion',
        'Brighton & Hove': 'Brighton & Hove Albion',
        'Wolves': 'Wolverhampton Wanderers',
        'Wolverhampton': 'Wolverhampton Wanderers',
        'West Ham': 'West Ham United',
        'Newcastle': 'Newcastle United',
        'Leicester': 'Leicester City',
        'Aston Villa': 'Aston Villa',
        'Crystal Palace': 'Crystal Palace',
        'Norwich': 'Norwich City',
        'Southampton': 'Southampton',
        'Leeds': 'Leeds United',
        'Burnley': 'Burnley',
        'Watford': 'Watford',
        'Brentford': 'Brentford'
    }
    
    df['HomeTeam'] = df['HomeTeam'].map(team_mapping).fillna(df['HomeTeam'])
    df['AwayTeam'] = df['AwayTeam'].map(team_mapping).fillna(df['AwayTeam'])
    
    return df
```

### Example 4: Season File Creation

```python
def create_season_file(season_data, season_name, output_path):
    """Create a properly formatted season file"""
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for league_code, league_df in season_data.items():
            # Ensure all required columns exist
            required_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
            
            # Add missing columns with default values
            for col in required_cols:
                if col not in league_df.columns:
                    if col == 'Date':
                        league_df[col] = pd.Timestamp.now()
                    elif col in ['FTHG', 'FTAG']:
                        league_df[col] = 0
                    elif col == 'FTR':
                        league_df[col] = 'D'
                    else:
                        league_df[col] = 'Unknown'
            
            # Clean and validate data
            league_df = standardize_team_names(league_df, {})
            league_df['Date'] = pd.to_datetime(league_df['Date'], errors='coerce')
            
            # Save to sheet
            league_df.to_excel(writer, sheet_name=league_code, index=False)
    
    print(f"Created season file: {output_path}")
    print(f"Sheets: {list(season_data.keys())}")
```

### Example 5: Integration with Global Data

```python
def integrate_new_league_data(new_league_file, target_season_file):
    """Integrate new league data into existing season file"""
    
    # Read existing data
    existing_data = pd.read_excel(target_season_file, sheet_name=None)
    
    # Read new league data
    new_data = pd.read_excel(new_league_file, sheet_name=None)
    
    # Merge data
    merged_data = existing_data.copy()
    merged_data.update(new_data)
    
    # Save merged data
    output_file = target_season_file.replace('.xlsx', '-expanded.xlsx')
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name, sheet_data in merged_data.items():
            sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"Integrated data saved to: {output_file}")
    return output_file
```

## Data Quality Checklist

Before submitting data files, ensure they pass this checklist:

### ✅ File Structure
- [ ] File follows naming convention: `all-euro-data-YYYY-YYYY.xlsx`
- [ ] Multiple worksheets, one per league
- [ ] Sheet names use standard league codes (E0, D1, SP1, etc.)

### ✅ Column Requirements
- [ ] All required columns present: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR
- [ ] Column names match exactly (case-sensitive)
- [ ] No extra spaces or special characters in column names

### ✅ Data Quality
- [ ] Dates are in parseable format
- [ ] Team names are consistent throughout
- [ ] Goal counts are non-negative integers
- [ ] Results (FTR) match actual goal differences
- [ ] No more than 5% missing values in core columns

### ✅ Content Validation
- [ ] Minimum 30 matches per league
- [ ] Complete seasons preferred
- [ ] Realistic goal distributions
- [ ] Valid team combinations (no team vs itself)

## Support and Contributions

For questions about data format requirements:
1. Check this documentation first
2. Review existing data files for examples
3. Use the validation scripts provided above
4. Open an issue with specific questions
5. Submit a pull request with data format improvements

Remember: Well-formatted data is crucial for accurate predictions and smooth processing through the entire pipeline.
