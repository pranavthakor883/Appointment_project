"""Availability business logic. Knows nothing about HTTP."""

import psycopg

from app.schemas.availability import AvailabilityCreate,AvailabilityUpdate


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
        
def get_availability_by_id(conn:psycopg.Connection,availability_id:int) -> tuple | None :
    """Return (id, provider_id, day_of_week, start_time, end_time) or None."""
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select id,provider_id,day_of_week,start_time,end_time from availability
            where id = %s
            ''',
            (availability_id,)

        )
        
        return cursor.fetchone()
    
    finally:
        cursor.close()

def update_availability(conn:psycopg.Connection,availability_id:int,availability:AvailabilityUpdate) -> tuple | None:
    cursor = conn.cursor()
    
    try:
        update_data = availability.model_dump(exclude_unset=True)
        
        if not update_data:
            return None
        
        fields = []
        values = []
        
        for field,value in update_data.items():
            fields.append(f"{field} = %s")
            values.append(value)
        values.append(availability_id)
        
        query = f"""
            update availability
            set {",".join(fields)}
            where id = %s
            returning id,provider_id,day_of_week,start_time,end_time
        """

        cursor.execute(query,values)

        updated_availability = cursor.fetchone()

        if updated_availability is None:
            #the update ran, so the transaction must not be left open
            conn.rollback()
            return None

        conn.commit()

        return updated_availability
        
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()