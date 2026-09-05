"""The only module that reads the environment."""

import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    """Read a variable that the application cannot run without.

    Raises at import time so a missing value stops the server on startup
    instead of surfacing as a 500 inside the first request that needs it.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is missing. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# No fallback for the secret: a default would silently sign real tokens with
# a value that is public in the source tree.
JWT_SECRET_KEY = _required("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
