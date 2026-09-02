from fastapi import APIRouter, HTTPException

from app.db.session import conn
from app.schemas.user import UserCreate
from app.services import users as users_service

router = APIRouter()


@router.post("/users")
def create_user(user: UserCreate):

    try:
        new_user = users_service.create_user(conn, user)

    except Exception as e:
        raise HTTPException( status_code = 400, detail = str(e) )

    #you can give the orderno of columns according to returing column orderno
    return{
            "message":"User created succesfully" ,
            "user":{
                "id": new_user[0],
                "name": new_user[1],
                "email": new_user[2],
                "role": new_user[3],
            }
        }
