from fastapi import APIRouter, HTTPException

from app.db.session import conn
from app.schemas.availability import AvailabilityCreate
from app.services import availability as availability_service

router = APIRouter()


@router.post("/availability")
def create_availability(availability: AvailabilityCreate):

    try:
        new_availability = availability_service.create_availability(conn, availability)

    except Exception as e:
        raise HTTPException(
        status_code=400,
        detail="Availability overlaps with existing availability"
        )

    return{
        "id":new_availability[0],
        "provider_id":new_availability[1],
        "day_of_week":new_availability[2],
        "start_time":new_availability[3],
        "end_time":new_availability[4]
    }


# Get availability of a provider
@router.get("/providers/{provider_id}/availability")
def get_provider_availability(provider_id: int):

    new_availabilities = availability_service.list_provider_availability(conn, provider_id)

    if not new_availabilities:
        raise HTTPException(status_code=404,detail="Availability not found")

    return[
        {
        "id":new_availability[0],
        "provider_id":new_availability[1],
        "day_of_week":new_availability[2],
        "start_time":new_availability[3],
        "end_time":new_availability[4]
        }
        for new_availability in new_availabilities
    ]
