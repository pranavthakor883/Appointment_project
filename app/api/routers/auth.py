from fastapi import APIRouter, HTTPException

from app.core.security import verify_password,create_access_token
from app.db.session import conn
from app.schemas.user import UserLogin
from app.services import users as users_service

router = APIRouter()


@router.post("/auth/login")
def login(user: UserLogin):

    exist_user = users_service.get_user_by_email(conn, user.email)
    
    if exist_user is None:
        raise HTTPException(status_code=401,detail="Invalid email or password")

    #but you also know what you gave the order in select query
    password_hash = exist_user[4]

    if not verify_password(user.password, password_hash):
        raise HTTPException(status_code=401,detail="Invalid email or password")

    #exist_user is the db row: (id, name, role, email, password_hash)
    access_token = create_access_token( user_id=exist_user[0], role=exist_user[2] )
    #in you must the same order which you gave in the while select query
    return{
        "message":"Login successfully",
        "access_token": access_token, 
        "token_type": "bearer",
        "user":{
            "id": exist_user[0],
            "name": exist_user[1],
            "role": exist_user[2],
            "email":exist_user[3],
        }
    }
