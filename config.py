"""Configuration settings for the sports betting parlay system."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
SPORTSDATA_API_KEY = os.getenv("SPORTSDATA_API_KEY", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "5e2b67818amsh444061baac2cbe6p1ad5efjsned7d83858933")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sports_betting.db")

# Notion Integration
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")

# Twilio SMS Configuration (for hourly picks texting)
# Get these from https://www.twilio.com/console
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")  # Your Twilio phone number
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER", "")  # Your phone number to receive texts

# Default Configuration
DEFAULT_SPORTS = os.getenv("DEFAULT_SPORTS", "NBA,NFL,MLB,NHL,UFC,BOXING").split(",")
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.6"))
MAX_PARLAY_LEGS = int(os.getenv("MAX_PARLAY_LEGS", "15"))
MIN_PARLAY_LEGS = int(os.getenv("MIN_PARLAY_LEGS", "2"))

# API Endpoints
SPORTSDATA_BASE_URL = "https://api.sportsdata.io/v3"
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
RAPIDAPI_SPORTSBOOK_BASE_URL = "https://sportsbook-api2.p.rapidapi.com"
RAPIDAPI_SPORTSBOOK_HOST = "sportsbook-api2.p.rapidapi.com"

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

