# global_data_integration.py - Integrate with your existing pipeline

import pandas as pd
import numpy as np
from global_config import (
    SeasonConfig, FileConfig, DataConfig, LeagueMappings, LoggingConfig
)
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GlobalDataIntegrator:
    """Integrates global leagues data with your existing multi-sheet season structure"""

    def __init__(self):
        self.league_mappings = {
            'ARG': 'ARG1',  # Argentina Primera
            'AUT': 'AUT1',  # Austria Bundesliga
            'BRA': 'BRA1',  # Brazil Serie A
            'CHN': 'CHN1',  # China Super League
            'DNK': 'DNK1',  # Denmark Superliga
            'FIN': 'FIN1',  # Finland Veikkausliiga
            'IRL': 'IRL1',  # Ireland Premier
            'JPN': 'JPN1',  # Japan J1 League
            'MEX': 'MEX1',  # Mexico Liga MX
            'NOR': 'NOR1',  # Norway Eliteserien
            'POL': 'POL1',  # Poland Ekstraklasa
            'ROU': 'ROU1',  # Romania Liga 1
            'RUS': 'RUS1',  # Russia Premier League
            'SWE': 'SWE1',  # Sweden Allsvenskan
            'SWZ': 'SWZ1',  # Switzerland Super League
            'USA': 'USA1'  # USA MLS
        }

    def process_global_excel_to_season_sheets(self, global_excel_path, output_dir):
        """Convert global Excel to season-based multi-sheet files matching your structure"""

        logger.info(f"Processing global data: {global_excel_path}")

        # Read all sheets from global file
        global_data = pd.ExcelFile(global_excel_path)

        # Process each country sheet
        all_season_data = {}

        for sheet_name in global_data.sheet_names:
            logger.info(f"Processing country: {sheet_name}")

            df = pd.read_excel(global_excel_path, sheet_name=sheet_name)

            # Standardize columns to match your format
            df_standardized = self.standardize_dataframe(df, sheet_name)

            # Group by season and add to season collections
            for season, season_data in df_standardized.groupby('Season'):
                if season not in all_season_data:
                    all_season_data[season] = {}

                # Use league code as sheet name (like E0, D1, etc.)
                league_code = self.league_mappings.get(sheet_name, sheet_name)
                all_season_data[season][league_code] = season_data.drop('Season', axis=1)

        # Create season files matching your structure
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        created_files = []
        for season, league_sheets in all_season_data.items():

            # Skip seasons outside your target range
            if not self.is_target_season(season):
                continue

            # Create filename matching your pattern
            filename = f"all-euro-data-{season}.xlsx"
            filepath = output_path / filename

            # Write multi-sheet Excel file
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for league_code, league_data in league_sheets.items():
                    if len(league_data) > 0:
                        league_data.to_excel(writer, sheet_name=league_code, index=False)

            logger.info(f"Created: {filename} with {len(league_sheets)} leagues")
            created_files.append(filepath)

        return created_files

    def standardize_dataframe(self, df, country_code):
        """Standardize dataframe to match your existing column structure"""

        standardized = pd.DataFrame()

        # Column mappings
        column_map = {
            'Date': 'Date',
            'Home': 'HomeTeam',
            'Away': 'AwayTeam',
            'HG': 'FTHG',
            'AG': 'FTAG',
            'Res': 'FTR',
            'Season': 'Season'
        }

        # Map columns
        for old_col, new_col in column_map.items():
            if old_col in df.columns:
                standardized[new_col] = df[old_col]

        # Add required columns
        standardized['League'] = self.league_mappings.get(country_code, country_code)

        # Standardize season format
        standardized['Season'] = standardized['Season'].apply(self.standardize_season)

        # Clean data types
        standardized['Date'] = pd.to_datetime(standardized['Date'], errors='coerce')
        standardized['FTHG'] = pd.to_numeric(standardized['FTHG'], errors='coerce').fillna(0).astype(int)
        standardized['FTAG'] = pd.to_numeric(standardized['FTAG'], errors='coerce').fillna(0).astype(int)

        # Handle FTR (Result)
        ftr_map = {'H': 'H', 'D': 'D', 'A': 'A'}
        standardized['FTR'] = standardized['FTR'].map(ftr_map).fillna('D')

        # Add betting odds columns if available
        odds_cols = ['B365H', 'B365D', 'B365A', 'B365>2.5', 'B365<2.5']

        # Map from original betting columns
        if 'PSCH' in df.columns:
            standardized['B365H'] = pd.to_numeric(df['PSCH'], errors='coerce')
        if 'PSCD' in df.columns:
            standardized['B365D'] = pd.to_numeric(df['PSCD'], errors='coerce')
        if 'PSCA' in df.columns:
            standardized['B365A'] = pd.to_numeric(df['PSCA'], errors='coerce')

        # Filter for target seasons only
        standardized = standardized[standardized['Season'].apply(self.is_target_season)]

        return standardized

    def standardize_season(self, season_val):
        """Convert season to YYYY-YYYY format"""
        if pd.isna(season_val):
            return '2024-2025'

        season_str = str(season_val).strip()

        # Handle different formats
        if '/' in season_str:
            parts = season_str.split('/')
            if len(parts) == 2:
                year1 = int(parts[0])
                year2 = int(parts[1])
                if year2 < 100:
                    year2 = 2000 + year2
                return f"{year1}-{year2}"

        elif len(season_str) == 4 and season_str.isdigit():
            year = int(season_str)
            return f"{year}-{year + 1}"

        elif '-' in season_str:
            return season_str

        return '2024-2025'

    def is_target_season(self, season):
        """Check if season is in target range (2021-2025)"""
        target_years = ['2021', '2022', '2023', '2024', '2025']
        return any(year in str(season) for year in target_years)

    def merge_with_existing_season_files(self, global_files, existing_data_dir):
        """Merge global data with existing season files"""

        existing_dir = Path(existing_data_dir)
        merged_files = []

        for global_file in global_files:
            season = self.extract_season_from_filename(global_file.name)
            existing_file = existing_dir / f"all-euro-data-{season}.xlsx"

            if existing_file.exists():
                logger.info(f"Merging {season}: global + existing data")

                # Read both files
                global_data = pd.ExcelFile(global_file)
                existing_data = pd.ExcelFile(existing_file)

                # Combine sheets
                combined_sheets = {}

                # Add existing sheets
                for sheet in existing_data.sheet_names:
                    combined_sheets[sheet] = pd.read_excel(existing_file, sheet_name=sheet)

                # Add global sheets
                for sheet in global_data.sheet_names:
                    if sheet not in combined_sheets:
                        combined_sheets[sheet] = pd.read_excel(global_file, sheet_name=sheet)

                # Write combined file
                output_file = existing_dir / f"all-euro-data-{season}-expanded.xlsx"
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    for sheet_name, sheet_data in combined_sheets.items():
                        sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)

                merged_files.append(output_file)
                logger.info(f"Created merged file: {output_file.name} with {len(combined_sheets)} leagues")

            else:
                # No existing file, just copy global file
                merged_files.append(global_file)

        return merged_files

    def extract_season_from_filename(self, filename):
        """Extract season from filename"""
        import re
        match = re.search(r'(\d{4}-\d{4})', filename)
        return match.group(1) if match else '2024-2025'


