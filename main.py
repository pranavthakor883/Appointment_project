from fastapi import FastAPI,HTTPException
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
    
    
    try: 
        cursor.execute(
            """insert into users (name,email,password_hash,role) values (%s,%s,%s,%s) RETURNING id, name, email, role""",
            (user.name,user.email,user.password,user.role)
        )
        
        new_user = cursor.fetchone()
        conn.commit()
        
        return{
                "message":"User created succesfully" ,
                "user":{
                    "id": new_user[0],
                    "name": new_user[1],
                    "email": new_user[2],
                    "role": new_user[3],
                }
            }
    
    except Exception as e:
        
        cursor.rollback()
        raise HTTPException( status_code = 400, detail = str(e) )
    
    finally:
        cursor.close()
     
     
    

