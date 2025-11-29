import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    # Database
    DATABASE_URL = "sqlite:///./tictactoe.db"
    # Security
    SECRET_KEY = "your-secret-key-change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 120
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

settings = Settings()
