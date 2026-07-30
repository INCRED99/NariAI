import os

# Load environment variables from .env if present
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Standard config variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "nari")

# Default API keys loaded from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("open_ai_key", ""))
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "serviceaccount.json")

# SMS Provider Configuration
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# Msg91 Credentials
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY", "")
MSG91_SENDER_ID = os.getenv("MSG91_SENDER_ID", "")
MSG91_ROUTE = os.getenv("MSG91_ROUTE", "4")

# Textlocal Credentials
TEXTLOCAL_API_KEY = os.getenv("TEXTLOCAL_API_KEY", "")
TEXTLOCAL_SENDER = os.getenv("TEXTLOCAL_SENDER", "")

# Exotel Credentials
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID", "")
EXOTEL_AUTH_TOKEN = os.getenv("EXOTEL_AUTH_TOKEN", "")
EXOTEL_FROM_NUMBER = os.getenv("EXOTEL_FROM_NUMBER", "")


# Fallback directories for local file DB if MongoDB is offline
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
FALLBACK_DB_PATH = os.path.join(DATA_DIR, "db_fallback.json")
QDRANT_STORAGE_PATH = os.path.join(DATA_DIR, "qdrant_db")
os.makedirs(QDRANT_STORAGE_PATH, exist_ok=True)

# Risk Threshold Constants
RISK_THRESHOLD_WARNING = 45
RISK_THRESHOLD_CRITICAL = 75
