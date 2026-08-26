"""Application configuration.

Every configurable value is read from an environment variable so that no secret
or environment specific value is hard coded in the source tree
(Coding Standards 3.1 and 3.6).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the JU_FIX monolithic application.

    Attributes:
        APP_NAME: Human readable application name used in the API metadata.
        ENVIRONMENT: Deployment environment name, for example ``development``.
        DATABASE_URL: SQLAlchemy connection string for the single relational database.
        JWT_SECRET_KEY: Secret used to sign JWT access tokens.
        JWT_ALGORITHM: Signing algorithm for JWT access tokens.
        ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of an issued access token.
        MAX_FAILED_LOGIN_ATTEMPTS: Failed logins allowed before a lock (FR-A6).
        ACCOUNT_LOCK_MINUTES: Duration of the automatic lock after too many failures.
        DEFAULT_SLOT_DURATION_MINUTES: Default appointment slot length (FR-J5).
        DEFAULT_DAILY_TOKEN_LIMIT: Tokens issued per doctor per day (FR-J5).
        CORS_ORIGINS: Comma separated list of origins allowed to call the API.
    """

    APP_NAME: str = "JU_FIX Medical Centre Automation System"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "sqlite:///./ju_fix.db"

    JWT_SECRET_KEY: str = "change-me-in-env-file"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    DEFAULT_SLOT_DURATION_MINUTES: int = 20
    DEFAULT_DAILY_TOKEN_LIMIT: int = 30

    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        """Return ``CORS_ORIGINS`` as a list of trimmed origin strings."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Caching keeps configuration parsing to a single pass per process and lets
    tests override the dependency cleanly.
    """
    return Settings()


settings = get_settings()
