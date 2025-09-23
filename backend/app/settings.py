from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None

    # Azure optional
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None

    DATA_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    ALLOWED_ORIGINS: List[str] = ["*"]  # tighten in prod
    PUBLIC_BASE_URL: str | None = None

settings = Settings()