def main():
    """Main integration function"""

    integrator = GlobalDataIntegrator()

    # Paths
    global_excel = 'new_leagues_data.xlsx'
    output_dir = 'data/global_processed'
    existing_data_dir = 'data/raw'

    if not Path(global_excel).exists():
        logger.error(f"Global data file not found: {global_excel}")
        return

    # Step 1: Convert global Excel to season-based multi-sheet files
    logger.info("Converting global data to season-based structure...")
    global_season_files = integrator.process_global_excel_to_season_sheets(
        global_excel, output_dir
    )

    # Step 2: Merge with existing data if available
    logger.info("Merging with existing data...")
    final_files = integrator.merge_with_existing_season_files(
        global_season_files, existing_data_dir
    )

    # Step 3: Update your data/raw directory
    raw_dir = Path('data/raw')
    for file in final_files:
        target = raw_dir / file.name.replace('-expanded', '')
        if file.name.endswith('-expanded.xlsx'):
            # Replace original with expanded version
            original = raw_dir / file.name.replace('-expanded', '')
            if original.exists():
                original.unlink()
            file.rename(target)
            logger.info(f"Updated: {target.name}")

    logger.info("Global data integration completed!")
    logger.info("Your existing pipeline can now process the expanded dataset")
    logger.info("Run your main.py to retrain with global data")


if __name__ == "__main__":
    main()
