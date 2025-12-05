import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path

load_dotenv()


class Settings(BaseSettings):
    # Database
    db_file: str = "tictactoe.db"
    scheme: str = "sqlite+aiosqlite:///"
    db_dir: Path = Path(__file__).parent.parent / db_file
    DATABASE_URL: str = os.environ.get("DATABASE_URL", f"{scheme}{db_dir}")
    # Security
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "your-secret-key-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BASE_DIR: Path = Path(__file__).parent.parent
    # FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
    FRONTEND_DIR: Path = BASE_DIR / "frontend"


settings = Settings()
