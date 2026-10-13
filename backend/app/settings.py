from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parent
REVISION = "0008_outcomes"


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    hosts: tuple[str, ...] = ("127.0.0.1", "localhost")
    origins: tuple[str, ...] = ("http://127.0.0.1:8766", "http://localhost:8766")
    cookie_name: str = "rpa_foundation_session"
    cookie_secure: bool = False
    session_hours: int = 8

    def __post_init__(self):
        if self.database_url and not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("Stage 01 requires a PostgreSQL psycopg URL")
        if not self.cookie_secure and any(h not in ("127.0.0.1", "localhost") for h in self.hosts):
            raise ValueError("Insecure cookies are permitted only for loopback hosts")
        if "*" in self.hosts:
            raise ValueError("Wildcard hosts are not permitted")

    @classmethod
    def from_environment(cls):
        load_dotenv(BACKEND / ".env.foundation")
        load_dotenv(BACKEND / ".env")
        return cls(
            database_url=os.getenv("APP_DATABASE_URL"),
            hosts=tuple(os.getenv("APP_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")),
            origins=tuple(os.getenv("APP_ALLOWED_ORIGINS",
                                   "http://127.0.0.1:8766,http://localhost:8766").split(",")),
            cookie_secure=os.getenv("APP_COOKIE_SECURE", "false").lower() == "true",
        )
