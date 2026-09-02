from fastapi import APIRouter, HTTPException

from app.db.session import conn
from app.schemas.provider import ProviderCreate
from app.services import providers as providers_service

router = APIRouter()


@router.post("/providers")
def create_provider(provider: ProviderCreate):

    try:
        new_provider = providers_service.create_provider(conn, provider)

    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

    return {
        "message": "Provider created successfully",
        "provider": {
            "id": new_provider[0],
            "user_id": new_provider[1],
            "specialization": new_provider[2],
            "description": new_provider[3],
            "created_at": new_provider[4]
        }
    }


@router.get("/providers")
def get_providers():

    providers = providers_service.list_providers(conn)

    return[
        {
            "id": provider[0],
            "user_id": provider[1],
            "name": provider[2],
            "email": provider[3],
            "specialization": provider[4],
            "description": provider[5],
            "created_at": provider[6]
        }
        for provider in providers
    ]


@router.get("/providers/{provider_id}")
def get_provider(provider_id: int):

    provider = providers_service.get_provider(conn, provider_id)

    if provider is None:
        raise HTTPException(status_code=404,detail="Provider not found")

    return {
        "id" : provider[0],
        "user_id":provider[1],
        "name":provider[2],
        "email":provider[3],
        "specialization":provider[4],
        "description":provider[5],
        "created_at":provider[6]
    }
