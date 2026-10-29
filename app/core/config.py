from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "control-io-api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/control_io"
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    STORAGE_DIR: str = "./storage"
    MAX_FILE_SIZE_MB: int = 15

    # Auth
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: str = "dev-key-change-me"

    # AI Provider
    AI_PROVIDER: str = "local"
    AI_BASE_URL: str = "http://localhost:11434/v1"
    # gemma4:12b es el modelo local con mejor lectura de manuscrito en las pruebas.
    AI_MODEL: str = "gemma4:12b"
    AI_API_KEY: str = "none"
    AI_TEMPERATURE: float = 0.0
    AI_TIMEOUT_SECONDS: int = 300
    AI_MAX_RETRIES: int = 2

    # Extracción confiable
    AI_MAX_PASSES: int = 2          # lecturas independientes por región
    AI_NUM_CTX: int = 8192
    AI_NUM_PREDICT: int = 2048
    AI_MIN_NAME_SIMILARITY: int = 85  # similitud mínima entre dos lecturas de un nombre
    AI_USE_SECTION_CROPS: bool = True
    AI_TARGET_CROP_WIDTH: int = 1800
    AI_SECOND_PASS_WIDTH: int = 2400
    AI_ENHANCE_SECOND_PASS: bool = True
    AI_USE_ROW_CROPS: bool = True
    AI_SIGNATURE_INK_THRESHOLD: float = 0.02

    # Confidence threshold
    CONFIDENCE_THRESHOLD: float = 0.7

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
