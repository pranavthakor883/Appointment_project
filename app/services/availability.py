"""Availability business logic. Knows nothing about HTTP."""

import psycopg

from app.schemas.availability import AvailabilityCreate


def create_availability(conn: psycopg.Connection, availability: AvailabilityCreate) -> tuple:
    """Return (id, provider_id, day_of_week, start_time, end_time)."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            insert into availability(provider_id,day_of_week,start_time,end_time) values(%s,%s,%s,%s) returning id,provider_id,day_of_week,start_time,end_time
            ''',
            (availability.provider_id, availability.day_of_week, availability.start_time, availability.end_time)
        )

        new_availability = cursor.fetchone()
        conn.commit()

        return new_availability

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()


def list_provider_availability(conn: psycopg.Connection, provider_id: int) -> list[tuple]:
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select id,provider_id,day_of_week,start_time,end_time from availability where provider_id=%s
            order by day_of_week,start_time
            ''',
            (provider_id,)
        )

        return cursor.fetchall()

    finally:
        cursor.close()
