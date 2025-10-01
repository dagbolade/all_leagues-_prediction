# constants.py - Central configuration for the football prediction pipeline
"""
Central configuration and constants for the football prediction pipeline.
This file contains all magic numbers, hard-coded values, and configuration
constants used throughout the main.py script.
"""

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================
class SystemConfig:
    """System-level configuration constants"""
    TF_LOG_LEVEL_ERROR_ONLY = '3'  # Suppress all TensorFlow logs except errors
    WARNINGS_FILTER = 'ignore'
    
# ============================================================================
# DATA PATHS
# ============================================================================
class DataPaths:
    """Centralized path configuration"""
    RAW_DATA_DIR = "data/raw"
    PROCESSED_DATA_DIR = "data/processed"
    MODELS_DIR = "models"
    
    # File patterns
    SEASON_FILE_PATTERN = "all-euro-data-*.xlsx"
    MODEL_FILE_NAME = "football_models.joblib"
    PROCESSED_DATA_FILE = "enhanced_bayesian_data.pkl"
    PROCESSED_CSV_FILE = "enhanced_bayesian_features.csv"

# ============================================================================
# ELO RATING CONSTRAINTS
# ============================================================================
class EloRatingBounds:
    """Realistic Elo rating boundaries for validation"""
    AVG_ELO_MIN = 1200  # Minimum acceptable average Elo
    AVG_ELO_MAX = 1800  # Maximum acceptable average Elo
    ABSOLUTE_MIN = 1000  # Absolute minimum Elo rating
    ABSOLUTE_MAX = 2000  # Absolute maximum Elo rating
    
    # Starting Elo for new teams
    DEFAULT_ELO = 1500

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================
class DisplayConfig:
    """Console output formatting constants"""
    MAJOR_SEPARATOR_LENGTH = 80  # Main section separators (=)
    MINOR_SEPARATOR_LENGTH = 50  # Sub-section separators (-)
    SECTION_SEPARATOR_LENGTH = 60  # Mid-level separators
    MATCH_SEPARATOR_LENGTH = 40  # Individual match separators
    MATCH_HEADER_LENGTH = 20   # Match header separators
    
    # Display limits
    MAX_SCORELINES_TO_SHOW = 3  # Top N most likely scorelines to display
    MAX_TEST_MATCHES = 5  # Number of test predictions to run
    
# ============================================================================
# PREDICTION CONFIGURATION
# ============================================================================
class PredictionConfig:
    """Match prediction configuration"""
    # Markets to validate for logical consistency
    GOAL_MARKETS = ['Over 1.5 Goals', 'Over 2.5 Goals', 'Over 3.5 Goals']
    
    # Key prediction fields to display
    KEY_MARKETS = ['Match Outcome', 'Over 1.5 Goals', 'Over 2.5 Goals', 
                   'Over 3.5 Goals', 'Both Teams to Score', 'Total Goals']

# ============================================================================
# FEATURE ENGINEERING
# ============================================================================
class FeaturePatterns:
    """Feature name patterns for filtering and identification"""
    # Patterns for Bayesian rolling features
    BAYESIAN_FEATURES = ['Bayesian', 'Elo', 'Form', 'Scoring', 'Over', 'BTTS', 'Expected']
    
    # Patterns for engineered features
    ENGINEERED_FEATURES = ['Bayesian', 'MatchOutcome', 'H2H', 'Ref', 'GW1']
    
    # Columns to exclude from feature count (metadata columns)
    METADATA_COLUMNS = ['Date', 'HomeTeam', 'AwayTeam', 'League', 'Season', 
                        'FTR', 'FTHG', 'FTAG']

# ============================================================================
# TEST DATA
# ============================================================================
class TestData:
    """Test fixtures and sample data for validation"""
    # Test match pairs for system validation
    VALIDATION_MATCHES = [
        ('Arsenal', 'Chelsea'),
        ('Man City', 'Liverpool'),
        ('Tottenham', 'Brighton'),
        ('Newcastle', 'West Ham'),
        ('Wolves', 'Fulham')
    ]
    
    # EPL 2024/25 season opening fixtures
    EPL_OPENING_FIXTURES_2024_25 = [
        ('Arsenal', 'Wolves'),
        ('Brighton', 'Man United'),
        ('Chelsea', 'Man City'),
        ('Liverpool', 'Ipswich'),
        ('Newcastle', 'Southampton')
    ]

# ============================================================================
# DATA LOADING
# ============================================================================
class DataLoadingConfig:
    """Configuration for data loading operations"""
    EXPECTED_SEASONS_COUNT = 5  # Expected number of seasons to load
    MIN_REQUIRED_SEASONS = 3    # Minimum seasons needed for training
    
# ============================================================================
# PHASE NAMES
# ============================================================================
class PhaseNames:
    """Standardized phase names for pipeline execution"""
    PHASE_1 = "ENHANCED DATA LOADING & CLEANING"
    PHASE_2 = "ENHANCED BAYESIAN FEATURE ENGINEERING"
    PHASE_3 = "ENHANCED BAYESIAN MODEL TRAINING"
    PHASE_4 = "ENHANCED BAYESIAN MATCH PREDICTOR SETUP"
    PHASE_5 = "ENHANCED EPL ANALYSIS"
    PHASE_6 = "ENHANCED BAYESIAN MATCH PREDICTIONS"
    PHASE_7 = "BAYESIAN SYSTEM VALIDATION & SUMMARY"
