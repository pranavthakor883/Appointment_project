"""Provider business logic. Knows nothing about HTTP."""

import psycopg

from app.schemas.provider import ProviderCreate


def create_provider(conn: psycopg.Connection, provider: ProviderCreate) -> tuple:
    """Return (id, user_id, specialization, description, created_at)."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            """insert into providers(user_id, specialization, description) values(%s, %s, %s) returning id, user_id, specialization, description, created_at""",
            (provider.user_id, provider.specialization, provider.description)
        )

        new_provider = cursor.fetchone()
        conn.commit()

        return new_provider

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()


def list_providers(conn: psycopg.Connection) -> list[tuple]:
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select p.id,p.user_id,u.name,u.email,p.specialization,p.description,p.created_at
            from providers p
            join users u
            on p.user_id = u.id
            order by p.id
            '''
        )

        return cursor.fetchall()

    finally:
        cursor.close()


def get_provider(conn: psycopg.Connection, provider_id: int) -> tuple | None:
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select p.id,p.user_id,u.name,u.email,
                p.specialization,p.description,p.created_at
                from providers p
                join users u
            on p.user_id = u.id
            where p.id = %s
            ''',
            (provider_id,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()
