from fastapi import APIRouter,Depends, HTTPException

from app.api.deps import get_current_user,require_role
from app.db.session import conn
from app.schemas.availability import AvailabilityCreate,AvailabilityUpdate
from app.services import availability as availability_service
from app.services import providers as providers_service

router = APIRouter()


@router.post("/availability")
def create_availability(availability: AvailabilityCreate,current_user=Depends(require_role("provider"))):
    
    #current_user[0] is users.id, availability.provider_id is providers.id
    provider = providers_service.get_provider_by_user_id(conn, current_user[0])

    if provider is None or availability.provider_id != provider[0]:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own availability"
        )

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
    
#Update the availability
@router.patch("/availability/{availability_id}")
def update_availability(
    availability_id:int,
    availability:AvailabilityUpdate,
    current_user = Depends(require_role("provider"))
):
    provider = providers_service.get_provider_by_user_id(conn,current_user[0])

    if provider is None:
        raise HTTPException(
            status_code=403,
            detail="You do not have provider profile"
        )

    existing_availability = availability_service.get_availability_by_id(conn, availability_id)

    if existing_availability is None:
        raise HTTPException(
            status_code=404,
            detail="Availability not found"
        )

    #existing_availability[1] is provider_id
    if existing_availability[1] != provider[0]:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own availability"
        )

    #an empty body would build "set  where id = %s" and fail in SQL
    if not availability.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    try:
        updated_availability = availability_service.update_availability(
            conn, availability_id, availability
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Availability overlaps with existing availability"
        )

    return{
        "message":"Availability updated successfully",
        "availability":{
            "id":updated_availability[0],
            "provider_id":updated_availability[1],
            "day_of_week":updated_availability[2],
            "start_time":updated_availability[3],
            "end_time":updated_availability[4]
        }
    }
    
