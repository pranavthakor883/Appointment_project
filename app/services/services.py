"""Service (what a provider sells) business logic. Knows nothing about HTTP."""

import psycopg

from app.schemas.service import ServiceCreate,ServiceUpdate


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


def get_service_by_id(conn: psycopg.Connection, service_id: int) -> tuple | None:
    """Return (id, provider_id, name, description, duration_minutes, price) or None.

    provider_id is at index 1 so the caller can check ownership before
    letting an update through.
    """
    cursor = conn.cursor()

    try:
        cursor.execute(
            '''
            select id, provider_id, name, description, duration_minutes, price
            from services
            where id = %s
            ''',
            (service_id,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()


def update_service(conn: psycopg.connection,service_id:int,service:ServiceUpdate) -> tuple | None:
    '''update a service  and return the updated row'''
    
    cursor = conn.cursor()
    
    try: 
        update_data = service.model_dump(exclude_unset=True) 
        
        if not update_data: 
            return None 
        
        fields = [] 
        values = []
          
        for field, value in update_data.items():
            fields.append(f"{field} = %s") 
            values.append(value) 
        
        values.append(service_id) 
        
        query = f""" 
            update services 
            set {", ".join(fields)} 
            where id = %s 
            returning id, provider_id, name, description, duration_minutes, price 
            """ 
            
        cursor.execute(query, values) 
            
        updated_service = cursor.fetchone() 
        
        if updated_service is None: 
            return None 
        
        conn.commit() 
        
        return updated_service 
    
    except Exception: 
        conn.rollback() 
        raise 
    
    finally: cursor.close()
    
    