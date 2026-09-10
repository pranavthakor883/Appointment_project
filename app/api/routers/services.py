from fastapi import APIRouter,Depends, HTTPException

from app.api.deps import get_current_user,require_role
from app.db.session import conn
from app.schemas.service import ServiceCreate,ServiceUpdate
from app.services import services as services_service
from app.services import providers as providers_service

router = APIRouter()


@router.post("/services")
def create_service(service: ServiceCreate,current_user=Depends(require_role("provider"))):
    
    provider = providers_service.get_provider_by_user_id(conn,(current_user[0]))
    
    if provider is None or service.provider_id != provider[0]:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own availability"
        )

    try:
        new_service = services_service.create_service(conn, service)

    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

    return{
        "message":"Service Created Successfully",
        "service":{
            "id" : new_service[0],
            "provider_id":new_service[1],
            "name":new_service[2],
            "description":new_service[3],
            "duration_minutes":new_service[4],
            "price":new_service[5]
        }
    }


# Get services of a provider
@router.get("/providers/{provider_id}/services")
def get_provider_services(provider_id: int):

    services = services_service.list_provider_services(conn, provider_id)

    if not services:
        raise HTTPException(
            status_code=404,
            detail="Provider or services not found"
        )

    return {
        "services": [
            {
                "id": service[0],
                "name": service[1],
                "description": service[2],
                "duration_minutes": service[3],
                "price": service[4],
                "created_at": service[5]
            }
            for service in services
        ]
    }

#Update the services using the patch method
@router.patch("/services/{service_id}")
def update_service(
    service_id: int,
    service: ServiceUpdate,
    current_user=Depends(require_role("provider"))
):

    provider = providers_service.get_provider_by_user_id(conn, current_user[0])

    if provider is None:
        raise HTTPException(
            status_code=403,
            detail="You do not have a provider profile"
        )

    existing_service = services_service.get_service_by_id(conn, service_id)

    if existing_service is None:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    #existing_service[1] is provider_id
    if existing_service[1] != provider[0]:
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own services"
        )

    #an empty body would build "set  where id = %s" and fail in SQL
    if not service.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    try:
        updated_service = services_service.update_service(conn, service_id, service)

    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

    return {
        "message": "Service updated successfully",
        "service": {
            "id": updated_service[0],
            "provider_id": updated_service[1],
            "name": updated_service[2],
            "description": updated_service[3],
            "duration_minutes": updated_service[4],
            "price": updated_service[5]
        }
    }
