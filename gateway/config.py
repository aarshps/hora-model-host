import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from root or local directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

# App settings
PORT = int(os.getenv("PORT", 8000))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
API_KEY = os.getenv("API_KEY")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:e4b")

if not API_KEY:
    # Raise warning or generate a fallback only for development
    print("WARNING: API_KEY is not set. The gateway will be unprotected!")
