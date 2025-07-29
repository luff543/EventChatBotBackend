import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# EventGO API Configuration
EVENTGO_API_BASE = os.getenv("EVENTGO_API_BASE", "https://eventgo.widm.csie.ncu.edu.tw:3006")

# Database Configuration
DATABASE_URL = "sqlite:///./event_chatbot.db"

# API Configuration
API_PREFIX = "/api"
API_TITLE = "Event Chatbot API"
API_DESCRIPTION = "A FastAPI-based backend service for an event chatbot"
API_VERSION = "1.0.0"

# 分頁配置
DEFAULT_EVENTS_PER_PAGE = 5 