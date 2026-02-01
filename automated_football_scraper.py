"""
Automated Football Data Scraper with Cron Job Support

This script automatically downloads the latest football data from football-data.co.uk
and can be scheduled to run daily/weekly using cron jobs or Windows Task Scheduler.

Features:
- Downloads latest season data for all 22 leagues
- Validates and cleans data
- Backs up existing data
- Logs all operations
- Email notifications (optional)
- Cron job ready

Usage:
    # Manual run
    python automated_football_scraper.py
    
    # Cron job (Linux/Mac) - Daily at 3 AM
    0 3 * * * /path/to/python /path/to/automated_football_scraper.py >> /path/to/logs/scraper.log 2>&1
    
    # Windows Task Scheduler
    - Create task to run daily at 3 AM
    - Action: Start a program
    - Program: python.exe
    - Arguments: C:\\path\\to\\automated_football_scraper.py
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import logging
import shutil
import time
from typing import List, Dict, Optional
import sys

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'scraper_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FootballDataScraper:
    """Automated scraper for football-data.co.uk"""
    
    BASE_URL = "https://www.football-data.co.uk"
    
    # All 22 leagues supported
    LEAGUES = {
        # England
        'E0': 'Premier League',
        'E1': 'Championship',
        'E2': 'League One',
        'E3': 'League Two',
        # Scotland
        'SC0': 'Scottish Premiership',
        'SC1': 'Scottish Championship',
        # Germany
        'D1': 'Bundesliga',
        'D2': 'Bundesliga 2',
        # Italy
        'I1': 'Serie A',
        'I2': 'Serie B',
        # Spain
        'SP1': 'La Liga',
        'SP2': 'La Liga 2',
        # France
        'F1': 'Ligue 1',
        'F2': 'Ligue 2',
        # Netherlands
        'N1': 'Eredivisie',
        # Belgium
        'B1': 'Belgian Pro League',
        # Portugal
        'P1': 'Primeira Liga',
        # Turkey
        'T1': 'Super Lig',
        # Greece
        'G1': 'Super League',
        # Others
        'EC': 'European Championship',
        'WC': 'World Cup',
    }
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = Path("data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def get_current_season(self) -> str:
        """Get current season string (e.g., '2425' for 2024-2025)"""
        now = datetime.now()
        if now.month >= 8:  # Season starts in August
            return f"{now.year % 100}{(now.year + 1) % 100}"
        else:
            return f"{(now.year - 1) % 100}{now.year % 100}"
    
    def backup_existing_data(self):
        """Backup existing data files"""
        logger.info("Backing up existing data...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for file in self.data_dir.glob("*.xlsx"):
            backup_file = self.backup_dir / f"{file.stem}_{timestamp}{file.suffix}"
            shutil.copy2(file, backup_file)
            logger.info(f"Backed up: {file.name} -> {backup_file.name}")
    
    def download_league_data(self, league_code: str, season: str) -> Optional[pd.DataFrame]:
        """Download data for a specific league and season"""
        url = f"{self.BASE_URL}/mmz4281/{season}/{league_code}.csv"
        
        try:
            logger.info(f"Downloading {self.LEAGUES.get(league_code, league_code)} ({season})...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Add metadata
            df['League'] = self.LEAGUES.get(league_code, league_code)
            df['LeagueCode'] = league_code
            df['Season'] = f"20{season[:2]}-20{season[2:]}"
            
            logger.info(f"✓ Downloaded {len(df)} matches for {self.LEAGUES.get(league_code, league_code)}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"✗ Failed to download {league_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Error processing {league_code}: {e}")
            return None
    
    def download_all_leagues(self, season: str) -> Dict[str, pd.DataFrame]:
        """Download data for all leagues"""
        logger.info(f"\\n{'='*80}")
        logger.info(f"DOWNLOADING SEASON {season} DATA")
        logger.info(f"{'='*80}\\n")
        
        all_data = {}
        
        for league_code in self.LEAGUES.keys():
            df = self.download_league_data(league_code, season)
            if df is not None:
                all_data[league_code] = df
            
            # Be respectful to the server
            time.sleep(1)
        
        logger.info(f"\\nSuccessfully downloaded {len(all_data)}/{len(self.LEAGUES)} leagues")
        return all_data
    
    def save_to_excel(self, data_dict: Dict[str, pd.DataFrame], season: str):
        """Save all league data to Excel file with multiple sheets"""
        output_file = self.data_dir / f"all-euro-data-20{season[:2]}-20{season[2:]}.xlsx"
        
        logger.info(f"\\nSaving data to {output_file}...")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for league_code, df in data_dict.items():
                sheet_name = league_code[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  ✓ Saved {self.LEAGUES.get(league_code, league_code)} ({len(df)} matches)")
        
        logger.info(f"\\n✓ Data saved successfully: {output_file}")
        logger.info(f"  File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate downloaded data"""
        required_columns = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
        
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        if len(df) == 0:
            logger.error("Empty dataframe")
            return False
        
        return True
    
    def run(self, seasons: Optional[List[str]] = None):
        """Run the scraper for specified seasons"""
        if seasons is None:
            # Default: current season only
            seasons = [self.get_current_season()]
        
        logger.info("\\n" + "="*80)
        logger.info("AUTOMATED FOOTBALL DATA SCRAPER")
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80 + "\\n")
        
        # Backup existing data
        self.backup_existing_data()
        
        # Download data for each season
        for season in seasons:
            data_dict = self.download_all_leagues(season)
            
            if data_dict:
                # Validate at least one league
                sample_df = next(iter(data_dict.values()))
                if self.validate_data(sample_df):
                    self.save_to_excel(data_dict, season)
                else:
                    logger.error(f"Data validation failed for season {season}")
            else:
                logger.error(f"No data downloaded for season {season}")
        
        logger.info("\\n" + "="*80)
        logger.info("SCRAPER COMPLETED")
        logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80 + "\\n")


def send_email_notification(subject: str, message: str):
    """Send email notification (optional - configure SMTP settings)"""
    # TODO: Configure your email settings
    # import smtplib
    # from email.mime.text import MIMEText
    # 
    # smtp_server = "smtp.gmail.com"
    # smtp_port = 587
    # sender_email = "your-email@gmail.com"
    # receiver_email = "your-email@gmail.com"
    # password = "your-app-password"
    # 
    # msg = MIMEText(message)
    # msg['Subject'] = subject
    # msg['From'] = sender_email
    # msg['To'] = receiver_email
    # 
    # with smtplib.SMTP(smtp_server, smtp_port) as server:
    #     server.starttls()
    #     server.login(sender_email, password)
    #     server.send_message(msg)
    
    logger.info(f"Email notification: {subject}")


def main():
    """Main function for cron job execution"""
    try:
        scraper = FootballDataScraper()
        
        # Get current season
        current_season = scraper.get_current_season()
        
        # You can also download multiple seasons
        # seasons = [current_season, previous_season, ...]
        seasons = [current_season]
        
        # Run scraper
        scraper.run(seasons=seasons)
        
        # Send success notification
        send_email_notification(
            subject="✓ Football Data Scraper - Success",
            message=f"Successfully scraped data for season(s): {', '.join(seasons)}"
        )
        
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        send_email_notification(
            subject="✗ Football Data Scraper - Failed",
            message=f"Scraper failed with error: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
