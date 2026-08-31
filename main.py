from fastapi import FastAPI
from pydantic import BaseModel
from database import conn


app = FastAPI()


@app.get("/")
def home():
    return {"message":"Appointment api is running!"}


class UserCreate(BaseModel):
    name : str
    email : str
    password : str
    role : str = "customer"
    
@app.post("/users")
def create_user(user:UserCreate):
     
    cursor = conn.cursor()
     
    cursor.execute(
         """insert into users (name,email,password_hash,role) values (%s,%s,%s,%s)""",
         (user.name,user.email,user.password,user.role)
     )
     
    conn.commit()
     
    cursor.close()
     
    return{
            "message":"User created succesfully" ,
        }
     
     
    

