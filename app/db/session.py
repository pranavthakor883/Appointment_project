"""Database connection. Moved from the old top-level database.py."""

import psycopg

from app.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

conn = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

print("Database Connected!")
