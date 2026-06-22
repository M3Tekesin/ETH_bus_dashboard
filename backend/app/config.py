import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load a local .env if present so secrets (auth hash, JWT key) stay out of code.
load_dotenv()


def _origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/telemetry",
        )
    )
    cors_origins: list[str] = field(default_factory=_origins)

    # Authentication. The password hash and JWT secret come from the
    # environment (.env locally, never committed). See .env.example.
    auth_username: str = field(
        default_factory=lambda: os.getenv("AUTH_USERNAME", "admin")
    )
    auth_password_hash: str = field(
        default_factory=lambda: os.getenv("AUTH_PASSWORD_HASH", "")
    )
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "")
    )
    jwt_ttl_hours: int = field(
        default_factory=lambda: int(os.getenv("JWT_TTL_HOURS", "12"))
    )


settings = Settings()
