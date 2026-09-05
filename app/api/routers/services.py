from fastapi import APIRouter,Depends, HTTPException

from app.api.deps import get_current_user,require_role
from app.db.session import conn
from app.schemas.service import ServiceCreate
from app.services import services as services_service

router = APIRouter()


@router.post("/services")
def create_service(service: ServiceCreate,current_user=Depends(require_role("provider"))):

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
