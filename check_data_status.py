"""
Check current season data status
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# Check current season file
data_file = Path("data/raw/all-euro-data-2025-2026.xlsx")

if data_file.exists():
    print(f"File: {data_file.name}")
    print(f"Size: {data_file.stat().st_size / 1024:.1f} KB")
    print(f"Last Modified: {datetime.fromtimestamp(data_file.stat().st_mtime)}")
    print("\n" + "="*80)
    
    # Check Premier League
    try:
        df = pd.read_excel(data_file, sheet_name='E0')
        print(f"\nPREMIER LEAGUE (E0)")
        print(f"Total matches: {len(df)}")
        
        if len(df) > 0:
            print(f"Latest match date: {df['Date'].max()}")
            print(f"\nLast 10 matches:")
            print(df[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].tail(10).to_string(index=False))
        else:
            print("No matches found!")
            
    except Exception as e:
        print(f"Error reading Premier League data: {e}")
    
    # Check all leagues
    print("\n" + "="*80)
    print("\nALL LEAGUES STATUS:")
    xl_file = pd.ExcelFile(data_file)
    for sheet in xl_file.sheet_names:
        try:
            df = pd.read_excel(data_file, sheet_name=sheet)
            print(f"  {sheet}: {len(df)} matches")
        except:
            print(f"  {sheet}: Error reading")
            
else:
    print(f"File not found: {data_file}")
    print("\nAvailable files:")
    for f in Path("data/raw").glob("*.xlsx"):
        print(f"  - {f.name}")
