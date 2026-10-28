import os
from pathlib import Path

from dotenv import load_dotenv

# Load the root .env (one level above web/)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    API_BASE_URL = os.environ.get("API_BASE_URL", "")
