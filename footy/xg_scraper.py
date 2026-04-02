import pandas as pd
from typing import Dict, Optional, List
import logging
from datetime import datetime
try:
    from understatapi import UnderstatClient
except ImportError:
    pass

logger = logging.getLogger(__name__)

class ExpectedGoalsScraper:
    """Scrapes Expected Goals (xG) data from Understat and maps it to football-data.co.uk formats."""
    
    def __init__(self):
        try:
            self.client = UnderstatClient()
        except NameError:
            logger.error("understatapi not installed. Install via: pip install understatapi")
            self.client = None
            
        # Map football-data Division to Understat League
        self.LEAGUE_MAPPING = {
            'E0': 'EPL',          # Premier League
            'SP1': 'La_Liga',     # La Liga
            'I1': 'Serie_A',      # Serie A
            'D1': 'Bundesliga',   # Bundesliga
            'F1': 'Ligue_1'       # Ligue 1
        }
        
        # Map Understat team names to football-data.co.uk team names
        self.TEAM_MAPPING = {
            # EPL
            'Manchester United': 'Man United',
            'Manchester City': 'Man City',
            'Newcastle United': 'Newcastle',
            'Wolverhampton Wanderers': 'Wolves',
            'Nottingham Forest': 'Nott\'m Forest',
            'Sheffield United': 'Sheffield United',
            'Tottenham': 'Tottenham',
            'Aston Villa': 'Aston Villa',
            'West Ham': 'West Ham',
            # La Liga
            'Real Madrid': 'Real Madrid',
            'Athletic Club': 'Athletic Club', # football-data sometimes uses 'Ath Bilbao' or 'Athletic Club'
            'Atletico Madrid': 'Ath Madrid', 
            'Celta Vigo': 'Celta',
            'Real Betis': 'Betis',
            'Real Sociedad': 'Sociedad',
            'Rayo Vallecano': 'Vallecano',
            'Cadiz': 'Cadiz',
            # Serie A
            'AC Milan': 'Milan',
            'Inter': 'Inter',
            'Roma': 'Roma',
            'Juventus': 'Juventus',
            'Lazio': 'Lazio',
            'Napoli': 'Napoli',
            'Bologna': 'Bologna',
            'Hellas Verona': 'Verona',
            # Bundesliga
            'Bayern Munich': 'Bayern Munich',
            'Bayer Leverkusen': 'Leverkusen',
            'Borussia Dortmund': 'Dortmund',
            'Borussia M.Gladbach': 'M\'gladbach',
            'Eintracht Frankfurt': 'Ein Frankfurt',
            'VfB Stuttgart': 'Stuttgart',
            'Union Berlin': 'Union Berlin',
            'Werder Bremen': 'Werder Bremen',
            # Ligue 1
            'Paris Saint Germain': 'PSG',
            'Marseille': 'Marseille',
            'Lyon': 'Lyon',
            'Lille': 'Lille',
            'Monaco': 'Monaco'
        }

    def _normalize_team_name(self, understat_name: str) -> str:
        """Convert Understat team name to football-data team name format."""
        return self.TEAM_MAPPING.get(understat_name, understat_name)

    def fetch_season_xg(self, div: str, year: str) -> pd.DataFrame:
        """
        Fetch all matches for a specific league and year.
        Year should be start year (e.g. '2024' for 2024/2025 season).
        Returns a DataFrame with ['Date', 'HomeTeam', 'AwayTeam', 'Home_xG', 'Away_xG']
        """
        if not self.client:
            return pd.DataFrame()
            
        understat_league = self.LEAGUE_MAPPING.get(div)
        if not understat_league:
            return pd.DataFrame() # Competition not supported by Understat
            
        logger.info(f"Fetching xG data for {understat_league} {year}...")
        
        try:
            league_client = self.client.league(league=understat_league)
            matches = league_client.get_match_data(season=year)
            
            data = []
            for match in matches:
                # Understat date format: '2024-08-16 19:00:00'
                date_str = match['datetime'].split(' ')[0] 
                
                home_team = self._normalize_team_name(match['h']['title'])
                away_team = self._normalize_team_name(match['a']['title'])
                
                home_xg_val = match['xG']['h']
                away_xg_val = match['xG']['a']
                
                # Future or postponed matches have no xG yet
                if home_xg_val is None or away_xg_val is None:
                    continue
                    
                home_xg = float(home_xg_val)
                away_xg = float(away_xg_val)
                
                data.append({
                    'Date': pd.to_datetime(date_str),
                    'HomeTeam': home_team,
                    'AwayTeam': away_team,
                    'Home_xG': home_xg,
                    'Away_xG': away_xg,
                    'League': div
                })
                
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            logger.error(f"Error fetching xG data for {div} {year}: {e}")
            return pd.DataFrame()

    def merge_xg_to_matches(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Matches a subset of football-data matches with their expected goals.
        Optimized by fetching only the needed years/leagues in bulk.
        """
        if matches_df.empty or not self.client:
            return matches_df
            
        result_df = matches_df.copy()
        
        # Determine which seasons and leagues we need to fetch
        # matches_df should have 'Date', 'HomeTeam', 'AwayTeam', 'Div' or 'League'
        # Fallback to identify league if not explicitly named
        league_col = 'League' if 'League' in result_df.columns else 'Div' if 'Div' in result_df.columns else None
        
        if not league_col:
            # Assume Premier League E0 if unknown
            result_df['League'] = 'E0'
            league_col = 'League'
            
        # Get unique year/league combinations
        # Note: August 2024 is part of the '2024' season. May 2025 is part of '2024' season.
        def get_season_start_year(date):
            if date.month >= 8:
                return str(date.year)
            else:
                return str(date.year - 1)
                
        result_df['season_year'] = pd.to_datetime(result_df['Date']).apply(get_season_start_year)
        
        # Avoid refetching same year/league multiple times
        needed_combos = result_df[[league_col, 'season_year']].drop_duplicates()
        
        all_xg_data = []
        for _, row in needed_combos.iterrows():
            league = row[league_col]
            year = row['season_year']
            
            # Fetch bulk data
            xg_df = self.fetch_season_xg(league, year)
            if not xg_df.empty:
                all_xg_data.append(xg_df)
                
        if not all_xg_data:
            logger.warning("Could not fetch any xG data for these matches.")
            # Ensure columns exist with NaN
            if 'Home_xG' not in result_df.columns:
                result_df['Home_xG'] = float('nan')
                result_df['Away_xG'] = float('nan')
            return result_df.drop(columns=['season_year'])
            
        # Merge the full xG database
        full_xg_df = pd.concat(all_xg_data, ignore_index=True)
        
        # Merge on Date, HomeTeam, AwayTeam
        # Convert Dates strictly to match
        result_df['Date'] = pd.to_datetime(result_df['Date'])
        full_xg_df['Date'] = pd.to_datetime(full_xg_df['Date'])
        
        # Perform left join
        merged = pd.merge(
            result_df, 
            full_xg_df[['Date', 'HomeTeam', 'AwayTeam', 'Home_xG', 'Away_xG']], 
            on=['Date', 'HomeTeam', 'AwayTeam'], 
            how='left'
        )
        
        # Instead of _x / _y from identical columns, check if we created dupes
        if 'Home_xG_x' in merged.columns and 'Home_xG_y' in merged.columns:
            merged['Home_xG'] = merged['Home_xG_y'].fillna(merged['Home_xG_x'])
            merged['Away_xG'] = merged['Away_xG_y'].fillna(merged['Away_xG_x'])
            merged = merged.drop(columns=['Home_xG_x', 'Home_xG_y', 'Away_xG_x', 'Away_xG_y'])
            
        merged = merged.drop(columns=['season_year'])
        return merged

if __name__ == "__main__":
    # Test script locally
    logging.basicConfig(level=logging.INFO)
    scraper = ExpectedGoalsScraper()
    df = scraper.fetch_season_xg('E0', '2024')
    if not df.empty:
        print(f"Successfully fetched {len(df)} xG match records.")
        print(df.tail())
    else:
        print("Failed to fetch data.")
