import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Server configuration
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

# Database configuration
CUSTOM_DB_URL = os.environ.get("DATABASE_URL")

IS_VERCEL = os.environ.get("VERCEL") == "1" or os.environ.get("NOW_BUILDER") is not None or not os.access(BASE_DIR, os.W_OK)

if CUSTOM_DB_URL:
    DATABASE_URL = CUSTOM_DB_URL
elif IS_VERCEL:
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "/tmp/networking_assistant.db")
    # Temporary demo storage. Curated sample documents are seeded at startup.
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
else:
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "networking_assistant.db"))
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# NLP Model configurations
NLP_THEME_MODEL = os.environ.get("NLP_THEME_MODEL", "distilbert-base-uncased")
NLP_GENERATOR_MODEL = os.environ.get("NLP_GENERATOR_MODEL", "gpt2")

# Wikipedia client configuration
WIKI_USER_AGENT = os.environ.get("WIKI_USER_AGENT", "PersonalizedNetworkingAssistant/1.0 (contact@example.com)")
