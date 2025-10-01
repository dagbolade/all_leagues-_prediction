# global_config.py - Configuration for global data integration
"""
Configuration constants for global data integration module.
Contains all magic numbers and hard-coded values used in global_data_integration.py
"""

# ============================================================================
# SEASON CONFIGURATION
# ============================================================================
class SeasonConfig:
    """Season-related configuration constants"""
    # Target season range for analysis
    TARGET_START_YEAR = 2021
    TARGET_END_YEAR = 2025
    TARGET_YEARS = [str(year) for year in range(TARGET_START_YEAR, TARGET_END_YEAR + 1)]
    
    # Default season when unknown or missing
    DEFAULT_SEASON = '2024-2025'
    DEFAULT_YEAR = 2024
    
    # Century conversion for two-digit years
    CENTURY_THRESHOLD = 100  # Years below this are considered 20xx
    BASE_CENTURY = 2000      # Base century for conversion (20xx)
    
    # Season string validation
    YEAR_STRING_LENGTH = 4   # Expected length of a year string (e.g., "2024")

# ============================================================================
# FILE CONFIGURATION
# ============================================================================
class FileConfig:
    """File paths, patterns, and naming conventions"""
    # Default file paths
    DEFAULT_GLOBAL_FILE = 'new_leagues_data.xlsx'
    DEFAULT_OUTPUT_DIR = 'data/global_processed'
    DEFAULT_EXISTING_DIR = 'data/raw'
    
    # File naming patterns
    SEASON_FILE_PREFIX = 'all-euro-data-'
    SEASON_FILE_EXTENSION = '.xlsx'
    EXPANDED_SUFFIX = '-expanded'
    
    # Excel configuration
    EXCEL_ENGINE = 'openpyxl'  # Excel engine for pandas

# ============================================================================
# DATA CONFIGURATION
# ============================================================================
class DataConfig:
    """Data processing and transformation configuration"""
    # Default values for missing or invalid data
    DEFAULT_GOALS = 0       # Default goal count when missing
    DEFAULT_RESULT = 'D'    # Default result (Draw) when missing
    
    # Standard column name mappings
    STANDARD_COLUMN_MAP = {
        'Date': 'Date',
        'Home': 'HomeTeam',
        'Away': 'AwayTeam',
        'HG': 'FTHG',          # Home Goals Full Time
        'AG': 'FTAG',          # Away Goals Full Time
        'Res': 'FTR',          # Full Time Result
        'Season': 'Season'
    }
    
    # Betting odds columns to include
    BETTING_COLUMNS = ['B365H', 'B365D', 'B365A', 'B365>2.5', 'B365<2.5']
    
    # Betting provider column mappings
    BETTING_COLUMN_MAP = {
        'PSCH': 'B365H',  # Pinnacle Sports Home odds -> Bet365 format
        'PSCD': 'B365D',  # Pinnacle Sports Draw odds -> Bet365 format
        'PSCA': 'B365A'   # Pinnacle Sports Away odds -> Bet365 format
    }
    
    # Match result mappings
    RESULT_MAP = {
        'H': 'H',  # Home win
        'D': 'D',  # Draw
        'A': 'A'   # Away win
    }

# ============================================================================
# LEAGUE MAPPINGS
# ============================================================================
class LeagueMappings:
    """Mapping of country codes to league identifiers"""
    LEAGUE_CODES = {
        'ARG': 'ARG1',  # Argentina Primera División
        'AUT': 'AUT1',  # Austria Bundesliga
        'BRA': 'BRA1',  # Brazil Serie A
        'CHN': 'CHN1',  # China Super League
        'DNK': 'DNK1',  # Denmark Superliga
        'FIN': 'FIN1',  # Finland Veikkausliiga
        'IRL': 'IRL1',  # Ireland Premier Division
        'JPN': 'JPN1',  # Japan J1 League
        'MEX': 'MEX1',  # Mexico Liga MX
        'NOR': 'NOR1',  # Norway Eliteserien
        'POL': 'POL1',  # Poland Ekstraklasa
        'ROU': 'ROU1',  # Romania Liga 1
        'RUS': 'RUS1',  # Russia Premier League
        'SWE': 'SWE1',  # Sweden Allsvenskan
        'SWZ': 'SWZ1',  # Switzerland Super League
        'USA': 'USA1'   # USA Major League Soccer
    }

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
class LoggingConfig:
    """Logging configuration constants"""
    DEFAULT_LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
