import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Zango Adaptive Assessment Service"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://zango:zango@localhost:5432/zango_assessment",
        description="Async database connection string"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # recycle connections after 30 minutes
    DB_POOL_PRE_PING: bool = True  # test connection validity before issuing queries
    DB_ECHO: bool = False

    # Security & Resource Hardening
    MAX_PAYLOAD_SIZE_BYTES: int = 1_048_576  # 1MB limit on request payloads
    SIMULATION_BATCH_SIZE: int = 25  # batch chunk size for simulation runs
    EVALUATION_BATCH_SIZE: int = 50  # batch size for evaluation processing

    # Security & JWT
    JWT_PUBLIC_KEY_PATH: str = "./keys/public.pem"
    JWT_ISSUER: str = "http://localhost:8081"
    JWT_AUDIENCE: str = "zango"
    JWT_ALGORITHM: str = "RS256"

    # Eureka Service Discovery
    EUREKA_ENABLED: bool = True
    EUREKA_SERVER_URL: str = "http://root:toor123@discovery-service:8761/eureka/"
    EUREKA_APP_NAME: str = "ASSESSMENT-SERVICE"
    EUREKA_INSTANCE_HOST: str = "assessment-service"
    EUREKA_INSTANCE_PORT: int = 8000
    EUREKA_RENEWAL_INTERVAL_SECS: int = 30
    EUREKA_DURATION_SECS: int = 90

    # Assessment Engine Defaults
    PROFILE_CODE: str = "TECHNICAL_TALENT_V1"
    MIN_QUESTIONS: int = 10
    MAX_QUESTIONS: int = 20
    SESSION_TIMEOUT_SECONDS: int = 2700  # 45 minutes
    DEFAULT_MIN_AGE: int = 8
    DEFAULT_MAX_AGE: int = 18
    ALGORITHM_VERSION: str = "2.0.0-irt-mfi"
    QUESTION_BANK_VERSION: str = "1.0.0"
    RAPID_GUESS_THRESHOLD_MS: int = 1500

    # Selector Weights
    SELECTOR_WEIGHT_INFO: float = 0.35
    SELECTOR_WEIGHT_COVERAGE: float = 0.30
    SELECTOR_WEIGHT_DIFFICULTY_FIT: float = 0.25
    SELECTOR_WEIGHT_EXPOSURE_PENALTY: float = 0.10

    # Estimator Parameters
    INITIAL_PRIOR_ABILITY: float = 0.0
    INITIAL_PRIOR_UNCERTAINTY: float = 1.0
    MIN_UNCERTAINTY_THRESHOLD: float = 0.32
    SESSION_TIMEOUT_SECONDS: int = 1200  # 20 minutes per clinical fatigue threshold

settings = Settings()
