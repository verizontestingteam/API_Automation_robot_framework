import os
from pathlib import Path

from dotenv import load_dotenv

# Load the project's .env; real environment variables (e.g. in CI) take priority
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
USERNAME = os.getenv("API_USERNAME", "")
PASSWORD = os.getenv("API_PASSWORD", "")
