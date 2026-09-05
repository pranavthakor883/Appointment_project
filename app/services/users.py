"""User business logic. Knows nothing about HTTP."""

import psycopg

from app.core.security import hash_password
from app.schemas.user import UserCreate


def create_user(conn: psycopg.Connection, user: UserCreate) -> tuple:
    """Insert a user and return the created row.

    Returns (id, name, email, role) — the RETURNING column order.
    """
    cursor = conn.cursor()

    try:
        password_hash = hash_password(user.password)
        cursor.execute(
            """insert into users (name,email,password_hash,role) values (%s,%s,%s,%s) RETURNING id, name, email, role""",
            (user.name, user.email, password_hash, user.role)
        )

        new_user = cursor.fetchone()
        conn.commit()

        return new_user

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()


def get_user_by_email(conn: psycopg.Connection, email: str) -> tuple | None:
    """Return (id, name, role, email, password_hash) or None."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            """select id, name, role, email, password_hash from users where email=%s""",
            (email,)
        )

        #fetch exist_user row in python using the fetchcone
        return cursor.fetchone()

    finally:
        cursor.close()


def get_user_by_id(conn: psycopg.Connection, user_id: int) -> tuple | None:
    """Return (id, name, role, email) or None.

    No password_hash here, unlike get_user_by_email. This row is what
    get_current_user hands to every protected endpoint, so the hash must not
    be in it — one stray `return current_user` would put it on the wire.
    """
    cursor = conn.cursor()

    try:
        cursor.execute(
            """select id, name, role, email from users where id=%s""",
            (user_id,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()
