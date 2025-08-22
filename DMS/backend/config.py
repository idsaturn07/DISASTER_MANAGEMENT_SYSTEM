import os
from dotenv import load_dotenv
import urllib.parse

# Load .env file
load_dotenv()

# Database settings
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "disaster_mgmt")

# URL-encode the password
DB_PASS_ENCODED = urllib.parse.quote(DB_PASS)

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS_ENCODED}@{DB_HOST}/{DB_NAME}"

# Twilio settings
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_AUTH = os.getenv("TWILIO_AUTH", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE", "")

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")
JWT_ALGORITHM = "HS256"
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "1440"))

# OTP settings
OTP_TTL = int(os.getenv("OTP_TTL_SECONDS", "300"))