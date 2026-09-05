"""Service (what a provider sells) business logic. Knows nothing about HTTP."""

import psycopg

from app.schemas.service import ServiceCreate


def create_service(conn: psycopg.Connection, service: ServiceCreate) -> tuple:
    """Return (id, provider_id, name, description, duration_minutes, price)."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''insert into services(provider_id,name,description,duration_minutes,price) values(%s,%s,%s,%s,%s) returning id,provider_id,name,description,duration_minutes,price''',
            (service.provider_id, service.name, service.description, service.duration_minutes, service.price)
        )

        new_service = cursor.fetchone()

        conn.commit()

        return new_service

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()


def list_provider_services(conn: psycopg.Connection, provider_id: int) -> list[tuple]:
    """Return (id, name, description, duration_minutes, price, created_at) rows."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select s.id, s.name, s.description,
                   s.duration_minutes, s.price, s.created_at
            from services s
            where s.provider_id = %s
            order by s.id
            ''',
            (provider_id,)
        )

        return cursor.fetchall()

    finally:
        cursor.close()
